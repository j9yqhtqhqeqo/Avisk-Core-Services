"""
FinancialDataScraper.py
=======================
Extracts annual financial metrics from SEC EDGAR XBRL company facts API
and writes them to t_financial_metrics.

No PDF parsing needed — EDGAR publishes machine-readable XBRL for every
10-K filer.  This is the same data that drives the SEC's EDGAR viewer and
financial data vendors.

Endpoint:
  https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json

Each US-GAAP concept returned looks like:
  {
    "label": "Revenue",
    "units": {
      "USD": [
        { "end": "2023-12-31", "val": 307394000000,
          "accn": "0001652044-24-000011", "form": "10-K",
          "fp": "FY", "frame": "CY2023" }
      ]
    }
  }

We filter for form == "10-K" (or 10-K405 etc.) and annual period (fp == "FY"
or frame startswith "CY"), then group by fiscal year, picking the most
recently-filed accession for each year.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── EDGAR constants ────────────────────────────────────────────────────────────
EDGAR_USER_AGENT = 'Avisk Research contact@avisk.com'
EDGAR_COMPANY_FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
EDGAR_COMPANY_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
EDGAR_10K_FORMS = {'10-K', '10-K405', '10-KSB', '10-KT'}

# ── XBRL concept → column mapping ─────────────────────────────────────────────
# Lists are tried in order; first one found with data wins for that column.
CONCEPT_MAP: Dict[str, List[str]] = {
    'revenue': [
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'Revenues',
        'SalesRevenueNet',
        'SalesRevenueGoodsNet',
        'RevenueFromContractWithCustomerIncludingAssessedTax',
        'RevenuesNetOfInterestExpense',
        # Banks/financial companies (AXP 2012-2014, WFC 2012-2015) report
        # gross interest income as their primary top-line revenue
        'InterestAndDividendIncomeOperating',
    ],
    'net_income': [
        'NetIncomeLoss',
        'ProfitLoss',
        'NetIncomeLossAvailableToCommonStockholdersBasic',
    ],
    'assets': [
        'Assets',
    ],
    'liabilities': [
        'Liabilities',
        'LiabilitiesAndStockholdersEquity',  # fallback
    ],
    'equity': [
        'StockholdersEquity',
        'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    ],
    'operating_expenses': [
        'OperatingExpenses',
        'CostsAndExpenses',
        # Banks (JPMorgan, BofA, etc.) report noninterest expense instead
        'NoninterestExpense',
        # Many companies report cost-of-goods + SG&A but not a rolled-up
        # OperatingExpenses line (Eli Lilly 2020+, Microsoft 2016-2022, etc.)
        'CostOfGoodsAndServicesSold',
        # Tech/service companies (IBM, Netflix, KLAC) file cost of revenue
        # as their primary cost line
        'CostOfRevenue',
        # Older filings (pre-2016): AMD, Costco, JNJ, Merck, Philip Morris,
        # P&G, Coca-Cola used the legacy CostOfGoodsSold tag instead of the
        # combined CostOfGoodsAndServicesSold concept
        'CostOfGoodsSold',
        # Linde plc (2016-2024) and some other industrials report SG&A as
        # their primary cost line when no rolled-up total is tagged
        'SellingGeneralAndAdministrativeExpense',
        'OperatingCostsAndExpenses',
        'BenefitsLossesAndExpenses',        # insurance companies
    ],
    'ebitda': [
        # EBITDA not directly reported; OperatingIncomeLoss is the best proxy
        'OperatingIncomeLoss',
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
        # Financial/energy companies (AXP, Chevron, Citigroup, JNJ, KLAC) use
        # this variant — excludes extraordinary items & minority interest
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
    ],
    'eps': [
        'EarningsPerShareDiluted',
        'EarningsPerShareBasic',
        # Pre-2015 filers that reported a single combined basic/diluted figure
        # (Tesla 2012-2014, early-stage companies)
        'EarningsPerShareBasicAndDiluted',
        'IncomeLossFromContinuingOperationsPerDilutedShare',
        'IncomeLossFromContinuingOperationsPerBasicShare',
    ],
    'cf_operations': [
        'NetCashProvidedByUsedInOperatingActivities',
        # Used by Apple, Exxon, Microsoft, Tesla in older 10-K filings
        'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
    ],
    'cf_investing': [
        'NetCashProvidedByUsedInInvestingActivities',
        'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
    ],
    'cf_financing': [
        'NetCashProvidedByUsedInFinancingActivities',
        'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
    ],
    # Free cash flow = CF Operations − CapEx (calculated, not mapped directly)
    'capex': [
        'PaymentsToAcquirePropertyPlantAndEquipment',
        'PaymentsForCapitalImprovements',
        'PaymentsToAcquireProductiveAssets',   # used by NVIDIA post-2012
    ],
    # Shares outstanding — used with stock price to compute market cap → Tobin's Q
    # Priority: exact year-end instant → weighted average (period proxy)
    # WeightedAverageNumberOfSharesOutstandingBasic is the most reliably filed
    # concept in all of EDGAR (mandatory since XBRL inception; it is the EPS
    # denominator) and fills gaps in early years (2009-2013) where the balance-
    # sheet concepts were often missing or mis-tagged.
    'shares_outstanding': [
        # ── Point-in-time (preferred) ─────────────────────────────────────────
        'CommonStockSharesOutstanding',
        'CommonStockSharesIssuedNet',
        'SharesOutstanding',
        # ── Weighted-average period proxy (reliable fallback) ─────────────────
        # Within 1-2% of year-end count for stable/slowly-buyback companies;
        # far better than NULL for Tobin's Q computation.
        'WeightedAverageNumberOfSharesOutstandingBasic',
        'WeightedAverageNumberOfDilutedSharesOutstanding',
        # Variant spellings used by some early EDGAR filers (pre-2014)
        'WeightedAverageNumberOfShareOutstandingBasic',
    ],
}

# ── Dual-class share aliases ──────────────────────────────────────────────────
# Some S&P 500 companies have two share classes (e.g. GOOG / GOOGL) that file a
# *single* 10-K under one CIK.  Map the non-primary company name → canonical
# company name so both tickers upsert into the same DB row instead of creating
# duplicates, and Tab 5 (Search) always shows a single entry.
_COMPANY_NAME_ALIASES: Dict[str, str] = {
    'Alphabet Inc Class A': 'Alphabet Inc Class C',   # GOOGL → GOOG
    # BRK.B → BRK.A (if present)
    'Berkshire Hathaway Class B': 'Berkshire Hathaway',
}

# ── Ticker → CIK cache (module-level, shared) ──────────────────────────────────
_ticker_map_cache: Optional[Dict] = None


def _get_headers() -> Dict[str, str]:
    return {
        'User-Agent': EDGAR_USER_AGENT,
        'Accept': 'application/json',
    }


def load_ticker_map() -> Dict[str, str]:
    """Load ticker → CIK mapping from EDGAR. Cached after first call."""
    global _ticker_map_cache
    if _ticker_map_cache is not None:
        return _ticker_map_cache

    try:
        resp = requests.get(
            EDGAR_COMPANY_TICKERS_URL,
            headers={**_get_headers(), 'Host': 'www.sec.gov'},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        ticker_map: Dict[str, str] = {}
        for entry in raw.values():
            t = str(entry.get('ticker', '')).upper()
            cik = str(entry.get('cik_str', '')).lstrip('0')
            if t and cik:
                ticker_map[t] = cik
        _ticker_map_cache = ticker_map
        logger.info(f"[XBRL] Loaded {len(ticker_map)} ticker→CIK mappings")
        return ticker_map
    except Exception as exc:
        logger.error(f"[XBRL] Failed to load ticker map: {exc}")
        return {}


def cik_for_symbol(symbol: str) -> Optional[str]:
    """Return zero-padded 10-digit CIK for a ticker symbol, or None."""
    ticker_map = load_ticker_map()
    cik = ticker_map.get(symbol.upper())
    if cik:
        return cik.zfill(10)
    return None


def _extract_dei_shares(
    facts: Dict,
    fiscal_end_dates: Dict[int, str],
    years_needed: Optional[List[int]] = None,
) -> Dict[int, float]:
    """
    Extract shares outstanding from the EDGAR *dei* namespace.

    ``dei/EntityCommonStockSharesOutstanding`` is filed on the cover page of
    every 10-K and is far more reliably tagged than the balance-sheet
    ``us-gaap/CommonStockSharesOutstanding`` concept.  It is an *instant*
    (point-in-time) value rather than a period value.

    For each reporting year we pick the entry whose date is closest to (and
    not later than) the fiscal year end date.  If we have no date to compare
    against, we fall back to year-of-date attribution.
    """
    dei = facts.get('dei', {})
    concept_data = dei.get('EntityCommonStockSharesOutstanding')
    if not concept_data:
        return {}

    # Collect candidate (date_str, value) pairs keyed by attributed year.
    #
    # KEY FIX: most 10-Ks are filed in February or March of the year *after*
    # the fiscal year end.  The cover-page EntityCommonStockSharesOutstanding
    # instant date therefore looks like "2013-02-15" for a FY2012 filing, which
    # the old Jan-1–10 heuristic wrongly attributes to year 2013.
    #
    # Correct attribution: a 10-K for FY{year} is filed 0–180 days after the
    # FYE.  Find the fiscal year whose FYE window contains the entry date.
    from datetime import datetime as _dt, timedelta as _td

    # Pre-parse FYE dates once for efficient comparison.
    _fye_dt: Dict[int, _dt] = {}
    for _yr, _fye_str in fiscal_end_dates.items():
        try:
            _fye_dt[_yr] = _dt.strptime(_fye_str, '%Y-%m-%d')
        except Exception:
            pass

    candidates: Dict[int, List[tuple]] = {}
    for unit_entries in concept_data.get('units', {}).values():
        for entry in unit_entries:
            form = entry.get('form', '')
            if form not in EDGAR_10K_FORMS:
                continue
            # DEI instant entries use 'instant'; period entries use 'end'
            date_str = entry.get('instant') or entry.get('end', '')
            if not date_str or len(date_str) < 10:
                continue
            val = entry.get('val')
            if not val or val == 0:
                continue

            # ── FYE-window attribution ────────────────────────────────────────
            # Find the year whose FYE is closest to (and just before) this
            # filing date.  Window: FYE − 10 days ≤ entry_date ≤ FYE + 180 days
            attributed_year = None
            best_gap: Optional[int] = None
            if _fye_dt:
                try:
                    entry_dt = _dt.strptime(date_str[:10], '%Y-%m-%d')
                    for _yr, _fye in _fye_dt.items():
                        if years_needed and _yr not in years_needed:
                            continue
                        delta = (entry_dt - _fye).days
                        if -10 <= delta <= 180:
                            if best_gap is None or abs(delta) < abs(best_gap):
                                best_gap = delta
                                attributed_year = _yr
                except Exception:
                    pass

            # ── Fallback: simple year heuristic (Jan 1–10 → prior year) ──────
            # Used when fiscal_end_dates is empty or no FYE window matched.
            if attributed_year is None:
                try:
                    y = int(date_str[:4])
                    m = int(date_str[5:7])
                    d = int(date_str[8:10])
                    attributed_year = y - 1 if (m == 1 and d <= 10) else y
                except (ValueError, IndexError):
                    continue
                if years_needed and attributed_year not in years_needed:
                    continue

            candidates.setdefault(attributed_year, []).append(
                (date_str, float(val)))

    result: Dict[int, float] = {}
    for year, pairs in candidates.items():
        fye = fiscal_end_dates.get(year, f'{year}-12-31')
        # Prefer entries on or before the fiscal year end date
        valid = [(d, v) for d, v in pairs if d <= fye]
        if valid:
            # Latest date wins (most recent filing for that FYE)
            result[year] = max(valid, key=lambda x: x[0])[1]
        elif pairs:
            # Fallback: entry closest in time to the FYE
            try:
                fye_dt = _dt.strptime(fye[:10], '%Y-%m-%d')
                result[year] = min(
                    pairs,
                    key=lambda x: abs(
                        (_dt.strptime(x[0][:10], '%Y-%m-%d') - fye_dt).days
                    )
                )[1]
            except Exception:
                result[year] = pairs[0][1]
    return result

    """
    Extract the fiscal/calendar year an XBRL data point belongs to.

    We use the *end-date year* as the primary source.  The `frame` field
    is NOT used for year attribution because EDGAR assigns a CY{year-1}
    frame to non-calendar fiscal year filers (e.g. NVIDIA FY2022 ended
    2022-01-30 but has frame='CY2021').  Using the end-date year means
    "the fiscal year whose books closed in this calendar year," which
    matches the company's own FY numbering.

    Frame patterns:
      CY2024        — full-year flow  ✅ keep
      CY2024Q4I     — year-end instant (balance sheet) ✅ keep
      CY2024Q1/Q2/Q3/Q4 — quarterly flow ❌ skip
    """
    frame = entry.get('frame', '')
    # Skip quarterly FLOW frames (e.g. CY2023Q4) but NOT instant frames
    # (e.g. CY2024Q4I).  Use fullmatch so the 'I' suffix is not ignored.
    if frame and re.fullmatch(r'CY\d{4}Q\d', frame):
        return None

    # Primary: end-date year, with adjustment for 52/53-week fiscal years
    # that end in early January (days 1-10).
    #
    # Examples:
    #   JNJ FY2015 ended 2016-01-03  →  return 2015  (frame=CY2015)
    #   JNJ FY2016 ended 2017-01-01  →  return 2016  (frame=CY2016)
    #   NVIDIA FY2022 ended 2022-01-30  →  return 2022  (day 30 > 10, no adj)
    #   WALMART FY2025 ended 2025-01-31  →  return 2025  (day 31 > 10, no adj)
    end = entry.get('end', '')
    if end and len(end) >= 10:
        try:
            end_year = int(end[:4])
            end_month = int(end[5:7])
            end_day = int(end[8:10])
            if end_month == 1 and end_day <= 10:
                # Fiscal year ended in the first week of January — it belongs
                # to the previous calendar year (52/53-week year-end convention).
                return end_year - 1
            return end_year
        except (ValueError, IndexError):
            pass
    elif end and len(end) >= 4:
        try:
            return int(end[:4])
        except ValueError:
            pass

    # Last resort: plain CY{year} frame
    if frame:
        m = re.match(r'CY(\d{4})$', frame)
        if m:
            return int(m.group(1))
    return None


def _extract_annual_values(
    facts: Dict, concept: str, years_needed: Optional[List[int]] = None
) -> Dict[int, float]:
    """
    Pull annual (10-K) values for a single US-GAAP concept from company facts.

    Returns:
        {fiscal_year: value}  — one value per year, latest accession wins.
    """
    us_gaap = facts.get('us-gaap', {})
    concept_data = us_gaap.get(concept)
    if not concept_data:
        return {}

    # Collect all annual entries: form must be a 10-K variant AND fp == 'FY'
    # or the frame is a plain CY{year} (no quarter suffix).
    annual: Dict[int, Tuple[str, float]] = {}  # year → (accn, val)

    for unit_entries in concept_data.get('units', {}).values():
        for entry in unit_entries:
            form = entry.get('form', '')
            fp = entry.get('fp', '')
            if form not in EDGAR_10K_FORMS:
                continue
            # Accept annual periods.
            # fp='FY'  — standard annual period (most filers)
            # fp='Q4'  — some filers (e.g. Mastercard) tag their year-end
            #            balance-sheet snapshot as Q4 inside a 10-K filing;
            #            this is still a valid full-year data point.
            # fp=''    — no fp; rely on frame check below.
            if fp and fp not in ('FY', 'Q4'):
                continue
            # If no fp (or fp=Q4 with no frame to cross-check), and frame is
            # present, allow plain annual (CY2024) and year-end instant
            # balance-sheet (CY2024Q4I); block mid-year quarterly flows.
            if not fp:
                frame = entry.get('frame', '')
                if frame and not re.match(r'^CY\d{4}($|Q\d+I$)', frame):
                    continue

            year = _fiscal_year_from_entry(entry)
            if year is None:
                continue
            if years_needed and year not in years_needed:
                continue

            val = entry.get('val')
            if val is None:
                continue

            accn = entry.get('accn', '')
            # Keep the entry with the latest (alphabetically largest) accession
            # number — this handles amended filings (10-K/A).
            existing = annual.get(year)
            if existing is None or accn >= existing[0]:
                annual[year] = (accn, float(val))

    return {yr: v for yr, (_, v) in annual.items()}


def _extract_fiscal_year_end_dates(
    facts: Dict, years_needed: Optional[List[int]] = None
) -> Dict[int, str]:
    """
    Return {reporting_year: end_date_str} by scanning 10-K entries for the
    actual fiscal year end date.  Used to look up the correct year-end stock
    price for P/E and to compute historically accurate beta/Sharpe ratios.

    Scans a priority list of flow concepts (most reliably tagged with fp=FY)
    and picks the entry with the latest accession number per year.
    """
    PROBE_CONCEPTS = [
        'NetIncomeLoss',
        'Revenues',
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'NetCashProvidedByUsedInOperatingActivities',
        'Assets',
    ]
    us_gaap = facts.get('us-gaap', {})
    end_dates: Dict[int, Tuple[str, str]] = {}  # year → (accn, end_date_str)

    for concept in PROBE_CONCEPTS:
        cd = us_gaap.get(concept)
        if not cd:
            continue
        found_any = False
        for unit_entries in cd.get('units', {}).values():
            for entry in unit_entries:
                form = entry.get('form', '')
                fp = entry.get('fp',   '')
                if form not in EDGAR_10K_FORMS:
                    continue
                if fp and fp not in ('FY', 'Q4'):
                    continue
                if not fp:
                    frame = entry.get('frame', '')
                    if frame and not re.match(r'^CY\d{4}($|Q\d+I$)', frame):
                        continue
                year = _fiscal_year_from_entry(entry)
                if year is None:
                    continue
                if years_needed and year not in years_needed:
                    continue
                end = entry.get('end', '')
                if not end:
                    continue
                accn = entry.get('accn', '')
                existing = end_dates.get(year)
                if existing is None or accn >= existing[0]:
                    end_dates[year] = (accn, end)
                    found_any = True
            break  # only need first unit type per concept
        if found_any and len(end_dates) > 0:
            # Once we have dates from a reliable concept, no need to keep probing
            # for years we already covered — but continue to fill missing years.
            pass

    return {yr: end for yr, (_, end) in end_dates.items()}


class FinancialDataScraper:
    """
    Scrapes annual financial metrics from EDGAR XBRL for a list of companies
    and writes them to t_financial_metrics.
    """

    def __init__(self, db_connection=None, years_needed: Optional[List[int]] = None):
        """
        Args:
            db_connection: psycopg2 connection (if None, data is returned but
                           not written to DB).
            years_needed:  list of years to pull (e.g. [2020, 2021, 2022]).
                           None → all available years.
        """
        self.db_connection = db_connection
        self.years_needed = years_needed
        self.session = requests.Session()
        self.session.headers.update(_get_headers())

    # ── Public API ──────────────────────────────────────────────────────────────

    def scrape_company(
        self, symbol: str, company_name: str
    ) -> List[Dict]:
        """
        Fetch XBRL financial facts for one company and return a list of
        per-year metric dicts ready for DB insertion.

        Each dict has keys matching t_financial_metrics columns.
        """
        # Normalise dual-class share names so both tickers (e.g. GOOG / GOOGL)
        # upsert into the same DB row.
        company_name = _COMPANY_NAME_ALIASES.get(company_name, company_name)

        cik_str = cik_for_symbol(symbol)
        if not cik_str:
            logger.warning(f"[XBRL] CIK not found for {symbol}")
            return []

        cik_int = int(cik_str)
        url = EDGAR_COMPANY_FACTS_URL.format(cik=cik_int)

        logger.info(
            f"[XBRL] Fetching company facts for {symbol} (CIK: {cik_int})")
        try:
            resp = self.session.get(
                url,
                headers={**_get_headers(), 'Host': 'data.sec.gov'},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[XBRL] HTTP {resp.status_code} for {symbol}")
                return []
            data = resp.json()
        except Exception as exc:
            logger.error(f"[XBRL] Request failed for {symbol}: {exc}")
            return []

        facts = data.get('facts', {})

        # ── Capture fiscal year end dates (for market data lookups) ───────────
        fiscal_end_dates = _extract_fiscal_year_end_dates(
            facts, self.years_needed)

        # ── Extract per-concept annual series ──────────────────────────────────
        # Merge across ALL matching concepts so companies that switch XBRL tags
        # between fiscal years (e.g. NVIDIA changed revenue concept after FY2022)
        # still get full coverage.  Earlier concepts in the list take priority;
        # later concepts only fill in years that are not yet present.
        extracted: Dict[str, Dict[int, float]] = {}
        for col, concepts in CONCEPT_MAP.items():
            merged: Dict[int, float] = {}
            for concept in concepts:
                vals = _extract_annual_values(
                    facts, concept, self.years_needed)
                if vals:
                    for yr, v in vals.items():
                        if yr not in merged:   # earlier concept wins for same year
                            merged[yr] = v
                    logger.debug(
                        f"[XBRL] {symbol} {col} ({concept}): {sorted(vals.keys())}")
            if merged:
                extracted[col] = merged

        # ── DEI fallback for shares_outstanding ───────────────────────────────
        # EntityCommonStockSharesOutstanding (dei namespace) is on the cover
        # page of every 10-K and fills gaps the us-gaap balance-sheet concept
        # often leaves behind.
        dei_shares = _extract_dei_shares(
            facts, fiscal_end_dates, self.years_needed)
        if dei_shares:
            existing = extracted.get('shares_outstanding', {})
            # Only fill years that are missing or zero in the us-gaap result
            filled = {yr: v for yr, v in dei_shares.items()
                      if yr not in existing or not existing[yr]}
            if filled:
                # existing wins on overlap
                merged_shares = {**filled, **existing}
                extracted['shares_outstanding'] = merged_shares
                logger.debug(
                    f"[XBRL] {symbol} DEI shares filled years: "
                    f"{sorted(filled.keys())}")

        if not extracted:
            logger.info(f"[XBRL] No annual XBRL data found for {symbol}")
            return []

        # ── Compute free cash flow = CF_ops − CapEx ────────────────────────────
        cf_ops = extracted.get('cf_operations', {})
        capex = extracted.get('capex', {})
        if cf_ops:
            fcf = {
                yr: cf_ops[yr] - capex.get(yr, 0.0)
                for yr in cf_ops
            }
            extracted['free_cash_flow'] = fcf

        # ── Union all years present in any column ──────────────────────────────
        all_years: set = set()
        for vals in extracted.values():
            all_years.update(vals.keys())

        rows = []
        for year in sorted(all_years):
            row = {
                'company_name': company_name,
                'symbol': symbol,
                'reporting_year': year,
                'assets':              extracted.get('assets', {}).get(year),
                'liabilities':         extracted.get('liabilities', {}).get(year),
                'equity':              extracted.get('equity', {}).get(year),
                'revenue':             extracted.get('revenue', {}).get(year),
                'operating_expenses':  extracted.get('operating_expenses', {}).get(year),
                'operating_income_ebitda': extracted.get('ebitda', {}).get(year),
                'net_income':          extracted.get('net_income', {}).get(year),
                'eps':                 extracted.get('eps', {}).get(year),
                'cash_flow_operations': extracted.get('cf_operations', {}).get(year),
                'cash_flow_investing':  extracted.get('cf_investing', {}).get(year),
                'cash_flow_financing':  extracted.get('cf_financing', {}).get(year),
                'free_cash_flow':       extracted.get('free_cash_flow', {}).get(year),
                'shares_outstanding':   extracted.get('shares_outstanding', {}).get(year),
                # stock_price, pe_ratio, roa, beta, sharpe come from MarketDataFetcher
                'fiscal_year_end_date':          fiscal_end_dates.get(year),
                'stock_price_calender_year_end': None,
                'pe_ratio': None,
                'return_on_asset': None,
                'exchange_ref': None,
                'beta_calender_year_end': None,
                'sharpe_ratio': None,
            }
            # Compute ROA if we have both net_income and assets
            if row['net_income'] and row['assets']:
                try:
                    row['return_on_asset'] = round(
                        row['net_income'] / row['assets'] * 100, 4)
                except ZeroDivisionError:
                    pass
            rows.append(row)

        logger.info(
            f"[XBRL] {symbol}: {len(rows)} year(s) of financial data extracted "
            f"({[r['reporting_year'] for r in rows]})")
        return rows

    def get_existing_years(self, company_name: str) -> set:
        """
        Return the set of reporting_year values already stored in
        t_financial_metrics for *company_name*.  Returns an empty set if there
        is no DB connection or the table is empty for that company.
        """
        company_name = _COMPANY_NAME_ALIASES.get(company_name, company_name)
        if not self.db_connection:
            return set()
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT reporting_year FROM t_financial_metrics "
                "WHERE company_name = %s",
                (company_name,),
            )
            return {r[0] for r in cursor.fetchall()}
        except Exception as exc:
            logger.warning(
                f"[XBRL] Could not query existing years for {company_name}: {exc}")
            return set()
        finally:
            cursor.close()

    def scrape_and_save(
        self, symbol: str, company_name: str
    ) -> Tuple[List[Dict], int]:
        """
        Scrape financial data for one company and upsert into t_financial_metrics.

        Returns:
            (rows, saved) — the list of year-dicts extracted from EDGAR and the
            number of rows that were successfully written to the DB.
        """
        rows = self.scrape_company(symbol, company_name)
        if not rows or not self.db_connection:
            return rows, len(rows)

        saved = 0
        for row in rows:
            try:
                self._upsert_row(row)
                saved += 1
            except Exception as exc:
                logger.error(
                    f"[XBRL] DB upsert failed for {symbol} {row['reporting_year']}: {exc}")
        logger.info(f"[XBRL] {symbol}: {saved}/{len(rows)} row(s) saved to DB")
        return rows, saved

    def scrape_batch(
        self,
        companies: List[Dict],   # [{'symbol': ..., 'company_name': ...}]
        progress_callback=None,  # callable(symbol, done, total)
    ) -> Dict[str, int]:
        """
        Scrape a batch of companies.

        Args:
            companies: list of dicts with 'symbol' and 'company_name' keys.
            progress_callback: optional callable called after each company.

        Returns:
            {symbol: rows_saved}
        """
        results = {}
        total = len(companies)
        for i, co in enumerate(companies, 1):
            sym = co['symbol']
            name = co['company_name']
            logger.info(f"[XBRL] Processing {i}/{total}: {sym}")
            _, saved = self.scrape_and_save(sym, name)
            results[sym] = saved
            if progress_callback:
                progress_callback(sym, i, total)
            # Be polite to EDGAR (max 10 req/sec)
            time.sleep(0.15)
        return results

    # ── DB helpers ──────────────────────────────────────────────────────────────

    def _upsert_row(self, row: Dict) -> None:
        """
        Upsert one row into t_financial_metrics.
        Uses ON CONFLICT (company_name, reporting_year) DO UPDATE so re-runs
        are idempotent and updates existing data.

        NOT NULL columns default to 0; audit columns are set automatically.
        """
        import datetime as _dt

        def _int(v): return int(v) if v is not None else 0
        def _float(v): return float(v) if v is not None else 0.0

        now = _dt.datetime.utcnow()
        agent = 'XBRL Scraper'

        sql = """
            INSERT INTO t_financial_metrics (
                company_name, reporting_year,
                assets, liabilities, equity,
                revenue, operating_expenses, operating_income_ebitda,
                net_income, eps,
                cash_flow_operations, cash_flow_investing,
                cash_flow_financing, free_cash_flow,
                shares_outstanding,
                fiscal_year_end_date,
                stock_price_calender_year_end, pe_ratio,
                return_on_asset, exchange_ref,
                beta_calender_year_end, sharpe_ratio,
                added_dt, added_by, modify_dt, modify_by
            ) VALUES (
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s,
                %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (company_name, reporting_year) DO UPDATE SET
                assets                       = EXCLUDED.assets,
                liabilities                  = EXCLUDED.liabilities,
                equity                       = EXCLUDED.equity,
                revenue                      = EXCLUDED.revenue,
                operating_expenses           = EXCLUDED.operating_expenses,
                operating_income_ebitda      = EXCLUDED.operating_income_ebitda,
                net_income                   = EXCLUDED.net_income,
                eps                          = EXCLUDED.eps,
                cash_flow_operations         = EXCLUDED.cash_flow_operations,
                cash_flow_investing          = EXCLUDED.cash_flow_investing,
                cash_flow_financing          = EXCLUDED.cash_flow_financing,
                free_cash_flow               = EXCLUDED.free_cash_flow,
                shares_outstanding            = COALESCE(
                                               NULLIF(EXCLUDED.shares_outstanding, 0),
                                               t_financial_metrics.shares_outstanding),
                fiscal_year_end_date         = COALESCE(EXCLUDED.fiscal_year_end_date,
                                               t_financial_metrics.fiscal_year_end_date),
                return_on_asset              = COALESCE(EXCLUDED.return_on_asset,
                                               t_financial_metrics.return_on_asset),
                modify_dt                    = EXCLUDED.modify_dt,
                modify_by                    = EXCLUDED.modify_by
        """
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(sql, (
                row['company_name'], row['reporting_year'],
                _int(row['assets']),          _int(
                    row['liabilities']),     _int(row['equity']),
                _int(row['revenue']),         _int(row['operating_expenses']),
                _int(row['operating_income_ebitda']),
                _int(row['net_income']),      _float(row['eps']),
                _int(row['cash_flow_operations']),
                _int(row['cash_flow_investing']),
                _int(row['cash_flow_financing']),
                _int(row['free_cash_flow']),
                # shares_outstanding: store NULL rather than 0 so COALESCE
                # never overwrites a good value with 0.
                (int(row['shares_outstanding'])
                 if row.get('shares_outstanding') else None),
                row.get('fiscal_year_end_date'),
                _float(row['stock_price_calender_year_end']),
                row['pe_ratio'],
                row['return_on_asset'],       row['exchange_ref'],
                row['beta_calender_year_end'], row['sharpe_ratio'],
                now, agent, now, agent,
            ))
            self.db_connection.commit()
        except Exception:
            self.db_connection.rollback()
            raise
        finally:
            cursor.close()
