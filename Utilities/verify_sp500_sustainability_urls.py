#!/usr/bin/env python3
"""
S&P 500 Sustainability Report URL Verification Script

This script verifies that sustainability report URLs work for all S&P 500 companies
and discovers new URL patterns for companies not yet covered.

Usage:
    python verify_sp500_sustainability_urls.py [--top N] [--year YEAR] [--output FILE]
"""

import requests
import pandas as pd
import json
import time
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Known URL patterns from SustainabilityReportDownloader
KNOWN_REPORT_URL_PATTERNS = {
    'NVDA': [
        'https://images.nvidia.com/aem-dam/Solutions/documents/NVIDIA-Sustainability-Report-Fiscal-Year-{year}.pdf',
        'https://images.nvidia.com/aem-dam/Solutions/documents/FY{year}-NVIDIA-Corporate-Responsibility-Report.pdf',
    ],
    'GOOG': [
        'https://www.gstatic.com/gumdrop/sustainability/google-{year}-environmental-report.pdf',
        'https://www.gstatic.com/gumdrop/sustainability/google-{year}-supplier-responsibility-report.pdf',
    ],
    'GOOGL': [
        'https://www.gstatic.com/gumdrop/sustainability/google-{year}-environmental-report.pdf',
        'https://www.gstatic.com/gumdrop/sustainability/google-{year}-supplier-responsibility-report.pdf',
    ],
    'AMZN': [
        'https://sustainability.aboutamazon.com/{year}-amazon-sustainability-report.pdf',
        'https://sustainability.aboutamazon.com/{year}-sustainability-executive-summary.pdf',
    ],
    'MSFT': [
        'https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RE5b38N',
    ],
    'AAPL': [
        'https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_{year}.pdf',
    ],
    'META': [
        'https://sustainability.fb.com/wp-content/uploads/{year}/07/Meta-{year}-Sustainability-Report.pdf',
    ],
    'TSLA': [
        'https://www.tesla.com/ns_videos/Tesla-Impact-Report-{year}.pdf',
    ],
    'JPM': [
        'https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/documents/{year}-esg-report.pdf',
    ],
    'V': [
        'https://usa.visa.com/content/dam/VCOM/regional/na/us/about-visa/documents/visa-{year}-esg-report.pdf',
    ],
    'MA': [
        'https://www.mastercard.com/content/dam/public/mastercardcom/na/global-site/documents/mastercard-{year}-sustainability-report.pdf',
    ],
    'BAC': [
        'https://about.bankofamerica.com/content/dam/about/report-center/{year}/Bank-of-America-{year}-Annual-Report.pdf',
    ],
    'WFC': [
        'https://www08.wellsfargomedia.com/assets/pdf/about/corporate-responsibility/environmental-social-governance-report-{year}.pdf',
    ],
    'GS': [
        'https://www.goldmansachs.com/a/pgs/sustainability-report-{year}.pdf',
    ],
    'XOM': [
        'https://corporate.exxonmobil.com/-/media/Global/Files/sustainability-report/publication/{year}-sustainability-report.pdf',
    ],
    'CVX': [
        'https://www.chevron.com/-/media/chevron/sustainability/documents/{year}-corporate-sustainability-report.pdf',
    ],
}

# Custom sustainability page URLs
CUSTOM_SUSTAINABILITY_PAGES = {
    'NVDA': 'https://www.nvidia.com/en-us/csr/',
    'MSFT': 'https://www.microsoft.com/en-us/corporate-responsibility/reports-hub',
    'AAPL': 'https://www.apple.com/environment/',
    'GOOGL': 'https://sustainability.google/reports/',
    'GOOG': 'https://sustainability.google/reports/',
    'AMZN': 'https://sustainability.aboutamazon.com/reporting',
    'META': 'https://sustainability.fb.com/reports/',
    'TSLA': 'https://www.tesla.com/impact',
    'JPM': 'https://www.jpmorganchase.com/about/governance/esg',
    'V': 'https://usa.visa.com/about-visa/esg.html',
    'MA': 'https://www.mastercard.us/en-us/vision/corp-responsibility.html',
    'BAC': 'https://about.bankofamerica.com/en/making-an-impact/esg-reporting',
    'WFC': 'https://www.wellsfargo.com/about/corporate-responsibility/',
    'GS': 'https://www.goldmansachs.com/our-firm/sustainability/',
    'XOM': 'https://corporate.exxonmobil.com/sustainability',
    'CVX': 'https://www.chevron.com/sustainability',
}

# Common sustainability URL patterns to try
COMMON_URL_PATTERNS = [
    # Generic patterns with company name placeholders
    '/sustainability',
    '/sustainability-report',
    '/sustainability/reports',
    '/esg',
    '/esg-report',
    '/esg/reports',
    '/corporate-responsibility',
    '/corporate-responsibility/reports',
    '/impact',
    '/impact-report',
    '/our-impact',
    '/environment',
    '/csr',
    '/governance/esg',
    '/about/sustainability',
    '/about/esg',
    '/investors/esg',
    '/responsibility',
]


class SP500SustainabilityVerifier:
    """Verify sustainability report URLs for S&P 500 companies."""
    
    def __init__(self, delay_seconds: float = 0.5):
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.results = []
        
    def load_sp500_companies(self, csv_path: str = None) -> pd.DataFrame:
        """Load S&P 500 companies from CSV."""
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / 'Clients' / 'sp500_market_cap_ranked.csv'
        
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} companies from {csv_path}")
        return df
    
    def check_url_exists(self, url: str) -> Tuple[bool, int, str]:
        """
        Check if a URL exists and returns a PDF.
        
        Returns:
            Tuple of (exists, status_code, content_type)
        """
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            
            # For some servers, HEAD doesn't work, try GET with stream
            if response.status_code == 405 or response.status_code == 403:
                response = self.session.get(url, timeout=10, allow_redirects=True, stream=True)
                content_type = response.headers.get('content-type', '').lower()
                response.close()
            
            is_pdf = 'pdf' in content_type or url.lower().endswith('.pdf')
            return response.status_code == 200 and is_pdf, response.status_code, content_type
            
        except requests.RequestException as e:
            return False, 0, str(e)
    
    def find_sustainability_page(self, company_name: str, website: str, symbol: str) -> Optional[str]:
        """
        Try to find the sustainability page for a company.
        
        Returns:
            URL of sustainability page if found, None otherwise
        """
        if not website:
            return None
            
        if not website.startswith('http'):
            website = f'https://{website}'
        
        # First check if we have a custom page
        if symbol in CUSTOM_SUSTAINABILITY_PAGES:
            custom_url = CUSTOM_SUSTAINABILITY_PAGES[symbol]
            try:
                response = self.session.head(custom_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return custom_url
            except:
                pass
        
        # Try common patterns
        for path in COMMON_URL_PATTERNS:
            url = urljoin(website, path)
            try:
                response = self.session.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except:
                continue
            time.sleep(0.2)
        
        return None
    
    def extract_pdfs_from_page(self, url: str) -> List[str]:
        """Extract PDF links from a sustainability page."""
        pdf_links = []
        
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return pdf_links
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check if it's a PDF link
                if '.pdf' in href.lower():
                    # Check for sustainability keywords
                    text = link.get_text().lower()
                    keywords = ['sustainability', 'esg', 'environmental', 'impact', 
                               'responsibility', 'climate', 'carbon', 'annual']
                    
                    if any(kw in href.lower() or kw in text for kw in keywords):
                        full_url = urljoin(url, href)
                        pdf_links.append(full_url)
            
            return list(set(pdf_links))
            
        except Exception as e:
            logger.debug(f"Error extracting PDFs from {url}: {e}")
            return pdf_links
    
    def verify_known_patterns(self, symbol: str, year: int) -> Dict:
        """Verify known URL patterns for a company."""
        result = {
            'symbol': symbol,
            'year': year,
            'known_patterns': [],
            'working_urls': [],
            'failed_urls': []
        }
        
        if symbol not in KNOWN_REPORT_URL_PATTERNS:
            return result
        
        patterns = KNOWN_REPORT_URL_PATTERNS[symbol]
        result['known_patterns'] = patterns
        
        for pattern in patterns:
            url = pattern.replace('{year}', str(year))
            exists, status, content_type = self.check_url_exists(url)
            
            if exists:
                result['working_urls'].append(url)
                logger.info(f"✓ {symbol}: {url}")
            else:
                result['failed_urls'].append({
                    'url': url,
                    'status': status,
                    'content_type': content_type
                })
                logger.debug(f"✗ {symbol}: {url} (status: {status})")
            
            time.sleep(self.delay_seconds)
        
        return result
    
    def discover_company_reports(self, symbol: str, company_name: str, 
                                  website: str, year: int) -> Dict:
        """
        Discover sustainability reports for a company.
        
        This tries multiple approaches:
        1. Check known URL patterns
        2. Find sustainability page and extract PDFs
        3. Try common URL patterns
        """
        result = {
            'symbol': symbol,
            'company': company_name,
            'website': website,
            'year': year,
            'has_known_patterns': symbol in KNOWN_REPORT_URL_PATTERNS,
            'sustainability_page': None,
            'pdf_urls_found': [],
            'suggested_patterns': [],
            'status': 'unknown'
        }
        
        # 1. Check known patterns
        if symbol in KNOWN_REPORT_URL_PATTERNS:
            known_result = self.verify_known_patterns(symbol, year)
            if known_result['working_urls']:
                result['pdf_urls_found'].extend(known_result['working_urls'])
                result['status'] = 'known_patterns_work'
        
        # 2. Find sustainability page
        sus_page = self.find_sustainability_page(company_name, website, symbol)
        if sus_page:
            result['sustainability_page'] = sus_page
            
            # Extract PDFs from the page
            pdfs = self.extract_pdfs_from_page(sus_page)
            
            # Filter by year
            year_pdfs = [p for p in pdfs if str(year) in p]
            result['pdf_urls_found'].extend(year_pdfs)
            
            if year_pdfs:
                result['status'] = 'pdfs_found_on_page'
                
                # Suggest URL patterns based on found PDFs
                for pdf in year_pdfs:
                    pattern = pdf.replace(str(year), '{year}')
                    if pattern not in result['suggested_patterns']:
                        result['suggested_patterns'].append(pattern)
        
        # Deduplicate
        result['pdf_urls_found'] = list(set(result['pdf_urls_found']))
        
        if not result['pdf_urls_found']:
            result['status'] = 'no_reports_found'
        
        return result
    
    def verify_all_companies(self, df: pd.DataFrame, year: int = 2024, 
                             limit: Optional[int] = None) -> List[Dict]:
        """Verify all companies in the DataFrame."""
        results = []
        companies = df.head(limit) if limit else df
        total = len(companies)
        
        logger.info(f"Verifying {total} companies for year {year}")
        
        for idx, row in companies.iterrows():
            symbol = row['symbol']
            company = row['company']
            
            # Try to get website (you may need to add this to the CSV or derive it)
            website = self._get_company_website(symbol, company)
            
            logger.info(f"[{idx+1}/{total}] Processing {company} ({symbol})")
            
            result = self.discover_company_reports(symbol, company, website, year)
            results.append(result)
            
            time.sleep(self.delay_seconds)
        
        return results
    
    def _get_company_website(self, symbol: str, company: str) -> str:
        """Derive company website from symbol or name."""
        # Common mappings
        website_map = {
            'NVDA': 'https://www.nvidia.com',
            'AAPL': 'https://www.apple.com',
            'GOOG': 'https://www.google.com',
            'GOOGL': 'https://www.google.com',
            'MSFT': 'https://www.microsoft.com',
            'AMZN': 'https://www.amazon.com',
            'META': 'https://www.meta.com',
            'TSLA': 'https://www.tesla.com',
            'JPM': 'https://www.jpmorganchase.com',
            'V': 'https://usa.visa.com',
            'MA': 'https://www.mastercard.com',
            'BAC': 'https://www.bankofamerica.com',
            'WFC': 'https://www.wellsfargo.com',
            'GS': 'https://www.goldmansachs.com',
            'MS': 'https://www.morganstanley.com',
            'C': 'https://www.citigroup.com',
            'LLY': 'https://www.lilly.com',
            'JNJ': 'https://www.jnj.com',
            'UNH': 'https://www.unitedhealthgroup.com',
            'ABBV': 'https://www.abbvie.com',
            'MRK': 'https://www.merck.com',
            'PFE': 'https://www.pfizer.com',
            'TMO': 'https://www.thermofisher.com',
            'ABT': 'https://www.abbott.com',
            'AMGN': 'https://www.amgen.com',
            'XOM': 'https://corporate.exxonmobil.com',
            'CVX': 'https://www.chevron.com',
            'COP': 'https://www.conocophillips.com',
            'COST': 'https://www.costco.com',
            'HD': 'https://www.homedepot.com',
            'WMT': 'https://www.walmart.com',
            'PG': 'https://us.pg.com',
            'KO': 'https://www.coca-colacompany.com',
            'PEP': 'https://www.pepsico.com',
            'MCD': 'https://corporate.mcdonalds.com',
            'DIS': 'https://thewaltdisneycompany.com',
            'NFLX': 'https://www.netflix.com',
            'ORCL': 'https://www.oracle.com',
            'IBM': 'https://www.ibm.com',
            'CSCO': 'https://www.cisco.com',
            'CRM': 'https://www.salesforce.com',
            'INTC': 'https://www.intel.com',
            'AMD': 'https://www.amd.com',
            'T': 'https://www.att.com',
            'VZ': 'https://www.verizon.com',
            'CAT': 'https://www.caterpillar.com',
            'BA': 'https://www.boeing.com',
            'GE': 'https://www.ge.com',
            'RTX': 'https://www.rtx.com',
            'HON': 'https://www.honeywell.com',
            'LMT': 'https://www.lockheedmartin.com',
            'UPS': 'https://www.ups.com',
            'FDX': 'https://www.fedex.com',
            'NEE': 'https://www.nexteraenergy.com',
            'DUK': 'https://www.duke-energy.com',
            'SO': 'https://www.southerncompany.com',
        }
        
        if symbol in website_map:
            return website_map[symbol]
        
        # Try to derive from company name
        clean_name = company.lower().replace(' ', '').replace(',', '').replace('.', '')
        clean_name = re.sub(r'(inc|corp|corporation|company|co|ltd|llc)$', '', clean_name)
        
        return f'https://www.{clean_name[:20]}.com'
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Generate a summary report from verification results."""
        total = len(results)
        
        with_patterns = [r for r in results if r['has_known_patterns']]
        working_patterns = [r for r in results if r['status'] == 'known_patterns_work']
        pdfs_found = [r for r in results if r['pdf_urls_found']]
        no_reports = [r for r in results if r['status'] == 'no_reports_found']
        
        report = {
            'summary': {
                'total_companies': total,
                'companies_with_known_patterns': len(with_patterns),
                'companies_with_working_patterns': len(working_patterns),
                'companies_with_pdfs_found': len(pdfs_found),
                'companies_without_reports': len(no_reports),
                'coverage_percentage': round(len(pdfs_found) / total * 100, 2) if total > 0 else 0
            },
            'companies_needing_patterns': [],
            'suggested_new_patterns': {},
            'all_results': results
        }
        
        # Find companies that need URL patterns
        for r in results:
            if not r['has_known_patterns'] and r['pdf_urls_found']:
                report['companies_needing_patterns'].append({
                    'symbol': r['symbol'],
                    'company': r['company'],
                    'found_pdfs': r['pdf_urls_found'],
                    'suggested_patterns': r['suggested_patterns']
                })
                
                if r['suggested_patterns']:
                    report['suggested_new_patterns'][r['symbol']] = r['suggested_patterns']
        
        return report
    
    def save_results(self, results: List[Dict], output_path: str):
        """Save results to JSON file."""
        report = self.generate_report(results)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        
        # Also save a summary CSV
        csv_path = output_path.replace('.json', '_summary.csv')
        summary_data = []
        for r in results:
            summary_data.append({
                'symbol': r['symbol'],
                'company': r['company'],
                'has_known_patterns': r['has_known_patterns'],
                'status': r['status'],
                'pdfs_found': len(r['pdf_urls_found']),
                'sustainability_page': r.get('sustainability_page', ''),
            })
        
        pd.DataFrame(summary_data).to_csv(csv_path, index=False)
        logger.info(f"Summary CSV saved to {csv_path}")
        
        return report
    
    def generate_code_suggestions(self, report: Dict) -> str:
        """Generate Python code for suggested URL patterns."""
        code = "# Suggested additions to KNOWN_REPORT_URL_PATTERNS\n\n"
        
        for symbol, patterns in report['suggested_new_patterns'].items():
            code += f"'{symbol}': [\n"
            for p in patterns:
                code += f"    '{p}',\n"
            code += "],\n"
        
        return code


def main():
    parser = argparse.ArgumentParser(description='Verify S&P 500 sustainability report URLs')
    parser.add_argument('--top', type=int, default=None, help='Number of top companies to verify')
    parser.add_argument('--year', type=int, default=2024, help='Year to verify reports for')
    parser.add_argument('--output', type=str, default='sustainability_verification_results.json',
                        help='Output file path')
    parser.add_argument('--csv', type=str, default=None, help='Path to S&P 500 CSV file')
    
    args = parser.parse_args()
    
    verifier = SP500SustainabilityVerifier(delay_seconds=0.5)
    
    # Load companies
    df = verifier.load_sp500_companies(args.csv)
    
    # Verify
    results = verifier.verify_all_companies(df, year=args.year, limit=args.top)
    
    # Save results
    report = verifier.save_results(results, args.output)
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Total companies verified: {report['summary']['total_companies']}")
    print(f"Companies with known patterns: {report['summary']['companies_with_known_patterns']}")
    print(f"Companies with working patterns: {report['summary']['companies_with_working_patterns']}")
    print(f"Companies with PDFs found: {report['summary']['companies_with_pdfs_found']}")
    print(f"Companies without reports: {report['summary']['companies_without_reports']}")
    print(f"Coverage: {report['summary']['coverage_percentage']}%")
    print("="*60)
    
    if report['suggested_new_patterns']:
        print("\nSuggested new URL patterns to add:")
        print(verifier.generate_code_suggestions(report))


if __name__ == '__main__':
    main()
