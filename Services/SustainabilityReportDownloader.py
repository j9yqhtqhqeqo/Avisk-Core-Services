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
from io import StringIO, BytesIO
import logging
from typing import List, Dict, Optional, Tuple

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    from Utilities.Lookups import DB_Connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

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

    # Common file patterns - expanded to catch more variations
    REPORT_PATTERNS = [
        r'sustainability.*report',
        r'sustainability',
        r'esg.*report',
        r'esg',
        r'corporate.*responsibility',
        r'environmental.*social.*governance',
        r'environmental.*progress.*report',
        r'environmental.*responsibility',
        r'environmental.*report',
        r'impact.*report',
        r'csr.*report',
        r'climate.*report',
        r'carbon.*report',
        r'progress.*report',
        r'responsibility.*report',
    ]

    # Known company website mappings (symbol -> domain)
    COMPANY_WEBSITES = {
        'AAPL': 'apple.com',
        'MSFT': 'microsoft.com',
        'GOOGL': 'google.com',
        'GOOG': 'google.com',
        'AMZN': 'amazon.com',
        'META': 'meta.com',
        'NVDA': 'nvidia.com',
        'TSLA': 'tesla.com',
        'JPM': 'jpmorganchase.com',
        'V': 'visa.com',
        'JNJ': 'jnj.com',
        'WMT': 'walmart.com',
        'MA': 'mastercard.com',
        'PG': 'pg.com',
        'XOM': 'exxonmobil.com',
        'UNH': 'unitedhealthgroup.com',
        'HD': 'homedepot.com',
        'CVX': 'chevron.com',
        'KO': 'coca-colacompany.com',
        'PFE': 'pfizer.com',
        'ABBV': 'abbvie.com',
        'MRK': 'merck.com',
        'COST': 'costco.com',
        'PEP': 'pepsico.com',
        'TMO': 'thermofisher.com',
        'AVGO': 'broadcom.com',
        'MCD': 'mcdonalds.com',
        'CSCO': 'cisco.com',
        'ABT': 'abbott.com',
        'ACN': 'accenture.com',
        'WFC': 'wellsfargo.com',
        'CRM': 'salesforce.com',
        'DHR': 'danaher.com',
        'BAC': 'bankofamerica.com',
        'LIN': 'linde.com',
        'AMD': 'amd.com',
        'INTC': 'intel.com',
        'TXN': 'ti.com',
        'NKE': 'nike.com',
        'ORCL': 'oracle.com',
        'UPS': 'ups.com',
        'BMY': 'bms.com',
        'QCOM': 'qualcomm.com',
        'RTX': 'rtx.com',
        'NEE': 'nexteraenergy.com',
        'PM': 'pmi.com',
        'UNP': 'up.com',
        'IBM': 'ibm.com',
        'GE': 'ge.com',
        'CAT': 'caterpillar.com',
        'BA': 'boeing.com',
        'DE': 'deere.com',
        'SPGI': 'spglobal.com',
        'AXP': 'americanexpress.com',
        'HON': 'honeywell.com',
        'AMGN': 'amgen.com',
        'GS': 'goldmansachs.com',
        'ISRG': 'intuitive.com',
        'BKNG': 'booking.com',
        'MDLZ': 'mondelezinternational.com',
        'GILD': 'gilead.com',
        'BLK': 'blackrock.com',
        'SYK': 'stryker.com',
        'ADI': 'analog.com',
        'VRTX': 'vrtx.com',
        'ADP': 'adp.com',
        'MMC': 'mmc.com',
        'TJX': 'tjx.com',
        'MMM': '3m.com',
        'CVS': 'cvshealth.com',
        'SCHW': 'schwab.com',
        'LRCX': 'lamresearch.com',
        'C': 'citigroup.com',
        'REGN': 'regeneron.com',
        'CB': 'chubb.com',
        'PLD': 'prologis.com',
        'ZTS': 'zoetis.com',
        'EOG': 'eogresources.com',
        'MO': 'altria.com',
        'SO': 'southerncompany.com',
        'CI': 'cigna.com',
        'DUK': 'duke-energy.com',
        'CME': 'cmegroup.com',
        'SNPS': 'synopsys.com',
        'CL': 'colgatepalmolive.com',
        'ICE': 'ice.com',
        'EQIX': 'equinix.com',
        'NOC': 'northropgrumman.com',
        'BDX': 'bd.com',
        'ITW': 'itw.com',
        'WM': 'wm.com',
        'SHW': 'sherwin-williams.com',
        'AON': 'aon.com',
        'CDNS': 'cadence.com',
        'APD': 'airproducts.com',
        'MPC': 'marathonpetroleum.com',
        'FDX': 'fedex.com',
        'USB': 'usbank.com',
        'ETN': 'eaton.com',
        'EMR': 'emerson.com',
        'PSX': 'phillips66.com',
        'KLAC': 'kla.com',
        'MCO': 'moodys.com',
        'MRNA': 'modernatx.com',
        'ORLY': 'oreillyauto.com',
        'AEP': 'aep.com',
        'D': 'dominionenergy.com',
        'GD': 'gd.com',
        'CTAS': 'cintas.com',
        'ADSK': 'autodesk.com',
        'SLB': 'slb.com',
        'HCA': 'hcahealthcare.com',
        'ROP': 'rfroper.com',
        'PCAR': 'paccar.com',
        'F': 'ford.com',
        'GM': 'gm.com',
        'VLO': 'valero.com',
        'AIG': 'aig.com',
        'MET': 'metlife.com',
        'TRV': 'travelers.com',
        'COP': 'conocophillips.com',
        'HUM': 'humana.com',
        'AZO': 'autozone.com',
        'MSCI': 'msci.com',
        'EW': 'edwards.com',
        'A': 'agilent.com',
        'ECL': 'ecolab.com',
        'AFL': 'aflac.com',
        'ALL': 'allstate.com',
        'PRU': 'prudential.com',
        'STZ': 'cbrands.com',
        'MAR': 'marriott.com',
        'WELL': 'welltower.com',
        'GIS': 'generalmills.com',
        'HES': 'hess.com',
        'DG': 'dollargeneral.com',
        'DLTR': 'dollartree.com',
        'KMB': 'kimberly-clark.com',
        'O': 'realtyincome.com',
        'SPG': 'simon.com',
        'EXC': 'exeloncorp.com',
        'PEG': 'pseg.com',
        'XEL': 'xcelenergy.com',
        'ED': 'coned.com',
        'WEC': 'wecenergygroup.com',
        'DTE': 'dteenergy.com',
        'ES': 'eversource.com',
        'AES': 'aes.com',
        'PPL': 'pplweb.com',
        'EIX': 'edison.com',
        'AEE': 'ameren.com',
        'LNT': 'alliantenergy.com',
        'CMS': 'cmsenergy.com',
        'EVRG': 'evergy.com',
        'NI': 'nisource.com',
        'PNW': 'pinnaclewest.com',
    }

    def __init__(self, download_dir: str = './sustainability_reports',
                 delay_seconds: float = 2.0,
                 current_sector_id: Optional[int] = None):
        """
        Initialize the downloader.

        Args:
            download_dir: Directory to save downloaded reports
            delay_seconds: Delay between requests to be respectful to servers
            current_sector_id: The current sector ID being processed (e.g., 1007)
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.current_sector_id = current_sector_id

        # Track progress
        self.downloaded_reports = []
        self.failed_downloads = []

        # Track companies already checked in t_sec_company (to avoid repeated lookups)
        self._checked_companies = set()

        # Database connection (optional)
        self.db_connection = None
        self._init_db_connection()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def _init_db_connection(self):
        """Initialize database connection if available."""
        if not DB_AVAILABLE:
            logger.warning(
                "Database modules not available - downloads will not be recorded to t_data_source")
            return

        try:
            connection_string = DB_Connection().DB_CONNECTION_STRING
            self.db_connection = psycopg2.connect(connection_string)
            logger.info(
                "Database connection established for tracking downloads")
        except Exception as e:
            logger.warning(
                f"Could not connect to database: {e} - downloads will not be recorded to t_data_source")
            self.db_connection = None

    def _get_next_company_id(self) -> int:
        """
        Get the next available company_id from t_sec_company.

        Returns:
            Next company_id (max + 1) or 1 if table is empty
        """
        if not self.db_connection:
            return 1

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(company_id), 0) + 1 FROM t_sec_company")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 1
        except Exception as e:
            logger.error(f"Failed to get next company_id: {e}")
            return 1

    def _company_exists(self, company_name: str) -> Optional[int]:
        """
        Check if a company already exists in t_sec_company.

        Args:
            company_name: Name of the company to check

        Returns:
            company_id if exists, None otherwise
        """
        if not self.db_connection:
            return None

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT company_id FROM t_sec_company WHERE conformed_name = %s LIMIT 1",
                (company_name,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to check if company exists: {e}")
            return None

    def _get_sector_id(self) -> Optional[int]:
        """
        Look up sector_id from t_data_lookups using the current sector ID.

        Returns:
            sector_id from t_data_lookups, or None if not found
        """
        if not self.db_connection or not self.current_sector_id:
            return None

        try:
            cursor = self.db_connection.cursor()
            # Self-join to find matching sector_id based on description
            cursor.execute("""
                SELECT b.data_lookups_id 
                FROM t_data_lookups a
                INNER JOIN t_data_lookups b ON a.data_lookups_description = b.data_lookups_description 
                WHERE a.data_lookups_id = %s 
                  AND b.data_lookups_id != %s
            """, (self.current_sector_id, self.current_sector_id))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(
                f"Failed to get sector_id for current_sector_id {self.current_sector_id}: {e}")
            return None

    def _sector_mapping_exists(self, company_id: int) -> bool:
        """
        Check if a company-sector mapping already exists.

        Args:
            company_id: The company_id to check

        Returns:
            True if mapping exists, False otherwise
        """
        if not self.db_connection:
            return False

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT 1 FROM t_sec_company_sector_map WHERE company_id = %s LIMIT 1",
                (company_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check sector mapping: {e}")
            return False

    def _ensure_sector_mapping(self, company_id: int, company_name: str, sector_id: int) -> bool:
        """
        Ensure company-sector mapping exists in t_sec_company_sector_map.

        Args:
            company_id: The company_id from t_sec_company
            company_name: Name of the company
            sector_id: The sector_id from t_data_lookups

        Returns:
            True if mapping exists or was created, False on error
        """
        if not self.db_connection:
            return False

        try:
            # Check if mapping already exists
            if self._sector_mapping_exists(company_id):
                logger.debug(
                    f"Sector mapping already exists for company_id {company_id}")
                return True

            cursor = self.db_connection.cursor()
            insert_sql = """
                INSERT INTO t_sec_company_sector_map (
                    company_id, company_name, sector_id,
                    added_dt, added_by, modify_dt, modify_by
                )
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
            """

            cursor.execute(insert_sql, (
                company_id,
                company_name,
                sector_id,
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added sector mapping for '{company_name}' (company_id: {company_id}, sector_id: {sector_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure sector mapping: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    def _ensure_company_exists(self, company_name: str) -> Optional[int]:
        """
        Ensure company exists in t_sec_company, inserting if necessary.
        Also ensures sector mapping exists in t_sec_company_sector_map.
        Only checks once per company per session.

        Args:
            company_name: Name of the company

        Returns:
            company_id if company exists or was inserted, None on error
        """
        if not self.db_connection:
            return None

        # Skip if already checked this company
        if company_name in self._checked_companies:
            # Return existing company_id
            return self._company_exists(company_name)

        try:
            # Check if company exists
            existing_id = self._company_exists(company_name)
            if existing_id:
                logger.info(
                    f"Company '{company_name}' already exists in t_sec_company (id: {existing_id})")
                self._checked_companies.add(company_name)
                # Ensure sector mapping exists if current_sector_id is set
                if self.current_sector_id:
                    sector_id = self._get_sector_id()
                    if sector_id:
                        self._ensure_sector_mapping(
                            existing_id, company_name, sector_id)
                return existing_id

            # Insert new company with placeholder values
            next_id = self._get_next_company_id()
            cursor = self.db_connection.cursor()

            insert_sql = """
                INSERT INTO t_sec_company (
                    company_id, reporting_year, conformed_name, sic_code, sic_code_4_digit,
                    irs_number, state_of_incorporation, street_1, city, state, zip,
                    added_dt, added_by, modify_dt, modify_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
            """

            cursor.execute(insert_sql, (
                next_id,
                0,  # reporting_year placeholder
                company_name,
                '9999',  # sic_code placeholder
                9999,  # sic_code_4_digit placeholder
                9999,  # irs_number placeholder
                'PH',  # state_of_incorporation placeholder
                'PlaceHolder',  # street_1 placeholder
                'PlaceHolder',  # city placeholder
                'PH',  # state placeholder
                '9999',  # zip placeholder
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added company '{company_name}' to t_sec_company (id: {next_id})")
            self._checked_companies.add(company_name)

            # Add sector mapping if current_sector_id is set
            if self.current_sector_id:
                sector_id = self._get_sector_id()
                if sector_id:
                    self._ensure_sector_mapping(
                        next_id, company_name, sector_id)
                else:
                    logger.warning(
                        f"Could not find sector_id for current_sector_id {self.current_sector_id}")

            return next_id

        except Exception as e:
            logger.error(f"Failed to ensure company exists: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    def _add_to_data_source(self, company_name: str, year: int, source_url: str,
                            document_name: str, filepath: str) -> Optional[int]:
        """
        Add a downloaded report entry to t_data_source table.

        Args:
            company_name: Name of the company
            year: Year of the report
            source_url: URL where the report was downloaded from
            document_name: Name of the document file
            filepath: Local file path where document is saved

        Returns:
            unique_id of the inserted record, or None if failed
        """
        if not self.db_connection:
            return None

        # Ensure company exists in t_sec_company first (with sector mapping)
        self._ensure_company_exists(company_name)

        try:
            cursor = self.db_connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            # content_type 1 = Sustainability Report
            # source_type = 'file' for downloaded files
            insert_sql = """
                INSERT INTO t_data_source 
                (company_name, year, content_type, source_type, source_url, 
                 processed_ind, added_dt, added_by, modify_dt, modify_by)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
                RETURNING unique_id
            """

            cursor.execute(insert_sql, (
                company_name,
                int(year),
                1,  # content_type: Sustainability Report
                'file',  # source_type: file
                document_name,  # source_url stores the filename
                0,  # processed_ind: Not yet processed
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            result = cursor.fetchone()
            unique_id = result['unique_id'] if result else None

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added to t_data_source: {document_name} (id: {unique_id})")
            return unique_id

        except Exception as e:
            logger.error(f"Failed to add to t_data_source: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return None

    def _extract_year_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """
        Extract year from PDF metadata or content.

        Args:
            pdf_content: Raw PDF file content as bytes

        Returns:
            Year string (e.g., '2024') or None if not found
        """
        if not PYMUPDF_AVAILABLE:
            return None

        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_content, filetype="pdf")

            # Try metadata first (creation date, modification date, title)
            metadata = doc.metadata
            if metadata:
                # Check creation date
                if metadata.get('creationDate'):
                    year_match = re.search(
                        r'20\d{2}', metadata['creationDate'])
                    if year_match:
                        doc.close()
                        return year_match.group()

                # Check modification date
                if metadata.get('modDate'):
                    year_match = re.search(r'20\d{2}', metadata['modDate'])
                    if year_match:
                        doc.close()
                        return year_match.group()

                # Check title
                if metadata.get('title'):
                    year_match = re.search(r'20\d{2}', metadata['title'])
                    if year_match:
                        doc.close()
                        return year_match.group()

            # If no year in metadata, check first page content
            if len(doc) > 0:
                first_page = doc[0]
                text = first_page.get_text()[:2000]  # First 2000 chars

                # Look for year patterns in context of reports
                # e.g., "2024 Report", "FY 2023", "Fiscal Year 2022"
                year_patterns = [
                    r'(?:FY|Fiscal Year|Annual Report|Report)\s*(20\d{2})',
                    r'(20\d{2})\s*(?:Annual|Report|Sustainability|ESG|Environmental)',
                    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(20\d{2})',
                    r'(20\d{2})'  # Fallback: any year
                ]

                for pattern in year_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        doc.close()
                        return match.group(1) if match.lastindex else match.group()

            doc.close()
            return None

        except Exception as e:
            logger.debug(f"Error extracting year from PDF: {e}")
            return None

    def get_company_website(self, symbol: str, company_name: str) -> Optional[str]:
        """
        Get the website URL for a company.

        Args:
            symbol: Stock symbol
            company_name: Company name

        Returns:
            Website URL or None if not found
        """
        # Check known mappings first
        if symbol in self.COMPANY_WEBSITES:
            return f"https://www.{self.COMPANY_WEBSITES[symbol]}"

        # Try to derive from company name
        # Clean the company name for URL generation
        clean_name = company_name.lower()

        # Remove common suffixes
        for suffix in [' inc.', ' inc', ' corp.', ' corp', ' corporation',
                       ' company', ' co.', ' co', ' ltd.', ' ltd', ' llc',
                       ' plc', ' n.v.', ' s.a.', ' ag', ' se', ' nv',
                       ' holdings', ' group', ' international', ' intl']:
            clean_name = clean_name.replace(suffix, '')

        # Remove special characters and spaces
        clean_name = re.sub(r'[^a-z0-9]', '', clean_name)

        if clean_name:
            return f"https://www.{clean_name}.com"

        return None

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
            # Use requests with proper headers to avoid 403 Forbidden
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(StringIO(response.text))
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
                '',  # Homepage first
                '/sustainability',
                '/sustainability-report',
                '/sustainability-reports',
                '/esg',
                '/esg-report',
                '/corporate-responsibility',
                '/about/sustainability',
                '/about/esg',
                '/investors/esg',
                '/investors/sustainability',
                '/responsibility',
                '/impact',
                '/impact-report',
                '/environment',
                '/our-impact',
                '/csr',
                '/corporate-social-responsibility',
            ]

            for path in search_paths:
                url = urljoin(base_url, path) if path else base_url
                try:
                    response = self.session.get(
                        url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        if path:
                            logger.info(f"Found sustainability page: {url}")
                        # Parse page for PDF links
                        soup = BeautifulSoup(response.content, 'html.parser')
                        pdf_links = self._extract_pdf_links(soup, url)
                        potential_urls.extend(pdf_links)

                        # Also look for links to sustainability pages
                        if not path:  # On homepage, look for sustainability links
                            for link in soup.find_all('a', href=True):
                                href = link['href'].lower()
                                text = link.get_text().lower()
                                if any(kw in href or kw in text for kw in ['sustainability', 'esg', 'impact', 'responsibility']):
                                    sub_url = urljoin(base_url, link['href'])
                                    if sub_url.startswith(base_url):
                                        try:
                                            sub_response = self.session.get(
                                                sub_url, timeout=15, allow_redirects=True)
                                            if sub_response.status_code == 200:
                                                sub_soup = BeautifulSoup(
                                                    sub_response.content, 'html.parser')
                                                sub_pdf_links = self._extract_pdf_links(
                                                    sub_soup, sub_url)
                                                potential_urls.extend(
                                                    sub_pdf_links)
                                                logger.info(
                                                    f"Found {len(sub_pdf_links)} PDFs on {sub_url}")
                                        except requests.RequestException:
                                            pass
                                        time.sleep(self.delay_seconds / 2)

                except requests.RequestException as e:
                    logger.debug(f"Path not found: {url} - {e}")
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
                        company_name: Optional[str] = None,
                        year: Optional[int] = None) -> Optional[str]:
        """
        Download a report PDF.

        Args:
            url: URL of the PDF
            company_symbol: Stock symbol of the company
            company_name: Name of the company (for database tracking)
            year: Year of the report (optional)

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Extract original filename from URL
            url_path = urlparse(url).path
            original_filename = os.path.basename(url_path)

            # Extract year from URL or filename first
            year_match = re.search(r'20\d{2}', url)
            year_str = None

            if year_match:
                year_str = year_match.group()
            else:
                # Try to extract year from PDF content/metadata
                year_str = self._extract_year_from_pdf(response.content)
                if year_str:
                    logger.debug(
                        f"Extracted year {year_str} from PDF content for {url}")

            # Fallback to current year if no year found
            if not year_str:
                year_str = str(datetime.now().year)
                logger.debug(f"No year found, using current year for {url}")

            # Use original filename if it's a valid PDF name, otherwise generate one
            if original_filename and original_filename.lower().endswith('.pdf'):
                # Remove .pdf extension
                base_name = original_filename[:-4]

                # Check if year is already at the end (e.g., _2020 or -2020)
                if not re.search(r'[-_]20\d{2}$', base_name):
                    # Append year at the end
                    base_name = f"{base_name}-{year_str}"

                # Prefix with company symbol if not already present
                if not base_name.upper().startswith(company_symbol):
                    filename = f"{company_symbol}_{base_name}.pdf"
                else:
                    filename = f"{base_name}.pdf"
            else:
                # Fallback: generate filename with year and hash for uniqueness
                url_hash = hash(url) % 10000
                filename = f"{company_symbol}_report_{url_hash:04d}-{year_str}.pdf"

            # Save file
            company_dir = self.download_dir / company_symbol
            company_dir.mkdir(exist_ok=True)
            filepath = company_dir / filename

            # Check if file already exists with same content (skip duplicate downloads)
            if filepath.exists():
                existing_size = filepath.stat().st_size
                if existing_size == len(response.content):
                    logger.debug(f"Skipping duplicate: {filepath}")
                    return str(filepath)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded: {filepath}")

            # Add entry to t_data_source table
            db_id = None
            if company_name:
                db_id = self._add_to_data_source(
                    company_name=company_name,
                    year=int(year_str),
                    source_url=url,
                    document_name=filename,
                    filepath=str(filepath)
                )

            # Track success
            self.downloaded_reports.append({
                'symbol': company_symbol,
                'company_name': company_name,
                'url': url,
                'filepath': str(filepath),
                'download_date': datetime.now().isoformat(),
                'file_size': len(response.content),
                'db_id': db_id
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
                filepath = self.download_report(url, symbol, company_name)
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
            # Try to get website from DataFrame first, otherwise derive it
            website = row.get('Website', row.get('website', None))
            if not website or pd.isna(website):
                website = self.get_company_website(symbol, company)

            logger.info(
                f"Progress: {idx + 1}/{total} - {company} ({website or 'No website'})")

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

    def close(self):
        """Close database connection and cleanup resources."""
        if self.db_connection:
            try:
                self.db_connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
        self.session.close()

    def __enter__(self):
        """Support context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context manager exit."""
        self.close()
        return False


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
