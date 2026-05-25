"""
EdgarDownloader — composed class for SEC EDGAR filing downloads.

Handles both 10-K annual reports and all other EDGAR filings via:
  - get_edgar_10k_filings       (fetch 10-K filing list from EDGAR)
  - download_edgar_10k          (download 10-K PDFs / HTMs)
  - get_edgar_other_filings     (fetch non-10-K filing list)
  - download_edgar_other_filings (download DEF 14A, 10-Q, 8-K, etc.)
  - _get_edgar_filing_best_url  (resolve best exhibit URL from filing index)
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EdgarDownloader:
    """
    Composed downloader for SEC EDGAR filings (10-K annual reports and others).

    All external dependencies are injected via __init__ so this class has no
    coupling to AviskDataScraper's inheritance hierarchy.
    """

    def __init__(
        self,
        base_download_dir,
        delay_seconds: float,
        year_filter,
        get_edgar_session_headers,
        get_all_ciks_for_symbol,
        is_url_in_database,
        is_accession_in_database,
        is_duplicate_content,
        calculate_file_hash,
        add_to_data_source,
        downloaded_reports: list,
        failed_downloads: list,
        edgar_archives_base: str,
        edgar_submissions_url: str,
        edgar_10k_forms: set,
    ):
        self.base_download_dir = base_download_dir
        self.delay_seconds = delay_seconds
        self.year_filter = year_filter
        self._get_edgar_session_headers = get_edgar_session_headers
        self.get_all_ciks_for_symbol = get_all_ciks_for_symbol
        self._is_url_in_database = is_url_in_database
        self._is_accession_in_database = is_accession_in_database
        self._is_duplicate_content = is_duplicate_content
        self.calculate_file_hash = calculate_file_hash
        self._add_to_data_source = add_to_data_source
        self.downloaded_reports = downloaded_reports
        self.failed_downloads = failed_downloads
        self.EDGAR_ARCHIVES_BASE = edgar_archives_base
        self.EDGAR_SUBMISSIONS_URL = edgar_submissions_url
        self.EDGAR_10K_FORMS = edgar_10k_forms

    # ──────────────────────────────────────────────────────────────────────────
    # 10-K helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_edgar_10k_filings(self, cik: str, company_name: str) -> List[Dict]:
        """
        Fetch the list of 10-K filings for a company from SEC EDGAR.

        Uses the EDGAR submissions API:
          https://data.sec.gov/submissions/CIK{cik}.json

        Paginates through older filings automatically.

        Args:
            cik: Zero-padded 10-digit CIK string
            company_name: Company name (for logging)

        Returns:
            List of dicts with keys:
              accession_number, filing_date, report_date,
              primary_document, filing_url, form
        """
        filings: List[Dict] = []
        cik_int = int(cik)
        headers = self._get_edgar_session_headers()
        headers['Host'] = 'data.sec.gov'

        def _parse_filings_block(block: dict) -> None:
            forms = block.get('form', [])
            accessions = block.get('accessionNumber', [])
            filing_dates = block.get('filingDate', [])
            report_dates = block.get('reportDate', [])
            primary_docs = block.get('primaryDocument', [])
            for i, form in enumerate(forms):
                if form in self.EDGAR_10K_FORMS:
                    accession = accessions[i]
                    accession_nodash = accession.replace('-', '')
                    filing_date = filing_dates[i] if i < len(
                        filing_dates) else ''
                    report_date = report_dates[i] if i < len(
                        report_dates) else ''
                    primary_doc = primary_docs[i] if i < len(
                        primary_docs) else ''
                    filing_url = (
                        f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/"
                        f"{accession_nodash}/{primary_doc}"
                    )
                    filings.append({
                        'accession_number': accession,
                        'filing_date': filing_date,
                        'report_date': report_date,
                        'primary_document': primary_doc,
                        'filing_url': filing_url,
                        'form': form,
                        # preserve source CIK for multi-CIK companies
                        'filing_cik': str(cik_int),
                    })

        try:
            url = self.EDGAR_SUBMISSIONS_URL.format(cik=cik_int)
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Parse the most-recent filings block
            _parse_filings_block(data.get('filings', {}).get('recent', {}))

            # Paginate through older filing archives if present
            for older_file in data.get('filings', {}).get('files', []):
                # The 'name' field is just the filename, e.g. 'CIK0000021344-submissions-001.json'
                # — it must be prefixed with the submissions/ path.
                older_url = f"https://data.sec.gov/submissions/{older_file['name']}"
                try:
                    older_resp = requests.get(
                        older_url, headers=headers, timeout=30)
                    older_resp.raise_for_status()
                    _parse_filings_block(older_resp.json())
                    time.sleep(0.2)  # Be respectful to SEC servers
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch older filings from {older_url}: {e}")

            logger.info(
                f"Found {len(filings)} 10-K filing(s) for {company_name} (CIK: {cik})")
        except Exception as e:
            logger.error(
                f"Failed to get EDGAR filings for {company_name} (CIK: {cik}): {e}")

        return filings

    def _get_edgar_filing_best_url(self, cik: str, accession_number: str,
                                   primary_document: str,
                                   accepted_forms: Optional[set] = None) -> str:
        """
        Resolve the best downloadable document URL for an EDGAR filing.

        Tries the filing index HTML first to find a PDF variant.  Falls back
        to the primary document URL if no PDF is listed.

        Args:
            cik: CIK as string
            accession_number: Accession number with dashes (e.g., '0000320193-22-000108')
            primary_document: Primary document filename from submissions JSON
            accepted_forms: Set of form types to match when looking for a PDF.
                            If None, any PDF in the filing index is accepted.
                            Defaults to None (used by non-10K callers);
                            pass self.EDGAR_10K_FORMS for the 10-K path.

        Returns:
            Direct URL to the best document
        """
        cik_int = int(cik)
        accession_nodash = accession_number.replace('-', '')
        base_url = f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/{accession_nodash}/"

        try:
            headers = self._get_edgar_session_headers()
            headers['Host'] = 'www.sec.gov'
            # Try the .htm index (the .json variant returns 404 for most filings)
            index_htm_url = f"{base_url}{accession_number}-index.htm"
            resp = requests.get(index_htm_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                idx_soup = BeautifulSoup(resp.content, 'lxml')
                for row in idx_soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue
                    doc_type_cell = cells[1].get_text(strip=True)
                    doc_link = cells[3].find('a')
                    if not doc_link:
                        continue
                    fname = doc_link['href'].split('/')[-1]
                    is_pdf = fname.lower().endswith('.pdf')
                    if accepted_forms is None:
                        if is_pdf:
                            return f"{base_url}{fname}"
                    else:
                        if doc_type_cell in accepted_forms and is_pdf:
                            return f"{base_url}{fname}"
        except Exception as e:
            logger.debug(
                f"Filing index lookup failed for {accession_number}: {e}")

        # Fall back to primary document (usually .htm)
        return f"{base_url}{primary_document}"

    def download_edgar_10k(self, symbol: str, company_name: str,
                           year_filter_override: Optional[List[int]] = None) -> List[str]:
        """
        Download 10-K filings for a company directly from SEC EDGAR.

        Workflow:
          1. Resolve ticker → CIK via company_tickers.json
          2. Fetch filing list from EDGAR submissions API
          3. Filter filings by year_filter_override (if supplied) else self.year_filter
          4. Download each filing, deduplicating by content hash
          5. Save to the year-based folder structure and record in t_data_source

        SEC rate-limit guidance: max 10 requests/second; we stay well below
        that by honouring self.delay_seconds between downloads.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            company_name: Human-readable company name
            year_filter_override: If provided, use this year list instead of self.year_filter.
                                  Allows process_company() to pass a narrowed year list after
                                  the DB-skip check without mutating self.year_filter.

        Returns:
            List of local file paths for successfully downloaded 10-Ks
        """
        downloaded_paths: List[str] = []

        # 1. CIK look-up — may return multiple CIKs for restructured companies
        all_ciks = self.get_all_ciks_for_symbol(symbol)
        if not all_ciks:
            logger.warning(
                f"Cannot download EDGAR 10-K for {symbol}: CIK not found")
            return downloaded_paths

        # 2. Retrieve filing list across ALL CIKs and merge
        filings: List[Dict] = []
        for cik in all_ciks:
            cik_filings = self.get_edgar_10k_filings(cik, company_name)
            logger.info(
                f"CIK {cik}: found {len(cik_filings)} 10-K filing(s) for {company_name}")
            filings.extend(cik_filings)

        if not filings:
            logger.info(
                f"No 10-K filings found on EDGAR for {company_name} ({symbol})")
            return downloaded_paths

        # 3. Apply year filter (prefer override so process_company can pass a narrowed list)
        effective_year_filter = year_filter_override if year_filter_override is not None else self.year_filter
        if effective_year_filter:
            filtered = []
            for filing in filings:
                date_str = (filing.get('report_date')
                            or filing.get('filing_date', ''))
                year_match = re.search(r'(20\d{2})', date_str)
                if year_match and int(year_match.group(1)) in effective_year_filter:
                    filtered.append(filing)
            logger.info(
                f"EDGAR filings after year filter {effective_year_filter}: "
                f"{len(filtered)}/{len(filings)} for {company_name}")
            filings = filtered

        # 4. Download each filing
        sec_headers = self._get_edgar_session_headers()
        sec_headers['Host'] = 'www.sec.gov'

        for filing in filings:
            accession = filing['accession_number']
            primary_doc = filing['primary_document']
            report_date = filing.get('report_date', '')
            filing_date = filing.get('filing_date', '')
            year_str = (report_date or filing_date)[:4]

            # Extract the CIK from the filing's own URL so multi-CIK companies
            # (e.g. Google Inc. vs Alphabet Inc.) resolve correctly.
            filing_cik = filing.get('filing_cik') or all_ciks[-1]
            doc_url = self._get_edgar_filing_best_url(
                filing_cik, accession, primary_doc,
                accepted_forms=self.EDGAR_10K_FORMS)

            # Skip if already in database
            if company_name and self._is_url_in_database(doc_url, company_name):
                logger.info(
                    f"Skipping EDGAR filing (already in DB): {doc_url}")
                continue

            logger.info(
                f"Downloading EDGAR 10-K [{filing_date}] for {symbol}: {doc_url}")
            try:
                resp = requests.get(doc_url, headers=sec_headers, timeout=60)
                resp.raise_for_status()
            except Exception as e:
                logger.error(
                    f"Failed to download EDGAR filing {doc_url}: {e}")
                self.failed_downloads.append({
                    'symbol': symbol,
                    'url': doc_url,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                })
                time.sleep(1)
                continue

            content = resp.content
            content_hash = self.calculate_file_hash(content)

            # Duplicate content check
            existing_doc = self._is_duplicate_content(
                content_hash, company_name)
            if existing_doc:
                logger.info(
                    f"Skipping EDGAR filing - duplicate content already stored "
                    f"as '{existing_doc}'")
                continue

            # Build a stable filename
            ext = 'pdf' if doc_url.lower().endswith('.pdf') else 'htm'
            accession_short = accession.replace('-', '')
            filename = (
                f"{symbol}_10K_{report_date or filing_date}_"
                f"{accession_short}.{ext}"
            )

            year_dir = self.base_download_dir / (year_str or 'unknown')
            year_dir.mkdir(parents=True, exist_ok=True)
            filepath = year_dir / filename

            # Write file (skip if byte-identical copy already exists)
            if filepath.exists():
                existing_hash = self.calculate_file_hash(filepath.read_bytes())
                if existing_hash == content_hash:
                    logger.debug(f"EDGAR 10-K already on disk: {filepath}")
                else:
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    logger.info(f"Updated EDGAR 10-K on disk: {filepath}")
            else:
                with open(filepath, 'wb') as f:
                    f.write(content)
                logger.info(f"Downloaded EDGAR 10-K: {filepath}")

            # Record in t_data_source
            db_id = self._add_to_data_source(
                company_name=company_name,
                year=int(year_str) if year_str.isdigit() else 0,
                source_url=doc_url,
                document_name=filename,
                filepath=str(filepath),
                content_type=2,          # Annual/10-K
                file_content=content,
                original_source_url=doc_url,
                http_response_code=resp.status_code,
                company_symbol=symbol,
                form_type=filing.get('form', '10-K'),
            )

            self.downloaded_reports.append({
                'symbol': symbol,
                'company_name': company_name,
                'url': doc_url,
                'filepath': str(filepath),
                'download_date': datetime.now().isoformat(),
                'file_size': len(content),
                'db_id': db_id,
                'source': 'EDGAR',
                'form_type': filing.get('form', '10-K'),
            })

            downloaded_paths.append(str(filepath))

            # Respect SEC rate limit (max 10 req/sec; we stay conservative)
            time.sleep(max(self.delay_seconds, 0.15))

        logger.info(
            f"EDGAR download complete for {company_name}: "
            f"{len(downloaded_paths)} 10-K(s) saved")
        return downloaded_paths

    # ──────────────────────────────────────────────────────────────────────────
    # Other EDGAR filings (DEF 14A, 10-Q, 8-K, etc.)
    # ──────────────────────────────────────────────────────────────────────────

    def get_edgar_other_filings(self, cik: str, company_name: str) -> List[Dict]:
        """
        Fetch all EDGAR filings for a company EXCEPT 10-K variants.

        Used by download_edgar_other_filings (content_type=3) to retrieve
        DEF 14A, 10-Q, 8-K, 20-F, ARS, S-1, and any other form types that
        are not annual report (10-K) forms.

        Args:
            cik: Zero-padded 10-digit CIK string
            company_name: Company name (for logging)

        Returns:
            List of dicts with keys:
              accession_number, filing_date, report_date,
              primary_document, filing_url, form, filing_cik
        """
        filings: List[Dict] = []
        cik_int = int(cik)
        headers = self._get_edgar_session_headers()
        headers['Host'] = 'data.sec.gov'

        def _parse_filings_block(block: dict) -> None:
            forms = block.get('form', [])
            accessions = block.get('accessionNumber', [])
            filing_dates = block.get('filingDate', [])
            report_dates = block.get('reportDate', [])
            primary_docs = block.get('primaryDocument', [])
            for i, form in enumerate(forms):
                if form not in self.EDGAR_10K_FORMS:
                    accession = accessions[i]
                    accession_nodash = accession.replace('-', '')
                    filing_date = filing_dates[i] if i < len(
                        filing_dates) else ''
                    report_date = report_dates[i] if i < len(
                        report_dates) else ''
                    primary_doc = primary_docs[i] if i < len(
                        primary_docs) else ''
                    filing_url = (
                        f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/"
                        f"{accession_nodash}/{primary_doc}"
                    )
                    filings.append({
                        'accession_number': accession,
                        'filing_date': filing_date,
                        'report_date': report_date,
                        'primary_document': primary_doc,
                        'filing_url': filing_url,
                        'form': form,
                        'filing_cik': str(cik_int),
                    })

        try:
            url = self.EDGAR_SUBMISSIONS_URL.format(cik=cik_int)
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            _parse_filings_block(data.get('filings', {}).get('recent', {}))

            for older_file in data.get('filings', {}).get('files', []):
                older_url = f"https://data.sec.gov/submissions/{older_file['name']}"
                try:
                    older_resp = requests.get(
                        older_url, headers=headers, timeout=30)
                    older_resp.raise_for_status()
                    _parse_filings_block(older_resp.json())
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch older filings from {older_url}: {e}")

            logger.info(
                f"Found {len(filings)} non-10K filing(s) for {company_name} (CIK: {cik})")
        except Exception as e:
            logger.error(
                f"Failed to get EDGAR other filings for {company_name} (CIK: {cik}): {e}")

        return filings

    def download_edgar_other_filings(self, symbol: str, company_name: str,
                                     year_filter_override: Optional[List[int]] = None) -> List[str]:
        """
        Download all non-10K EDGAR filings for a company and year(s).

        Covers form types such as DEF 14A (proxy), 10-Q (quarterly),
        8-K (current reports), 20-F, ARS, S-1, and any other SEC filing
        that is not a 10-K annual report variant.

        Workflow:
          1. Resolve ticker → CIK via company_tickers.json
          2. Fetch all non-10K filings from EDGAR submissions API
          3. Filter by year (year_filter_override or self.year_filter)
          4. Download each filing, deduplicating by URL and content hash
          5. Save to year-based folder and record in t_data_source (content_type=3)

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            company_name: Human-readable company name
            year_filter_override: Narrowed year list from process_company()

        Returns:
            List of local file paths for successfully downloaded filings
        """
        downloaded_paths: List[str] = []

        all_ciks = self.get_all_ciks_for_symbol(symbol)
        if not all_ciks:
            logger.warning(
                f"Cannot download EDGAR other filings for {symbol}: CIK not found")
            return downloaded_paths

        filings: List[Dict] = []
        for cik in all_ciks:
            cik_filings = self.get_edgar_other_filings(cik, company_name)
            logger.info(
                f"CIK {cik}: found {len(cik_filings)} non-10K filing(s) for {company_name}")
            filings.extend(cik_filings)

        if not filings:
            logger.info(
                f"No non-10K filings found on EDGAR for {company_name} ({symbol})")
            return downloaded_paths

        # Apply year filter
        effective_year_filter = (
            year_filter_override if year_filter_override is not None
            else self.year_filter
        )
        if effective_year_filter:
            filtered = []
            for filing in filings:
                date_str = (filing.get('report_date')
                            or filing.get('filing_date', ''))
                year_match = re.search(r'(20\d{2})', date_str)
                if year_match and int(year_match.group(1)) in effective_year_filter:
                    filtered.append(filing)
            logger.info(
                f"EDGAR other filings after year filter {effective_year_filter}: "
                f"{len(filtered)}/{len(filings)} for {company_name}")
            filings = filtered

        sec_headers = self._get_edgar_session_headers()
        sec_headers['Host'] = 'www.sec.gov'

        for filing in filings:
            accession = filing['accession_number']
            primary_doc = filing['primary_document']
            report_date = filing.get('report_date', '')
            filing_date = filing.get('filing_date', '')
            year_str = (report_date or filing_date)[:4]
            form_type = filing.get('form', 'OTHER')
            filing_cik = filing.get('filing_cik') or all_ciks[-1]

            # --- Fast pre-check: skip EDGAR HTTP index request if we already
            # have this accession stored (accession_short is embedded in the
            # filename saved at insert time).
            accession_short = accession.replace('-', '')[:12]
            year_int = int(year_str) if year_str.isdigit() else 0
            if self._is_accession_in_database(company_name, year_int,
                                              accession_short):
                continue

            # accepted_forms=None → accept any PDF in the filing index
            doc_url = self._get_edgar_filing_best_url(
                filing_cik, accession, primary_doc, accepted_forms=None)

            if doc_url and self._is_url_in_database(doc_url, company_name):
                logger.debug(
                    f"Skipping EDGAR other filing (already in DB): {doc_url}")
                continue

            logger.info(
                f"Downloading EDGAR {form_type} [{filing_date}] for {symbol}: {doc_url}")
            try:
                resp = requests.get(doc_url, headers=sec_headers, timeout=60)
                resp.raise_for_status()
            except Exception as e:
                logger.error(
                    f"Failed to download EDGAR other filing {doc_url}: {e}")
                self.failed_downloads.append({
                    'symbol': symbol,
                    'url': doc_url,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                })
                time.sleep(1)
                continue

            content = resp.content
            content_hash = self.calculate_file_hash(content)

            existing_doc = self._is_duplicate_content(
                content_hash, company_name)
            if existing_doc:
                logger.info(
                    f"Skipping EDGAR other filing - duplicate content already stored "
                    f"as '{existing_doc}'")
                continue

            ext = 'pdf' if doc_url.lower().endswith('.pdf') else 'htm'
            form_safe = form_type.replace('/', '_').replace(' ', '')
            filename = (
                f"{symbol}_{form_safe}_{report_date or filing_date}_"
                f"{accession_short}.{ext}"
            )

            year_dir = self.base_download_dir / (year_str or 'unknown')
            year_dir.mkdir(parents=True, exist_ok=True)
            filepath = year_dir / filename

            if filepath.exists():
                existing_hash = self.calculate_file_hash(filepath.read_bytes())
                if existing_hash == content_hash:
                    logger.debug(
                        f"EDGAR other filing already on disk: {filepath}")
                else:
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    logger.info(
                        f"Updated EDGAR other filing on disk: {filepath}")
            else:
                with open(filepath, 'wb') as f:
                    f.write(content)
                logger.info(f"Downloaded EDGAR {form_type}: {filepath}")

            db_id = self._add_to_data_source(
                company_name=company_name,
                year=int(year_str) if year_str.isdigit() else 0,
                source_url=doc_url,
                document_name=filename,
                filepath=str(filepath),
                content_type=3,           # Other EDGAR filings
                file_content=content,
                original_source_url=doc_url,
                http_response_code=resp.status_code,
                company_symbol=symbol,
                form_type=form_type,
            )

            self.downloaded_reports.append({
                'symbol': symbol,
                'company_name': company_name,
                'url': doc_url,
                'filepath': str(filepath),
                'download_date': datetime.now().isoformat(),
                'file_size': len(content),
                'db_id': db_id,
                'source': 'EDGAR',
                'form_type': form_type,
            })

            downloaded_paths.append(str(filepath))
            time.sleep(max(self.delay_seconds, 0.15))

        logger.info(
            f"EDGAR other filings download complete for {company_name}: "
            f"{len(downloaded_paths)} filing(s) saved")
        return downloaded_paths
