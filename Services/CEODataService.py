"""
CEODataService.py
-----------------
Two-stage pipeline for every S&P 500 company × year:

  Stage 1 – CEO identification
    Primary  : FMP /stable/historical-key-executives + key-executives
    Secondary: Local 10-K PDF (t_data_source content_type=2, Stage0SourcePDFFiles)
    Tertiary : DDGS web search "{company} CEO {year}" + name extraction heuristic

  Stage 2 – Statement collection
    Primary  : FMP /stable/earning_call_transcript (structured; CEO text extracted)
    Secondary: DDGS news search + article scrape

Tables created automatically on first run:
    t_ceo              (company_name, ticker, year, ceo_name, source, ...)
    t_ceo_statements   (ceo_id FK, statement_text, statement_type, source_url, ...)
"""

from __future__ import annotations

import logging
import re
import time
import threading
import functools
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Callable
import requests
from bs4 import BeautifulSoup

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    from Utilities.Lookups import DB_Connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

try:
    from openai import OpenAI as _OpenAI
    _openai_client = _OpenAI()   # reads OPENAI_API_KEY from env
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── FMP constants (same key used in SustainabilityReportDownloader) ───────────
FMP_API_KEY = 'j1sUHyVT1lU3gsc2l6zF2jkuleFJEA2o'
FMP_BASE = 'https://financialmodelingprep.com/stable'
# seconds between calls  ≈ 270 calls/min (free: 300/min)
FMP_RATE_LIMIT = 0.22

# ── DDG rate limit ─────────────────────────────────────────────────────────────
DDGS_DELAY = 1.5   # seconds between DDGS calls

_fmp_lock = threading.Lock()
_fmp_last = [0.0]
_ddgs_lock = threading.Lock()
_ddgs_last = [0.0]
_openai_lock = threading.Lock()
_openai_last = [0.0]
_OPENAI_RATE_LIMIT = 0.5          # 2 req/s — conservative
_openai_cache: dict = {}          # (ticker_or_name, year) → name | None

# Thread-local DB connections — psycopg2 connections are NOT thread-safe.
# Each worker thread gets its own connection via _get_thread_conn().
_thread_local = threading.local()


def _get_thread_conn():
    """Return a per-thread psycopg2 connection, creating one if needed.

    Detects silently-broken connections via a cheap liveness ping so a
    stale TCP socket never causes a query to hang indefinitely.
    statement_timeout=30s provides a hard cap even if the ping passes.
    """
    conn = getattr(_thread_local, 'conn', None)
    if conn is not None and not conn.closed:
        # Verify the connection is still alive (catches silently-broken TCP).
        try:
            conn.cursor().execute('SELECT 1')
        except Exception:
            conn = None  # will reconnect below
    if conn is None or conn.closed:
        try:
            conn = psycopg2.connect(
                DB_Connection().DB_CONNECTION_STRING,
                connect_timeout=10,
                options='-c statement_timeout=30000',  # 30-s hard cap on any query
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=5,
                keepalives_count=3,
            )
            conn.autocommit = True
            _thread_local.conn = conn
        except Exception as e:
            logger.error('_get_thread_conn failed: %s', e)
            raise
    return conn


def _fmp_get(path: str, params: dict = None) -> list | dict | None:
    """Rate-limited FMP GET."""
    with _fmp_lock:
        wait = FMP_RATE_LIMIT - (time.monotonic() - _fmp_last[0])
        if wait > 0:
            time.sleep(wait)
        _fmp_last[0] = time.monotonic()

    p = params or {}
    p['apikey'] = FMP_API_KEY
    try:
        r = requests.get(f"{FMP_BASE}{path}", params=p, timeout=15)
        if r.status_code == 200:
            return r.json()
        logger.debug("FMP %s → HTTP %s", path, r.status_code)
    except Exception as e:
        logger.debug("FMP error %s: %s", path, e)
    return None


_DDGS_CALL_TIMEOUT = 20   # hard wall-clock seconds per DDGS HTTP call
_DDGS_BACKOFF_SECS = 30   # pause DDGS only after an actual hang/timeout
_ddgs_backoff_until = [0.0]  # monotonic time; protected by _ddgs_lock
_ddgs_consecutive_empty = [0]  # count of consecutive empty (no-results) calls


def _ddgs_text(query: str, max_results: int = 5) -> list[dict]:
    """
    Rate-limited, serialized DDGS text search with a hard per-call timeout.

    Backoff policy:
      - Only backs off on TIMEOUT (hung curl_cffi call > 20s), NOT on empty results.
        Empty results just mean "no CEO found this query" — legitimate for old/small tickers.
      - After 5 consecutive empty calls, adds a 10s extra delay (search engine cool-down).
    """
    with _ddgs_lock:
        # Skip entirely if still in a timeout-backoff window
        now = time.monotonic()
        if now < _ddgs_backoff_until[0]:
            remaining = int(_ddgs_backoff_until[0] - now)
            logger.debug("DDGS in backoff, skipping for %ds more", remaining)
            return []

        # Extra delay after many consecutive empties (likely rate-limited)
        if _ddgs_consecutive_empty[0] >= 5:
            extra = min(_ddgs_consecutive_empty[0] * 2, 20)
            logger.debug("DDGS %d consecutive empties — extra %ds delay",
                         _ddgs_consecutive_empty[0], extra)
            time.sleep(extra)

        wait = DDGS_DELAY - (time.monotonic() - _ddgs_last[0])
        if wait > 0:
            time.sleep(wait)

        results: list[dict] = []
        try:
            _container: list = []

            def _call():
                try:
                    with DDGS(timeout=12) as ddgs:
                        _container.extend(
                            ddgs.text(query, max_results=max_results))
                except Exception as _e:
                    logger.debug("DDGS inner error '%s': %s", query, _e)
            _t = threading.Thread(target=_call, daemon=True)
            _t.start()
            _t.join(timeout=_DDGS_CALL_TIMEOUT)
            if _t.is_alive():
                # Actual hang — back off
                logger.warning("DDGS call timed out after %ds, backing off %ds: %s",
                               _DDGS_CALL_TIMEOUT, _DDGS_BACKOFF_SECS, query[:80])
                _ddgs_backoff_until[0] = time.monotonic() + _DDGS_BACKOFF_SECS
                _ddgs_consecutive_empty[0] = 0
            else:
                results = list(_container)
                if results:
                    _ddgs_consecutive_empty[0] = 0
                else:
                    _ddgs_consecutive_empty[0] += 1
        except Exception as e:
            logger.debug("DDGS error '%s': %s", query, e)
        _ddgs_last[0] = time.monotonic()
    return results


# ── EDGAR constants ────────────────────────────────────────────────────────────
EDGAR_BASE = 'https://data.sec.gov'
EDGAR_HEADERS = {
    'User-Agent': 'Avisk-AI-Platform contact@avisk.ai',
    'Accept-Encoding': 'gzip, deflate',
}
EDGAR_RATE_LIMIT = 0.12   # ~8 req/s  (SEC allows 10/s)

_edgar_lock = threading.Lock()
_edgar_last = [0.0]


def _edgar_get(url: str, **kwargs) -> Optional[requests.Response]:
    """Rate-limited GET for any SEC/EDGAR endpoint."""
    with _edgar_lock:
        wait = EDGAR_RATE_LIMIT - (time.monotonic() - _edgar_last[0])
        if wait > 0:
            time.sleep(wait)
        _edgar_last[0] = time.monotonic()
    try:
        r = requests.get(url, headers=EDGAR_HEADERS, timeout=15, **kwargs)
        if r.status_code == 200:
            return r
        logger.debug("EDGAR %s → HTTP %s", url, r.status_code)
    except Exception as e:
        logger.debug("EDGAR error %s: %s", url, e)
    return None


# ── Ticker → CIK map  (fetched once, cached in memory) ────────────────────────
@functools.lru_cache(maxsize=1)
def _edgar_ticker_to_cik() -> dict[str, str]:
    """
    Returns {TICKER: '0001234567'} for every company in EDGAR.
    Source: https://www.sec.gov/files/company_tickers.json
    """
    r = _edgar_get('https://www.sec.gov/files/company_tickers.json')
    if not r:
        return {}
    data = r.json()
    mapping: dict[str, str] = {}
    for entry in data.values():
        ticker = (entry.get('ticker') or '').upper().strip()
        cik = str(entry.get('cik_str') or '').zfill(10)
        if ticker and cik:
            mapping[ticker] = cik
    logger.info("EDGAR ticker map loaded: %d entries", len(mapping))
    return mapping


def _cik_for_ticker(ticker: str) -> Optional[str]:
    """Return zero-padded 10-digit CIK string or None."""
    if not ticker:
        return None
    m = _edgar_ticker_to_cik()
    return m.get(ticker.upper().strip())


# ── Filing lookup ──────────────────────────────────────────────────────────────

def _get_filings_for_year(cik: str, year: int,
                          form_types: list[str]) -> list[dict]:
    """
    Fetch the company's submission history and return filings of the
    requested form types filed in `year` or `year+1` Q1
    (proxy statements for fiscal year N are typically filed Jan–Apr N+1).
    """
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    r = _edgar_get(url)
    if not r:
        return []

    subs = r.json()
    recent = subs.get('filings', {}).get('recent', {})
    forms = recent.get('form', [])
    dates = recent.get('filingDate', [])
    accnums = recent.get('accessionNumber', [])
    primary = recent.get('primaryDocument', [])

    results = []
    for form, filed, accn, doc in zip(forms, dates, accnums, primary):
        if form not in form_types:
            continue
        try:
            filed_year = int(filed[:4])
        except (ValueError, TypeError):
            continue
        # DEF 14A for FY{year} is usually filed in year or year+1 Q1
        if filed_year == year or (filed_year == year + 1 and filed[5:7] <= '04'):
            results.append({
                'form': form,
                'filed': filed,
                'accn': accn.replace('-', ''),
                'doc': doc,
                'cik': cik,
            })
    # Prefer filings from same year; sort by date desc
    results.sort(key=lambda x: x['filed'], reverse=True)
    return results


def _filing_url(cik: str, accn: str, doc: str) -> str:
    return (f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{accn}/{doc}")


# ── CEO name extraction from SEC text ─────────────────────────────────────────

# Strict Title-Case name: 2–4 words, 2–25 chars each, no common words
_NOT_NAME_WORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'by', 'for', 'to', 'from',
    'with', 'and', 'or', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
    # 'will' removed — valid CEO surname (Tony Will)
    'has', 'have', 'had', 'would', 'could', 'should', 'might',
    'this', 'that', 'these', 'those', 'it', 'its', 'he', 'she', 'his', 'her',
    'they', 'their', 'we', 'our', 'you', 'your', 'i', 'my', 'me',
    'prior', 'after', 'before', 'during', 'since', 'until', 'who', 'which',
    'what', 'when', 'where', 'how', 'why', 'not', 'no', 'yes', 'than',
    'then', 'also', 'but', 'so', 'if', 'as', 'up', 'out', 'about', 'into',
    # corporate roles / titles
    'chief', 'executive', 'officer', 'president', 'chairman', 'chair',
    'director', 'senior', 'vice', 'principal', 'managing', 'general',
    'counsel', 'secretary', 'treasurer', 'independent', 'outside',
    # company / entity words
    'global', 'group', 'company', 'corp', 'inc', 'llc', 'ltd', 'limited',
    'corporation', 'holdings', 'division', 'corporate', 'international',
    'services', 'solutions', 'management', 'partners', 'associates',
    'consulting', 'advisors', 'industries', 'technologies', 'ventures',
    # compensation / equity plan words  ← key additions
    'restricted', 'stock', 'unit', 'award', 'grant', 'equity', 'incentive',
    'performance', 'plan', 'agreement', 'compensation', 'committee',
    'option', 'vesting', 'accelerated', 'acceleration',
    # finance / audit words
    'financial', 'accounting', 'audit', 'auditor', 'fiscal', 'operating',
    'technology', 'information', 'marketing', 'sales', 'legal',
    # calendar — only months unlikely to be surnames; May removed (common surname: John May)
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    # other noise
    'new', 'old', 'first', 'last', 'next', 'more', 'most', 'some', 'few',
    'pursuant', 'section', 'board', 'annual', 'meeting', 'year',
    'certain', 'following', 'applicable', 'below', 'above', 'herein',
    'including', 'related', 'respective', 'other', 'such', 'any',
    # role / advisory titles that are NOT the CEO
    'special', 'advisor', 'independent', 'outside', 'lead', 'emeritus',
    'interim', 'acting', 'deputy', 'assistant', 'associate', 'executive',
    # 10-K section headings / pay-ratio language
    'pay', 'ratio', 'message', 'letter', 'shareholders', 'overview',
    'summary', 'highlights', 'discussion', 'analysis', 'results',
    'business', 'risk', 'factors', 'governance', 'proxy', 'notice',
    'report', 'review', 'outlook', 'strategy', 'vision', 'mission',
    # additional financial / org words
    'human', 'resources', 'capital', 'digital', 'data', 'supply',
    'chain', 'brand', 'consumer', 'growth', 'revenue', 'profit',
    'audit', 'compliance', 'regulatory', 'finance', 'treasury',
    # geographic / country / entity words  ← stop "Grameen America", "North America" etc.
    'america', 'americas', 'europe', 'european', 'asia', 'asian',
    'africa', 'african', 'australia', 'australian', 'pacific',
    'north', 'south', 'east', 'west', 'central', 'united', 'states',
    'national', 'federal', 'government', 'grameen', 'bank',
    'foundation', 'institute', 'university', 'college', 'school',
    'fund', 'trust', 'association', 'society', 'alliance', 'network',
    # known company-name words that appear in director bios in proxy statements
    'northrop', 'grumman', 'boeing', 'lockheed', 'raytheon', 'honeywell',
    'comcast', 'chevron', 'exxon', 'pfizer', 'merck', 'abbott',
    # industrial / product / segment words  ← stop "Commercial Engines", "Power Systems" etc.
    'commercial', 'industrial', 'aerospace', 'aviation', 'defense', 'power',
    'energy', 'engines', 'engine', 'systems', 'system', 'products', 'product',
    'healthcare', 'medical', 'pharma', 'pharmaceutical', 'biotech',
    'infrastructure', 'construction', 'transportation', 'logistics',
    'insurance', 'banking', 'investment', 'ventures', 'enterprises',
    'semiconductor', 'software', 'hardware', 'cloud', 'platform',
    'retail', 'wholesale', 'distribution', 'manufacturing', 'production',
}

# Allows: Smith, DeRosa, McKenzie, O'Day, O'Brien, Smith-Jones,
#         André, Calantzopoulos, Jørgen, Björn, etc.
_WORD_RE = re.compile(
    r"[A-ZÀ-ÖØ-Ý][a-zA-ZÀ-ÖØ-öø-ÿ]{0,23}"
    r"(?:'[A-ZÀ-ÖØ-Ý][a-zA-ZÀ-ÖØ-öø-ÿ]{1,23})?"
    r"(?:-[A-ZÀ-ÖØ-Ý][a-zA-ZÀ-ÖØ-öø-ÿ]{1,24})?",
    re.UNICODE,
)
# Matches a middle initial like "D" or "D."
_INITIAL_RE = re.compile(r'^[A-Z]\.?$')

# Lowercase name particles common in Dutch/German/French/Portuguese/Arabic names
# e.g. "Aart de Geus", "Jan van Rijswijk", "Claudio del Vecchio"
_NAME_PARTICLES = frozenset({
    'de', 'van', 'von', 'der', 'den', 'du', 'da', 'di',
    'la', 'le', 'del', 'della', 'des', 'dos', 'das',
    'el', 'al', 'bin', 'binte', 'op', 'ten', 'ter',
})


# Strips honorific prefixes that FMP/OpenAI sometimes include before the name.
# E.g. 'Dr. F. Thomson Leighton' → 'F. Thomson Leighton' before initial-stripping.
_HONORIFIC_RE = re.compile(
    r'^(?:Dr|Mr|Mrs|Ms|Miss|Prof|Sir|Dame|Lord|Hon|Rev|Gen|Col|Lt|Cpl|Capt|Adm)\.?\s+',
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """Strip honorifics, middle initials, and lowercase name particles.

    Examples:
      'Timothy D. Cook'         -> 'Timothy Cook'
      'Dr. F. Thomson Leighton' -> 'Thomson Leighton'
      'Aart J. de Geus'         -> 'Aart Geus'
      'Jan van Rijswijk'        -> 'Jan Rijswijk'
    """
    name = _HONORIFIC_RE.sub('', name).strip()
    return ' '.join(
        w for w in name.split()
        if not _INITIAL_RE.fullmatch(w) and w.lower() not in _NAME_PARTICLES
    )


def _is_valid_name(name: str) -> bool:
    # Strip middle initials + particles first, then validate remaining words
    normalized = _normalize_name(name)
    words = normalized.split()
    # Need 2-3 proper name words (after stripping initials/particles)
    if not (2 <= len(words) <= 3):
        return False
    # Total original word count <=5 (e.g. First M. de Last1 Last2)
    orig_words = name.split()
    if len(orig_words) > 5:
        return False
    for w in words:
        if not _WORD_RE.fullmatch(w):
            return False
        if w.lower() in _NOT_NAME_WORDS:
            return False
    return True


# Word-or-initial component for name capture groups.
# Uses [a-zA-Z] (not just [a-z]) so mixed-case surnames like McDonnell,
# MacKenzie, DeRosa, O'Brien are captured in full by the regex before
# _is_valid_name validates them with _WORD_RE.
_W = r'(?:[A-Z]\.?|[A-Z][a-zA-Z]{1,24})'

# Patterns for SEC/10-K structured text — strict, prevent mid-sentence matches
_SEC_CEO_PATTERNS = [
    # 1. Signature block:  "/s/ Timothy D. Cook" then newlines then "Chief Executive Officer"
    re.compile(
        r'/s/[ \t]+([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})[ \t]*\n'
        r'[^\n]*\n[^\n]*Chief Executive Officer', re.M),
    # 2. Officer table row (line-start anchored):
    #    "Timothy D. Cook    63    Chief Executive Officer"
    #    Name must be at line-start; only whitespace/digits before the title.
    #    Negative lookahead prevents "CEO and Chairman" or "CEO of [Company]"
    #    (those appear in director-bio sections of proxy statements).
    re.compile(
        r'(?:^|\n)[ \t]*([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})'
        r'[ \t]+(?:\d+[ \t]+)?Chief Executive Officer'
        r'(?![ \t]+(?:and|of|formerly|since|until|&)\b)', re.M),
    # 2b. Officer table — ALL multi-line EDGAR formats:
    #    a) XBRL 3-line:  "Robert A. Michael\n55\nChairman... Chief Executive Officer"
    #    b) Prose-age:    "Padraig McDonnell\n, 53, has served as ... Chief Executive Officer"
    #    c) No-age:       "Ron M. Vachris\nPresident and Chief Executive Officer"
    #    The optional bare-age sub-pattern handles (a); [^\n]{0,100} handles (b) and (c).
    re.compile(
        r'(?:^|\n)[ \t]*([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})'
        r'[ \t]*\n'
        r'[ \t]*(?:\d{1,3}[ \t]*\n[ \t]*)?'   # optional bare-age line (XBRL)
        r'[^\n]{0,100}Chief Executive Officer',
        re.M),
    # 3. Reverse — name after title with optional comma or parenthetical:
    #    "Chief Executive Officer  Timothy D. Cook"
    #    "Chief Executive Officer, Timothy D. Cook"
    #    "Chief Executive Officer (CEO) Timothy D. Cook"
    re.compile(
        r'Chief Executive Officer(?:\s*\([^)]{1,15}\))?[,]?[ \t]+'
        r'([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'),
    # 4. "CEO John Smith" or "CEO, John Smith"
    re.compile(
        r'\bCEO[,:\s]+([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'),
    # 5. Signature block Name:/Title: lines (EDGAR filing signature page):
    #    "Name:\nRobert A. Michael\nTitle:\nChairman and Chief Executive Officer"
    #    The title label and title text may be on the same OR successive lines.
    re.compile(
        r'Name:[ \t]*\n[ \t]*([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})'
        r'[ \t]*\n[ \t]*Title:[ \t]*\n?[^\n]*Chief Executive Officer',
        re.M),
    # 6. Co-CEO: "Co-Chief Executive Officers, Ted Sarandos and Greg Peters"
    #    Take the first name listed.
    re.compile(
        r'[Cc]o[-\s]?Chief Executive Officer[s]?[,\s]+'
        r'([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'),
]

# Patterns for web/DDGS snippets — looser, allow name within 50 chars of title
_WEB_CEO_PATTERNS = [
    # Forward: "Timothy D. Cook ... Chief Executive Officer"  (max 50 chars between)
    re.compile(
        r'\b([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'
        r'(?:[^\n]{0,50})Chief Executive Officer'),
    # Reverse: "Chief Executive Officer ... Timothy D. Cook"  (max 50 chars between)
    re.compile(
        r'Chief Executive Officer'
        r'(?:[^\n]{0,50})\b([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'),
    # "CEO: Timothy D. Cook" / "CEO, Tim Cook"
    re.compile(
        r'\bCEO[,:\s]+([A-Z][a-z]{1,24}(?:[ \t]+' + _W + r'){1,2})\b'),
]


def _extract_ceo_from_sec_text(text: str) -> Optional[str]:
    """Apply strict 10-K patterns to SEC document plain text; return first valid name."""
    if not text:
        return None
    # Collapse excessive whitespace but keep newlines for signature pattern
    text = re.sub(r'[ \t]{2,}', ' ', text)
    for pat in _SEC_CEO_PATTERNS:
        for m in pat.finditer(text):
            # Collapse residual whitespace, then strip middle initials
            candidate = _normalize_name(
                re.sub(r'\s+', ' ', m.group(1)).strip())
            if _is_valid_name(candidate):
                return candidate
    return None


def _extract_ceo_from_web_text(text: str) -> Optional[str]:
    """Apply looser web-snippet patterns to DDGS result text; return first valid name."""
    if not text:
        return None
    text = re.sub(r'[ \t]{2,}', ' ', text)
    for pat in _WEB_CEO_PATTERNS:
        for m in pat.finditer(text):
            candidate = _normalize_name(
                re.sub(r'\s+', ' ', m.group(1)).strip())
            if _is_valid_name(candidate):
                return candidate
    return None


def _fetch_and_parse_filing(filing: dict) -> Optional[str]:
    """Download a filing document and extract the CEO name."""
    cik = filing['cik']
    accn = filing['accn']
    doc = filing['doc']

    # Try the primary document first
    r = _edgar_get(_filing_url(cik, accn, doc))
    if not r:
        # Try the filing index to find an alternative document
        idx_url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{int(cik)}/{accn}/{accn}-index.htm")
        ri = _edgar_get(idx_url)
        if not ri:
            return None
        soup_idx = BeautifulSoup(ri.content, 'html.parser')
        for link in soup_idx.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith(('.htm', '.html', '.txt')):
                r = _edgar_get(f"https://www.sec.gov{href}")
                if r:
                    break
        if not r:
            return None

    content_type = r.headers.get('Content-Type', '')
    if 'html' in content_type or doc.lower().endswith(('.htm', '.html')):
        soup = BeautifulSoup(r.content, 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
    else:
        text = r.text

    return _extract_ceo_from_sec_text(text)


# ── Public CEO identification functions ────────────────────────────────────────

def fetch_ceo_from_edgar(ticker: str, year: int) -> tuple[Optional[str], str]:
    """
    Primary source: look up CEO from EDGAR proxy statement (DEF 14A)
    or annual report (10-K) for the given year.
    Returns (ceo_name, 'edgar_def14a' | 'edgar_10k') or (None, '').
    """
    cik = _cik_for_ticker(ticker)
    if not cik:
        logger.debug("No EDGAR CIK for ticker %s", ticker)
        return None, ''

    # Try DEF 14A first (most explicit CEO identification)
    for form_type, tag in [('DEF 14A', 'edgar_def14a'), ('10-K', 'edgar_10k')]:
        filings = _get_filings_for_year(cik, year, [form_type])
        for filing in filings[:2]:   # try top 2 matches at most
            name = _fetch_and_parse_filing(filing)
            if name:
                logger.info("EDGAR %s → %s CEO %s (%s)",
                            ticker, year, name, tag)
                return name, tag

    return None, ''


_PROXY_RE = re.compile(r'(?i)def14a|defm14a|proxy|prxy')

# ── missing-file audit log ────────────────────────────────────────────────────
_missing_file_log: Optional[object] = None   # file handle, opened lazily
_missing_file_lock = threading.Lock()
_missing_file_count = 0
# raised — missing files are expected for some tickers
_MISSING_FILE_HALT_THRESHOLD = 500
_halt_event = threading.Event()          # set when threshold is exceeded


def _get_missing_file_log():
    """Return (and lazily open) the missing-file audit log file handle."""
    global _missing_file_log
    if _missing_file_log is not None:
        return _missing_file_log
    with _missing_file_lock:
        if _missing_file_log is not None:
            return _missing_file_log
        try:
            from Utilities.PathConfiguration import PathConfiguration
            log_path = PathConfiguration().get_log_path('ceo_missing_files.log')
        except Exception:
            log_path = '/tmp/ceo_missing_files.log'
        try:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            _missing_file_log = open(
                log_path, 'a', buffering=1)  # line-buffered
            logger.info("local_10k missing-file audit log: %s", log_path)
        except Exception as e:
            logger.warning(
                "Could not open missing-file log %s: %s", log_path, e)
            _missing_file_log = False   # sentinel: don't retry
    return _missing_file_log


def _log_missing_file(ticker: str, year: int, source: str, tried: list[str]) -> None:
    """
    Append one line to the missing-file audit log and increment the counter.
    Raises RuntimeError if the count exceeds _MISSING_FILE_HALT_THRESHOLD —
    this signals a likely configuration bug (wrong mount path etc.) rather
    than isolated gaps in the data.
    """
    global _missing_file_count
    fh = _get_missing_file_log()
    if not fh:
        return
    import datetime
    line = (
        f"{datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\t"
        f"{ticker}\t{year}\t{source}\t{'|'.join(tried)}\n"
    )
    with _missing_file_lock:
        try:
            fh.write(line)
        except Exception as e:
            logger.debug("missing-file log write error: %s", e)
        _missing_file_count += 1
        count = _missing_file_count

    if count > _MISSING_FILE_HALT_THRESHOLD:
        logger.error(
            "local_10k: %d missing files exceeded halt threshold (%d). "
            "Setting halt event. Last: ticker=%s year=%s file=%s. Tried: %s",
            count, _MISSING_FILE_HALT_THRESHOLD, ticker, year, source, tried
        )
        _halt_event.set()


def _extract_text_from_file(path: Path) -> Optional[str]:
    """Extract plain text from a local .pdf, .htm, or .html file."""
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        if not FITZ_AVAILABLE:
            return None
        try:
            doc = fitz.open(str(path))
            total = len(doc)
            pages = sorted(set(
                list(range(min(30, total))) +
                list(range(max(0, total - 15), total))
            ))
            text = '\n'.join(doc[pg].get_text() for pg in pages)
            doc.close()
            return text
        except Exception as e:
            logger.debug("PDF parse error %s: %s", path, e)
            return None
    elif suffix in ('.htm', '.html'):
        try:
            raw = path.read_bytes()
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()
            return soup.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.debug("HTM parse error %s: %s", path, e)
            return None
    return None


def _fetch_text_from_url(url: str) -> Optional[str]:
    """Fetch and extract text from a remote SEC/EDGAR URL."""
    try:
        # Use EDGAR headers if it's an SEC URL, otherwise generic browser headers
        if 'sec.gov' in url or 'edgar' in url.lower():
            headers = EDGAR_HEADERS
        else:
            headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        ct = r.headers.get('Content-Type', '')
        if 'html' in ct or url.lower().endswith(('.htm', '.html')):
            soup = BeautifulSoup(r.content, 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()
            return soup.get_text(separator='\n', strip=True)
        return r.text
    except Exception as e:
        logger.debug("URL fetch error %s: %s", url, e)
        return None


def fetch_ceo_from_local_10k(ticker: str, company_name: str, year: int,
                             conn) -> tuple[Optional[str], str]:
    """
    Query t_data_source (content_type=2) for a 10-K filing.
    Handles:
      - Local .pdf files  → PyMuPDF
      - Local .htm/.html  → BeautifulSoup
      - Full https:// URLs → HTTP fetch + BeautifulSoup
    Returns (ceo_name, 'local_10k') or (None, '').
    """
    if conn is None:
        return None, ''

    try:
        import psycopg2.extras as _extras
        with conn.cursor(cursor_factory=_extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT source_url
                FROM   t_data_source
                WHERE  content_type = 2
                  AND  year = %s
                  AND  (
                           ticker       ILIKE %s
                        OR company_name ILIKE %s
                  )
                ORDER BY source_confidence_score DESC NULLS LAST, unique_id DESC
                LIMIT 5
                """,
                (year, ticker, company_name)
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.debug("local_10k DB query failed: %s", e)
        return None, ''

    if not rows:
        return None, ''

    try:
        from Utilities.PathConfiguration import PathConfiguration
        base_path = PathConfiguration().get_stage0_input_path()
    except Exception as e:
        logger.debug("local_10k PathConfiguration failed: %s", e)
        base_path = None

    # Files may be stored under a different environment prefix than what
    # PathConfiguration resolves to on the VM (e.g. stored in Development
    # but VM detects Production).  Build a list of candidate base paths to try.
    _gcs_root = '/opt/avisk/gcs-data'
    _candidate_paths: list[Optional[str]] = [base_path]
    if base_path and _gcs_root in base_path:
        for _env in ('Development', 'Production', 'Test'):
            _alt = f"{_gcs_root}/{_env}/data/Stage0SourcePDFFiles/"
            if _alt != base_path:
                _candidate_paths.append(_alt)

    for row in rows:
        source = (row.get('source_url') or '').strip()
        if not source:
            continue

        # Skip proxy/DEF 14A — contain director bios with misleading CEO mentions
        if _PROXY_RE.search(source):
            logger.debug('local_10k skipping proxy: %s', source)
            continue

        text = None

        # Case 1: full URL (https://...)
        if source.startswith('http://') or source.startswith('https://'):
            text = _fetch_text_from_url(source)

        # Case 2: local file on GCS FUSE mount — try each candidate base path
        else:
            _tried: list[str] = []
            for _bp in _candidate_paths:
                if not _bp:
                    continue
                file_path = Path(_bp) / str(year) / source
                _tried.append(str(file_path))
                if file_path.exists():
                    text = _extract_text_from_file(file_path)
                    if text:
                        break
                    # file exists but unreadable — stop searching
                    break
            else:
                logger.warning(
                    "local_10k FILE NOT FOUND | ticker=%s year=%s file=%s",
                    ticker, year, source
                )
                _log_missing_file(ticker, year, source, _tried)

        if not text:
            continue

        name = _extract_ceo_from_sec_text(text)
        if name:
            logger.info("local_10k %s/%s → CEO %s (src=%s)",
                        ticker, year, name, source[:60])
            return name, 'local_10k'

    return None, ''


# ── FMP per-run cache  ────────────────────────────────────────────────────────
# Keyed by ticker. Dict reads/writes are GIL-atomic in CPython so no extra
# lock is needed; the worst-case duplicate fetch (two threads for the same
# ticker starting simultaneously) is harmless — one result simply overwrites.
_fmp_historical_cache: dict[str, list] = {}   # ticker → historical execs list
_fmp_current_cache: dict[str, list] = {}      # ticker → current execs list
# ticker → profile dict or None
_fmp_profile_cache: dict[str, dict | None] = {}

# ── Company existence dates (spinoffs / IPOs) ──────────────────────────────────
# For these tickers, years STRICTLY BEFORE the value have no standalone CEO
# (the company was a division of its parent or hadn't yet been formed).
# CEO identification is skipped for pre-existence years.
_COMPANY_EXISTS_FROM: dict[str, int] = {
    'CARR': 2020,   # Carrier Global spun from United Technologies Apr 2020
    'CEG':  2022,   # Constellation Energy spun from Exelon Feb 2022
    'EVRG': 2018,   # Evergy formed from Great Plains Energy + Westar Jun 2018
    'FOX':  2019,   # Fox Corp spun from 21st Century Fox Mar 2019
    'FOXA': 2019,
    'FTV':  2016,   # Fortive spun from Danaher Jul 2016
    'GEHC': 2023,   # GE HealthCare spun from GE Jan 2023
    'INVH': 2017,   # Invitation Homes IPO Feb 2017
    'IQV':  2016,   # IQVIA formed from IMS Health + Quintiles Oct 2016
    'KHC':  2015,   # Kraft Heinz formed Jul 2015
    'KVUE': 2023,   # Kenvue spun from J&J May 2023
    'LIN':  2018,   # Linde plc formed Oct 2018 (Praxair + Linde AG)
    'LW':   2016,   # Lamb Weston spun from ConAgra Nov 2016
    'MTCH': 2015,   # Match Group spun from IAC Nov 2015
    'OTIS': 2020,   # Otis Worldwide spun from United Technologies Apr 2020
    'SOLV': 2024,   # Solventum spun from 3M Apr 2024
    'SW':   2024,   # Smurfit WestRock formed Jul 2024
    'SYF':  2014,   # Synchrony Financial IPO Jul 2014
    'VICI': 2017,   # VICI Properties IPO Oct 2017
    'VLTO': 2023,   # Veralto spun from Danaher Sep 2023
    'VST':  2016,   # Vistra Energy emerged from EFH bankruptcy Oct 2016
    'VTRS': 2020,   # Viatris formed Nov 2020 (Mylan + Upjohn)
}

# ── Historical ticker aliases ──────────────────────────────────────────────────
# Companies that changed tickers or names: map year ranges to historical
# identifiers so FMP + OpenAI can be retried under the former name.
# Format: current_ticker → [(from_year, to_year, old_ticker, old_company_name)]
_TICKER_ALIASES: dict[str, list[tuple[int, int, str, str]]] = {
    'APTV': [(2009, 2016, 'DLPH', 'Delphi Automotive PLC')],
    'BF':   [(2012, 9999, 'BF.B', 'Brown-Forman Corporation')],
    'BKR':  [(2012, 2017, 'BHI',  'Baker Hughes Inc')],
    'BRK':  [(2012, 9999, 'BRK.B', 'Berkshire Hathaway Inc')],
    'GEN':  [(2012, 2019, 'SYMC', 'Symantec Corp'),
             (2019, 2022, 'NLOK', 'NortonLifeLock Inc')],
    'K':    [(2012, 2023, 'K',    'Kellogg Company')],
    'PARA': [(2012, 2019, 'VIAB', 'Viacom Inc'),
             (2019, 2022, 'VIAC', 'ViacomCBS Inc')],
    'RVTY': [(2012, 2023, 'PKI',  'PerkinElmer Inc')],
}


def clear_fmp_cache() -> None:
    """Call between pipeline runs to reset the per-run caches and counters."""
    global _missing_file_count
    _fmp_historical_cache.clear()
    _fmp_current_cache.clear()
    _fmp_profile_cache.clear()
    _openai_cache.clear()
    with _missing_file_lock:
        _missing_file_count = 0
    _halt_event.clear()
    with _ddgs_lock:
        _ddgs_backoff_until[0] = 0.0
        _ddgs_consecutive_empty[0] = 0


def fetch_ceo_from_fmp(ticker: str, year: int = None) -> tuple[Optional[str], str]:
    """
    Primary source: FMP historical or current key-executives.
    Returns (ceo_name, source_tag) or (None, '').
    """
    if not ticker:
        return None, ''

    # Try historical endpoint (year-specific)
    if year:
        if ticker not in _fmp_historical_cache:
            fetched = _fmp_get('/historical-key-executives',
                               {'symbol': ticker})
            _fmp_historical_cache[ticker] = fetched if isinstance(
                fetched, list) else []
        data = _fmp_historical_cache[ticker]
        if data:
            for exec_ in data:
                title = (exec_.get('title') or '').lower()
                if 'chief executive' not in title and 'ceo' not in title:
                    continue
                active = str(exec_.get('yearActive') or
                             exec_.get('startDate') or '')[:4]
                end_yr = str(exec_.get('endDate') or
                             exec_.get('endYear') or '')[:4]
                try:
                    start_int = int(active) if active.isdigit() else 0
                    end_int = int(end_yr) if end_yr.isdigit() else 9999
                except ValueError:
                    start_int, end_int = 0, 9999
                if start_int <= year <= end_int:
                    name = _normalize_name((exec_.get('name') or '').strip())
                    if name and _is_valid_name(name):
                        return name, 'fmp_historical'

    # Fallback: current key-executives (cached per ticker per run)
    if ticker not in _fmp_current_cache:
        fetched_cur = _fmp_get('/key-executives', {'symbol': ticker})
        _fmp_current_cache[ticker] = fetched_cur if isinstance(
            fetched_cur, list) else []
    data = _fmp_current_cache[ticker]
    if data:
        for exec_ in data:
            title = (exec_.get('title') or '').lower()
            if 'chief executive' in title or 'ceo' in title:
                name = _normalize_name((exec_.get('name') or '').strip())
                if name and _is_valid_name(name):
                    return name, 'fmp_key_executives'

    # Last resort: company profile endpoint — always has current CEO as plain text.
    # Most reliable source for 2024+ where historical/key-exec data may lag.
    if ticker not in _fmp_profile_cache:
        fetched_profile = _fmp_get('/profile', {'symbol': ticker})
        if isinstance(fetched_profile, list) and fetched_profile:
            _fmp_profile_cache[ticker] = fetched_profile[0]
        elif isinstance(fetched_profile, dict) and fetched_profile:
            _fmp_profile_cache[ticker] = fetched_profile
        else:
            _fmp_profile_cache[ticker] = None
    prof = _fmp_profile_cache.get(ticker)
    if isinstance(prof, dict):
        name = _normalize_name((prof.get('ceo') or '').strip())
        if name and _is_valid_name(name):
            return name, 'fmp_profile'

    return None, ''


def fetch_ceo_from_ddgs(company_name: str, year: int) -> tuple[Optional[str], str]:
    """
    Last-resort fallback: DDGS web search + strict name extraction.
    """
    if not DDGS_AVAILABLE:
        return None, ''
    queries = [
        f'"{company_name}" CEO {year} site:reuters.com OR site:bloomberg.com OR site:wsj.com',
        f'"{company_name}" "Chief Executive Officer" {year}',
    ]
    for q in queries:
        results = _ddgs_text(q, max_results=5)
        for r in results:
            for field in ('body', 'title'):
                text = r.get(field, '')
                name = _extract_ceo_from_web_text(text)
                if name:
                    return name, 'ddgs'
    return None, ''


# Sentinel for OpenAI cache miss (distinct from None = "tried, got nothing")
_OPENAI_SENTINEL = object()


def fetch_ceo_from_openai(ticker: str, company_name: str,
                          year: int) -> tuple[Optional[str], str]:
    """
    AI fallback: ask GPT-4o-mini who the CEO was for a given company/year.
    Strong factual recall for S&P 500 history — covers pre-2015 gaps where
    FMP historical data is sparse and DDGS gets rate-limited.
    Returns (ceo_name, 'openai') or (None, '').
    """
    if not OPENAI_AVAILABLE:
        return None, ''

    cache_key = (ticker.upper() if ticker else company_name, year)

    # Fast path: already have a cached answer (None means "tried, found nothing")
    cached = _openai_cache.get(cache_key, _OPENAI_SENTINEL)
    if cached is not _OPENAI_SENTINEL:
        return (cached, 'openai') if cached else (None, '')

    with _openai_lock:
        # Re-check inside lock in case another thread just populated it
        cached = _openai_cache.get(cache_key, _OPENAI_SENTINEL)
        if cached is not _OPENAI_SENTINEL:
            return (cached, 'openai') if cached else (None, '')

        wait = _OPENAI_RATE_LIMIT - (time.monotonic() - _openai_last[0])
        if wait > 0:
            time.sleep(wait)
        _openai_last[0] = time.monotonic()

        try:
            resp = _openai_client.chat.completions.create(
                model='gpt-4o-mini',     # more willing to answer near training cutoff than gpt-4o
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert in US public company leadership. '
                            'When asked who the CEO of a company was for a given year, '
                            'respond with the name of the person who served as CEO '
                            'for most of that year, based on your training data. '
                            'Answer from whatever point in the year your training data covers; '
                            'you do not need data for December 31 to answer. '
                            'Respond ONLY with the person\'s exact full name. '
                            'No explanation, no titles, no punctuation. '
                            'Only reply "unknown" if the company genuinely had no CEO '
                            'or you have absolutely no information about that company.'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': (
                            f'Who was the CEO of {company_name} (ticker: {ticker}) '
                            f'during fiscal year {year}? '
                            f'Reply with ONLY the full name (e.g. "John Smith").'
                        ),
                    },
                ],
                max_tokens=60,           # allow full sentence in case model elaborates
                temperature=0,
                timeout=30,              # hard cap — prevents holding _openai_lock forever
            )
            raw = (resp.choices[0].message.content or '').strip()
        except Exception as e:
            logger.debug('OpenAI CEO lookup failed %s/%s: %s', ticker, year, e)
            _openai_cache[cache_key] = None
            return None, ''

    # Parse outside the lock
    if not raw or raw.lower() in (
            'unknown', 'n/a', 'not known', 'not available', "i don't know"):
        print(
            f'[CEO] OpenAI returned unknown for {ticker}/{year}: {raw!r}', flush=True)
        _openai_cache[cache_key] = None
        return None, ''

    # Detect hallucinated repeated-initial pattern:
    # "David S. R. R. H. H. H..." → model doesn't know, treat as unknown
    single_letters = re.findall(r'\b[A-Z]\.?\b', raw)
    if len(single_letters) >= 4:
        print(
            f'[CEO] OpenAI hallucinated initials for {ticker}/{year}: {raw!r}', flush=True)
        _openai_cache[cache_key] = None
        return None, ''

    # Strip common prefixes GPT occasionally adds
    name = re.sub(r'\s+', ' ', raw).strip()
    # Strip surrounding quotes GPT sometimes adds: "George Kurtz" → George Kurtz
    name = name.strip('"\'')
    # Strip trailing punctuation: "George Kurtz." → "George Kurtz"
    name = name.rstrip('.,;:')
    for prefix in ('CEO: ', 'CEO ', 'Name: ', 'Answer: ', 'The CEO is '):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()

    name = _normalize_name(name)
    if _is_valid_name(name):
        _openai_cache[cache_key] = name
        return name, 'openai'

    # Try extracting valid name from the first 2–3 words
    words = name.split()
    for end in (3, 2):
        candidate = ' '.join(words[:end])
        if _is_valid_name(candidate):
            _openai_cache[cache_key] = candidate
            return candidate, 'openai'

    # Model returned a full sentence — extract name using web patterns
    # e.g. "Joaquin Duato was the Chief Executive Officer of Johnson & Johnson in 2024"
    extracted = _extract_ceo_from_web_text(raw)
    if extracted:
        _openai_cache[cache_key] = extracted
        return extracted, 'openai'

    print(
        f'[CEO] OpenAI returned unparseable response for {ticker}/{year}: {raw!r}', flush=True)
    _openai_cache[cache_key] = None
    return None, ''


# ── Repair helper ──────────────────────────────────────────────────────────────

def _clean_stored_name(raw: str) -> Optional[str]:
    """Salvage a valid name from a noisy stored string."""
    if not raw:
        return None
    tokens = raw.split()
    for end in range(min(len(tokens), 4), 1, -1):
        candidate = ' '.join(tokens[:end])
        if _is_valid_name(candidate):
            return candidate
    return None


# ── Statement collection ───────────────────────────────────────────────────────

def _extract_ceo_text(content: str, ceo_name: str) -> str:
    """
    Extract the CEO's speaking portions from an earnings call transcript.
    Transcripts follow the pattern:  "Speaker Name:\n text text text\n\nNext Speaker:\n ..."
    We grab all paragraphs attributed to ceo_name.
    """
    if not ceo_name or not content:
        return content  # return full text if we can't identify

    # Build a loose first-name / last-name match
    parts = ceo_name.split()
    pattern = re.compile(
        r'(?:^|\n)(' + re.escape(ceo_name) + r'|' +
        re.escape(parts[-1]) + r')[^\n]*:\s*(.*?)(?=\n[A-Z][^\n]+:|$)',
        re.DOTALL | re.IGNORECASE
    )
    matches = pattern.findall(content)
    if matches:
        text = '\n\n'.join(m[1].strip() for m in matches)
        return text[:8000]
    return content[:8000]


def fetch_statements_fmp(ticker: str, ceo_name: str, year: int) -> list[dict]:
    """
    Download earnings call transcripts for all 4 quarters of `year`.
    Extracts the CEO's speaking portions.
    """
    statements = []
    for quarter in range(1, 5):
        data = _fmp_get('/earning_call_transcript',
                        {'symbol': ticker, 'year': year, 'quarter': quarter})
        if not data:
            continue
        records = data if isinstance(data, list) else [data]
        for t in records:
            raw_content = t.get('content') or ''
            if not raw_content:
                continue
            ceo_text = _extract_ceo_text(raw_content, ceo_name or '')
            stmt_date = None
            try:
                stmt_date = datetime.strptime(
                    t.get('date', '')[:10], '%Y-%m-%d').date()
            except Exception:
                pass
            statements.append({
                'statement_text': ceo_text,
                'statement_date': stmt_date,
                'source_url': (f"{FMP_BASE}/earning_call_transcript"
                               f"?symbol={ticker}&year={year}&quarter={quarter}"),
                'source_title': f"Q{quarter} {year} Earnings Call – {ticker}",
                'statement_type': 'earnings_call',
                'search_query': f'{ticker} Q{quarter} {year} earnings call transcript',
            })
    return statements


def _scrape_article_text(url: str, max_chars: int = 6000) -> str:
    """Best-effort article text extraction."""
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'),
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return ''
        soup = BeautifulSoup(r.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                         'aside', 'form', 'iframe']):
            tag.decompose()
        # Prefer <article> or <main> if present
        body = soup.find('article') or soup.find('main') or soup.body
        if not body:
            return ''
        text = body.get_text(separator=' ', strip=True)
        # Collapse whitespace
        text = re.sub(r'\s{2,}', ' ', text)
        return text[:max_chars]
    except Exception as e:
        logger.debug("Scrape failed %s: %s", url, e)
        return ''


def fetch_statements_ddgs(ceo_name: str, company_name: str, year: int,
                          max_per_query: int = 3) -> list[dict]:
    """
    DDGS-based statement collection: search multiple queries,
    deduplicate URLs, scrape article text.
    """
    if not DDGS_AVAILABLE or not ceo_name:
        return []

    queries = [
        f'"{ceo_name}" "{company_name}" statement {year}',
        f'"{ceo_name}" CEO speech interview {year}',
        f'"{ceo_name}" "{company_name}" announcement {year}',
    ]

    seen: set[str] = set()
    statements: list[dict] = []

    for query in queries:
        results = _ddgs_text(query, max_results=max_per_query)
        for r in results:
            url = r.get('href', '')
            if not url or url in seen:
                continue
            seen.add(url)
            body = _scrape_article_text(url)
            if len(body) < 200:
                body = r.get('body', '')
            if not body:
                continue
            statements.append({
                'statement_text': body,
                'statement_date': None,
                'source_url': url,
                'source_title': r.get('title', '')[:490],
                'statement_type': 'article',
                'search_query': query,
            })
    return statements


# ── Database layer ─────────────────────────────────────────────────────────────


class CEODataService:
    """
    Main service.  Usage:
        svc = CEODataService()
        svc.run_pipeline(companies_df, years=[2020,2021,2022,2023],
                         workers=4, on_progress=callback)
    """

    def __init__(self):
        if not DB_AVAILABLE:
            raise RuntimeError("psycopg2 / DB not available")
        self.conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
        self.conn.autocommit = True

    def _reconnect(self) -> None:
        """Close any existing connection and open a fresh one.

        Called at the start of each pipeline run to prevent stale cached
        connections (the service instance is long-lived via st.cache_resource)
        from hanging on the first DB query when the TCP connection has gone away.
        """
        try:
            if self.conn and not self.conn.closed:
                self.conn.close()
        except Exception:
            pass
        self.conn = psycopg2.connect(
            DB_Connection().DB_CONNECTION_STRING, connect_timeout=15)
        self.conn.autocommit = True

    # ── CEO upsert ─────────────────────────────────────────────────────────────
    def save_ceo(self, company_name: str, ticker: str, year: int,
                 ceo_name: str, source: str,
                 confidence: float = 1.0) -> Optional[int]:
        sql = """
            INSERT INTO t_ceo (company_name, ticker, year, ceo_name, source,
                               confidence_score, added_dt, modify_dt)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (company_name, year)
            DO UPDATE SET
                ceo_name         = EXCLUDED.ceo_name,
                ticker           = COALESCE(EXCLUDED.ticker, t_ceo.ticker),
                source           = EXCLUDED.source,
                confidence_score = EXCLUDED.confidence_score,
                modify_dt        = NOW()
            RETURNING ceo_id
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (company_name, ticker, year,
                              ceo_name, source, confidence))
            row = cur.fetchone()
            return row[0] if row else None

    def get_ceo_id(self, company_name: str, year: int) -> Optional[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ceo_id FROM t_ceo WHERE company_name=%s AND year=%s",
                (company_name, year))
            row = cur.fetchone()
            return row[0] if row else None

    # ── Statement insert ───────────────────────────────────────────────────────
    def save_statements(self, ceo_id: int, company_name: str,
                        ticker: str, year: int, ceo_name: str,
                        statements: list[dict]) -> int:
        sql = """
            INSERT INTO t_ceo_statements
                (ceo_id, company_name, ticker, year, ceo_name,
                 statement_text, statement_date, source_url, source_title,
                 statement_type, search_query)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        count = 0
        with self.conn.cursor() as cur:
            for s in statements:
                if not (s.get('statement_text') or '').strip():
                    continue
                cur.execute(sql, (
                    ceo_id, company_name, ticker, year, ceo_name,
                    s.get('statement_text', ''),
                    s.get('statement_date'),
                    (s.get('source_url') or '')[:999],
                    (s.get('source_title') or '')[:499],
                    s.get('statement_type', 'unknown'),
                    (s.get('search_query') or '')[:499],
                ))
                count += 1
        return count

    # ── Already-processed checks ───────────────────────────────────────────────
    def already_has_ceo(self, company_name: str, year: int) -> bool:
        """True if a t_ceo row already exists for this company/year."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM t_ceo WHERE company_name=%s AND year=%s LIMIT 1",
                (company_name, year))
            return cur.fetchone() is not None

    def already_has_statements(self, company_name: str, year: int) -> bool:
        """True if at least one statement exists for this company/year."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM t_ceo c
                JOIN t_ceo_statements s ON s.ceo_id = c.ceo_id
                WHERE c.company_name = %s AND c.year = %s
                LIMIT 1
            """, (company_name, year))
            return cur.fetchone() is not None

    def already_processed(self, company_name: str, year: int) -> bool:
        """True if t_ceo row exists AND at least one statement is stored."""
        return (self.already_has_ceo(company_name, year) and
                self.already_has_statements(company_name, year))

    # ── Stage 1: identify CEO for one company/year ────────────────────────────
    def identify_ceo_one(self, company_name: str, ticker: str,
                         year: int, skip_existing: bool = True,
                         sources: Optional[list[str]] = None) -> dict:
        """
        Identify and save CEO for one company/year.

        sources: ordered list of sources to try, e.g. ['AI', '10K', 'FMP', 'Web Search'].
                 None (default) uses ['AI'] only (current production default).
                 Priority is the order of the list.
        Returns a result dict for progress reporting.
        """
        # Normalise — default to AI-only if nothing supplied
        _sources = [s.strip() for s in (sources or ['AI'])]

        result = {
            'company': company_name, 'ticker': ticker, 'year': year,
            'ceo_name': None, 'ceo_source': None,
            'status': 'ok', 'error': None,
        }
        # Bail out immediately if the halt event has been set (e.g. too many
        # missing files detected — likely a mount path misconfiguration).
        if _halt_event.is_set():
            result['status'] = 'halted'
            return result

        # Skip years before this company existed as a standalone entity
        # (e.g. CARR pre-2020 was a UTC division with no independent CEO).
        _exists_from = _COMPANY_EXISTS_FROM.get((ticker or '').upper())
        if _exists_from and year < _exists_from:
            result['status'] = 'pre_existence'
            print(f"[CEO]   ○ pre_existence: {ticker} {year} "
                  f"(entity exists from {_exists_from})", flush=True)
            return result

        print(
            f"[CEO] Processing: {ticker} | {company_name} | {year}", flush=True)

        try:
            if skip_existing and self.already_has_ceo(company_name, year):
                result['status'] = 'skipped'
                return result

            ceo_name: Optional[str] = None
            source: str = ''

            # For very recent years (2024+) FMP profile is more reliable than
            # OpenAI whose training data may not cover the full year.
            # Re-order: FMP first, then AI, then 10K, then Web.
            if year >= 2024 and 'FMP' in _sources and not ceo_name:
                ceo_name, source = fetch_ceo_from_fmp(ticker, year)

            # Standard source cascade in user-selected order
            if 'AI' in _sources and not ceo_name:
                ceo_name, source = fetch_ceo_from_openai(
                    ticker, company_name, year)
            if '10K' in _sources and not ceo_name:
                ceo_name, source = fetch_ceo_from_local_10k(
                    ticker, company_name, year, _get_thread_conn())
            if 'FMP' in _sources and not ceo_name:
                ceo_name, source = fetch_ceo_from_fmp(ticker, year)
            if 'Web Search' in _sources and not ceo_name:
                ceo_name, source = fetch_ceo_from_ddgs(company_name, year)

            # Retry under historical ticker/name for renamed/rebranded companies.
            # E.g. GEN (Gen Digital) pre-2023 was SYMC (Symantec) / NLOK (NortonLifeLock).
            if not ceo_name:
                for (a_from, a_to, old_ticker,
                     old_name) in _TICKER_ALIASES.get((ticker or '').upper(), []):
                    if a_from <= year <= a_to:
                        if 'FMP' in _sources:
                            ceo_name, source = fetch_ceo_from_fmp(
                                old_ticker, year)
                        if not ceo_name and 'AI' in _sources:
                            ceo_name, source = fetch_ceo_from_openai(
                                old_ticker, old_name, year)
                        if not ceo_name and 'Web Search' in _sources:
                            ceo_name, source = fetch_ceo_from_ddgs(
                                old_name, year)
                        break

            if not ceo_name:
                result['status'] = 'no_ceo'
                print(f"[CEO]   ✗ no_ceo:  {ticker} {year}", flush=True)
                return result

            result['ceo_name'] = ceo_name
            result['ceo_source'] = source
            # Use thread-local connection for the insert so concurrent workers
            # don't race on self.conn (psycopg2 connections are not thread-safe)
            _tconn = _get_thread_conn()
            with _tconn.cursor() as cur:
                cur.execute("""
                    INSERT INTO t_ceo (company_name, ticker, year, ceo_name, source,
                                       confidence_score, added_dt, modify_dt)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (company_name, year)
                    DO UPDATE SET
                        ceo_name         = EXCLUDED.ceo_name,
                        ticker           = COALESCE(EXCLUDED.ticker, t_ceo.ticker),
                        source           = EXCLUDED.source,
                        confidence_score = EXCLUDED.confidence_score,
                        modify_dt        = NOW()
                """, (company_name, ticker, year, ceo_name, source, 1.0))
            print(f"[CEO]   ✓ {ceo_name} ({source})", flush=True)

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error("identify_ceo_one %s/%s/%s: %s",
                         company_name, ticker, year, e)
        return result

    # ── Stage 2: collect statements for one company/year ──────────────────────
    def collect_statements_one(self, company_name: str, ticker: str,
                               year: int, skip_existing: bool = True) -> dict:
        """
        Collect and save statements for one company/year.
        Requires a t_ceo row to already exist.
        Returns a result dict for progress reporting.
        """
        result = {
            'company': company_name, 'ticker': ticker, 'year': year,
            'ceo_name': None, 'statements_saved': 0,
            'status': 'ok', 'error': None,
        }
        try:
            if skip_existing and self.already_has_statements(company_name, year):
                result['status'] = 'skipped'
                return result

            ceo_id = self.get_ceo_id(company_name, year)
            if not ceo_id:
                result['status'] = 'no_ceo'
                return result

            # Look up the CEO name stored in DB
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT ceo_name, ticker FROM t_ceo "
                    "WHERE ceo_id=%s", (ceo_id,))
                row = cur.fetchone()
            if not row:
                result['status'] = 'no_ceo'
                return result

            ceo_name = row[0] or ''
            ticker = row[1] or ticker
            result['ceo_name'] = ceo_name

            statements = []
            if ticker:
                statements += fetch_statements_fmp(ticker, ceo_name, year)
            statements += fetch_statements_ddgs(ceo_name, company_name, year)

            count = self.save_statements(
                ceo_id, company_name, ticker, year, ceo_name, statements)
            result['statements_saved'] = count

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error("collect_statements_one %s/%s/%s: %s",
                         company_name, ticker, year, e)
        return result

    # ── CEO pipeline (Stage 1 only) ────────────────────────────────────────────
    def get_unprocessed_tasks(
        self,
        companies: list[dict],
        years: list[int],
        _conn=None,
    ) -> list[tuple[str, str, int]]:
        """
        Return (company_name, ticker, year) tuples from the requested
        companies × years that do NOT yet have a row in t_ceo.
        Uses a single SQL query instead of N per-worker round-trips.

        _conn: optional explicit connection to use (e.g. self.conn from the
               pipeline thread that just called _reconnect).  When None the
               caller's thread-local connection is used (render-thread path).
        """
        if not companies or not years:
            return []

        tickers = [c.get('ticker', '') for c in companies]
        ticker_map = {c.get('ticker', '')
                            : c['company_name'] for c in companies}

        try:
            db = _conn if _conn is not None else _get_thread_conn()
            with db.cursor() as cur:
                cur.execute(
                    """
                    SELECT ticker, year
                    FROM t_ceo
                    WHERE ticker = ANY(%s)
                      AND year   = ANY(%s)
                      AND ceo_name IS NOT NULL
                    """,
                    (tickers, years)
                )
                already_done = {(r[0], r[1]) for r in cur.fetchall()}
        except Exception as e:
            logger.warning("get_unprocessed_tasks DB query failed (%s), "
                           "falling back to full task list", e)
            already_done = None

        # Build full task list; if DB query failed keep all tasks
        tasks = []
        for c in companies:
            ticker = c.get('ticker', '')
            cname = c['company_name']
            for y in years:
                if already_done is None or (ticker, y) not in already_done:
                    tasks.append((cname, ticker, y))
        return tasks

    def run_ceo_pipeline(
        self,
        companies: list[dict],
        years: list[int],
        workers: int = 4,
        skip_existing: bool = True,
        on_progress: Optional[Callable[[dict], None]] = None,
        sources: Optional[list[str]] = None,
    ) -> dict:
        """Identify and save CEOs for all companies × years (no statements).

        sources: ordered list of data sources to try per task.
                 e.g. ['AI', '10K', 'FMP', 'Web Search']
                 Defaults to ['AI'] when None.
        """
        # Fresh DB connection — the service instance is cached (st.cache_resource)
        # and the connection can go stale over hours, causing get_unprocessed_tasks
        # to hang indefinitely on a dead TCP socket.
        self._reconnect()
        clear_fmp_cache()  # fresh cache per run
        _sources = sources or ['AI']
        logger.info("run_ceo_pipeline: sources=%s", _sources)

        total_requested = len(companies) * len(years)

        if skip_existing:
            # Reuse self.conn (just refreshed by _reconnect) — avoids opening
            # a redundant second connection in the background thread which can
            # stall if the Cloud SQL proxy is busy.
            tasks = self.get_unprocessed_tasks(
                companies, years, _conn=self.conn)
            skipped_count = total_requested - len(tasks)
            logger.info("run_ceo_pipeline: %d/%d tasks after skipping existing",
                        len(tasks), total_requested)
        else:
            tasks = [
                (c['company_name'], c.get('ticker', ''), y)
                for c in companies for y in years
            ]
            skipped_count = 0

        # Notify the UI of the actual task count (after skip-existing deduction)
        # so the progress bar shows pending/pending instead of total/total.
        if on_progress:
            on_progress({'status': '_task_count', 'total': len(tasks),
                         'skipped': skipped_count})

        summary = {'total': total_requested, 'ok': 0,
                   'skipped': skipped_count, 'no_ceo': 0,
                   'pre_existence': 0, 'error': 0, 'halted': 0}
        with ThreadPoolExecutor(max_workers=workers) as exe:
            futs = {
                exe.submit(self.identify_ceo_one, cname, ticker, year,
                           False, _sources): (cname, ticker, year)   # skip_existing handled by SQL
                for cname, ticker, year in tasks
            }
            for fut in as_completed(futs):
                r = fut.result()
                summary[r['status']] = summary.get(r['status'], 0) + 1
                if on_progress:
                    on_progress(r)
        if _halt_event.is_set():
            summary['halt_reason'] = (
                f"Aborted: >{_MISSING_FILE_HALT_THRESHOLD} source files not found "
                f"on GCS FUSE mount. Check mount path and re-run."
            )
            logger.error("run_ceo_pipeline halted: %s", summary['halt_reason'])
        return summary

    # ── Statements pipeline (Stage 2 only) ────────────────────────────────────
    def run_statements_pipeline(
        self,
        companies: list[dict],
        years: list[int],
        workers: int = 4,
        skip_existing: bool = True,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Collect statements for all companies × years that already have a CEO."""
        tasks = [
            (c['company_name'], c.get('ticker', ''), y)
            for c in companies for y in years
        ]
        summary = {'total': len(tasks), 'ok': 0, 'skipped': 0,
                   'no_ceo': 0, 'error': 0, 'statements': 0}
        with ThreadPoolExecutor(max_workers=workers) as exe:
            futs = {
                exe.submit(self.collect_statements_one, cname, ticker, year,
                           skip_existing): (cname, ticker, year)
                for cname, ticker, year in tasks
            }
            for fut in as_completed(futs):
                r = fut.result()
                summary[r['status']] = summary.get(r['status'], 0) + 1
                summary['statements'] += r.get('statements_saved', 0)
                if on_progress:
                    on_progress(r)
        return summary

    # ── Combined pipeline (Stage 1 + 2) ───────────────────────────────────────
    def run_pipeline(
        self,
        companies: list[dict],
        years: list[int],
        workers: int = 4,
        skip_existing: bool = True,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Run CEO identification then statement collection for all companies × years."""
        ceo_summary = self.run_ceo_pipeline(
            companies, years, workers, skip_existing, on_progress)
        stmt_summary = self.run_statements_pipeline(
            companies, years, workers, skip_existing, on_progress)
        return {
            'total':      ceo_summary['total'],
            'ok':         ceo_summary.get('ok', 0),
            'skipped':    ceo_summary.get('skipped', 0),
            'no_ceo':     ceo_summary.get('no_ceo', 0),
            'error':      ceo_summary.get('error', 0),
            'statements': stmt_summary.get('statements', 0),
        }

    # ── Repair bad rows already in t_ceo ──────────────────────────────────────
    def clean_existing_ceo_names(
        self,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """
        Scans every row in t_ceo and:
          - If ceo_name passes _is_valid_name → keep it
          - If _clean_stored_name can salvage it → update
          - Otherwise re-fetch from FMP historical / DDGS → update or null out
        Returns summary counts.
        """
        with self.conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT ceo_id, company_name, ticker, year, ceo_name "
                "FROM t_ceo ORDER BY ceo_id")
            rows = cur.fetchall()

        fixed = skipped = cleared = 0
        for row in rows:
            raw = row['ceo_name'] or ''
            ceo_id = row['ceo_id']
            company = row['company_name']
            ticker = row['ticker'] or ''
            year = row['year']

            # Already valid
            if _is_valid_name(raw):
                skipped += 1
                continue

            # Try to salvage from the stored string
            new_name = _clean_stored_name(raw)
            source = 'cleaned'

            # If that fails, re-fetch (FMP → Local 10-K → DDGS)
            if not new_name:
                new_name, source = fetch_ceo_from_fmp(ticker, year)
            if not new_name:
                new_name, source = fetch_ceo_from_local_10k(
                    ticker, company, year, self.conn)
            if not new_name:
                new_name, source = fetch_ceo_from_ddgs(company, year)

            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE t_ceo SET ceo_name=%s, source=%s, modify_dt=NOW() "
                    "WHERE ceo_id=%s",
                    (new_name, source, ceo_id))

            if new_name:
                fixed += 1
            else:
                cleared += 1

            if on_progress:
                on_progress({'ceo_id': ceo_id, 'company': company,
                             'year': year, 'old': raw, 'new': new_name,
                             'source': source})

        return {'fixed': fixed, 'skipped': skipped, 'cleared': cleared}

    # ── Clean orphan / duplicate statements ───────────────────────────────────
    def clean_existing_statements(
        self,
        companies: list[dict] = None,
        years: list[int] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """
        For every (company, year) that has statements already:
          - Delete all existing statements
          - Re-fetch fresh ones from FMP + DDGS
        If companies/years are None, processes all rows in t_ceo_statements.
        Returns summary counts.
        """
        clauses, params = [], []
        if companies:
            tickers = [c.get('ticker', '')
                       for c in companies if c.get('ticker')]
            co_names = [c.get('company_name', '') for c in companies]
            if tickers or co_names:
                clauses.append(
                    "(c.ticker = ANY(%s) OR c.company_name = ANY(%s))")
                params += [tickers, co_names]
        if years:
            clauses.append("c.year = ANY(%s)")
            params.append(years)

        where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
        sql = f"""
            SELECT DISTINCT c.ceo_id, c.company_name, c.ticker, c.year, c.ceo_name
            FROM t_ceo c
            JOIN t_ceo_statements s ON s.ceo_id = c.ceo_id
            {where}
            ORDER BY c.company_name, c.year
        """
        with self.conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        refreshed = skipped = error_count = 0
        for row in rows:
            ceo_id = row['ceo_id']
            company = row['company_name']
            ticker = row['ticker'] or ''
            year = row['year']
            ceo_name = row['ceo_name'] or ''
            try:
                # Delete existing statements for this CEO
                with self.conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM t_ceo_statements WHERE ceo_id = %s",
                        (ceo_id,))

                # Re-fetch
                statements = []
                if ticker:
                    statements += fetch_statements_fmp(ticker, ceo_name, year)
                statements += fetch_statements_ddgs(ceo_name, company, year)

                count = self.save_statements(
                    ceo_id, company, ticker, year, ceo_name, statements)
                refreshed += 1

                if on_progress:
                    on_progress({'ceo_id': ceo_id, 'company': company,
                                 'year': year, 'ceo_name': ceo_name,
                                 'statements_saved': count})
            except Exception as e:
                error_count += 1
                logger.error("clean_existing_statements %s/%s: %s",
                             company, year, e)

        return {'refreshed': refreshed, 'skipped': skipped,
                'error': error_count}

    # ── Query helpers (for UI) ─────────────────────────────────────────────────
    def get_progress_counts(self) -> dict:
        """How many (company, year) pairs are fully processed."""
        with _get_thread_conn().cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS ceo_rows FROM t_ceo")
            ceo_rows = cur.fetchone()['ceo_rows']
            cur.execute("SELECT COUNT(*) AS stmt_rows FROM t_ceo_statements")
            stmt_rows = cur.fetchone()['stmt_rows']
            cur.execute(
                "SELECT COUNT(DISTINCT (company_name, year)) AS pairs "
                "FROM t_ceo_statements")
            pairs = cur.fetchone()['pairs']
        return {'ceo_rows': ceo_rows, 'stmt_rows': stmt_rows,
                'covered_pairs': pairs}

    def search_statements(self, company: str = '', ceo: str = '',
                          year: int = None, stmt_type: str = '',
                          limit: int = 200) -> list[dict]:
        """Search t_ceo_statements for the UI data grid."""
        clauses, params = [], []
        if company:
            clauses.append("s.company_name ILIKE %s")
            params.append(f'%{company}%')
        if ceo:
            clauses.append("s.ceo_name ILIKE %s")
            params.append(f'%{ceo}%')
        if year:
            clauses.append("s.year = %s")
            params.append(year)
        if stmt_type:
            clauses.append("s.statement_type = %s")
            params.append(stmt_type)
        where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
        sql = f"""
            SELECT s.statement_id, s.company_name, s.ticker, s.year,
                   s.ceo_name, s.statement_type, s.statement_date,
                   s.source_title,
                   LEFT(s.statement_text, 300) AS preview,
                   s.source_url
            FROM t_ceo_statements s
            {where}
            ORDER BY s.year DESC, s.company_name
            LIMIT %s
        """
        params.append(limit)
        with self.conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
