"""
Sustainability Report Downloader for S&P 500 Companies

This module downloads sustainability/ESG reports from S&P 500 company websites.
It searches for common sustainability report patterns and downloads PDF files.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SustainabilityReportDownloader:
    """
    Downloads sustainability reports for S&P 500 companies.

    Features:
    - Loads S&P 500 company list
    - Searches company websites for sustainability reports
    - Downloads PDF reports with metadata
    - Tracks download progress and errors
    """

    # Common keywords for sustainability reports
    SUSTAINABILITY_KEYWORDS = [
        'sustainability',
        'esg',
        'corporate-responsibility',
        'environmental',
        'social-responsibility',
        'citizenship',
        'impact-report',
        'annual-report',
        'csr'
    ]

    # Common file patterns
    REPORT_PATTERNS = [
        r'sustainability.*report',
        r'esg.*report',
        r'corporate.*responsibility',
        r'environmental.*social.*governance',
        r'impact.*report',
        r'csr.*report'
    ]

    def __init__(self, download_dir: str = './sustainability_reports',
                 delay_seconds: float = 2.0):
        """
        Initialize the downloader.

        Args:
            download_dir: Directory to save downloaded reports
            delay_seconds: Delay between requests to be respectful to servers
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds

        # Track progress
        self.downloaded_reports = []
        self.failed_downloads = []

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AviskResearchBot/1.0; +https://avisk.ai)'
        })

    def load_sp500_companies(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load S&P 500 company list.

        Args:
            csv_path: Path to CSV file with company data. If None, fetches from Wikipedia.

        Returns:
            DataFrame with columns: Symbol, Company, Website
        """
        if csv_path and os.path.exists(csv_path):
            logger.info(f"Loading companies from {csv_path}")
            return pd.read_csv(csv_path)

        # Fetch from Wikipedia
        logger.info("Fetching S&P 500 list from Wikipedia")
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            tables = pd.read_html(url)
            df = tables[0]

            # Rename columns for consistency
            df = df.rename(columns={
                'Symbol': 'Symbol',
                'Security': 'Company',
                'GICS Sector': 'Sector'
            })

            # Save for future use
            cache_file = self.download_dir / 'sp500_companies.csv'
            df.to_csv(cache_file, index=False)
            logger.info(f"Saved company list to {cache_file}")

            return df

        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            raise

    def search_company_website(self, company_name: str,
                               base_url: str) -> List[str]:
        """
        Search company website for sustainability report links.

        Args:
            company_name: Name of the company
            base_url: Base URL of company website

        Returns:
            List of potential report URLs
        """
        potential_urls = []

        try:
            # Try common sustainability page patterns
            search_paths = [
                '/sustainability',
                '/esg',
                '/corporate-responsibility',
                '/about/sustainability',
                '/investors/esg',
                '/responsibility',
                '/impact'
            ]

            for path in search_paths:
                url = urljoin(base_url, path)
                try:
                    response = self.session.get(
                        url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        logger.info(f"Found sustainability page: {url}")
                        # Parse page for PDF links
                        soup = BeautifulSoup(response.content, 'html.parser')
                        pdf_links = self._extract_pdf_links(soup, url)
                        potential_urls.extend(pdf_links)

                except requests.RequestException as e:
                    logger.debug(f"Path not found: {url}")
                    continue

                # Be respectful - add delay
                time.sleep(self.delay_seconds)

        except Exception as e:
            logger.error(f"Error searching {company_name} website: {e}")

        return list(set(potential_urls))  # Remove duplicates

    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract PDF links from HTML that match sustainability patterns.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of PDF URLs
        """
        pdf_links = []

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().lower()

            # Check if it's a PDF
            if href.lower().endswith('.pdf'):
                # Check if it matches sustainability patterns
                full_url = urljoin(base_url, href)

                # Check both URL and link text for keywords
                combined_text = f"{href} {link_text}".lower()

                for pattern in self.REPORT_PATTERNS:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        pdf_links.append(full_url)
                        logger.debug(f"Found potential report: {full_url}")
                        break

        return pdf_links

    def download_report(self, url: str, company_symbol: str,
                        year: Optional[int] = None) -> Optional[str]:
        """
        Download a report PDF.

        Args:
            url: URL of the PDF
            company_symbol: Stock symbol of the company
            year: Year of the report (optional)

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Determine filename
            if year:
                filename = f"{company_symbol}_{year}_sustainability_report.pdf"
            else:
                # Extract year from URL if possible
                year_match = re.search(r'20\d{2}', url)
                if year_match:
                    year = year_match.group()
                    filename = f"{company_symbol}_{year}_sustainability_report.pdf"
                else:
                    filename = f"{company_symbol}_{datetime.now().year}_sustainability_report.pdf"

            # Save file
            company_dir = self.download_dir / company_symbol
            company_dir.mkdir(exist_ok=True)
            filepath = company_dir / filename

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded: {filepath}")

            # Track success
            self.downloaded_reports.append({
                'symbol': company_symbol,
                'url': url,
                'filepath': str(filepath),
                'download_date': datetime.now().isoformat(),
                'file_size': len(response.content)
            })

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            self.failed_downloads.append({
                'symbol': company_symbol,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return None

    def process_company(self, symbol: str, company_name: str,
                        website: Optional[str] = None) -> Dict:
        """
        Process a single company - search and download reports.

        Args:
            symbol: Stock symbol
            company_name: Company name
            website: Company website URL

        Returns:
            Dictionary with processing results
        """
        result = {
            'symbol': symbol,
            'company': company_name,
            'website': website,
            'reports_found': 0,
            'reports_downloaded': 0,
            'status': 'pending'
        }

        if not website:
            result['status'] = 'no_website'
            logger.warning(f"No website for {company_name} ({symbol})")
            return result

        try:
            # Normalize website URL
            if not website.startswith('http'):
                website = f'https://{website}'

            # Search for reports
            logger.info(f"Processing {company_name} ({symbol})")
            report_urls = self.search_company_website(company_name, website)
            result['reports_found'] = len(report_urls)

            # Download reports
            downloaded_count = 0
            for url in report_urls:
                filepath = self.download_report(url, symbol)
                if filepath:
                    downloaded_count += 1
                time.sleep(self.delay_seconds)

            result['reports_downloaded'] = downloaded_count
            result['status'] = 'completed'

        except Exception as e:
            logger.error(f"Error processing {company_name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def download_all_reports(self, companies_df: pd.DataFrame,
                             limit: Optional[int] = None) -> pd.DataFrame:
        """
        Download sustainability reports for all companies.

        Args:
            companies_df: DataFrame with company information
            limit: Maximum number of companies to process (for testing)

        Returns:
            DataFrame with processing results
        """
        results = []

        # Get required columns
        required_cols = ['Symbol', 'Company']
        if not all(col in companies_df.columns for col in required_cols):
            raise ValueError(f"DataFrame must have columns: {required_cols}")

        # Process companies
        companies = companies_df.head(limit) if limit else companies_df
        total = len(companies)

        logger.info(f"Starting download for {total} companies")

        for idx, row in companies.iterrows():
            symbol = row['Symbol']
            company = row['Company']
            website = row.get('Website', row.get('website', None))

            logger.info(f"Progress: {idx + 1}/{total} - {company}")

            result = self.process_company(symbol, company, website)
            results.append(result)

            # Save progress periodically
            if (idx + 1) % 10 == 0:
                self._save_progress(results)

        # Final save
        results_df = pd.DataFrame(results)
        self._save_progress(results)
        self._save_metadata()

        logger.info(
            f"Completed! Downloaded {len(self.downloaded_reports)} reports")
        return results_df

    def _save_progress(self, results: List[Dict]):
        """Save download progress to CSV."""
        progress_file = self.download_dir / 'download_progress.csv'
        pd.DataFrame(results).to_csv(progress_file, index=False)
        logger.debug(f"Saved progress to {progress_file}")

    def _save_metadata(self):
        """Save download metadata."""
        # Save successful downloads
        if self.downloaded_reports:
            downloads_file = self.download_dir / 'downloaded_reports.csv'
            pd.DataFrame(self.downloaded_reports).to_csv(
                downloads_file, index=False)
            logger.info(
                f"Saved {len(self.downloaded_reports)} download records")

        # Save failures
        if self.failed_downloads:
            failures_file = self.download_dir / 'failed_downloads.csv'
            pd.DataFrame(self.failed_downloads).to_csv(
                failures_file, index=False)
            logger.info(f"Saved {len(self.failed_downloads)} failure records")


def main():
    """Example usage of the downloader."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download sustainability reports for S&P 500 companies'
    )
    parser.add_argument(
        '--output-dir',
        default='./sustainability_reports',
        help='Directory to save reports'
    )
    parser.add_argument(
        '--companies-csv',
        help='CSV file with company data (optional)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of companies to process (for testing)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds'
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = SustainabilityReportDownloader(
        download_dir=args.output_dir,
        delay_seconds=args.delay
    )

    # Load companies
    companies_df = downloader.load_sp500_companies(args.companies_csv)

    # Download reports
    results_df = downloader.download_all_reports(
        companies_df, limit=args.limit)

    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total companies processed: {len(results_df)}")
    print(f"Reports found: {results_df['reports_found'].sum()}")
    print(f"Reports downloaded: {results_df['reports_downloaded'].sum()}")
    print(f"Failed: {len(downloader.failed_downloads)}")
    print(f"\nResults saved to: {args.output_dir}")
    print("="*60)


if __name__ == '__main__':
    main()
