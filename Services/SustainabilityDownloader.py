"""
SustainabilityDownloader — composed class for web-search-based PDF downloads.

Handles sustainability / ESG report discovery and downloading via:
  - Company website crawl  (search_company_website)
  - DuckDuckGo search      (search_duckduckgo)
  - Known direct PDF URLs  (try_known_report_urls)
  - Generic PDF downloader (download_report)
"""

import re
import time
import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

logger = logging.getLogger(__name__)


class SustainabilityDownloader:
    """
    Composed downloader for sustainability / ESG reports sourced from the web.

    All external dependencies are injected via __init__ so this class has no
    coupling to AviskDataScraper's inheritance hierarchy.
    """

    def __init__(
        self,
        session,
        base_download_dir,
        delay_seconds: float,
        year_filter,
        content_types,
        is_url_in_database,
        is_duplicate_content,
        calculate_file_hash,
        extract_year_from_pdf,
        add_to_data_source,
        downloaded_reports: list,
        failed_downloads: list,
        report_patterns: list,
        custom_sustainability_pages: dict,
        known_report_url_patterns: dict,
    ):
        self.session = session
        self.base_download_dir = base_download_dir
        self.delay_seconds = delay_seconds
        self.year_filter = year_filter
        self.content_types = content_types
        self._is_url_in_database = is_url_in_database
        self._is_duplicate_content = is_duplicate_content
        self.calculate_file_hash = calculate_file_hash
        self._extract_year_from_pdf = extract_year_from_pdf
        self._add_to_data_source = add_to_data_source
        self.downloaded_reports = downloaded_reports
        self.failed_downloads = failed_downloads
        self.REPORT_PATTERNS = report_patterns
        self.CUSTOM_SUSTAINABILITY_PAGES = custom_sustainability_pages
        self.KNOWN_REPORT_URL_PATTERNS = known_report_url_patterns
        # Search metadata stored temporarily between search and download_report
        self._current_search_query = None
        self._current_search_rank = None

    # ──────────────────────────────────────────────────────────────────────────
    # Website / search helpers
    # ──────────────────────────────────────────────────────────────────────────

    def search_company_website(self, company_name: str,
                               base_url: str, symbol: str = None) -> List[str]:
        """
        Search company website for sustainability report links.

        Args:
            company_name: Name of the company
            base_url: Base URL of company website
            symbol: Stock symbol (optional, for custom URL lookup)

        Returns:
            List of potential report URLs
        """
        potential_urls = []

        try:
            # Check for custom sustainability pages first (for companies like Microsoft, Apple, etc.)
            custom_pages = []
            if symbol and symbol in self.CUSTOM_SUSTAINABILITY_PAGES:
                custom_pages = self.CUSTOM_SUSTAINABILITY_PAGES[symbol]
                logger.info(
                    f"Using custom sustainability pages for {symbol}: {custom_pages}")

            # Try custom pages first
            for custom_url in custom_pages:
                try:
                    response = self.session.get(
                        custom_url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        logger.info(
                            f"Found custom sustainability page: {custom_url}")
                        soup = BeautifulSoup(response.content, 'html.parser')
                        pdf_links = self._extract_pdf_links(soup, custom_url)
                        potential_urls.extend(pdf_links)
                        logger.info(
                            f"Found {len(pdf_links)} PDFs on custom page {custom_url}")
                except requests.RequestException as e:
                    logger.debug(f"Custom page not found: {custom_url} - {e}")
                time.sleep(self.delay_seconds / 2)

            # Try common sustainability page patterns
            search_paths = [
                '',  # Homepage first
                '/sustainability',
                '/sustainability-report',
                '/sustainability-reports',
                '/sustainability/reports',
                '/esg',
                '/esg-report',
                '/esg-reports',
                '/esg/reports',
                '/corporate-responsibility',
                '/corporate-responsibility/reports',
                '/about/sustainability',
                '/about/esg',
                '/about/responsibility',
                '/investors/esg',
                '/investors/sustainability',
                '/investor-relations/esg',
                '/responsibility',
                '/responsibility/reports',
                '/impact',
                '/impact-report',
                '/our-impact',
                '/our-impact/reports',
                '/environment',
                '/environmental',
                '/csr',
                '/corporate-social-responsibility',
                '/governance/esg',
                '/citizenship',
                '/corporate-citizenship',
                '/social-impact',
                '/reports',
                '/annual-report',
                '/annual-reports',
                '/company/sustainability',
                '/who-we-are/sustainability',
                '/our-story/sustainability',
                '/about-us/sustainability',
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

    def search_duckduckgo(self, company_name: str, year: Optional[int] = None) -> List[str]:
        """
        Search DuckDuckGo for reports based on configured content types.

        Args:
            company_name: Name of the company
            year: Optional year to filter results

        Returns:
            List of PDF URLs found
        """
        pdf_urls = []

        try:
            # Build search queries based on content types
            year_str = str(year) if year else ""
            search_terms = []

            # Sustainability/ESG searches (content_type = 1)
            if 1 in self.content_types:
                search_terms.extend([
                    f'"{company_name}" sustainability report {year_str} filetype:pdf',
                    f'"{company_name}" ESG report {year_str} filetype:pdf',
                    f'"{company_name}" corporate responsibility report {year_str} filetype:pdf',
                ])

            # Annual Report/10K searches (content_type = 2)
            if 2 in self.content_types:
                search_terms.extend([
                    f'"{company_name}" annual report {year_str} filetype:pdf',
                    f'"{company_name}" 10-K {year_str} filetype:pdf',
                    f'"{company_name}" form 10-K SEC filing {year_str} filetype:pdf',
                ])

            # Earnings call transcripts are sourced directly from SEC EDGAR 8-K
            # exhibits (see download_edgar_transcripts) — they are not published
            # as PDFs so DuckDuckGo searches for them would be fruitless.

            # Use duckduckgo-search library if available (handles bot detection)
            if DDGS_AVAILABLE:
                for query in search_terms:
                    try:
                        with DDGS() as ddgs:
                            results = list(ddgs.text(query, max_results=15))
                            for result in results:
                                url = result.get('href', '')
                                if not url:
                                    continue

                                # Check if URL is a PDF (by extension or content)
                                is_pdf = url.lower().endswith('.pdf')

                                # Also check if URL contains pdf in path (some CDNs)
                                if not is_pdf and '/pdf/' in url.lower():
                                    is_pdf = True

                                if is_pdf:
                                    # If year filter, verify year is in URL
                                    if year_str:
                                        if year_str in url:
                                            pdf_urls.append(url)
                                            logger.info(
                                                f"DuckDuckGo found PDF for {year_str}: {url}")
                                        else:
                                            logger.debug(
                                                f"Skipping PDF (year {year_str} not in URL): {url}")
                                    else:
                                        pdf_urls.append(url)
                                        logger.info(
                                            f"DuckDuckGo found PDF: {url}")
                        # Longer delay between searches to avoid rate limiting
                        time.sleep(self.delay_seconds * 2)
                    except Exception as e:
                        logger.debug(f"DDGS search error for '{query}': {e}")
                        # Extra delay on error (rate limiting)
                        time.sleep(self.delay_seconds * 3)
                        continue
            else:
                # Fallback to HTML scraping (may be blocked by CAPTCHA)
                logger.warning(
                    "duckduckgo-search library not available, using HTML fallback (may be blocked)")
                for query in search_terms:
                    try:
                        # Use DuckDuckGo HTML search (no API key needed)
                        encoded_query = requests.utils.quote(query)
                        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        }

                        response = self.session.get(
                            url, headers=headers, timeout=15)

                        if response.status_code == 200:
                            soup = BeautifulSoup(
                                response.content, 'html.parser')

                            # Find result links
                            for result in soup.find_all('a', class_='result__a'):
                                href = result.get('href', '')
                                # DuckDuckGo wraps URLs, extract actual URL
                                if 'uddg=' in href:
                                    # Extract the actual URL from DuckDuckGo's redirect
                                    import urllib.parse
                                    parsed = urllib.parse.parse_qs(
                                        urllib.parse.urlparse(href).query)
                                    if 'uddg' in parsed:
                                        actual_url = parsed['uddg'][0]
                                        if actual_url.lower().endswith('.pdf'):
                                            pdf_urls.append(actual_url)
                                            logger.info(
                                                f"DuckDuckGo found PDF: {actual_url}")
                                elif href.lower().endswith('.pdf'):
                                    pdf_urls.append(href)
                                    logger.info(
                                        f"DuckDuckGo found PDF: {href}")

                            # Also check result snippets for PDF links
                            for result in soup.find_all('a', class_='result__url'):
                                href = result.get('href', '')
                                if href.lower().endswith('.pdf'):
                                    pdf_urls.append(href)

                        time.sleep(self.delay_seconds)  # Be respectful

                    except Exception as e:
                        logger.debug(
                            f"DuckDuckGo search error for '{query}': {e}")
                        continue

            # Deduplicate and validate URLs
            pdf_urls = list(set(pdf_urls))
            logger.info(
                f"DuckDuckGo search for {company_name}, year {year_str} found {len(pdf_urls)} PDFs")

        except Exception as e:
            logger.error(f"DuckDuckGo search failed for {company_name}: {e}")

        return pdf_urls

    def try_known_report_urls(self, symbol: str, year: int) -> List[str]:
        """
        Try known direct PDF URLs for major companies.

        Major tech companies like Google, Amazon, Microsoft have predictable
        URL patterns for their sustainability reports.

        Args:
            symbol: Stock symbol (e.g., 'GOOG', 'AMZN')
            year: Year to search for

        Returns:
            List of valid PDF URLs that exist
        """
        valid_urls = []

        if symbol not in self.KNOWN_REPORT_URL_PATTERNS:
            return valid_urls

        patterns = self.KNOWN_REPORT_URL_PATTERNS[symbol]
        logger.info(
            f"Trying {len(patterns)} known URL patterns for {symbol} {year}")

        for pattern in patterns:
            url = pattern.replace('{year}', str(year))
            try:
                # HEAD request to check if PDF exists
                response = self.session.head(
                    url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get(
                        'content-type', '').lower()
                    if 'pdf' in content_type or url.lower().endswith('.pdf'):
                        logger.info(f"Found known report: {url}")
                        valid_urls.append(url)
                else:
                    logger.debug(
                        f"Known URL not found (status {response.status_code}): {url}")
            except requests.RequestException as e:
                logger.debug(f"Failed to check known URL: {url} - {e}")

            time.sleep(0.5)  # Brief delay between checks

        return valid_urls

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

    def _filter_urls_by_year(self, urls: List[str]) -> List[str]:
        """
        Filter URLs to only include those matching the year filter.
        This is done by checking if any year from the filter appears in the URL.

        Args:
            urls: List of URLs to filter

        Returns:
            Filtered list of URLs matching the year filter
        """
        if self.year_filter is None:
            return urls

        filtered_urls = []
        year_patterns = [str(year) for year in self.year_filter]

        for url in urls:
            # Check if any of the target years appear in the URL
            url_lower = url.lower()
            year_found = False

            for year in year_patterns:
                if year in url_lower:
                    filtered_urls.append(url)
                    year_found = True
                    break

            # If no year found in URL, we can't pre-filter - include it for PDF check
            if not year_found:
                # Check if URL has ANY year pattern (20xx)
                year_match = re.search(r'20\d{2}', url)
                if year_match:
                    # URL has a year but it's not in our filter - skip it
                    logger.debug(
                        f"Skipping {url} - year {year_match.group()} not in filter {self.year_filter}")
                else:
                    # No year in URL - include for PDF metadata check
                    filtered_urls.append(url)

        logger.info(
            f"Year filter applied: {len(filtered_urls)}/{len(urls)} URLs match years {self.year_filter}")
        return filtered_urls

    # ──────────────────────────────────────────────────────────────────────────
    # PDF downloader
    # ──────────────────────────────────────────────────────────────────────────

    def download_report(self, url: str, company_symbol: str,
                        company_name: Optional[str] = None,
                        year: Optional[int] = None,
                        max_retries: int = 3,
                        search_query_used: Optional[str] = None,
                        search_result_rank: Optional[int] = None) -> Optional[str]:
        """
        Download a report PDF with retry logic for transient errors.

        Args:
            url: URL of the PDF
            company_symbol: Stock symbol of the company
            company_name: Name of the company (for database tracking)
            year: Year of the report (optional)
            max_retries: Maximum number of retry attempts for 5xx errors
            search_query_used: The search query that found this URL
            search_result_rank: Position in search results (1 = top)

        Returns:
            Path to downloaded file, or None if failed
        """
        # Store search metadata for later use in _add_to_data_source
        self._current_search_query = search_query_used
        self._current_search_rank = search_result_rank

        # Check if already in DATABASE BEFORE making HTTP request
        # (only checks DB, not file system - allows re-registering existing files)
        if company_name and self._is_url_in_database(url, company_name):
            return None  # Skip - already tracked in database

        response = None
        last_error = None

        # Add dynamic Referer header based on the URL's domain
        parsed_url = urlparse(url)
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        request_headers = {'Referer': referer}

        # Retry logic for transient server errors (502, 503, 504)
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url, timeout=30, headers=request_headers)
                response.raise_for_status()
                break  # Success - exit retry loop
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else 0
                # Retry on 502, 503, 504 (transient server errors)
                if status_code in (502, 503, 504) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # 3s, 6s, 9s
                    logger.warning(
                        f"HTTP {status_code} for {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    last_error = e
                    continue
                else:
                    # Non-retryable error or max retries reached
                    logger.error(f"Failed to download {url}: {e}")
                    self.failed_downloads.append({
                        'symbol': company_symbol,
                        'url': url,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    return None
            except Exception as e:
                # Non-HTTP errors (SSL, timeout, etc.) - don't retry
                logger.error(f"Failed to download {url}: {e}")
                self.failed_downloads.append({
                    'symbol': company_symbol,
                    'url': url,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                return None

        # If we exhausted retries without success
        if response is None:
            logger.error(
                f"Failed to download {url} after {max_retries} retries: {last_error}")
            self.failed_downloads.append({
                'symbol': company_symbol,
                'url': url,
                'error': str(last_error),
                'timestamp': datetime.now().isoformat()
            })
            return None

        try:
            # Compute content hash early for duplicate detection
            content_hash = self.calculate_file_hash(response.content)

            # Check for duplicate content (same document, different URL/filename)
            if company_name:
                existing_doc = self._is_duplicate_content(
                    content_hash, company_name)
                if existing_doc:
                    logger.info(
                        f"Skipping {url} - duplicate content already stored as '{existing_doc}' "
                        f"(hash: {content_hash[:12]}...)"
                    )
                    return None

            # Extract original filename from URL
            url_path = urlparse(url).path
            original_filename = os.path.basename(url_path)

            # ── Year extraction ───────────────────────────────────────────────
            # When a URL contains two DIFFERENT years (e.g. a 2025 folder path
            # but a 2021 document year) the URL alone is ambiguous.  Strategy:
            #   1. Collect all distinct plausible years from the full URL.
            #   2. If exactly one → use it.
            #   3. If two or more → open the PDF and let content/metadata decide.
            #   4. Fallback: first year found in the filename stem (left-to-right).
            #   5. Last resort: current year.
            _this_year = datetime.now().year
            _all_url_years = sorted(
                {int(m) for m in re.findall(r'20\d{2}', url)
                 if 2000 <= int(m) <= _this_year}
            )

            if len(_all_url_years) == 1:
                # Unambiguous — only one year present
                year_str = str(_all_url_years[0])
                logger.debug(f"Single year {year_str} found in URL for {url}")
            elif len(_all_url_years) >= 2:
                # Ambiguous — let the PDF content decide
                logger.debug(
                    f"Multiple years {_all_url_years} in URL — inspecting PDF "
                    f"content to determine reporting year for {url}")
                year_str = self._extract_year_from_pdf(response.content)
                if year_str:
                    logger.debug(
                        f"PDF content resolved year to {year_str} for {url}")
                else:
                    # PDF gave no answer — fall back to first year in filename stem
                    _fname_stem = os.path.splitext(original_filename)[
                        0] if original_filename else ""
                    _fname_match = re.search(r'20\d{2}', _fname_stem)
                    if _fname_match:
                        year_str = _fname_match.group()
                        logger.debug(
                            f"PDF inconclusive; using first filename year "
                            f"{year_str} for {url}")
                    else:
                        year_str = str(_all_url_years[0])
                        logger.debug(
                            f"PDF inconclusive, no filename year; using "
                            f"earliest URL year {year_str} for {url}")
            else:
                # No year in URL at all
                year_str = None

            # If no plausible year in URL, try PDF content/metadata
            if not year_str:
                year_str = self._extract_year_from_pdf(response.content)
                if year_str:
                    logger.debug(
                        f"Extracted year {year_str} from PDF content for {url}")

            # Fallback to current year if no year found
            if not year_str:
                year_str = str(datetime.now().year)
                logger.debug(f"No year found, using current year for {url}")

            # Check year filter - skip if year doesn't match filter
            if self.year_filter is not None:
                try:
                    report_year = int(year_str)
                    if report_year not in self.year_filter:
                        logger.info(
                            f"Skipping {url} - year {year_str} not in filter {self.year_filter}")
                        return None
                except ValueError:
                    logger.warning(
                        f"Could not parse year from {year_str}, skipping filter check")

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

            # Create yearly folder structure (e.g., Stage0SourcePDFFiles/2023/)
            year_dir = self.base_download_dir / year_str
            year_dir.mkdir(parents=True, exist_ok=True)
            filepath = year_dir / filename

            # Check if file already exists with identical content (skip duplicate downloads)
            if filepath.exists():
                existing_hash = self.calculate_file_hash(filepath.read_bytes())
                if existing_hash == content_hash:
                    logger.debug(f"File exists, skipping write: {filepath}")
                    # Still add to database if not already tracked
                    db_id = None
                    if company_name:
                        db_id = self._add_to_data_source(
                            company_name=company_name,
                            year=int(year_str),
                            source_url=url,
                            document_name=filename,
                            filepath=str(filepath),
                            file_content=response.content,
                            original_source_url=url,
                            search_query_used=getattr(
                                self, '_current_search_query', None),
                            search_result_rank=getattr(
                                self, '_current_search_rank', None),
                            http_response_code=response.status_code,
                            company_symbol=company_symbol
                        )
                        if db_id:
                            logger.info(
                                f"Registered existing file in database: {filepath} (id: {db_id})")
                    return str(filepath)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded: {filepath}")

            # Add entry to t_data_source table with authenticity tracking
            db_id = None
            if company_name:
                db_id = self._add_to_data_source(
                    company_name=company_name,
                    year=int(year_str),
                    source_url=url,
                    document_name=filename,
                    filepath=str(filepath),
                    file_content=response.content,
                    original_source_url=url,
                    search_query_used=getattr(
                        self, '_current_search_query', None),
                    search_result_rank=getattr(
                        self, '_current_search_rank', None),
                    http_response_code=response.status_code,
                    company_symbol=company_symbol
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

            # Add delay after successful download to avoid rate limiting
            time.sleep(self.delay_seconds)

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to process downloaded file {url}: {e}")
            self.failed_downloads.append({
                'symbol': company_symbol,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return None
