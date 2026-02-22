"""
Step 11 - Extract Financial Data from 10-Ks
============================================
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
    page_title="Extract Financial Data",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💰 Extract Financial Data from 10-Ks")
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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Select Companies",
    "📅 Select Years",
    "🚀 Extract",
    "📊 DB Coverage",
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
            ["All Available Years (2010 - present)",
             "Specific Year Range", "Single Year"],
        )

        if year_mode == "Specific Year Range":
            start_year = st.slider(
                "Start Year", 2010, current_year, current_year - 5)
            end_year = st.slider("End Year", start_year,
                                 current_year, current_year)
            years_to_extract = list(range(start_year, end_year + 1))
        elif year_mode == "Single Year":
            single_year = st.selectbox("Select Year",
                                       list(range(current_year, 2009, -1)), index=0)
            years_to_extract = [single_year]
        else:
            years_to_extract = list(range(2010, current_year + 1))

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
# TAB 3 - Extract
# =============================================================================
with tab3:
    st.header("Extract Financial Data")

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
            status_text.text("Done!")
            if db_conn:
                try:
                    db_conn.close()
                except Exception:
                    pass

            st.session_state.fin_extract_results = summary_rows
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


# =============================================================================
# TAB 4 - DB Coverage
# =============================================================================
@st.cache_data(ttl=120, show_spinner=False)
def _load_coverage() -> pd.DataFrame:
    """Query t_financial_metrics directly via psycopg2 (no pyodbc needed)."""
    import psycopg2
    from Utilities.Lookups import DB_Connection
    sql = """
        SELECT company_name, reporting_year,
               revenue        IS NOT NULL AS has_revenue,
               net_income     IS NOT NULL AS has_net_income,
               assets         IS NOT NULL AS has_assets,
               free_cash_flow IS NOT NULL AS has_fcf
        FROM t_financial_metrics
        ORDER BY company_name, reporting_year DESC
    """
    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    try:
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()
    return df


with tab4:
    st.header("DB Coverage - t_financial_metrics")

    if st.button("\U0001f504 Refresh", key="cov_refresh"):
        st.cache_data.clear()

    try:
        status_df = _load_coverage()

        if status_df.empty:
            st.info("t_financial_metrics is empty - run an extraction first.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Companies in DB", status_df["company_name"].nunique())
            c2.metric("Total rows",      len(status_df))
            c3.metric("With revenue",
                      int(status_df["has_revenue"].sum())
                      if "has_revenue" in status_df.columns else "-")
            c4.metric("With FCF",
                      int(status_df["has_fcf"].sum())
                      if "has_fcf" in status_df.columns else "-")

            st.markdown("---")
            st.subheader("\U0001f50d Filter")
            cov_search = st.text_input(
                "Search company", placeholder="e.g., Apple")
            cov_df = status_df.copy()
            if cov_search:
                cov_df = cov_df[
                    cov_df["company_name"].str.contains(
                        cov_search, case=False, na=False)
                ]
            st.dataframe(cov_df, use_container_width=True, height=450)

    except Exception as exc:
        st.error(f"Could not load DB coverage: {exc}")


# =============================================================================
# TAB 5 - Search Financial Metrics
# =============================================================================

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
               return_on_asset, beta_calender_year_end, sharpe_ratio
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
                filtered_cos = [c for c in all_companies
                                if company_search.lower() in c.lower()]
            else:
                filtered_cos = all_companies

            selected_companies = st.multiselect(
                "Select companies",
                options=filtered_cos,
                default=filtered_cos[:1] if filtered_cos else [],
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
                    "EPS (Diluted)", "Total Assets"]

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

                # Format numeric columns
                for m in selected_metrics:
                    db_col = _METRIC_COLS[m]
                    if m in display_df.columns:
                        display_df[m] = display_df[m].apply(
                            lambda v: _fmt_val(v, db_col))

                total = len(display_df)
                companies_shown = display_df["Company"].nunique()
                st.markdown(
                    f"**{total} row(s)** · **{companies_shown} company/ies** "
                    f"· years {sel_years[0]}–{sel_years[1]}"
                )
                st.dataframe(display_df, use_container_width=True, height=520)

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
