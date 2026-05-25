"""
TranscriptDownloader
====================
Standalone class providing all earnings-call transcript download methods.
Used by AviskDataScraper via composition (``self.transcripts``).

Sources (in priority order, as wired in AviskDataScraper.process_company):
  1. HuggingFace  — glopardo/sp500-earnings-transcripts (496 companies,
                    2013Q2–2025Q1, ~20 k transcripts, no API key required)
  2. EDGAR 8-K    — EX-99.2 / EX-99.3 exhibits for companies that attach
                    written transcripts to their 8-K filings
  3. IR Website   — scrape company investor-relations pages for transcript PDFs
                    / HTML pages
  4. FMP          — Financial Modeling Prep /stable/earning-call-transcript
                    (currently HTTP 402; fast-fails on first hit)
  5. EDGAR PR     — EX-99.1 earnings press-release fallback for companies
                    (e.g. Apple) that never file a written transcript

Dependencies are injected via __init__ (composition pattern):
  session                  — requests.Session from the host scraper
  base_download_dir        — pathlib.Path  output root
  delay_seconds            — float  inter-request delay
  data_source_exists       — AviskDataScraper._data_source_exists callable
  add_to_data_source       — AviskDataScraper._add_to_data_source callable
  get_edgar_session_headers — AviskDataScraper._get_edgar_session_headers callable
  get_all_ciks_for_symbol  — AviskDataScraper.get_all_ciks_for_symbol callable
  edgar_archives_base      — str  SEC archives URL prefix
  edgar_submissions_url    — str  SEC submissions API URL template
"""

import io as _io
import re
import time
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Financial Modeling Prep — transcript endpoint (currently gated behind paid tier)
FMP_API_KEY = 'j1sUHyVT1lU3gsc2l6zF2jkuleFJEA2o'
FMP_STABLE_BASE_URL = 'https://financialmodelingprep.com/stable'

logger = logging.getLogger(__name__)


class TranscriptDownloader:
    """
    Standalone downloader for all earnings-call transcript sources.
    Instantiated by AviskDataScraper as ``self.transcripts`` (composition).
    """

    def __init__(
        self,
        session,
        base_download_dir,
        delay_seconds: float,
        data_source_exists,
        add_to_data_source,
        get_edgar_session_headers,
        get_all_ciks_for_symbol,
        edgar_archives_base: str,
        edgar_submissions_url: str,
    ):
        """
        Inject all external dependencies from the host AviskDataScraper.

        Args:
            session:                  requests.Session (shared with host)
            base_download_dir:        pathlib.Path output root
            delay_seconds:            inter-request delay in seconds
            data_source_exists:       host._data_source_exists callable
            add_to_data_source:       host._add_to_data_source callable
            get_edgar_session_headers: host._get_edgar_session_headers callable
            get_all_ciks_for_symbol:  host.get_all_ciks_for_symbol callable
            edgar_archives_base:      SEC archives URL prefix
            edgar_submissions_url:    SEC submissions API URL template
        """
        self.session = session
        self.base_download_dir = base_download_dir
        self.delay_seconds = delay_seconds
        self._data_source_exists = data_source_exists
        self._add_to_data_source = add_to_data_source
        self._get_edgar_session_headers = get_edgar_session_headers
        self.get_all_ciks_for_symbol = get_all_ciks_for_symbol
        self.EDGAR_ARCHIVES_BASE = edgar_archives_base
        self.EDGAR_SUBMISSIONS_URL = edgar_submissions_url

    # ── Hugging Face dataset config ──────────────────────────────────────────
    # Public dataset: glopardo/sp500-earnings-transcripts
    # Coverage: 2013Q2 – 2025Q1, 496 companies, 20 681 transcripts, 0 API key.
    HF_DATASET_ID = "glopardo/sp500-earnings-transcripts"
    HF_PARQUET_BASE = (
        "https://huggingface.co/datasets/glopardo/sp500-earnings-transcripts"
        "/resolve/main/data/"
    )
    HF_CACHE_FILENAME = "_hf_sp500_transcripts_cache.parquet"

    # ── IR website overrides ─────────────────────────────────────────────────
    # Companies whose IR domain differs from their corporate website.
    # Maps ticker symbol → IR base URL (no trailing slash).
    _IR_WEBSITE_OVERRIDES: Dict[str, str] = {
        'GOOGL': 'https://abc.xyz',
        'GOOG':  'https://abc.xyz',
        'META':  'https://investor.fb.com',
        'AAPL':  'https://investor.apple.com',
        'MSFT':  'https://www.microsoft.com',
        'AMZN':  'https://ir.aboutamazon.com',
        'NVDA':  'https://investor.nvidia.com',
        'TSLA':  'https://ir.tesla.com',
        'NFLX':  'https://ir.netflix.net',
        'CRM':   'https://investor.salesforce.com',
        'ADBE':  'https://www.adobe.com',
        'AVGO':  'https://investors.broadcom.com',
        'ORCL':  'https://investor.oracle.com',
        'WMT':   'https://stock.walmart.com',
        'JPM':   'https://www.jpmorganchase.com',
        'JNJ':   'https://investor.jnj.com',
        'XOM':   'https://investor.exxonmobil.com',
        'BRK.B': 'https://www.berkshirehathaway.com',
        'BRK.A': 'https://www.berkshirehathaway.com',
    }

    # Common IR path patterns for Investors → Events & Presentations pages
    _IR_TRANSCRIPT_PATHS = [
        '/investors/events-and-presentations',
        '/investors/events-presentations',
        '/investor-relations/events-and-presentations',
        '/investor-relations/events-presentations',
        '/investors/events',
        '/investor-relations/events',
        '/investors/earnings',
        '/investor-relations/earnings',
        '/investors/quarterly-earnings',
        '/investor-relations/quarterly-earnings',
        '/investors/earnings-transcripts',
        '/investor-relations/earnings-transcripts',
        '/investors/transcripts',
        '/investor-relations/transcripts',
        '/investors/presentations',
        '/investor-relations/presentations',
        '/ir/events',
        '/ir/events-and-presentations',
        '/ir/earnings',
        '/ir/transcripts',
        '/investors',
        '/investor-relations',
    ]

    # Keywords in anchor text / href that suggest a transcript link
    _IR_TRANSCRIPT_LINK_KWS = [
        'transcript', 'earnings call', 'earnings transcript',
        'quarterly earnings', 'investor call', 'conference call',
        'q1 ', 'q2 ', 'q3 ', 'q4 ',
        'first quarter', 'second quarter', 'third quarter', 'fourth quarter',
    ]

    # ────────────────────────────────────────────────────────────────────────
    # Helper
    # ────────────────────────────────────────────────────────────────────────

    def _quarter_from_filing_date(self, filing_date: str) -> Tuple[int, int]:
        """
        Estimate the fiscal quarter and year from an 8-K filing date.

        Earnings calls are typically filed shortly after the quarter ends:
          Q1 (Jan–Mar results) → filed in Mar–May
          Q2 (Apr–Jun results) → filed in Jun–Aug
          Q3 (Jul–Sep results) → filed in Sep–Nov
          Q4 (Oct–Dec results) → filed in Jan–Feb of the FOLLOWING year

        Returns:
            (fiscal_year, quarter) or (0, 0) on parse error
        """
        if not filing_date or len(filing_date) < 7:
            return 0, 0
        try:
            year = int(filing_date[:4])
            month = int(filing_date[5:7])
            if month in (1, 2):
                return year - 1, 4   # Q4 filed in Jan/Feb of next year
            elif month in (3, 4, 5):
                return year, 1
            elif month in (6, 7, 8):
                return year, 2
            elif month in (9, 10, 11):
                return year, 3
            else:  # December — some companies file Q4 in Dec
                return year, 4
        except (ValueError, IndexError):
            return 0, 0

    # ────────────────────────────────────────────────────────────────────────
    # Source 1 — HuggingFace
    # ────────────────────────────────────────────────────────────────────────

    def _get_hf_cache_path(self) -> Path:
        """Return the local path for the cached HF parquet file."""
        cache_dir = Path(tempfile.gettempdir())
        return cache_dir / self.HF_CACHE_FILENAME

    def _ensure_hf_cache(self) -> Optional[Path]:
        """
        Download the Hugging Face dataset parquet to a local cache file the
        first time it is needed.  Subsequent calls return immediately.

        Returns the cache path, or None if the download failed.
        """
        cache_path = self._get_hf_cache_path()
        if cache_path.exists() and cache_path.stat().st_size > 10_000_000:
            logger.debug(f"[HF] Using cached parquet: {cache_path}")
            return cache_path

        logger.info(
            "[HF] Downloading S&P 500 earnings transcript dataset from "
            "Hugging Face (~562 MB, one-time download)…")

        # Try to resolve the exact shard filename via the HF dataset info API.
        shard_names: List[str] = []
        try:
            info_url = (
                "https://huggingface.co/api/datasets/"
                "glopardo/sp500-earnings-transcripts"
            )
            ir = requests.get(info_url, timeout=20)
            if ir.status_code == 200:
                siblings = ir.json().get("siblings", [])
                shard_names = [
                    s["rfilename"]
                    for s in siblings
                    if s.get("rfilename", "").startswith("data/") and
                    s["rfilename"].endswith(".parquet")
                ]
        except Exception:
            pass

        if not shard_names:
            shard_names = ["data/train-00000-of-00001.parquet"]

        try:
            import pandas as _pd
        except ImportError:
            logger.warning(
                "[HF] pandas not installed — cannot use HF transcript cache")
            return None

        frames = []
        for shard in shard_names:
            url = (
                "https://huggingface.co/datasets/"
                f"glopardo/sp500-earnings-transcripts/resolve/main/{shard}"
            )
            try:
                logger.info(f"[HF] Fetching shard: {shard}")
                r = requests.get(url, timeout=300, stream=True)
                if r.status_code != 200:
                    logger.warning(f"[HF] HTTP {r.status_code} for {url}")
                    continue
                buf = _io.BytesIO(r.content)
                frames.append(_pd.read_parquet(buf))
            except Exception as exc:
                logger.warning(f"[HF] Failed to fetch shard {shard}: {exc}")

        if not frames:
            logger.warning(
                "[HF] No shards downloaded — HF transcript source unavailable")
            return None

        df = _pd.concat(frames, ignore_index=True) if len(
            frames) > 1 else frames[0]
        df.to_parquet(str(cache_path), index=False)
        logger.info(f"[HF] Cached {len(df)} transcripts → {cache_path}")
        return cache_path

    def download_huggingface_transcripts(
            self, symbol: str, company_name: str,
            years_needed: Optional[List[int]] = None) -> List[str]:
        """
        Download earnings call transcripts from the Hugging Face dataset
        ``glopardo/sp500-earnings-transcripts``.

        Covers 496 S&P 500 companies from 2013Q2 to 2025Q1 (~20 000
        transcripts) with no API key required.  The full parquet is downloaded
        once to a local temp-dir cache; subsequent calls are instant.

        Returns:
            List of saved file paths.
        """
        saved_paths: List[str] = []

        try:
            import pandas as _pd
        except ImportError:
            logger.warning(
                "[HF] pandas not available — skipping HF transcript source")
            return saved_paths

        cache_path = self._ensure_hf_cache()
        if cache_path is None:
            return saved_paths

        try:
            df = _pd.read_parquet(str(cache_path), columns=[
                "ticker", "year", "quarter", "datacqtr",
                "earnings_date", "transcript"
            ])
        except Exception as exc:
            logger.warning(f"[HF] Failed to read cache: {exc}")
            return saved_paths

        sym_df = df[df["ticker"].str.upper() == symbol.upper()].copy()
        if sym_df.empty:
            logger.info(
                f"[HF] No transcripts found for {symbol} in HF dataset")
            return saved_paths

        if years_needed:
            sym_df = sym_df[sym_df["year"].isin(years_needed)]

        if sym_df.empty:
            logger.info(
                f"[HF] No transcripts for {symbol} in years {years_needed}")
            return saved_paths

        for _, row in sym_df.iterrows():
            try:
                yr = int(row["year"])
                raw_quarter = row.get("quarter")
                quarter = 0

                if _pd.notna(raw_quarter):
                    try:
                        quarter = int(
                            float(str(raw_quarter).strip().upper().lstrip("Q")))
                    except (TypeError, ValueError):
                        quarter = 0

                if quarter not in {1, 2, 3, 4}:
                    datacqtr = str(row.get("datacqtr", "")).strip().upper()
                    match = re.search(r"Q([1-4])$", datacqtr)
                    if match:
                        quarter = int(match.group(1))

                if quarter not in {1, 2, 3, 4}:
                    logger.warning(
                        f"[HF] Invalid quarter '{raw_quarter}' / datacqtr '{row.get('datacqtr', '')}' for {symbol} {yr}"
                    )
                    continue

                transcript_text = str(row.get("transcript", "")).strip()
                if len(transcript_text) < 200:
                    continue

                filing_date = str(row.get("earnings_date", f"{yr}-01-01"))[:10]
                filename_out = f"{symbol}_transcript_Q{quarter}_{yr}_hf.txt"

                if self._data_source_exists(company_name, yr, filename_out):
                    logger.debug(f"[HF] Already in DB: {filename_out}")
                    fp = self.base_download_dir / str(yr) / filename_out
                    if fp.exists():
                        saved_paths.append(str(fp))
                    continue

                header = (
                    f"SYMBOL: {symbol}\n"
                    f"COMPANY: {company_name}\n"
                    f"QUARTER: Q{quarter} {yr}\n"
                    f"DATE: {filing_date}\n"
                    f"SOURCE: Hugging Face — glopardo/sp500-earnings-transcripts\n"
                    f"{'=' * 80}\n\n"
                )
                content_bytes = (header + transcript_text).encode("utf-8")

                year_dir = self.base_download_dir / str(yr)
                year_dir.mkdir(parents=True, exist_ok=True)
                filepath = year_dir / filename_out

                if not filepath.exists():
                    filepath.write_bytes(content_bytes)
                    logger.info(f"[HF] Saved: {filepath}")
                else:
                    logger.debug(f"[HF] Already on disk: {filepath}")

                hf_url = (
                    f"https://huggingface.co/datasets/{self.HF_DATASET_ID}"
                    f"?ticker={symbol}&year={yr}&quarter={quarter}"
                )
                self._add_to_data_source(
                    company_name=company_name,
                    year=yr,
                    source_url=hf_url,
                    document_name=filename_out,
                    filepath=str(filepath),
                    content_type=4,
                    file_content=content_bytes,
                    original_source_url=hf_url,
                    search_query_used=(
                        f"HuggingFace glopardo/sp500-earnings-transcripts "
                        f"Q{quarter} {yr}"),
                    search_result_rank=1,
                    http_response_code=200,
                    company_symbol=symbol,
                )
                saved_paths.append(str(filepath))

            except Exception as exc:
                logger.warning(
                    f"[HF] Error processing row for {symbol}: {exc}")
                continue

        logger.info(
            f"[HF] {len(saved_paths)} transcript(s) saved for {symbol} from HF dataset")
        return saved_paths

    # ────────────────────────────────────────────────────────────────────────
    # Source 2 — EDGAR 8-K transcript exhibits
    # ────────────────────────────────────────────────────────────────────────

    def download_edgar_transcripts(
            self, symbol: str, company_name: str,
            years_needed: Optional[List[int]] = None) -> List[str]:
        """
        Download earnings call transcripts from SEC EDGAR 8-K exhibit filings.

        Many public companies attach their earnings call transcripts as an
        EX-99.x exhibit to an 8-K filed on the day of the call.  This method:
          1. Resolves the ticker → CIK(s) via the existing EDGAR CIK lookup
          2. Fetches 8-K filings from the EDGAR submissions API
          3. Inspects each filing's index for exhibits whose description
             or filename contains the word "transcript"
          4. Downloads the exhibit, strips HTML → plain text
          5. Saves as {SYMBOL}_transcript_Q{Q}_{YEAR}_{exhibit}.txt
             and registers in DB

        Returns:
            List of saved file paths.
        """
        saved_paths: List[str] = []

        all_ciks = self.get_all_ciks_for_symbol(symbol)
        if not all_ciks:
            logger.warning(
                f"[EDGAR-T] Cannot find CIK for {symbol} — skipping transcripts")
            return saved_paths

        if years_needed:
            relevant_filing_years: Optional[Set[int]] = (
                set(years_needed) | {y + 1 for y in years_needed}
            )
        else:
            relevant_filing_years = None

        base_hdrs = self._get_edgar_session_headers()
        sub_hdrs = {**base_hdrs, 'Host': 'data.sec.gov'}
        www_hdrs = {**base_hdrs, 'Host': 'www.sec.gov'}

        for cik in all_ciks:
            cik_int = int(cik)
            submissions_url = self.EDGAR_SUBMISSIONS_URL.format(cik=cik_int)
            try:
                resp = requests.get(
                    submissions_url, headers=sub_hdrs, timeout=30)
                resp.raise_for_status()
                sub_data = resp.json()
            except Exception as exc:
                logger.warning(
                    f"[EDGAR-T] Failed to fetch submissions for CIK {cik}: {exc}")
                continue

            eight_k_filings: List[Dict] = []

            def _collect_8k(block: dict) -> None:
                forms = block.get('form', [])
                accessions = block.get('accessionNumber', [])
                filing_dates = block.get('filingDate', [])
                for i, form in enumerate(forms):
                    if form not in ('8-K', '8-K/A'):
                        continue
                    fd = filing_dates[i] if i < len(filing_dates) else ''
                    if relevant_filing_years and fd:
                        try:
                            if int(fd[:4]) not in relevant_filing_years:
                                continue
                        except ValueError:
                            continue
                    eight_k_filings.append({
                        'accession': accessions[i],
                        'filing_date': fd,
                        'cik': cik_int,
                    })

            _collect_8k(sub_data.get('filings', {}).get('recent', {}))

            current_year = datetime.now().year
            if not years_needed or min(years_needed) < current_year - 3:
                for older_file in sub_data.get('filings', {}).get('files', []):
                    older_url = (
                        f"https://data.sec.gov/submissions/{older_file['name']}")
                    try:
                        or_ = requests.get(
                            older_url, headers=sub_hdrs, timeout=30)
                        or_.raise_for_status()
                        _collect_8k(or_.json())
                        time.sleep(0.2)
                    except Exception as exc:
                        logger.warning(
                            f"[EDGAR-T] Older submissions fetch failed: {exc}")

            logger.info(
                f"[EDGAR-T] {len(eight_k_filings)} 8-K filing(s) in scope for "
                f"{symbol} (CIK: {cik})")

            for filing in eight_k_filings:
                accession = filing['accession']
                accession_nodash = accession.replace('-', '')
                filing_date = filing['filing_date']

                index_url = (
                    f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/{accession_nodash}/"
                    f"{accession}-index.htm"
                )
                try:
                    time.sleep(0.15)
                    idx_resp = requests.get(
                        index_url, headers=www_hdrs, timeout=15)
                    if idx_resp.status_code != 200:
                        continue
                    idx_soup = BeautifulSoup(idx_resp.content, 'lxml')
                    idx_docs = []
                    for row in idx_soup.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) < 4:
                            continue
                        doc_link = cells[3].find('a')
                        idx_docs.append({
                            'type': cells[1].get_text(strip=True),
                            'description': cells[2].get_text(strip=True),
                            'filename': (
                                doc_link['href'].split('/')[-1] if doc_link else ''),
                        })
                except Exception as exc:
                    logger.debug(
                        f"[EDGAR-T] Index fetch failed for {accession}: {exc}")
                    continue

                for doc in idx_docs:
                    doc_type = doc.get('type', '')
                    description = doc.get('description', '').lower()
                    doc_fname = doc.get('filename', '')

                    is_exhibit = doc_type.startswith('EX-99')
                    is_transcript = (
                        'transcript' in description
                        or 'transcript' in doc_fname.lower()
                        or doc_type in ('EX-99.2', 'EX-99.3')
                    )
                    if not (is_exhibit and is_transcript):
                        continue

                    fiscal_year, quarter = self._quarter_from_filing_date(
                        filing_date)
                    if not fiscal_year:
                        continue
                    if years_needed and fiscal_year not in years_needed:
                        continue

                    exhibit_tag = doc_type.replace('EX-', '').replace('.', '_')
                    filename_out = (
                        f"{symbol}_transcript_Q{quarter}_{fiscal_year}_{exhibit_tag}.txt")

                    if self._data_source_exists(company_name, fiscal_year, filename_out):
                        logger.info(
                            f"[EDGAR-T] Already in DB: {filename_out} — skipping")
                        fp = self.base_download_dir / \
                            str(fiscal_year) / filename_out
                        if fp.exists():
                            saved_paths.append(str(fp))
                        continue

                    exhibit_url = (
                        f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/{accession_nodash}/"
                        f"{doc_fname}"
                    )
                    try:
                        time.sleep(max(self.delay_seconds * 0.25, 0.3))
                        ex_resp = requests.get(
                            exhibit_url, headers=www_hdrs, timeout=30)
                        if ex_resp.status_code != 200:
                            logger.warning(
                                f"[EDGAR-T] HTTP {ex_resp.status_code} "
                                f"for {exhibit_url}")
                            continue

                        raw = ex_resp.content
                        if (doc_fname.lower().endswith(('.htm', '.html'))
                                or b'<html' in raw[:200].lower()):
                            soup = BeautifulSoup(raw, 'lxml')
                            text = soup.get_text(separator='\n', strip=True)
                        else:
                            text = raw.decode('utf-8', errors='replace')

                        if len(text.strip()) < 500:
                            logger.info(
                                f"[EDGAR-T] Skipping near-empty exhibit: {exhibit_url}")
                            continue

                        header = (
                            f"SYMBOL: {symbol}\n"
                            f"COMPANY: {company_name}\n"
                            f"QUARTER: Q{quarter} {fiscal_year}\n"
                            f"DATE: {filing_date}\n"
                            f"SOURCE: SEC EDGAR 8-K ({doc_type}) — {accession}\n"
                            f"{'=' * 80}\n\n"
                        )
                        content_bytes = (header + text).encode('utf-8')

                        year_dir = self.base_download_dir / str(fiscal_year)
                        year_dir.mkdir(parents=True, exist_ok=True)
                        filepath = year_dir / filename_out

                        if not filepath.exists():
                            filepath.write_bytes(content_bytes)
                            logger.info(f"[EDGAR-T] Saved: {filepath}")
                        else:
                            logger.debug(
                                f"[EDGAR-T] Already on disk: {filepath}")

                        self._add_to_data_source(
                            company_name=company_name,
                            year=fiscal_year,
                            source_url=exhibit_url,
                            document_name=filename_out,
                            filepath=str(filepath),
                            content_type=4,
                            file_content=content_bytes,
                            original_source_url=exhibit_url,
                            search_query_used=f"EDGAR 8-K Q{quarter} {fiscal_year}",
                            search_result_rank=1,
                            http_response_code=ex_resp.status_code,
                            company_symbol=symbol,
                        )
                        saved_paths.append(str(filepath))

                    except Exception as exc:
                        logger.warning(
                            f"[EDGAR-T] Error downloading exhibit {exhibit_url}: {exc}")
                        continue

        logger.info(
            f"[EDGAR-T] {len(saved_paths)} transcript(s) saved for {symbol}")
        return saved_paths

    # ────────────────────────────────────────────────────────────────────────
    # Source 3 — IR website scraper
    # ────────────────────────────────────────────────────────────────────────

    def download_ir_website_transcripts(
            self, symbol: str, company_name: str, website: str,
            years_needed: Optional[List[int]] = None) -> List[str]:
        """
        Scrape earnings call transcripts from the company's own Investor
        Relations website (Investors → Events & Presentations).

        Strategy:
          1. Try common IR path patterns against the company domain
          2. On each page, locate anchor tags whose text/href contains
             transcript keywords
          3. HTML pages → strip to plain text; PDFs → download binary
          4. Estimate fiscal year/quarter from link text or URL, save as
             {SYMBOL}_transcript_Q{Q}_{YEAR}_ir.txt

        Returns:
            List of saved file paths.
        """
        saved_paths: List[str] = []

        if not website:
            return saved_paths

        raw_base = website.rstrip('/')
        if not raw_base.startswith('http'):
            raw_base = f'https://{raw_base}'

        override = self._IR_WEBSITE_OVERRIDES.get(symbol.upper())
        if override:
            ir_bases = [override, raw_base]
            logger.info(
                f"[IR-T] Using known IR override for {symbol}: {override}")
        else:
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(raw_base)
            apex = parsed.netloc.lstrip('www.')
            ir_bases = [
                f'https://investor.{apex}',
                f'https://investors.{apex}',
                f'https://ir.{apex}',
                raw_base,
            ]

        base = raw_base
        for candidate in ir_bases:
            try:
                probe = self.session.get(
                    candidate, timeout=10, allow_redirects=True)
                if probe.status_code == 200:
                    base = candidate
                    logger.info(
                        f"[IR-T] Resolved IR base for {symbol}: {base}")
                    break
            except Exception:
                continue

        visited_ir_pages: Set[str] = set()
        transcript_links: List[Tuple[str, str]] = []

        for path in self._IR_TRANSCRIPT_PATHS:
            url = base + path
            if url in visited_ir_pages:
                continue
            try:
                time.sleep(max(self.delay_seconds * 0.5, 0.5))
                resp = self.session.get(url, timeout=15, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                visited_ir_pages.add(resp.url)
                soup = BeautifulSoup(resp.content, 'lxml')

                for a in soup.find_all('a', href=True):
                    text = a.get_text(' ', strip=True).lower()
                    href = a['href'].lower()
                    if any(kw in text or kw in href
                           for kw in self._IR_TRANSCRIPT_LINK_KWS):
                        full = urljoin(resp.url, a['href'])
                        if (full, a.get_text(' ', strip=True)) not in transcript_links:
                            transcript_links.append(
                                (full, a.get_text(' ', strip=True)))

                logger.info(
                    f"[IR-T] Found {len(transcript_links)} candidate link(s) "
                    f"on {resp.url} for {symbol}")

                if len(transcript_links) >= 60:
                    break

            except Exception as exc:
                logger.debug(f"[IR-T] {url}: {exc}")
                continue

        if not transcript_links:
            logger.info(
                f"[IR-T] No transcript links found on IR site for {symbol}")
            return saved_paths

        logger.info(
            f"[IR-T] {len(transcript_links)} candidate transcript link(s) "
            f"for {symbol} — filtering by year and downloading")

        for link_url, anchor_text in transcript_links:
            year_match = re.search(r'(20\d{2})', anchor_text + ' ' + link_url)
            if not year_match:
                continue
            fiscal_year = int(year_match.group(1))
            if years_needed and fiscal_year not in years_needed:
                continue

            combined = (anchor_text + ' ' + link_url).lower()
            if any(x in combined for x in ('q1', 'first quarter', 'first-quarter')):
                quarter = 1
            elif any(x in combined for x in ('q2', 'second quarter', 'second-quarter')):
                quarter = 2
            elif any(x in combined for x in ('q3', 'third quarter', 'third-quarter')):
                quarter = 3
            elif any(x in combined for x in (
                    'q4', 'fourth quarter', 'fourth-quarter',
                    'full year', 'full-year', 'annual')):
                quarter = 4
            else:
                quarter = 0

            quarter_tag = f'Q{quarter}' if quarter else 'Qx'
            filename_out = f"{symbol}_transcript_{quarter_tag}_{fiscal_year}_ir.txt"

            if self._data_source_exists(company_name, fiscal_year, filename_out):
                logger.info(f"[IR-T] Already in DB: {filename_out} — skipping")
                fp = self.base_download_dir / str(fiscal_year) / filename_out
                if fp.exists():
                    saved_paths.append(str(fp))
                continue

            try:
                time.sleep(max(self.delay_seconds * 0.5, 0.5))
                ex_resp = self.session.get(link_url, timeout=30)
                if ex_resp.status_code != 200:
                    logger.debug(
                        f"[IR-T] HTTP {ex_resp.status_code} for {link_url}")
                    continue

                raw = ex_resp.content
                is_pdf = (
                    link_url.lower().endswith('.pdf')
                    or ex_resp.headers.get('Content-Type', '').startswith(
                        'application/pdf')
                )

                if is_pdf:
                    content_bytes = raw
                    filename_out = filename_out.replace('.txt', '.pdf')
                else:
                    page_soup = BeautifulSoup(raw, 'lxml')
                    text = page_soup.get_text(separator='\n', strip=True)
                    if len(text.strip()) < 500:
                        logger.debug(
                            f"[IR-T] Near-empty page, skipping: {link_url}")
                        continue
                    header = (
                        f"SYMBOL: {symbol}\n"
                        f"COMPANY: {company_name}\n"
                        f"QUARTER: {quarter_tag} {fiscal_year}\n"
                        f"SOURCE: Company IR Website — {link_url}\n"
                        f"ANCHOR: {anchor_text}\n"
                        f"{'=' * 80}\n\n"
                    )
                    content_bytes = (header + text).encode('utf-8')

                year_dir = self.base_download_dir / str(fiscal_year)
                year_dir.mkdir(parents=True, exist_ok=True)
                filepath = year_dir / filename_out

                if not filepath.exists():
                    filepath.write_bytes(content_bytes)
                    logger.info(f"[IR-T] Saved: {filepath}")
                else:
                    logger.debug(f"[IR-T] Already on disk: {filepath}")

                self._add_to_data_source(
                    company_name=company_name,
                    year=fiscal_year,
                    source_url=link_url,
                    document_name=filename_out,
                    filepath=str(filepath),
                    content_type=4,
                    file_content=content_bytes,
                    original_source_url=link_url,
                    search_query_used=f"IR website {quarter_tag} {fiscal_year}",
                    search_result_rank=1,
                    http_response_code=ex_resp.status_code,
                    company_symbol=symbol,
                )
                saved_paths.append(str(filepath))

            except Exception as exc:
                logger.warning(f"[IR-T] Error downloading {link_url}: {exc}")
                continue

        logger.info(
            f"[IR-T] {len(saved_paths)} IR website transcript(s) saved for {symbol}")
        return saved_paths

    # ────────────────────────────────────────────────────────────────────────
    # Source 4 — Financial Modeling Prep (FMP)
    # ────────────────────────────────────────────────────────────────────────

    def download_fmp_transcripts(
            self, symbol: str, company_name: str,
            years_needed: Optional[List[int]] = None) -> List[str]:
        """
        Download earnings call transcripts from Financial Modeling Prep (FMP).

        NOTE: As of Aug 31 2025 this endpoint returns HTTP 402 (subscription
        required) for all callers on the free tier.  The method fast-fails on
        the first 402 to avoid wasting N×4 requests.

        Returns:
            List of saved file paths.
        """
        saved_paths: List[str] = []

        if years_needed:
            target_years = sorted(years_needed)
        else:
            current_yr = datetime.now().year
            target_years = list(range(2012, current_yr + 1))

        url_base = f"{FMP_STABLE_BASE_URL}/earning-call-transcript"

        for year in target_years:
            for quarter in (1, 2, 3, 4):
                filename_out = f"{symbol}_transcript_Q{quarter}_{year}_fmp.txt"

                if self._data_source_exists(company_name, year, filename_out):
                    logger.debug(
                        f"[FMP-T] Already in DB: {filename_out} — skipping")
                    fp = self.base_download_dir / str(year) / filename_out
                    if fp.exists():
                        saved_paths.append(str(fp))
                    continue

                try:
                    time.sleep(0.25)
                    resp = requests.get(
                        url_base,
                        params={
                            'symbol':  symbol,
                            'year':    year,
                            'quarter': quarter,
                            'apikey':  FMP_API_KEY,
                        },
                        timeout=20,
                    )
                    if resp.status_code == 402:
                        logger.warning(
                            f"[FMP-T] HTTP 402 (subscription required) for "
                            f"{symbol} — FMP transcripts unavailable; "
                            f"skipping all remaining quarters/years")
                        return saved_paths
                    if resp.status_code != 200:
                        logger.debug(
                            f"[FMP-T] HTTP {resp.status_code} for "
                            f"{symbol} Q{quarter} {year}")
                        continue

                    data = resp.json()
                    if not data or not isinstance(data, list):
                        continue
                    entry = data[0]
                    content = entry.get('content', '').strip()
                    if len(content) < 500:
                        logger.debug(
                            f"[FMP-T] Near-empty transcript for "
                            f"{symbol} Q{quarter} {year} — skipping")
                        continue

                    filing_date = entry.get('date', f"{year}-01-01")[:10]
                    header = (
                        f"SYMBOL: {symbol}\n"
                        f"COMPANY: {company_name}\n"
                        f"QUARTER: Q{quarter} {year}\n"
                        f"DATE: {filing_date}\n"
                        f"SOURCE: Financial Modeling Prep (FMP)\n"
                        f"{'=' * 80}\n\n"
                    )
                    content_bytes = (header + content).encode('utf-8')

                    year_dir = self.base_download_dir / str(year)
                    year_dir.mkdir(parents=True, exist_ok=True)
                    filepath = year_dir / filename_out

                    if not filepath.exists():
                        filepath.write_bytes(content_bytes)
                        logger.info(f"[FMP-T] Saved: {filepath}")
                    else:
                        logger.debug(f"[FMP-T] Already on disk: {filepath}")

                    fmp_url = (
                        f"{url_base}?symbol={symbol}&year={year}&quarter={quarter}")
                    self._add_to_data_source(
                        company_name=company_name,
                        year=year,
                        source_url=fmp_url,
                        document_name=filename_out,
                        filepath=str(filepath),
                        content_type=4,
                        file_content=content_bytes,
                        original_source_url=fmp_url,
                        search_query_used=(
                            f"FMP earning-call-transcript Q{quarter} {year}"),
                        search_result_rank=1,
                        http_response_code=resp.status_code,
                        company_symbol=symbol,
                    )
                    saved_paths.append(str(filepath))

                except Exception as exc:
                    logger.warning(
                        f"[FMP-T] Error for {symbol} Q{quarter} {year}: {exc}")
                    continue

        logger.info(
            f"[FMP-T] {len(saved_paths)} FMP transcript(s) saved for {symbol}")
        return saved_paths

    # ────────────────────────────────────────────────────────────────────────
    # Source 5 — EDGAR 8-K EX-99.1 earnings press releases (last-resort)
    # ────────────────────────────────────────────────────────────────────────

    def download_edgar_press_releases(
            self, symbol: str, company_name: str,
            years_needed: Optional[List[int]] = None) -> List[str]:
        """
        Download earnings press releases from SEC EDGAR 8-K EX-99.1 exhibits.

        Used as the final fallback for companies (e.g. Apple) that never file
        a written transcript.  Saves as {SYMBOL}_earnings_pr_Q{Q}_{YEAR}.txt
        and registers in t_data_source (content_type=4).

        Returns:
            List of local file paths for successfully downloaded press releases.
        """
        saved_paths: List[str] = []

        all_ciks = self.get_all_ciks_for_symbol(symbol)
        if not all_ciks:
            logger.warning(
                f"[EDGAR-PR] Cannot find CIK for {symbol} — skipping press releases")
            return saved_paths

        if years_needed:
            relevant_filing_years: Optional[Set[int]] = (
                set(years_needed) | {y + 1 for y in years_needed}
            )
        else:
            relevant_filing_years = None

        base_hdrs = self._get_edgar_session_headers()
        sub_hdrs = {**base_hdrs, 'Host': 'data.sec.gov'}
        www_hdrs = {**base_hdrs, 'Host': 'www.sec.gov'}

        _PR_KEYWORDS = frozenset([
            'earnings', 'results', 'financial results', 'press release',
            'quarterly results', 'annual results', 'income',
        ])

        for cik in all_ciks:
            cik_int = int(cik)
            submissions_url = self.EDGAR_SUBMISSIONS_URL.format(cik=cik_int)
            try:
                resp = requests.get(
                    submissions_url, headers=sub_hdrs, timeout=30)
                resp.raise_for_status()
                sub_data = resp.json()
            except Exception as exc:
                logger.warning(
                    f"[EDGAR-PR] Failed to fetch submissions for CIK {cik}: {exc}")
                continue

            eight_k_filings: List[Dict] = []

            def _collect_8k_pr(block: dict) -> None:
                forms = block.get('form', [])
                accessions = block.get('accessionNumber', [])
                filing_dates = block.get('filingDate', [])
                for i, form in enumerate(forms):
                    if form not in ('8-K', '8-K/A'):
                        continue
                    fd = filing_dates[i] if i < len(filing_dates) else ''
                    if relevant_filing_years and fd:
                        try:
                            if int(fd[:4]) not in relevant_filing_years:
                                continue
                        except ValueError:
                            continue
                    eight_k_filings.append({
                        'accession': accessions[i],
                        'filing_date': fd,
                        'cik': cik_int,
                    })

            _collect_8k_pr(sub_data.get('filings', {}).get('recent', {}))

            current_year = datetime.now().year
            if not years_needed or min(years_needed) < current_year - 3:
                for older_file in sub_data.get('filings', {}).get('files', []):
                    older_url = (
                        f"https://data.sec.gov/submissions/{older_file['name']}")
                    try:
                        or_ = requests.get(
                            older_url, headers=sub_hdrs, timeout=30)
                        or_.raise_for_status()
                        _collect_8k_pr(or_.json())
                        time.sleep(0.2)
                    except Exception as exc:
                        logger.warning(
                            f"[EDGAR-PR] Older submissions fetch failed: {exc}")

            logger.info(
                f"[EDGAR-PR] {len(eight_k_filings)} 8-K filing(s) in scope for "
                f"{symbol} (CIK: {cik})")

            for filing in eight_k_filings:
                accession = filing['accession']
                accession_nodash = accession.replace('-', '')
                filing_date = filing['filing_date']

                index_url = (
                    f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/{accession_nodash}/"
                    f"{accession}-index.htm"
                )
                try:
                    time.sleep(0.15)
                    idx_resp = requests.get(
                        index_url, headers=www_hdrs, timeout=15)
                    if idx_resp.status_code != 200:
                        continue
                    idx_soup = BeautifulSoup(idx_resp.content, 'lxml')
                    idx_docs = []
                    for row in idx_soup.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) < 4:
                            continue
                        doc_link = cells[3].find('a')
                        idx_docs.append({
                            'type': cells[1].get_text(strip=True),
                            'description': cells[2].get_text(strip=True),
                            'filename': (
                                doc_link['href'].split('/')[-1] if doc_link else ''),
                        })
                except Exception as exc:
                    logger.debug(
                        f"[EDGAR-PR] Index fetch failed for {accession}: {exc}")
                    continue

                for doc in idx_docs:
                    doc_type = doc.get('type', '')
                    description = doc.get('description', '').lower()
                    doc_fname = doc.get('filename', '').lower()

                    if doc_type != 'EX-99.1':
                        continue
                    if 'transcript' in description or 'transcript' in doc_fname:
                        continue
                    if not any(kw in description or kw in doc_fname
                               for kw in _PR_KEYWORDS):
                        continue

                    fiscal_year, quarter = self._quarter_from_filing_date(
                        filing_date)
                    if not fiscal_year:
                        continue
                    if years_needed and fiscal_year not in years_needed:
                        continue

                    filename_out = (
                        f"{symbol}_earnings_pr_Q{quarter}_{fiscal_year}.txt")

                    if self._data_source_exists(
                            company_name, fiscal_year, filename_out):
                        logger.info(
                            f"[EDGAR-PR] Already in DB: {filename_out} — skipping")
                        fp = self.base_download_dir / \
                            str(fiscal_year) / filename_out
                        if fp.exists():
                            saved_paths.append(str(fp))
                        continue

                    exhibit_url = (
                        f"{self.EDGAR_ARCHIVES_BASE}{cik_int}/{accession_nodash}/"
                        f"{doc.get('filename', '')}"
                    )
                    try:
                        time.sleep(max(self.delay_seconds * 0.25, 0.3))
                        ex_resp = requests.get(
                            exhibit_url, headers=www_hdrs, timeout=30)
                        if ex_resp.status_code != 200:
                            logger.warning(
                                f"[EDGAR-PR] HTTP {ex_resp.status_code} "
                                f"for {exhibit_url}")
                            continue

                        raw = ex_resp.content
                        if (doc.get('filename', '').lower().endswith(('.htm', '.html'))
                                or b'<html' in raw[:200].lower()):
                            soup = BeautifulSoup(raw, 'lxml')
                            text = soup.get_text(separator='\n', strip=True)
                        else:
                            text = raw.decode('utf-8', errors='replace')

                        if len(text.strip()) < 300:
                            logger.info(
                                f"[EDGAR-PR] Skipping near-empty exhibit: {exhibit_url}")
                            continue

                        header = (
                            f"SYMBOL: {symbol}\n"
                            f"COMPANY: {company_name}\n"
                            f"QUARTER: Q{quarter} {fiscal_year}\n"
                            f"DATE: {filing_date}\n"
                            f"SOURCE: SEC EDGAR 8-K EX-99.1 "
                            f"(Earnings Press Release) — {accession}\n"
                            f"{'=' * 80}\n\n"
                        )
                        content_bytes = (header + text).encode('utf-8')

                        year_dir = self.base_download_dir / str(fiscal_year)
                        year_dir.mkdir(parents=True, exist_ok=True)
                        filepath = year_dir / filename_out

                        if not filepath.exists():
                            filepath.write_bytes(content_bytes)
                            logger.info(f"[EDGAR-PR] Saved: {filepath}")
                        else:
                            logger.debug(
                                f"[EDGAR-PR] Already on disk: {filepath}")

                        self._add_to_data_source(
                            company_name=company_name,
                            year=fiscal_year,
                            source_url=exhibit_url,
                            document_name=filename_out,
                            filepath=str(filepath),
                            content_type=4,
                            file_content=content_bytes,
                            original_source_url=exhibit_url,
                            search_query_used=(
                                f"EDGAR 8-K EX-99.1 Q{quarter} {fiscal_year}"),
                            search_result_rank=1,
                            http_response_code=ex_resp.status_code,
                            company_symbol=symbol,
                        )
                        saved_paths.append(str(filepath))

                    except Exception as exc:
                        logger.warning(
                            f"[EDGAR-PR] Error downloading exhibit "
                            f"{exhibit_url}: {exc}")
                        continue

        logger.info(
            f"[EDGAR-PR] {len(saved_paths)} press release(s) saved for {symbol}")
        return saved_paths
