"""
MarketDataFetcher.py
====================
Fetches end-of-fiscal-year stock prices and computes Beta and Sharpe Ratio
using yfinance.  Updates t_financial_metrics in-place (market columns only —
EDGAR financial data is never overwritten).

Metrics calculated
------------------
stock_price_calender_year_end
    Closing price on the last trading day on or before fiscal_year_end_date.

beta_calender_year_end
    Trailing 52-week beta vs SPY using weekly returns ending on
    fiscal_year_end_date.
        β = Cov(r_stock, r_SPY) / Var(r_SPY)

sharpe_ratio
    Annualised Sharpe ratio for the 52-week period ending on
    fiscal_year_end_date.
        Sharpe = mean(daily_excess) / std(daily_excess) × √252
    Excess return = daily_return − risk_free_daily  (default 4 % p.a.)

pe_ratio
    Price / EPS (diluted), computed from the fetched price and the EPS
    already stored in t_financial_metrics.

Requires
--------
    pip install yfinance>=0.2.0
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Risk-free rate proxy (annualised) ─────────────────────────────────────────
# Approximates US 3-month T-bill / 10-year treasury average.
# Can be overridden per-instance via MarketDataFetcher(risk_free_annual=...).
DEFAULT_RISK_FREE = 0.04   # 4 % p.a.

# ── Module-level SPY caches (keyed by calendar year) ─────────────────────────
# Avoids downloading SPY repeatedly when processing many companies in the
# same fiscal year.
_spy_weekly_cache: Dict[int, pd.Series] = {}
_spy_daily_cache:  Dict[int, pd.Series] = {}


# ── Low-level market data helpers ─────────────────────────────────────────────

def _ticker_history(symbol: str, start: str, end: str,
                    interval: str = '1d') -> pd.Series:
    """Download Close series via yfinance; returns empty Series on error."""
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(
            start=start, end=end, interval=interval, auto_adjust=True)
        if hist.empty:
            return pd.Series(dtype=float)
        close = hist['Close']
        # Normalise to tz-naive date index so pd.concat aligns reliably
        # regardless of yfinance version or ticker exchange.
        if hasattr(close.index, 'tz') and close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        close.index = close.index.normalize()
        return close
    except Exception as exc:
        logger.warning(f"[MktData] yfinance error for {symbol}: {exc}")
        return pd.Series(dtype=float)


def _spy_weekly(end_dt: datetime) -> Optional[pd.Series]:
    """
    Cached SPY weekly returns for the 52-week window ending on end_dt.

    Cache is keyed by the EXACT end date (not just calendar year) because
    NVIDIA's January fiscal year end would otherwise poison the cache for
    all December-FYE companies in that same calendar year, giving only
    ~4 weeks of overlap and causing beta = None.
    """
    key = end_dt.strftime('%Y-%m-%d')          # exact date, not end_dt.year
    if key not in _spy_weekly_cache:
        start = (end_dt - timedelta(days=390)).strftime('%Y-%m-%d')
        end = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        prices = _ticker_history('SPY', start, end, interval='1wk')
        _spy_weekly_cache[key] = prices.pct_change().dropna()
    series = _spy_weekly_cache[key]
    return series if len(series) >= 10 else None


def _spy_daily(end_dt: datetime) -> Optional[pd.Series]:
    """
    Cached SPY daily returns for the 52-week window ending on end_dt.
    Cache keyed by exact date (see _spy_weekly for rationale).
    """
    key = end_dt.strftime('%Y-%m-%d')          # exact date, not end_dt.year
    if key not in _spy_daily_cache:
        start = (end_dt - timedelta(days=390)).strftime('%Y-%m-%d')
        end = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        prices = _ticker_history('SPY', start, end)
        _spy_daily_cache[key] = prices.pct_change().dropna()
    series = _spy_daily_cache[key]
    return series if len(series) >= 20 else None


def fetch_year_end_price(symbol: str, fiscal_year_end: str) -> Optional[float]:
    """
    Return the closing price on or just before fiscal_year_end.
    Looks back up to 7 calendar days to skip weekends / market holidays.
    """
    try:
        end_dt = datetime.strptime(fiscal_year_end[:10], '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=7)
        prices = _ticker_history(
            symbol,
            start_dt.strftime('%Y-%m-%d'),
            (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        if prices.empty:
            logger.warning(
                f"[MktData] No price data for {symbol} @ {fiscal_year_end}")
            return None
        return round(float(prices.iloc[-1]), 4)
    except Exception as exc:
        logger.warning(
            f"[MktData] Price failed {symbol} @ {fiscal_year_end}: {exc}")
        return None


def compute_beta(symbol: str, fiscal_year_end: str) -> Optional[float]:
    """
    52-week trailing beta vs SPY using weekly returns ending on
    fiscal_year_end.  β = Cov(r_i, r_m) / Var(r_m).
    """
    try:
        end_dt = datetime.strptime(fiscal_year_end[:10], '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=390)
        stock_prices = _ticker_history(
            symbol,
            start_dt.strftime('%Y-%m-%d'),
            (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
            interval='1wk',
        )
        spy = _spy_weekly(end_dt)
        if stock_prices.empty or spy is None:
            return None
        stock_ret = stock_prices.pct_change().dropna()
        aligned = pd.concat([stock_ret, spy], axis=1, join='inner').dropna()
        if len(aligned) < 10:
            return None
        cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
        var = aligned.iloc[:, 1].var()
        return round(cov / var, 4) if var > 0 else None
    except Exception as exc:
        logger.warning(
            f"[MktData] Beta failed {symbol} @ {fiscal_year_end}: {exc}")
        return None


def compute_sharpe(
    symbol: str,
    fiscal_year_end: str,
    risk_free_annual: float = DEFAULT_RISK_FREE,
) -> Optional[float]:
    """
    Annualised Sharpe ratio for the 52-week period ending on fiscal_year_end.
    Sharpe = mean(daily_excess) / std(daily_excess) × √252
    """
    try:
        end_dt = datetime.strptime(fiscal_year_end[:10], '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=390)
        prices = _ticker_history(
            symbol,
            start_dt.strftime('%Y-%m-%d'),
            (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        if len(prices) < 20:
            return None
        daily_ret = prices.pct_change().dropna()
        rf_daily = risk_free_annual / 252
        excess = daily_ret - rf_daily
        std = excess.std()
        if std == 0:
            return None
        return round(float(excess.mean() / std * np.sqrt(252)), 4)
    except Exception as exc:
        logger.warning(
            f"[MktData] Sharpe failed {symbol} @ {fiscal_year_end}: {exc}")
        return None


def _fetch_shares_edgar(
    symbol: str, company_name: str, year: int
) -> Optional[int]:
    """
    Re-scrape EDGAR XBRL for a single year and return shares_outstanding.

    This picks up WeightedAverageNumberOfSharesOutstandingBasic (added to
    CONCEPT_MAP) which is the most reliably tagged shares concept in early
    EDGAR filings (2009-2013) and is often present when balance-sheet
    point-in-time concepts are missing.

    Uses FinancialDataScraper with years_needed=[year] so only one EDGAR
    call is made.  No DB write — caller is responsible for persistence.
    """
    try:
        from Services.FinancialDataScraper import FinancialDataScraper
        scraper = FinancialDataScraper(db_connection=None, years_needed=[year])
        rows = scraper.scrape_company(symbol, company_name)
        for row in rows:
            if row.get('reporting_year') == year:
                shares = row.get('shares_outstanding')
                if shares and shares > 0:
                    return int(shares)
        return None
    except Exception as exc:
        logger.warning(
            f"[MktData] EDGAR re-scrape shares failed {symbol} {year}: {exc}")
        return None


# ── Ticker rename map for yfinance layer-2 fallback ─────────────────────────
# Some companies changed tickers (renamed or merged).  yfinance can only query
# by the *current* ticker; for historical years we must use the *old* ticker so
# Yahoo Finance returns data for the correct time window.
#
# Format:  current_symbol → (last_year_old_ticker_was_used, old_ticker)
_HISTORICAL_TICKERS: Dict[str, Tuple[int, str]] = {
    'META': (2021, 'FB'),   # Facebook → Meta Platforms, Oct 2021
    # United Technologies → Raytheon Technologies, Apr 2020
    'RTX':  (2019, 'UTX'),
    'LIN':  (2017, 'PX'),   # Praxair → Linde plc, Oct 2018
}


def _historical_ticker(symbol: str, year: int) -> str:
    """
    Return the ticker that was valid for *symbol* during *year*.

    For companies that renamed / rebranded after a merger, yfinance will not
    carry historical share data under the current ticker.  This maps to the
    old ticker for affected fiscal years so the correct Yahoo Finance series
    is retrieved.
    """
    if symbol in _HISTORICAL_TICKERS:
        last_old_year, old_ticker = _HISTORICAL_TICKERS[symbol]
        if year <= last_old_year:
            return old_ticker
    return symbol


def _fetch_shares_yfinance(
    symbol: str, fiscal_year_end: str
) -> Optional[int]:
    """
    Fetch historical shares outstanding from yfinance as a last-resort fallback
    when EDGAR XBRL (both us-gaap and dei) has no value for a given year.

    Uses ``Ticker.get_shares_full()`` which returns a quarterly time-series
    of shares outstanding sourced from SEC filings.  The SEC quarterly filing
    that *contains* the share count is often filed 60-90 days after quarter-
    end, so a narrow window misses many valid entries.  We therefore use a
    wide ±1-year window and then pick the entry on or closest to the FYE.
    """
    try:
        import yfinance as yf
        end_dt = datetime.strptime(fiscal_year_end[:10], '%Y-%m-%d')
        # Wide window: 1 year before FYE → 1 year after FYE.
        # The entry closest to (and not after) the FYE is preferred.
        start_dt = end_dt - timedelta(days=365)
        fetch_end = end_dt + timedelta(days=365)
        series = yf.Ticker(symbol).get_shares_full(
            start=start_dt.strftime('%Y-%m-%d'),
            end=fetch_end.strftime('%Y-%m-%d'),
        )
        if series is None or len(series) == 0:
            return None
        # Normalise index to tz-naive timestamps
        if hasattr(series.index, 'tz') and series.index.tz is not None:
            series.index = series.index.tz_localize(None)
        series.index = series.index.normalize()
        fye_ts = pd.Timestamp(fiscal_year_end[:10])
        # Prefer the most recent entry on or before the FYE
        valid = series[series.index <= fye_ts]
        if not valid.empty:
            val = int(valid.iloc[-1])
        else:
            # Fallback: first available entry after FYE
            after = series[series.index > fye_ts]
            val = int(after.iloc[0]) if not after.empty else int(
                series.iloc[-1])
        return val if val > 0 else None
    except Exception as exc:
        logger.warning(
            f"[MktData] yfinance shares failed {symbol} @ {fiscal_year_end}: {exc}")
        return None


# ── Main class ────────────────────────────────────────────────────────────────

class MarketDataFetcher:
    """
    Fetches year-end stock prices, beta, and Sharpe ratio for companies that
    already have rows in t_financial_metrics, then upserts the market columns
    back.

    Does NOT touch EDGAR-sourced financial columns (revenue, net_income, …).

    Typical usage
    -------------
        fetcher = MarketDataFetcher(db_conn)
        results = fetcher.update_company('AAPL', 'Apple Inc')

    Ratios computed
    ---------------
    P/E ratio:   stock_price / eps  (from t_financial_metrics.eps)
    Beta:        52-week trailing vs SPY (weekly returns)
    Sharpe:      annualised, using 52 weeks of daily returns
    """

    def __init__(
        self,
        db_connection,
        risk_free_annual: float = DEFAULT_RISK_FREE,
    ):
        self.db_connection = db_connection
        self.risk_free_annual = risk_free_annual

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_company(
        self, symbol: str, company_name: str
    ) -> List[Dict]:
        """
        Fetch market data for all DB rows that have fiscal_year_end_date set.

        Returns a list of per-year result dicts for UI display.
        """
        rows = self._load_company_rows(company_name)
        if not rows:
            msg = (f"[MktData] {symbol}: no rows with fiscal_year_end_date "
                   f"— re-extract EDGAR data first")
            logger.info(msg)
            print(msg)
            return []

        print(f"[MktData] {symbol} ({company_name}) — "
              f"{len(rows)} year(s) to update")

        results = []
        for row in rows:
            year = row['reporting_year']
            fye = row['fiscal_year_end_date']     # e.g. '2024-09-28'
            eps = row.get('eps')
            assets = row.get('assets')
            liabs = row.get('liabilities')
            shares = row.get('shares_outstanding')

            price = fetch_year_end_price(symbol, fye)
            beta = compute_beta(symbol, fye)
            sharpe = compute_sharpe(symbol, fye, self.risk_free_annual)
            pe = (round(price / eps, 2)
                  if price is not None and eps and eps != 0 else None)

            # yfinance fallback for shares_outstanding when EDGAR has no value
            if not shares and fye:
                shares = _fetch_shares_yfinance(symbol, fye)
                if shares:
                    print(
                        f"  [{symbol} {year}] shares from yfinance: {shares:,}")
                    # Persist so future runs don't need to re-fetch
                    self._write_shares(company_name, year, shares)

            # Tobin's Q = (Market Cap + Total Liabilities) / Total Assets
            # Market Cap = price × shares_outstanding
            tobins_q = None
            if price and shares and shares > 0 and assets and assets > 0:
                market_cap = price * shares
                tobins_q = round((market_cap + (liabs or 0)) / assets, 4)

            # Derived EPS fallback — for companies (e.g. Visa) that don't tag
            # EarningsPerShareDiluted in XBRL at all.  Only fills when eps IS
            # NULL; never overwrites a value already set by EDGAR extraction.
            derived_eps = None
            if not eps:
                net_income = row.get('net_income')
                if net_income and shares and shares > 0:
                    derived_eps = round(net_income / shares, 4)
                    print(
                        f"  [{symbol} {year}] EPS derived from "
                        f"net_income/shares: {derived_eps}")

            self._upsert_market_row(
                company_name, year, price, beta, sharpe, pe, tobins_q,
                derived_eps)
            results.append({
                'year':           year,
                'fiscal_year_end': fye,
                'price':          price,
                'beta':           beta,
                'sharpe':         sharpe,
                'pe_ratio':       pe,
                'tobins_q':       tobins_q,
            })

            def _fmt(v, prefix=''):
                return f"{prefix}{v}" if v is not None else 'N/A'

            line = (
                f"  {symbol} {year} ({fye})"
                f"  price={_fmt(price, '$')}"
                f"  beta={_fmt(beta)}"
                f"  sharpe={_fmt(sharpe)}"
                f"  pe={_fmt(pe)}"
                f"  tobins_q={_fmt(tobins_q)}"
            )
            logger.info(line)
            print(line)
            time.sleep(0.1)   # polite delay for yfinance

        print(f"[MktData] {symbol} done — {len(results)} year(s) saved.")
        return results

    def update_batch(
        self,
        # [{'symbol': ..., 'company_name': ...}]
        companies: List[Dict],
        progress_callback=None,          # callable(symbol, done, total)
    ) -> Dict[str, List[Dict]]:
        """Process a list of companies; returns {symbol: [result_dicts]}."""
        # Clear module-level SPY caches so a fresh batch always fetches
        # correctly-windowed SPY data (avoids stale entries from a prior run
        # or from a different set of fiscal year end dates).
        _spy_weekly_cache.clear()
        _spy_daily_cache.clear()

        results = {}
        total = len(companies)
        print(f"[MktData] Starting batch: {total} company/ies")
        for i, co in enumerate(companies, 1):
            sym = co['symbol']
            name = co['company_name']
            print(f"[MktData] [{i}/{total}] {sym} — {name}")
            logger.info(f"[MktData] {i}/{total}: {sym}")
            results[sym] = self.update_company(sym, name)
            if progress_callback:
                progress_callback(sym, i, total)
        print(f"[MktData] Batch complete — {total} company/ies processed.")
        return results

    def _write_shares(
        self, company_name: str, reporting_year: int, shares: int
    ) -> None:
        """
        Persist a yfinance-sourced shares_outstanding value back to the DB.
        Only writes if the existing value is NULL or 0 (never overwrites a
        good EDGAR value).
        """
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE t_financial_metrics
                SET    shares_outstanding = %s
                WHERE  company_name   = %s
                  AND  reporting_year = %s
                  AND  (shares_outstanding IS NULL OR shares_outstanding = 0)
                """,
                (shares, company_name, reporting_year),
            )
            self.db_connection.commit()
        except Exception:
            self.db_connection.rollback()
        finally:
            cursor.close()

    def patch_missing_shares(
        self, symbol: str, company_name: str
    ):
        """
        Targeted fix: query every row for *company_name* where
        ``shares_outstanding`` is NULL (or 0) and try to fill it using
        the yfinance wide-window fallback.

        Returns a tuple:
            (patched_count: int, still_missing: List[Dict])

        ``still_missing`` contains one dict per year that could not be filled:
            {'year': int, 'fiscal_year_end': str, 'reason': str}

        Tobins_q is also recomputed and saved for any row where price and
        balance-sheet data are available after patching shares.

        Known-unsolvable cases:
        - Palantir pre-2020:  private company, no public shares data before IPO
        - Linde plc pre-2018: German Linde AG / pre-merger, not SEC-registered
        - AbbVie pre-2013:    spun off from Abbott Jan 1 2013; no prior FY filings
        """
        # ── Known-unsolvable guard ──────────────────────────────────────────
        _UNSOLVABLE: Dict[str, int] = {
            # company_name (exact, lowercase) → first year with public data
            'palantir technologies inc. class a common stock': 2020,
            'linde plc ordinary shares': 2018,
            'abbvie inc': 2013,
        }
        key = company_name.lower()
        if key in _UNSOLVABLE:
            first_ok = _UNSOLVABLE[key]
            print(f"  [{symbol}] NOTE: {company_name} has no public share data "
                  f"before {first_ok} (corporate structure). Skipping pre-{first_ok} rows.")

        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                """
                SELECT reporting_year,
                       fiscal_year_end_date::text,
                       assets, liabilities,
                       stock_price_calender_year_end
                FROM   t_financial_metrics
                WHERE  company_name = %s
                  AND  fiscal_year_end_date IS NOT NULL
                  AND  (shares_outstanding IS NULL OR shares_outstanding = 0)
                ORDER  BY reporting_year
                """,
                (company_name,),
            )
            rows = cursor.fetchall()
        except Exception as exc:
            logger.warning(
                f"[MktData] patch_missing_shares query failed {symbol}: {exc}")
            return 0, []
        finally:
            cursor.close()

        if not rows:
            return 0, []

        patched = 0
        still_missing: List[Dict] = []
        min_year = _UNSOLVABLE.get(key, 0)

        for year, fye, assets, liabilities, price in rows:
            # Skip known-unsolvable years
            if year < min_year:
                reason = (f"Pre-{min_year} corporate structure "
                          f"(no public data before {min_year})")
                logger.info(
                    f"[MktData] {symbol} {year}: skipped — {reason}")
                still_missing.append(
                    {'year': year, 'fiscal_year_end': fye, 'reason': reason})
                continue

            # ── Layer 1: EDGAR re-scrape ──────────────────────────────────
            # Picks up WeightedAverageNumberOfSharesOutstandingBasic which is
            # reliably tagged in early EDGAR filings (2009-2013) and often
            # present when balance-sheet point-in-time concepts are absent.
            shares = _fetch_shares_edgar(symbol, company_name, year)
            if shares:
                print(
                    f"  [{symbol} {year}] patched shares from EDGAR: {shares:,}")

            # ── Layer 2: yfinance (historical ticker aware) ───────────────────
            # Use the ticker that was valid during *year* (e.g. FB for META
            # pre-2022, UTX for RTX pre-2020, PX for LIN pre-2018).
            if not shares:
                yf_sym = _historical_ticker(symbol, year)
                shares = _fetch_shares_yfinance(yf_sym, fye)
                if shares:
                    label = (
                        f"{yf_sym} (historical)" if yf_sym != symbol
                        else yf_sym
                    )
                    print(
                        f"  [{symbol} {year}] patched shares from yfinance "
                        f"({label}): {shares:,}")

            if not shares:
                logger.info(
                    f"[MktData] {symbol} {year}: not found in EDGAR or yfinance")
                still_missing.append(
                    {'year': year, 'fiscal_year_end': fye,
                     'reason': 'Not found in EDGAR or yfinance'})
                continue

            self._write_shares(company_name, year, shares)
            patched += 1

            # Recompute Tobin's Q now that shares are available
            if price and shares > 0 and assets and assets > 0:
                market_cap = price * shares
                tobins_q = round((market_cap + (liabilities or 0)) / assets, 4)
                upd = self.db_connection.cursor()
                try:
                    upd.execute(
                        """
                        UPDATE t_financial_metrics
                        SET    tobins_q  = %s,
                               modify_dt = NOW(),
                               modify_by = 'Shares Patcher'
                        WHERE  company_name   = %s
                          AND  reporting_year = %s
                        """,
                        (tobins_q, company_name, year),
                    )
                    self.db_connection.commit()
                except Exception:
                    self.db_connection.rollback()
                finally:
                    upd.close()

        return patched, still_missing

    def rows_missing_fye(self, company_name: str) -> int:
        """Return count of rows for company_name with no fiscal_year_end_date."""
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM t_financial_metrics "
                "WHERE company_name = %s AND fiscal_year_end_date IS NULL",
                (company_name,),
            )
            return cursor.fetchone()[0]
        except Exception:
            return 0
        finally:
            cursor.close()

    # ── DB helpers ─────────────────────────────────────────────────────────────

    def _load_company_rows(self, company_name: str) -> List[Dict]:
        """Load rows that have fiscal_year_end_date populated."""
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                """
                SELECT reporting_year,
                       fiscal_year_end_date::text AS fiscal_year_end_date,
                       eps,
                       net_income,
                       assets,
                       liabilities,
                       NULLIF(shares_outstanding, 0) AS shares_outstanding
                FROM   t_financial_metrics
                WHERE  company_name = %s
                  AND  fiscal_year_end_date IS NOT NULL
                ORDER  BY reporting_year
                """,
                (company_name,),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as exc:
            logger.warning(
                f"[MktData] DB load failed for {company_name}: {exc}")
            return []
        finally:
            cursor.close()

    @staticmethod
    def _f(v) -> Optional[float]:
        """Convert numpy scalar → native Python float (None stays None).
        psycopg2 cannot adapt numpy types and will raise a 'schema does not
        exist' error if a numpy.float64 is passed directly as a parameter."""
        if v is None:
            return None
        try:
            f = float(v)
            return None if (f != f) else f   # NaN → None
        except (TypeError, ValueError):
            return None

    def _upsert_market_row(
        self,
        company_name: str,
        reporting_year: int,
        price:    Optional[float],
        beta:     Optional[float],
        sharpe:   Optional[float],
        pe_ratio: Optional[float],
        tobins_q: Optional[float] = None,
        eps:      Optional[float] = None,
    ) -> None:
        """
        Update only the market-data columns for an existing row.
        EDGAR financial columns are left untouched.
        eps is only written when the existing DB value is NULL (COALESCE).
        """
        import datetime as _dt
        # Coerce all numpy scalars to native Python floats so psycopg2
        # can serialise them correctly.
        price, beta, sharpe, pe_ratio, tobins_q, eps = (
            self._f(price), self._f(beta), self._f(sharpe),
            self._f(pe_ratio), self._f(tobins_q), self._f(eps)
        )
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE t_financial_metrics
                SET    stock_price_calender_year_end = %s,
                       beta_calender_year_end        = %s,
                       sharpe_ratio                  = %s,
                       pe_ratio                      = %s,
                       tobins_q                      = %s,
                       eps                           = COALESCE(NULLIF(eps, 0), %s),
                       -- When we successfully write eps, strip it from the
                       -- missing_data_reason so the gap list stays accurate.
                       missing_data_reason = CASE
                           WHEN %s IS NOT NULL AND missing_data_reason IS NOT NULL
                           THEN NULLIF(
                               TRIM(BOTH ', ' FROM
                                   REGEXP_REPLACE(missing_data_reason,
                                       '(^|, )eps(, |$)', '', 'g')),
                               '')
                           ELSE missing_data_reason
                       END,
                       modify_dt                     = %s,
                       modify_by                     = %s
                WHERE  company_name   = %s
                  AND  reporting_year = %s
                """,
                (
                    price, beta, sharpe, pe_ratio, tobins_q, eps,
                    eps,   # extra bind for the CASE WHEN %s IS NOT NULL check
                    _dt.datetime.utcnow(), 'Market Data Fetcher',
                    company_name, reporting_year,
                ),
            )
            self.db_connection.commit()
        except Exception as exc:
            self.db_connection.rollback()
            logger.error(
                f"[MktData] DB update failed {company_name} {reporting_year}: {exc}")
        finally:
            cursor.close()
