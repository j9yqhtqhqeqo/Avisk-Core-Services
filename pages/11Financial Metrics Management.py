"""
Step 11 - Financial Data Management Studio
==========================================
Reads annual financial metrics directly from SEC EDGAR XBRL.
Data is written to t_financial_metrics via an upsert so re-runs are safe.
"""

import datetime
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

st.set_page_config(
    page_title="Financial Data Management Studio",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💰 Financial Data Management Studio")
st.markdown(
    "Pulls structured annual financial data directly from **SEC EDGAR XBRL** "
    "(the same source used by Bloomberg / FactSet) and saves it to `t_financial_metrics`."
)
st.markdown("---")

_SP500_CSV = Path(__file__).resolve().parent.parent / \
    "Clients" / "sp500_market_cap_ranked.csv"
_CKEY = "fin_companies_select"
_PENDING = "fin_companies_pending"

for _k, _v in {
    "fin_companies_df":       None,
    "fin_selected_companies": [],
    "fin_extract_results":    None,
    "fin_years":              None,
    "fin_patch_results":      None,   # auto-populated after each extract run
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


@st.cache_data(ttl=3600, show_spinner=False)
def load_companies() -> pd.DataFrame:
    try:
        if _SP500_CSV.exists():
            df = pd.read_csv(_SP500_CSV)
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={"company": "Company", "symbol": "Symbol",
                                    "sector": "Sector", "rank": "rank"})
            return df
        import requests
        from io import StringIO
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=30,
        )
        resp.raise_for_status()
        df = pd.read_html(StringIO(resp.text))[0]
        df = df.rename(columns={"Symbol": "Symbol",
                       "Security": "Company", "GICS Sector": "Sector"})
        df["rank"] = range(1, len(df) + 1)
        return df
    except Exception as exc:
        st.error(f"Could not load company list: {exc}")
        return pd.DataFrame(columns=["Symbol", "Company", "Sector", "rank"])


def _parse_symbol(option: str) -> str:
    return option.split(" - ")[0].split(" ")[-1]


if st.session_state.fin_companies_df is None:
    with st.spinner("Loading S&P 500 companies ..."):
        st.session_state.fin_companies_df = load_companies()

current_year = datetime.datetime.now().year


@st.cache_data(ttl=300, show_spinner=False)
def _load_ds_years() -> list:
    """Distinct years from t_data_source, descending. Clamped to 2000–current year."""
    import psycopg2
    from Utilities.Lookups import DB_Connection
    conn_str = DB_Connection().DB_CONNECTION_STRING
    if not conn_str:
        raise ValueError("DB_CONNECTION_STRING is not configured")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT year FROM t_data_source
        WHERE year BETWEEN 2000 AND EXTRACT(YEAR FROM CURRENT_DATE)
        ORDER BY year DESC
    """)
    years = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return years


@st.cache_data(ttl=300, show_spinner=False)
def _load_ds_companies() -> list:
    """Distinct company names from t_data_source, alphabetical."""
    import psycopg2
    from Utilities.Lookups import DB_Connection
    conn_str = DB_Connection().DB_CONNECTION_STRING
    if not conn_str:
        raise ValueError("DB_CONNECTION_STRING is not configured")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT company_name FROM t_data_source ORDER BY company_name")
    companies = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return companies


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Select Companies",
    "📅 Select Years",
    "🚀 Extract Financial Data",
    "📈 Update Market Data",
    "🔍 Search Financial Metrics",
])

# =============================================================================
# TAB 1 - Company Selection
# =============================================================================
with tab1:
    st.header("Select Companies")
    df = st.session_state.fin_companies_df

    if df is None or df.empty:
        st.warning("Company list not loaded.")
    else:
        st.markdown("---")
        st.subheader("🔍 Filter & Select Companies")

        col1, col2, col3 = st.columns(3)

        with col1:
            search_term = st.text_input("Search by Name or Symbol",
                                        placeholder="e.g., Apple, AAPL")
        with col2:
            if "Sector" in df.columns:
                sectors = ["All Sectors"] + \
                    sorted(df["Sector"].dropna().unique().tolist())
                selected_sector = st.selectbox("Filter by Sector", sectors)
            else:
                selected_sector = "All Sectors"

        with col3:
            quick_select = st.selectbox(
                "Quick Select",
                ["Custom Selection", "All Companies",
                 "Top 10 (by Market Cap)", "Top 50 (by Market Cap)",
                 "Top 100 (by Market Cap)", "Tech Companies", "Energy Companies",
                 "Financial Companies", "Healthcare Companies"],
            )

        fdf = df.copy()

        if search_term:
            mask = (
                fdf["Symbol"].str.contains(search_term, case=False, na=False)
                | fdf["Company"].str.contains(search_term, case=False, na=False)
            )
            fdf = fdf[mask]

        if selected_sector != "All Sectors" and "Sector" in fdf.columns:
            fdf = fdf[fdf["Sector"] == selected_sector]

        if "rank" in fdf.columns:
            fdf = fdf.sort_values("rank")

        _sector_map = {
            "Tech Companies":       ["Technology", "Information Technology"],
            "Energy Companies":     ["Energy"],
            "Financial Companies":  ["Financials", "Financial Services"],
            "Healthcare Companies": ["Health Care", "Healthcare"],
        }
        if quick_select in _sector_map and "Sector" in df.columns:
            fdf = fdf[fdf["Sector"].str.contains(
                "|".join(_sector_map[quick_select]), case=False, na=False)]
        elif quick_select == "Top 10 (by Market Cap)":
            fdf = df.sort_values("rank").head(
                10) if "rank" in df.columns else df.head(10)
        elif quick_select == "Top 50 (by Market Cap)":
            fdf = df.sort_values("rank").head(
                50) if "rank" in df.columns else df.head(50)
        elif quick_select == "Top 100 (by Market Cap)":
            fdf = df.sort_values("rank").head(
                100) if "rank" in df.columns else df.head(100)
        elif quick_select == "All Companies":
            fdf = df.copy()

        rank_col = "rank" if "rank" in fdf.columns else None
        company_options = fdf.apply(
            lambda r: (f"#{int(r['rank'])} {r['Symbol']} - {r['Company']}"
                       if rank_col else f"{r['Symbol']} - {r['Company']}"),
            axis=1,
        ).tolist()

        if _PENDING in st.session_state:
            st.session_state[_CKEY] = st.session_state.pop(_PENDING)
        if _CKEY not in st.session_state:
            st.session_state[_CKEY] = []

        all_options = list(company_options)
        for item in st.session_state[_CKEY]:
            if item not in all_options:
                all_options.insert(0, item)

        st.markdown(f"**Showing {len(fdf)} companies** (sorted by market cap)")

        col_sel, col_btns = st.columns([3, 1])
        with col_sel:
            st.multiselect(
                "Select Companies to Extract",
                options=all_options,
                key=_CKEY,
                help="Pick one or more companies (ranked by market cap)",
            )
            st.session_state.fin_selected_companies = st.session_state[_CKEY]

        with col_btns:
            st.markdown("### Quick Actions")
            if st.button("Select All Shown"):
                st.session_state[_PENDING] = list(company_options)
                st.rerun()
            if st.button("Clear Selection"):
                st.session_state[_PENDING] = []
                st.rerun()

        st.info(
            f"📌 **{len(st.session_state.fin_selected_companies)}** companies selected")

        if st.session_state.fin_selected_companies:
            with st.expander("📋 View Selected Companies", expanded=False):
                syms = [_parse_symbol(c)
                        for c in st.session_state.fin_selected_companies]
                sel_df = df[df["Symbol"].isin(syms)]
                if rank_col:
                    sel_df = sel_df.sort_values("rank")
                dcols = [c for c in ["rank", "Symbol", "Company", "Sector"]
                         if c in sel_df.columns]
                st.dataframe(
                    sel_df[dcols].rename(columns={"rank": "Rank"}),
                    use_container_width=True,
                )


# =============================================================================
# TAB 2 - Year Selection
# =============================================================================
with tab2:
    st.header("Select Years to Extract")
    st.markdown(
        "Choose which fiscal years to pull from EDGAR XBRL. "
        "Re-running the same year is safe -- rows are upserted."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Year Range")
        year_mode = st.radio(
            "Year Selection Mode",
            ["Specific Year Range", "Single Year"],
        )

        try:
            _ds_years = _load_ds_years()
        except Exception as _ye:
            st.error(f"⚠️ Cannot load years — database inaccessible: {_ye}")
            st.stop()

        _yr_min = int(_ds_years[-1]) if _ds_years else 2010
        _yr_max = int(_ds_years[0]) if _ds_years else current_year

        if year_mode == "Single Year":
            single_year = st.selectbox("Select Year", _ds_years, index=0)
            years_to_extract = [single_year]
        else:
            start_year = st.slider(
                "Start Year", _yr_min, _yr_max, min(_yr_min + 2, _yr_max))
            end_year = st.slider("End Year", start_year,
                                 _yr_max, max(_yr_max - 1, start_year))
            years_to_extract = list(range(start_year, end_year + 1))

        st.session_state["fin_years"] = years_to_extract

    with col2:
        st.subheader("📊 Selected Years")
        yrs = st.session_state.get("fin_years", years_to_extract)
        st.metric("Years to extract", len(yrs))
        if yrs:
            st.caption(f"{min(yrs)} - {max(yrs)}")
            with st.expander("View all selected years"):
                st.write(sorted(yrs))


# =============================================================================
# TAB 3 - Extract Financial Data
# =============================================================================
with tab3:
    st.header("Extract Financial Data")
    st.caption(
        "Extracts EDGAR XBRL financial metrics and automatically fills any "
        "missing `shares_outstanding` values (EDGAR re-scrape → yfinance fallback) "
        "and recomputes **Tobin's Q** — no manual patching needed."
    )

    selected = st.session_state.get("fin_selected_companies", [])
    years_now = (st.session_state.get("fin_years")
                 or list(range(current_year - 5, current_year + 1)))
    df_ref = st.session_state.fin_companies_df

    if selected:
        syms = [_parse_symbol(c) for c in selected]
        if df_ref is not None and not df_ref.empty:
            companies_to_run = (
                df_ref[df_ref["Symbol"].isin(syms)][["Symbol", "Company"]]
                .rename(columns={"Symbol": "symbol", "Company": "company_name"})
                .to_dict("records")
            )
        else:
            companies_to_run = [{"symbol": s, "company_name": s} for s in syms]
    else:
        companies_to_run = []

    col_a, col_b = st.columns(2)
    col_a.metric("Companies selected", len(companies_to_run))
    col_b.metric("Years to extract",   len(years_now))

    if not companies_to_run:
        st.warning("⬅️ Go to **Select Companies** and pick at least one.")
    elif not years_now:
        st.warning("⬅️ Go to **Select Years** and pick at least one year.")
    else:
        yr_label = (f"{min(years_now)}-{max(years_now)}"
                    if len(years_now) > 1 else str(years_now[0]))

        reload_mode = st.radio(
            "🔄 Re-run behaviour",
            [
                "Skip companies already in DB (faster)",
                "Re-extract all — overwrite existing data",
            ],
            index=0,
            horizontal=True,
        )
        skip_existing = reload_mode.startswith("Skip")

        if st.button(
            (f"🚀 Extract Financial Data"
             f"  ({len(companies_to_run)} companies · {yr_label})"),
            type="primary",
        ):
            import psycopg2
            from Utilities.Lookups import DB_Connection
            from Services.FinancialDataScraper import FinancialDataScraper

            st.session_state.fin_patch_results = None   # clear stale results
            db_conn = None
            try:
                db_conn = psycopg2.connect(
                    DB_Connection().DB_CONNECTION_STRING)
            except Exception as exc:
                st.error(f"DB connection failed: {exc}")
                st.stop()

            scraper = FinancialDataScraper(
                db_connection=db_conn, years_needed=years_now)
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(companies_to_run)
            summary_rows = []

            for i, co in enumerate(companies_to_run, 1):
                sym = co["symbol"]
                name = co["company_name"]
                progress_bar.progress(int(i / total * 100))
                status_text.text(f"Processing {sym} ... ({i}/{total})")
                try:
                    # ── Skip check ────────────────────────────────────────────
                    if skip_existing:
                        existing_years = scraper.get_existing_years(name)
                        needed = set(years_now)
                        if needed and needed.issubset(existing_years):
                            summary_rows.append({
                                "Symbol": sym, "Company": name,
                                "Years saved": 0,
                                "Years available": len(existing_years),
                                "Status": "⏭️ Skipped (already in DB)",
                            })
                            continue

                    # ── Single EDGAR fetch — scrape_and_save returns (rows, saved) ──
                    rows, saved = scraper.scrape_and_save(sym, name)
                    if saved > 0:
                        icon = "✅"
                    elif rows:
                        icon = "⚠️ No DB write"
                    else:
                        icon = "⚠️ No XBRL data"
                    summary_rows.append({
                        "Symbol": sym, "Company": name,
                        "Years saved": saved, "Years available": len(rows),
                        "Status": icon,
                    })
                except Exception as exc:
                    summary_rows.append({
                        "Symbol": sym, "Company": name,
                        "Years saved": 0, "Years available": 0,
                        "Status": f"❌ {exc}",
                    })

            progress_bar.progress(100)
            status_text.text("✅ Extraction done — patching missing shares...")
            st.session_state.fin_extract_results = summary_rows

            # ── Auto-patch: fill NULL shares_outstanding ───────────────────────
            # Runs immediately after extraction on the same DB connection.
            # Two-layer strategy: EDGAR re-scrape first, yfinance fallback second.
            # Historical ticker aliases (FB→META, UTX→RTX, PX→LIN) are applied
            # automatically inside patch_missing_shares.
            from Services.MarketDataFetcher import MarketDataFetcher
            _patch_fetcher_auto = MarketDataFetcher(db_conn)
            _patch_prog = st.progress(0)
            _patch_stat = st.empty()
            _patch_n = len(companies_to_run)
            _auto_patched = 0
            _auto_still_missing: list = []

            for _pi, _co_p in enumerate(companies_to_run, 1):
                _sym_p = _co_p["symbol"]
                _name_p = _co_p["company_name"]
                _patch_prog.progress(int(_pi / _patch_n * 100))
                _patch_stat.text(
                    f"Patching shares: {_sym_p} … ({_pi}/{_patch_n})")
                try:
                    _filled_p, _missing_p = \
                        _patch_fetcher_auto.patch_missing_shares(
                            _sym_p, _name_p)
                    _auto_patched += _filled_p
                    for _m in _missing_p:
                        _auto_still_missing.append({
                            "Company":        _name_p,
                            "Symbol":         _sym_p,
                            "Year":           _m["year"],
                            "Fiscal Year End": _m["fiscal_year_end"],
                            "Reason":         _m["reason"],
                        })
                except Exception:
                    pass   # patch errors are non-fatal

            _patch_prog.progress(100)
            _patch_stat.text("Done!")
            st.session_state.fin_patch_results = {
                "patched":       _auto_patched,
                "still_missing": _auto_still_missing,
            }

            if db_conn:
                try:
                    db_conn.close()
                except Exception:
                    pass

            st.cache_data.clear()

        if st.session_state.fin_extract_results:
            summary_df = pd.DataFrame(st.session_state.fin_extract_results)
            total_saved = int(summary_df["Years saved"].sum())
            skipped = int((summary_df["Status"].str.startswith("⏭️")).sum())
            with_data = int((summary_df["Years saved"] > 0).sum())

            st.success("✅ Extraction complete!")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Companies processed", len(summary_df))
            c2.metric("Year-rows saved",     total_saved)
            c3.metric("With data",           with_data)
            c4.metric("Skipped (in DB)",     skipped)

            st.markdown("### 📋 Results")
            st.dataframe(summary_df, use_container_width=True)

            # Preview the first company that had rows saved — read from DB
            first_ok = summary_df[summary_df["Years saved"] > 0]
            if not first_ok.empty:
                prev_sym = first_ok.iloc[0]["Symbol"]
                prev_name = first_ok.iloc[0]["Company"]
                st.markdown(f"### 🔍 Preview: {prev_sym} - {prev_name}")
                try:
                    import psycopg2
                    from Utilities.Lookups import DB_Connection
                    _conn = psycopg2.connect(
                        DB_Connection().DB_CONNECTION_STRING)
                    _sql = """
                        SELECT reporting_year, revenue, net_income, assets,
                               liabilities, equity, operating_income_ebitda,
                               cash_flow_operations, free_cash_flow, eps
                        FROM   t_financial_metrics
                        WHERE  company_name = %s
                        ORDER  BY reporting_year DESC
                    """
                    prev_df = pd.read_sql(_sql, _conn, params=(prev_name,))
                    _conn.close()
                    _bn = ["revenue", "net_income", "assets", "liabilities",
                           "equity", "operating_income_ebitda",
                           "cash_flow_operations", "free_cash_flow"]
                    for _c in _bn:
                        if _c in prev_df.columns:
                            prev_df[_c] = prev_df[_c].apply(
                                lambda x: f"${x/1e9:,.2f}B" if x is not None else "-")
                    st.dataframe(prev_df, use_container_width=True)
                except Exception as _exc:
                    st.warning(f"Preview unavailable: {_exc}")

        # ── Shares patch results (auto-populated after extraction) ─────────────
        _pr = st.session_state.get("fin_patch_results")
        if _pr is not None:
            st.markdown("### 🩹 Shares Patch Results")
            _pc1, _pc2 = st.columns(2)
            _pc1.metric("Rows patched", _pr["patched"])
            _pc2.metric("Still missing", len(_pr["still_missing"]))
            if _pr["patched"]:
                st.success(
                    f"✅ Patched **{_pr['patched']}** company-year rows with "
                    "shares outstanding.")
            if _pr["still_missing"]:
                st.warning(
                    f"⚠️ **{len(_pr['still_missing'])}** company-year row(s) "
                    "still have no shares outstanding (see below). "
                    "Truly unsolvable rows (Palantir pre-2020, Linde pre-2018, "
                    "AbbVie 2012) are expected."
                )
                _miss_df = pd.DataFrame(_pr["still_missing"])[
                    ["Company", "Symbol", "Year", "Fiscal Year End", "Reason"]
                ]
                st.dataframe(
                    _miss_df, use_container_width=True, hide_index=True)
            elif _pr["patched"] == 0:
                st.info("All shares already populated — nothing to patch.")
            else:
                st.success("✅ All rows now have shares outstanding.")


# =============================================================================
# TAB 5 - Search Financial Metrics
# =============================================================================

# Dual-class share aliases for Tab 5 search — maps alternate names / tickers
# to the canonical company_name stored in t_financial_metrics.
_SEARCH_ALIASES: dict = {
    'alphabet inc class a': 'Alphabet Inc Class C',
    'alphabet class a':     'Alphabet Inc Class C',
    'googl':                'Alphabet Inc Class C',
    'google class a':       'Alphabet Inc Class C',
}

_METRIC_COLS = {
    "Revenue":                  "revenue",
    "Net Income":               "net_income",
    "Total Assets":             "assets",
    "Total Liabilities":        "liabilities",
    "Equity":                   "equity",
    "Operating Expenses":       "operating_expenses",
    "Operating Income (EBITDA)": "operating_income_ebitda",
    "EPS (Diluted)":            "eps",
    "Cash Flow – Operations":   "cash_flow_operations",
    "Cash Flow – Investing":    "cash_flow_investing",
    "Cash Flow – Financing":    "cash_flow_financing",
    "Free Cash Flow":           "free_cash_flow",
    "Stock Price (Year End)":   "stock_price_calender_year_end",
    "P/E Ratio":                "pe_ratio",
    "Return on Assets":         "return_on_asset",
    "Beta":                     "beta_calender_year_end",
    "Sharpe Ratio":             "sharpe_ratio",
    "Tobin's Q":                "tobins_q",
    "Shares Outstanding":       "shares_outstanding",
}

_DOLLAR_COLS = {
    "revenue", "net_income", "assets", "liabilities", "equity",
    "operating_expenses", "operating_income_ebitda",
    "cash_flow_operations", "cash_flow_investing",
    "cash_flow_financing", "free_cash_flow",
}


@st.cache_data(ttl=120, show_spinner=False)
def _load_all_metrics() -> pd.DataFrame:
    """Load all rows from t_financial_metrics."""
    import psycopg2
    from Utilities.Lookups import DB_Connection
    sql = """
        SELECT company_name, reporting_year,
               revenue, net_income, assets, liabilities, equity,
               operating_expenses, operating_income_ebitda, eps,
               cash_flow_operations, cash_flow_investing,
               cash_flow_financing, free_cash_flow,
               stock_price_calender_year_end, pe_ratio,
               return_on_asset, beta_calender_year_end, sharpe_ratio,
               tobins_q, shares_outstanding
        FROM   t_financial_metrics
        ORDER  BY company_name, reporting_year
    """
    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def _fmt_val(v, col):
    """Human-readable formatting for a single cell value."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if col in _DOLLAR_COLS:
        if abs(v) >= 1e12:
            return f"${v/1e12:,.2f}T"
        if abs(v) >= 1e9:
            return f"${v/1e9:,.1f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:,.1f}M"
        return f"${v:,.0f}"
    if col == "eps":
        return f"{v:.2f}"
    if col in {"pe_ratio", "return_on_asset", "beta_calender_year_end", "sharpe_ratio"}:
        return f"{v:.3f}"
    if col == "stock_price_calender_year_end":
        return f"${v:,.2f}"
    return str(v)


with tab5:
    st.header("🔍 Search Financial Metrics")

    if st.button("🔄 Refresh data", key="search_refresh"):
        st.cache_data.clear()

    try:
        _all_df = _load_all_metrics()
    except Exception as _exc:
        st.error(f"Could not load metrics: {_exc}")
        _all_df = pd.DataFrame()

    if _all_df.empty:
        st.info("No data in t_financial_metrics yet — run an extraction first.")
    else:
        # ── Filter controls ──────────────────────────────────────────────────
        st.markdown("---")
        fc1, fc2, fc3 = st.columns([2, 1, 2])

        with fc1:
            company_search = st.text_input(
                "🏢 Company (type to filter)",
                placeholder="e.g. Apple, NVIDIA, JP …",
                key="search_co",
            )
            all_companies = sorted(_all_df["company_name"].dropna().unique())
            if company_search:
                term = company_search.lower()
                # Direct substring match
                filtered_cos = [c for c in all_companies if term in c.lower()]
                # Alias match — e.g. "GOOGL" / "Alphabet Class A" → Class C
                canonical = _SEARCH_ALIASES.get(term)
                if canonical and canonical in all_companies and canonical not in filtered_cos:
                    filtered_cos.append(canonical)
            else:
                filtered_cos = all_companies

            selected_companies = st.multiselect(
                "Select companies",
                options=filtered_cos,
                default=[],
                key="search_co_select",
            )

        with fc2:
            all_years = sorted(_all_df["reporting_year"].dropna().unique())
            year_min, year_max = int(all_years[0]), int(all_years[-1])
            sel_years = st.slider(
                "📅 Year range",
                min_value=year_min,
                max_value=year_max,
                value=(year_min, year_max),
                key="search_yr",
            )

        with fc3:
            st.markdown("**📊 Metrics to show**")
            # Quick-select buttons
            qc1, qc2, qc3 = st.columns(3)
            if qc1.button("All metrics", key="search_all_m"):
                st.session_state["search_metric_sel"] = list(
                    _METRIC_COLS.keys())
            if qc2.button("P&L only", key="search_pl"):
                st.session_state["search_metric_sel"] = [
                    "Revenue", "Operating Expenses",
                    "Operating Income (EBITDA)", "Net Income", "EPS (Diluted)"]
            if qc3.button("Cash flow", key="search_cf"):
                st.session_state["search_metric_sel"] = [
                    "Cash Flow – Operations", "Cash Flow – Investing",
                    "Cash Flow – Financing", "Free Cash Flow"]

            if "search_metric_sel" not in st.session_state:
                st.session_state["search_metric_sel"] = [
                    "Revenue", "Net Income", "Free Cash Flow",
                    "EPS (Diluted)", "Total Assets",
                    "Beta", "Sharpe Ratio", "Tobin's Q"]

            selected_metrics = st.multiselect(
                "Choose metrics",
                options=list(_METRIC_COLS.keys()),
                default=st.session_state["search_metric_sel"],
                key="search_metrics",
            )
            st.session_state["search_metric_sel"] = selected_metrics

        st.markdown("---")

        # ── Apply filters ────────────────────────────────────────────────────
        view_df = _all_df.copy()
        if selected_companies:
            view_df = view_df[view_df["company_name"].isin(selected_companies)]
        view_df = view_df[
            (view_df["reporting_year"] >= sel_years[0]) &
            (view_df["reporting_year"] <= sel_years[1])
        ]

        if view_df.empty:
            st.warning("No rows match the selected filters.")
        else:
            metric_db_cols = [_METRIC_COLS[m] for m in selected_metrics]
            keep_cols = ["company_name", "reporting_year"] + metric_db_cols
            view_df = view_df[keep_cols].copy()

            # ── Layout choice ────────────────────────────────────────────────
            layout_mode = st.radio(
                "Layout",
                ["Tall table (one row per company-year)",
                 "Wide pivot (years as columns)"],
                horizontal=True,
                key="search_layout",
            )

            if layout_mode.startswith("Wide") and len(selected_metrics) == 1:
                # Pivot: rows = companies, columns = years
                col_db = metric_db_cols[0]
                pivot = view_df.pivot_table(
                    index="company_name",
                    columns="reporting_year",
                    values=col_db,
                    aggfunc="first",
                )
                pivot.columns = [str(c) for c in pivot.columns]
                # Format values
                display_pivot = pivot.applymap(
                    lambda v: _fmt_val(v, col_db) if pd.notna(v) else ""
                )
                display_pivot.index.name = "Company"
                st.markdown(f"### {selected_metrics[0]} by Year")
                st.dataframe(
                    display_pivot, use_container_width=True, height=450)

            elif layout_mode.startswith("Wide") and len(selected_metrics) > 1:
                st.info("Wide pivot works best with a single metric selected. "
                        "Showing tall table instead.")
                layout_mode = "Tall"

            if not layout_mode.startswith("Wide"):
                # Rename columns to friendly names for display
                col_rename = {"company_name": "Company",
                              "reporting_year": "Year"}
                col_rename.update(
                    {_METRIC_COLS[m]: m for m in selected_metrics})
                display_df = view_df.rename(columns=col_rename)

                # Columns that receive colour-coding — kept numeric for Styler
                _COLOUR_COLS = {"Sharpe Ratio", "Tobin's Q"}
                styled_set = _COLOUR_COLS & set(selected_metrics)

                # Format every column EXCEPT the styled ones (keep those numeric)
                for m in selected_metrics:
                    db_col = _METRIC_COLS[m]
                    if m in display_df.columns and m not in styled_set:
                        display_df[m] = display_df[m].apply(
                            lambda v: _fmt_val(v, db_col))

                total = len(display_df)
                companies_shown = display_df["Company"].nunique()
                st.markdown(
                    f"**{total} row(s)** · **{companies_shown} company/ies** "
                    f"· years {sel_years[0]}–{sel_years[1]}"
                )

                # ── Per-cell colour rules ─────────────────────────────────────
                # Sharpe Ratio:  <0 red · 0-0.5 yellow · 0.5-1 light green · ≥1 green
                # Tobin's Q:     <0.8 red · 0.8-1 yellow · 1-2 light green · ≥2 green
                def _sharpe_color(v):
                    if not isinstance(v, (int, float)) or pd.isna(v):
                        return ""
                    if v < 0.0:
                        return "background-color:#ffd6d6;color:#7b0000"
                    if v < 0.5:
                        return "background-color:#fff3cd;color:#7a5700"
                    if v < 1.0:
                        return "background-color:#d4edda;color:#155724"
                    return "background-color:#28a745;color:white"

                def _tobinsq_color(v):
                    if not isinstance(v, (int, float)) or pd.isna(v):
                        return ""
                    if v < 0.8:
                        return "background-color:#ffd6d6;color:#7b0000"
                    if v < 1.0:
                        return "background-color:#fff3cd;color:#7a5700"
                    if v < 2.0:
                        return "background-color:#d4edda;color:#155724"
                    return "background-color:#28a745;color:white"

                # pandas ≥2.1 renamed Styler.applymap → Styler.map
                def _style_col(s, fn, col):
                    try:
                        return s.map(fn, subset=[col])
                    except AttributeError:
                        return s.applymap(fn, subset=[col])

                styler = display_df.style
                fmt_override = {}
                if "Sharpe Ratio" in styled_set:
                    styler = _style_col(styler, _sharpe_color, "Sharpe Ratio")
                    fmt_override["Sharpe Ratio"] = (
                        lambda v: f"{v:.3f}" if isinstance(v, (int, float))
                        and not pd.isna(v) else "—")
                if "Tobin's Q" in styled_set:
                    styler = _style_col(styler, _tobinsq_color, "Tobin's Q")
                    fmt_override["Tobin's Q"] = (
                        lambda v: f"{v:.4f}" if isinstance(v, (int, float))
                        and not pd.isna(v) else "—")
                if fmt_override:
                    styler = styler.format(fmt_override)

                st.dataframe(styler, use_container_width=True, height=520)

                # ── Colour legend ─────────────────────────────────────────────
                if styled_set:
                    legend = []
                    if "Sharpe Ratio" in styled_set:
                        legend.append(
                            "**Sharpe Ratio:** "
                            "🔴 < 0 &nbsp;·&nbsp; "
                            "🟡 0 – 0.5 &nbsp;·&nbsp; "
                            "🟢 0.5 – 1 &nbsp;·&nbsp; "
                            "💚 ≥ 1")
                    if "Tobin's Q" in styled_set:
                        legend.append(
                            "**Tobin's Q:** "
                            "🔴 < 0.8 &nbsp;·&nbsp; "
                            "🟡 0.8 – 1 &nbsp;·&nbsp; "
                            "🟢 1 – 2 &nbsp;·&nbsp; "
                            "💚 ≥ 2")
                    st.caption("  &nbsp;&nbsp;  ".join(legend))

            # ── CSV export ───────────────────────────────────────────────────
            st.markdown("---")
            export_df = view_df.copy()
            export_df = export_df.rename(
                columns={"company_name": "Company", "reporting_year": "Year"}
            )
            export_df = export_df.rename(
                columns={_METRIC_COLS[m]: m for m in selected_metrics}
            )
            csv_bytes = export_df.to_csv(index=False).encode()
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv_bytes,
                file_name="avisk_financial_metrics.csv",
                mime="text/csv",
            )


# =============================================================================
# TAB 4 - Update Market Data (Price · Beta · Sharpe · P/E)
# =============================================================================
with tab4:
    st.header("📈 Market Data")
    st.markdown(
        "Fetches **fiscal-year-end stock price**, **beta** (52-week vs SPY), "
        "and **Sharpe ratio** via yfinance, then computes **P/E ratio** "
        "(price ÷ EPS). Updates `t_financial_metrics` in-place — EDGAR financial "
        "data is never overwritten."
    )
    st.info(
        "💡 **Prerequisite:** Companies must be extracted first (Tab 3) so that "
        "`fiscal_year_end_date` and `eps` are populated in the DB."
    )
    st.markdown("---")

    _mkt_selected = st.session_state.get("fin_selected_companies", [])
    _mkt_df_ref = st.session_state.fin_companies_df

    if _mkt_selected:
        _mkt_syms = [_parse_symbol(c) for c in _mkt_selected]
        if _mkt_df_ref is not None and not _mkt_df_ref.empty:
            _mkt_companies = (
                _mkt_df_ref[_mkt_df_ref["Symbol"].isin(_mkt_syms)][
                    ["Symbol", "Company"]
                ]
                .rename(columns={"Symbol": "symbol", "Company": "company_name"})
                .to_dict("records")
            )
        else:
            _mkt_companies = [{"symbol": s, "company_name": s}
                              for s in _mkt_syms]
    else:
        _mkt_companies = []

    mc1, mc2 = st.columns(2)
    mc1.metric("Companies selected", len(_mkt_companies))
    mc2.markdown(
        "_Select companies in **🏢 Select Companies** tab first._"
        if not _mkt_companies else ""
    )

    rf_pct = st.slider(
        "Risk-free rate (% p.a., used for Sharpe)",
        min_value=0.0, max_value=10.0, value=4.0, step=0.25,
        key="mkt_rf",
    )

    if not _mkt_companies:
        st.warning("⬅️ Go to **Select Companies** and pick at least one company.")
    else:
        if st.button(
            f"📈 Fetch Market Data  ({len(_mkt_companies)} companies)",
            type="primary",
            key="mkt_fetch_btn",
        ):
            import psycopg2
            from Utilities.Lookups import DB_Connection
            from Services.MarketDataFetcher import MarketDataFetcher

            _mkt_conn = None
            try:
                _mkt_conn = psycopg2.connect(
                    DB_Connection().DB_CONNECTION_STRING)
            except Exception as _exc:
                st.error(f"DB connection failed: {_exc}")
                st.stop()

            fetcher = MarketDataFetcher(
                _mkt_conn, risk_free_annual=rf_pct / 100)
            _mkt_progress = st.progress(0)
            _mkt_status = st.empty()
            _mkt_total = len(_mkt_companies)
            _mkt_results = []   # flat list of result rows
            _mkt_warnings = []

            for _mi, _co in enumerate(_mkt_companies, 1):
                _sym = _co["symbol"]
                _name = _co["company_name"]
                _mkt_progress.progress(int(_mi / _mkt_total * 100))
                _mkt_status.text(f"Fetching {_sym} … ({_mi}/{_mkt_total})")

                # Warn if rows have no fiscal_year_end_date (need re-extraction)
                missing = fetcher.rows_missing_fye(_name)
                if missing:
                    _mkt_warnings.append(
                        f"⚠️ **{_sym}**: {missing} row(s) have no "
                        f"`fiscal_year_end_date` — re-extract in Tab 3 first."
                    )

                try:
                    year_results = fetcher.update_company(_sym, _name)
                    for yr in year_results:
                        yr["symbol"] = _sym
                        yr["company"] = _name
                        _mkt_results.append(yr)
                except Exception as _exc:
                    _mkt_warnings.append(f"❌ **{_sym}**: {_exc}")

            _mkt_progress.progress(100)
            _mkt_status.text("Done!")
            if _mkt_conn:
                try:
                    _mkt_conn.close()
                except Exception:
                    pass

            st.cache_data.clear()

            if _mkt_warnings:
                for _w in _mkt_warnings:
                    st.warning(_w)

            if _mkt_results:
                st.success(
                    f"✅ Market data updated for {len(_mkt_results)} company-year rows.")
                _res_df = pd.DataFrame(_mkt_results)[
                    ["company", "symbol", "year", "fiscal_year_end",
                     "price", "pe_ratio", "beta", "sharpe"]
                ]
                _res_df.columns = [
                    "Company", "Symbol", "Year", "Fiscal Year End",
                    "Price ($)", "P/E Ratio", "Beta", "Sharpe Ratio"
                ]
                # Format for display
                for col, fmt in [
                    ("Price ($)", lambda v: f"${v:,.2f}" if pd.notna(
                        v) else "-"),
                    ("P/E Ratio",
                     lambda v: f"{v:.1f}" if pd.notna(v) else "-"),
                    ("Beta", lambda v: f"{v:.3f}" if pd.notna(v) else "-"),
                    ("Sharpe Ratio",
                     lambda v: f"{v:.3f}" if pd.notna(v) else "-"),
                ]:
                    _res_df[col] = _res_df[col].apply(fmt)

                st.dataframe(_res_df, use_container_width=True, height=480)

                csv_mkt = pd.DataFrame(_mkt_results).to_csv(
                    index=False).encode()
                st.download_button(
                    "⬇️ Download as CSV",
                    data=csv_mkt,
                    file_name="avisk_market_data.csv",
                    mime="text/csv",
                )
            else:
                st.info(
                    "No rows updated. Make sure the selected companies have been "
                    "extracted in Tab 3 (needed to populate `fiscal_year_end_date`)."
                )

    # ── Patch Missing Shares ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🩹 Patch Missing Shares Outstanding")
    st.markdown(
        "Shares patching now runs **automatically after every extraction** in "
        "Tab 3 — use this button only to **re-run the patch independently** "
        "(e.g. after a failed run or to pick up newly added EDGAR filings). "
        "Uses a two-layer strategy: EDGAR re-scrape first (picks up "
        "`WeightedAverageNumberOfSharesOutstandingBasic` from early filings), "
        "then yfinance with historical-ticker aliases (FB, UTX, PX) as a "
        "fallback. Recomputes **Tobin's Q** for every patched row."
    )

    if not _mkt_companies:
        st.info("Select companies in **🏢 Select Companies** first.")
    else:
        if st.button(
            f"🩹 Patch Missing Shares  ({len(_mkt_companies)} companies)",
            key="mkt_patch_btn",
        ):
            import psycopg2
            from Utilities.Lookups import DB_Connection
            from Services.MarketDataFetcher import MarketDataFetcher

            _patch_conn = None
            try:
                _patch_conn = psycopg2.connect(
                    DB_Connection().DB_CONNECTION_STRING)
            except Exception as _exc:
                st.error(f"DB connection failed: {_exc}")
                st.stop()

            _patch_fetcher = MarketDataFetcher(_patch_conn)
            _patch_progress = st.progress(0)
            _patch_status = st.empty()
            _patch_total = len(_mkt_companies)
            _total_patched = 0
            # flat list: {Company, Symbol, Year, Reason}
            _still_missing_rows = []

            for _pi, _co in enumerate(_mkt_companies, 1):
                _sym = _co["symbol"]
                _name = _co["company_name"]
                _patch_progress.progress(int(_pi / _patch_total * 100))
                _patch_status.text(f"Patching {_sym} … ({_pi}/{_patch_total})")
                try:
                    _filled, _missing = _patch_fetcher.patch_missing_shares(
                        _sym, _name)
                    _total_patched += _filled
                    for _m in _missing:
                        _still_missing_rows.append({
                            "Company":        _name,
                            "Symbol":         _sym,
                            "Year":           _m["year"],
                            "Fiscal Year End": _m["fiscal_year_end"],
                            "Reason":         _m["reason"],
                        })
                except Exception as _exc:
                    _still_missing_rows.append({
                        "Company":        _name,
                        "Symbol":         _sym,
                        "Year":           "—",
                        "Fiscal Year End": "—",
                        "Reason":         f"Error: {_exc}",
                    })

            _patch_progress.progress(100)
            _patch_status.text("Done!")
            if _patch_conn:
                try:
                    _patch_conn.close()
                except Exception:
                    pass

            st.cache_data.clear()
            if _total_patched:
                st.success(
                    f"✅ Patched **{_total_patched}** company-year rows with "
                    "shares outstanding.")
            else:
                st.info(
                    "No rows patched — either shares are already populated "
                    "or yfinance has no data for those years."
                )

            if _still_missing_rows:
                st.warning(
                    f"⚠️ **{len(_still_missing_rows)}** company-year row(s) "
                    "still have no shares outstanding:")
                _miss_df = pd.DataFrame(_still_missing_rows)[
                    ["Company", "Symbol", "Year", "Fiscal Year End", "Reason"]
                ]
                st.dataframe(_miss_df, use_container_width=True,
                             hide_index=True)
            else:
                st.success("✅ All rows now have shares outstanding.")
