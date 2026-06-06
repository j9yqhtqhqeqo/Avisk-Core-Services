"""
11CEO Insights.py
-----------------
Streamlit page for CEO data collection and browsing.

  Tab 1 - Select Companies  : filter/search S&P 500, multiselect with coverage overlay
  Tab 2 - Select Years       : year range selector with DB coverage summary
  Tab 3 - Load CEOs          : identify & save CEOs for selected companies/years
  Tab 4 - Load Statements    : collect CEO statements for companies that already have a CEO
  Tab 5 - Delete Records     : remove t_ceo rows OR t_ceo_statements rows independently
  Tab 6 - Browse CEOs        : searchable table of t_ceo
  Tab 7 - Browse Statements  : searchable full-text view of t_ceo_statements
"""

import streamlit as st
import pandas as pd
import threading
import time
from pathlib import Path
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ── Module-level CEO run state ─────────────────────────────────────────────────
# Stored at module level (not session state) so it survives Streamlit reruns
# within the same process. Keyed by run_id so a new run never races a stale read.
_ceo_run_lock = threading.Lock()
_ceo_run: dict = {
    'run_id': None,
    'results': [],
    'done': False,
    'summary': None,
    'task_ready_t': 0.0,   # set when get_unprocessed_tasks completes
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CEO Insights",
    page_icon="👔",
    layout="wide",
)

from Utilities.auth import require_login  # noqa: E402

require_login()

st.title("👔 CEO Insights")
st.caption(
    "Identify S&P 500 CEOs by year and collect their significant public statements.")

# ── Lazy service import (avoids import errors on local dev) ───────────────────


@st.cache_resource(show_spinner=False)
def _get_service():
    try:
        from Services.CEODataService import CEODataService
        return CEODataService(), None
    except Exception as e:
        return None, str(e)


svc, svc_error = _get_service()

# ── Load S&P 500 company list ──────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def _load_companies() -> list[dict]:
    """
    Pull distinct (company_name, ticker) from t_data_source.
    Falls back to the local CSV if DB unavailable.
    """
    try:
        import psycopg2
        import psycopg2.extras
        from Utilities.Lookups import DB_Connection
        conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT DISTINCT company_name,
                   MAX(ticker) FILTER (WHERE ticker IS NOT NULL AND ticker <> '') AS ticker
            FROM t_data_source
            WHERE company_name IS NOT NULL AND company_name <> ''
            GROUP BY company_name
            ORDER BY company_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{'company_name': r['company_name'],
                 'ticker': r['ticker'] or ''} for r in rows]
    except Exception:
        pass
    # Fallback - local CSV
    try:
        df = pd.read_csv('Clients/sp500_market_cap_ranked.csv')
        return [{'company_name': row.get('Name', row.get('company_name', '')),
                 'ticker': row.get('Symbol', row.get('ticker', ''))}
                for _, row in df.iterrows()]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _load_sp500_df() -> pd.DataFrame:
    """Load S&P 500 ranked list (rank, symbol, company, market_cap, sector) from CSV."""
    csv_path = (Path(__file__).resolve().parent.parent
                / 'Clients' / 'sp500_market_cap_ranked.csv')
    df = pd.read_csv(str(csv_path))
    df.columns = [c.strip().lower() for c in df.columns]
    df['symbol'] = df['symbol'].str.upper().str.strip()
    df['company'] = df['company'].str.strip()
    df['sector'] = df.get('sector', pd.Series(
        ['Unknown'] * len(df))).fillna('Unknown')
    df['rank'] = pd.to_numeric(
        df.get('rank', pd.Series([999] * len(df))), errors='coerce'
    ).fillna(999).astype(int)
    return df.sort_values('rank').reset_index(drop=True)


@st.cache_data(ttl=120, show_spinner=False)
def _load_ceo_coverage() -> dict:
    """
    Return {TICKER: {year: ceo_name}} from t_ceo for the coverage overlay.
    Falls back to {} on any DB error.
    """
    try:
        import psycopg2
        import psycopg2.extras
        from Utilities.Lookups import DB_Connection
        conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT UPPER(ticker) AS ticker, year, ceo_name "
            "FROM t_ceo WHERE ticker IS NOT NULL AND ticker <> ''")
        coverage: dict = {}
        for r in cur.fetchall():
            t = (r['ticker'] or '').strip()
            if t:
                coverage.setdefault(t, {})[int(
                    r['year'])] = r['ceo_name'] or ''
        cur.close()
        conn.close()
        return coverage
    except Exception:
        return {}


# ── Session state: company + year selection ────────────────────────────────────
if '_ceo_sel_companies' not in st.session_state:
    # [{company_name, ticker}]
    st.session_state['_ceo_sel_companies'] = []

# Always enforce the canonical default range (2012 – current year − 1).
# Reset if session state holds stale values from an older default.
_cur_yr = datetime.now().year
_DEFAULT_YR_START = 2012
_DEFAULT_YR_END = _cur_yr - 1
if (
    '_ceo_sel_years' not in st.session_state
    or st.session_state.get('_ceo_yr_start', 0) < _DEFAULT_YR_START
    or st.session_state.get('_ceo_yr_end',   0) > _DEFAULT_YR_END
    or 'yr_range_slider' not in st.session_state
):
    st.session_state['_ceo_yr_start'] = _DEFAULT_YR_START
    st.session_state['_ceo_yr_end'] = _DEFAULT_YR_END
    st.session_state['_ceo_sel_years'] = list(
        range(_DEFAULT_YR_START, _DEFAULT_YR_END + 1))
    # Clear the slider key so Streamlit re-renders with the new default value
    st.session_state.pop('yr_range_slider', None)


tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["🏢 Select Companies", "📅 Select Years",
     "👤 Load CEOs", "💬 Load Statements",
     "🗑️ Delete Records",
     "📋 Browse CEOs", "📄 Browse Statements"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 - Select Companies
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🏢 Select Companies")

    sp500_df = _load_sp500_df()
    coverage = _load_ceo_coverage()

    # ── Filters ────────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        co_search = st.text_input("Search by Name or Ticker",
                                  placeholder="e.g. Apple, AAPL", key="co_search")
    with fc2:
        sectors = ['All Sectors'] + sorted(
            sp500_df['sector'].dropna().unique().tolist())
        sel_sector = st.selectbox("Filter by Sector", sectors, key="co_sector")
    with fc3:
        quick_sel = st.selectbox(
            "Quick Select",
            ["Custom", "Top 10", "Top 50", "Top 100", "Top 200", "All (500)"],
            key="co_quick")

    # Apply text / sector filters
    fdf = sp500_df.copy()
    if co_search.strip():
        s = co_search.strip().lower()
        fdf = fdf[fdf['symbol'].str.lower().str.contains(s, na=False) |
                  fdf['company'].str.lower().str.contains(s, na=False)]
    if sel_sector != 'All Sectors':
        fdf = fdf[fdf['sector'] == sel_sector]

    # Add live CEO-coverage column
    def _cov_label(row):
        done = sorted(coverage.get(row['symbol'], {}).keys())
        return f"{len(done)} yrs ({done[0]}-{done[-1]})" if done else "none"
    fdf = fdf.copy()
    fdf['ceo_coverage'] = fdf.apply(_cov_label, axis=1)

    # Build option strings for the multiselect
    options = fdf.apply(
        lambda r: f"#{int(r['rank'])} {r['symbol']} - {r['company']}", axis=1
    ).tolist()

    # Pending-key trick: avoid writing to a widget key in the same render pass
    _CKEY = '_ceo_co_widget'
    _CPEND = '_ceo_co_pending'
    if _CPEND in st.session_state:
        st.session_state[_CKEY] = st.session_state.pop(_CPEND)

    # Seed widget on first load from existing selection
    if _CKEY not in st.session_state:
        sel_tickers = {c['ticker'] for c in
                       st.session_state.get('_ceo_sel_companies', [])}
        st.session_state[_CKEY] = [
            o for o in options
            if o.split()[1] in sel_tickers
        ]

    # Always keep currently-selected items visible even when filter hides them
    all_opts = list(options)
    for item in st.session_state.get(_CKEY, []):
        if item not in all_opts:
            all_opts.insert(0, item)

    msc1, msc2 = st.columns([4, 1])
    with msc1:
        st.multiselect(
            f"Companies   ({len(fdf):,} shown, "
            f"{len(st.session_state.get(_CKEY, [])):,} selected)",
            options=all_opts,
            key=_CKEY,
            help="Select companies to include in the CEO pipeline",
        )
    with msc2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Select All Shown", key="co_sel_all", use_container_width=True):
            st.session_state[_CPEND] = list(options)
            st.rerun()
        if st.button("Clear Selection",  key="co_clear",   use_container_width=True):
            st.session_state[_CPEND] = []
            st.rerun()
        n_map = {"Top 10": 10, "Top 50": 50,
                 "Top 100": 100, "Top 200": 200}
        if quick_sel in n_map:
            n = n_map[quick_sel]
            if st.button(f"Apply {quick_sel}", key="co_apply_quick",
                         use_container_width=True):
                top = sp500_df.nsmallest(n, 'rank')
                st.session_state[_CPEND] = top.apply(
                    lambda r: f"#{int(r['rank'])} {r['symbol']} - {r['company']}",
                    axis=1).tolist()
                st.rerun()
        elif quick_sel == "All (500)":
            if st.button("Select All 500", key="co_all500", use_container_width=True):
                st.session_state[_CPEND] = sp500_df.apply(
                    lambda r: f"#{int(r['rank'])} {r['symbol']} - {r['company']}",
                    axis=1).tolist()
                st.rerun()

    # Sync multiselect back to session state as {company_name, ticker} dicts
    sel_opts = st.session_state.get(_CKEY, [])
    sel_companies_state = []
    for opt in sel_opts:
        parts = opt.split(' - ', 1)
        ticker = parts[0].split()[-1]
        co_name = parts[1] if len(parts) > 1 else ticker
        sel_companies_state.append({'company_name': co_name, 'ticker': ticker})
    st.session_state['_ceo_sel_companies'] = sel_companies_state

    st.info(
        f"📌 **{len(sel_companies_state):,}** companies selected for the pipeline")

    if sel_companies_state:
        with st.expander("📋 Selected Companies + CEO Coverage", expanded=False):
            prev_rows = []
            for c in sel_companies_state:
                cov_yr = sorted(coverage.get(c['ticker'], {}).keys())
                prev_rows.append({
                    'Ticker':         c['ticker'],
                    'Company':        c['company_name'],
                    'CEO Years in DB': ', '.join(map(str, cov_yr)) if cov_yr else '—',
                    'Count':          len(cov_yr),
                })
            st.dataframe(pd.DataFrame(prev_rows), hide_index=True,
                         use_container_width=True)

    with st.expander(f"📊 All {len(fdf):,} Shown Companies (with Coverage)",
                     expanded=False):
        disp = fdf[['rank', 'symbol', 'company', 'sector', 'ceo_coverage']].rename(
            columns={'rank': 'Rank', 'symbol': 'Ticker', 'company': 'Company',
                     'sector': 'Sector', 'ceo_coverage': 'CEO Coverage'})
        st.dataframe(disp, hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 - Select Years
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📅 Select Years")

    _cur_yr = datetime.now().year
    _yr_min = 2010
    _yr_max = _cur_yr

    cov_y = _load_ceo_coverage()
    year_counts: dict = {}
    for _td in cov_y.values():
        for _yr in _td:
            year_counts[_yr] = year_counts.get(_yr, 0) + 1

    sl_col, cov_col = st.columns([2, 2])

    with sl_col:
        yr_start, yr_end = st.slider(
            "Year range",
            min_value=_yr_min,
            max_value=_yr_max,
            value=(
                st.session_state.get('_ceo_yr_start', _DEFAULT_YR_START),
                st.session_state.get('_ceo_yr_end',   _DEFAULT_YR_END),
            ),
            step=1,
            key="yr_range_slider",
            help="Drag the handles to set the start and end year for the pipeline.",
        )
        st.session_state['_ceo_yr_start'] = yr_start
        st.session_state['_ceo_yr_end'] = yr_end
        st.session_state['_ceo_sel_years'] = list(range(yr_start, yr_end + 1))

        _sel_yrs = st.session_state['_ceo_sel_years']
        st.success(
            f"📅 **{len(_sel_yrs)}** years selected: **{yr_start}** – **{yr_end}**"
        )

        # Year badges
        st.markdown(" ".join(f"`{y}`" for y in _sel_yrs))

    with cov_col:
        st.markdown("**Coverage — CEO records already in DB**")
        _max_count = max(year_counts.values(), default=1)
        _cov_rows = [
            {
                'Year':        yr,
                'CEO records': year_counts.get(yr, 0),
                'In range':    '✅' if yr_start <= yr <= yr_end else '',
            }
            for yr in range(_yr_min, _yr_max + 1)
        ]
        st.dataframe(
            pd.DataFrame(_cov_rows),
            hide_index=True,
            use_container_width=True,
            height=350,
            column_config={
                'CEO records': st.column_config.ProgressColumn(
                    'CEO records', min_value=0, max_value=_max_count),
            },
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 - Load CEOs
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if svc_error:
        st.error(f"❌ Service unavailable: {svc_error}")
        st.stop()

    st.subheader("👤 Load CEOs")
    st.caption(
        "Identify the CEO for each selected company × year and save to **`t_ceo`**.")

    try:
        counts = svc.get_progress_counts()
        m1, m2, m3 = st.columns(3)
        m1.metric("CEO records",        f"{counts['ceo_rows']:,}")
        m2.metric("Statement records",  f"{counts['stmt_rows']:,}")
        m3.metric("Company×Year pairs", f"{counts['covered_pairs']:,}")
    except Exception as e:
        st.warning(f"Could not load progress counts: {e}")

    st.divider()

    companies_to_run = st.session_state.get('_ceo_sel_companies', [])
    years = sorted(st.session_state.get('_ceo_sel_years', []))

    if not companies_to_run:
        st.warning(
            "⚠️ No companies selected — go to the **🏢 Select Companies** tab first.")
    if not years:
        st.warning(
            "⚠️ No years selected — go to the **📅 Select Years** tab first.")

    co_col, yr_col = st.columns(2)
    co_col.info(f"**{len(companies_to_run):,}** companies selected"
                + (f" | first: {companies_to_run[0]['company_name']}" if companies_to_run else ""))
    yr_col.info(f"**{len(years)}** years selected: "
                + (f"{years[0]}-{years[-1]}" if years else "none"))

    # ── Source selector ────────────────────────────────────────────────────────
    _SRC_OPTIONS = ['All Sources', 'AI', '10K', 'FMP', 'Web Search']
    _SRC_HELP = (
        "**All Sources** — Try AI → 10K → FMP → Web Search in order until one succeeds *(best for gap-fill)*  \n"
        "**AI** — OpenAI gpt-4o-mini: fast, accurate, covers all years  \n"
        "**10K** — Parse local SEC 10-K filings from disk/GCS mount  \n"
        "**FMP** — Financial Modeling Prep API: structured historical data, sparse pre-2015  \n"
        "**Web Search** — DuckDuckGo: last-resort fallback, serialized to avoid rate limits"
    )
    ceo_source = st.radio(
        "Data Source",
        options=_SRC_OPTIONS,
        index=2,
        horizontal=True,
        key="ceo_source_radio",
        help=_SRC_HELP,
    )
    # 'All Sources' cascades through all four in priority order
    ceo_sources = (['AI', '10K', 'FMP', 'Web Search']
                   if ceo_source == 'All Sources' else [ceo_source])

    st.divider()

    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        ceo_workers = st.slider("Parallel workers", 1, 50, 10, key="ceo_workers",
                                help="Web Search is serialized — more workers queue up rather than run in parallel. 10 is optimal.")
    with opt_col2:
        ceo_skip_existing = st.checkbox(
            "Skip companies already in t_ceo", value=True, key="ceo_skip")

    total_ceo_tasks = len(companies_to_run) * len(years)

    # Cache key based on current selection — avoid re-querying DB on every 1-sec rerun
    _pending_cache_key = (tuple(sorted(c['ticker'] for c in companies_to_run)), tuple(
        sorted(years)), ceo_skip_existing)
    if st.session_state.get('_ceo_pending_cache_key') != _pending_cache_key:
        # Selection changed — recompute
        if ceo_skip_existing and companies_to_run and years:
            try:
                _pending_tasks = svc.get_unprocessed_tasks(
                    companies_to_run, years)
                st.session_state['_ceo_pending_count'] = len(_pending_tasks)
            except Exception:
                st.session_state['_ceo_pending_count'] = total_ceo_tasks
        else:
            st.session_state['_ceo_pending_count'] = total_ceo_tasks
        st.session_state['_ceo_pending_cache_key'] = _pending_cache_key

    pending_count = st.session_state.get('_ceo_pending_count', total_ceo_tasks)
    skipped_count = total_ceo_tasks - pending_count

    if ceo_skip_existing:
        st.caption(
            f"**{len(companies_to_run):,}** companies × **{len(years)}** years "
            f"= **{total_ceo_tasks:,}** total | "
            f"✅ **{skipped_count:,}** already done | "
            f"⏳ **{pending_count:,}** to process"
        )
    else:
        st.caption(f"**{len(companies_to_run):,}** companies × **{len(years)}** years "
                   f"= **{total_ceo_tasks:,}** tasks")

    if '_ceo_id_running' not in st.session_state:
        st.session_state['_ceo_id_running'] = False
    if '_ceo_id_run_id' not in st.session_state:
        st.session_state['_ceo_id_run_id'] = None
    if '_ceo_id_summary' not in st.session_state:
        st.session_state['_ceo_id_summary'] = None

    if st.button("▶️ Identify CEOs", key="btn_ceo_id_start", type="primary",
                 use_container_width=True,
                 disabled=(
                     st.session_state['_ceo_id_running']
                     or pending_count == 0
                 )):
        run_id = str(time.time())
        # Reset module-level run state
        with _ceo_run_lock:
            _ceo_run['run_id'] = run_id
            _ceo_run['results'] = []
            _ceo_run['done'] = False
            _ceo_run['summary'] = None
            # set by bg thread after get_unprocessed_tasks
            _ceo_run['total'] = None
        st.session_state['_ceo_id_running'] = True
        st.session_state['_ceo_id_run_id'] = run_id
        st.session_state['_ceo_id_summary'] = None
        st.session_state['_ceo_last_progress_t'] = time.time()
        # Invalidate pending cache so it re-queries after this run completes
        st.session_state.pop('_ceo_pending_cache_key', None)

        def _bg_ceo(companies, yrs, w, skip, srcs, rid):
            def _cb(r):
                with _ceo_run_lock:
                    if _ceo_run['run_id'] == rid:
                        if r.get('status') == '_task_count':
                            # Actual pending count after skip-existing deduction.
                            # Also reset stale timer — workers are about to start.
                            _ceo_run['total'] = r['total']
                            _ceo_run['task_ready_t'] = time.time()
                        else:
                            _ceo_run['results'].append(r)
            try:
                summary = svc.run_ceo_pipeline(
                    companies=companies, years=yrs,
                    workers=w, skip_existing=skip,
                    sources=srcs, on_progress=_cb)
            except Exception as ex:
                summary = {'error': str(ex)}
            with _ceo_run_lock:
                if _ceo_run['run_id'] == rid:
                    _ceo_run['done'] = True
                    _ceo_run['summary'] = summary

        threading.Thread(
            target=_bg_ceo,
            args=(companies_to_run, years, ceo_workers, ceo_skip_existing,
                  list(ceo_sources), run_id),
            daemon=True).start()
        st.rerun()

    if st.session_state['_ceo_id_running']:
        run_id = st.session_state.get('_ceo_id_run_id')
        with _ceo_run_lock:
            results = list(_ceo_run['results']
                           ) if _ceo_run['run_id'] == run_id else []
            is_done = _ceo_run['done'] if _ceo_run['run_id'] == run_id else False
            summary_r = _ceo_run['summary'] if _ceo_run['run_id'] == run_id else None
            run_total = _ceo_run.get('total')   # None until task list is ready

        if is_done:
            st.session_state['_ceo_id_running'] = False
            st.session_state['_ceo_id_summary'] = summary_r
            _load_ceo_coverage.clear()
            st.rerun()

        # Track stale progress — use task_ready_t (DB query done, workers started)
        # as the baseline so a slow get_unprocessed_tasks doesn't trigger false alarms.
        prev_len = st.session_state.get('_ceo_last_result_count', 0)
        if len(results) > prev_len:
            st.session_state['_ceo_last_progress_t'] = time.time()
            st.session_state['_ceo_last_result_count'] = len(results)

        with _ceo_run_lock:
            task_ready_t = _ceo_run.get('task_ready_t', 0.0)
        # Stale seconds: count from whichever is latest —
        # run start, last result, or task list ready (workers started)
        _last_activity = max(
            st.session_state.get('_ceo_last_progress_t', time.time()),
            task_ready_t,
        )

        if run_total is None:
            # Still in get_unprocessed_tasks — show indeterminate state
            st.progress(0.0, text="⏳ Computing pending task list from DB…")
        elif not results:
            st.progress(0.0, text=(
                f"⏳ Starting workers… 0/{run_total:,} unprocessed"
                f"  (first result may take 5–15 s)"))
        else:
            pct = len(results) / max(run_total, 1)
            last = results[-1]
            last_label = (
                f" — last: **{last.get('company', last.get('ticker','?'))}** "
                f"{last.get('year','')} "
                f"\u2192 {last.get('ceo_name') or last.get('status','?')}"
            )
            st.progress(
                pct, text=f"Identifying\u2026 {len(results):,}/{run_total:,}{last_label}")

        stale_secs = time.time() - _last_activity
        if stale_secs > 120:
            st.warning(
                f"⚠️ No progress for **{int(stale_secs)}s** — workers may be waiting. "
                f"Results so far: {len(results):,}.")
            if st.button("⏹ Stop pipeline", key="btn_ceo_stop"):
                st.session_state['_ceo_id_running'] = False
                st.rerun()
        # Non-blocking auto-refresh: page renders fully, then browser triggers rerun after 1.5s
        st_autorefresh(interval=1500, limit=None, key="ceo_poll")

    else:
        run_id = st.session_state.get('_ceo_id_run_id')
        with _ceo_run_lock:
            results = list(_ceo_run['results']
                           ) if _ceo_run['run_id'] == run_id else []
        if results:
            st.progress(1.0, text=f"✅ Complete — {len(results):,} tasks")

    summary_ceo = st.session_state.get('_ceo_id_summary')
    results_ceo: list
    with _ceo_run_lock:
        run_id = st.session_state.get('_ceo_id_run_id')
        results_ceo = list(_ceo_run['results']
                           ) if _ceo_run['run_id'] == run_id else []
    if summary_ceo and not st.session_state['_ceo_id_running']:
        st.success(
            f"CEO identification complete — "
            f"✅ ok: **{summary_ceo.get('ok',0):,}**  "
            f"⏭️ skipped: **{summary_ceo.get('skipped',0):,}**  "
            f"🏗️ pre-existence: **{summary_ceo.get('pre_existence',0):,}**  "
            f"❓ no CEO found: **{summary_ceo.get('no_ceo',0):,}**  "
            f"❌ errors: **{summary_ceo.get('error',0):,}**"
        )
        if summary_ceo.get('halt_reason'):
            st.error(f"⛔ Pipeline halted: {summary_ceo['halt_reason']}")
    if results_ceo:
        with st.expander(f"Last {min(len(results_ceo),500)} results", expanded=False):
            st.dataframe(pd.DataFrame(results_ceo[-500:]),
                         hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 - Load Statements
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    if svc_error:
        st.error(f"❌ Service unavailable: {svc_error}")
        st.stop()

    st.subheader("💬 Load Statements")
    st.caption(
        "Collect CEO statements (earnings calls + articles) for companies that "
        "already have a CEO identified in **`t_ceo`**.")

    companies_to_stmt = st.session_state.get('_ceo_sel_companies', [])
    years_stmt = sorted(st.session_state.get('_ceo_sel_years', []))

    if not companies_to_stmt:
        st.warning(
            "⚠️ No companies selected — go to the **🏢 Select Companies** tab first.")
    if not years_stmt:
        st.warning(
            "⚠️ No years selected — go to the **📅 Select Years** tab first.")

    s_co_col, s_yr_col = st.columns(2)
    s_co_col.info(f"**{len(companies_to_stmt):,}** companies selected")
    s_yr_col.info(f"**{len(years_stmt)}** years selected: "
                  + (f"{years_stmt[0]}-{years_stmt[-1]}" if years_stmt else "none"))

    stmt_workers = st.slider("Parallel workers", 1, 50, 50, key="stmt_workers")
    stmt_skip_existing = st.checkbox(
        "Skip company×year pairs that already have statements",
        value=True, key="stmt_skip")

    total_stmt_tasks = len(companies_to_stmt) * len(years_stmt)
    st.caption(f"**{len(companies_to_stmt):,}** companies × **{len(years_stmt)}** years "
               f"= **{total_stmt_tasks:,}** tasks")

    if '_stmt_running' not in st.session_state:
        st.session_state['_stmt_running'] = False
    if '_stmt_results' not in st.session_state:
        st.session_state['_stmt_results'] = []
    if '_stmt_summary' not in st.session_state:
        st.session_state['_stmt_summary'] = None
    if '_stmt_q' not in st.session_state:
        st.session_state['_stmt_q'] = None

    if st.button("▶️ Collect Statements", key="btn_stmt_start", type="primary",
                 use_container_width=True,
                 disabled=st.session_state['_stmt_running'] or total_stmt_tasks == 0):
        st.session_state['_stmt_running'] = True
        st.session_state['_stmt_results'] = []
        st.session_state['_stmt_summary'] = None
        sq: queue.Queue = queue.Queue()
        st.session_state['_stmt_q'] = sq

        def _bg_stmt(companies, yrs, w, skip, rq):
            def _cb(r): rq.put(r)
            try:
                summary = svc.run_statements_pipeline(
                    companies=companies, years=yrs,
                    workers=w, skip_existing=skip, on_progress=_cb)
            except Exception as ex:
                summary = {'error': str(ex)}
            rq.put({'__DONE__': True, 'summary': summary})

        threading.Thread(
            target=_bg_stmt,
            args=(companies_to_stmt, years_stmt,
                  stmt_workers, stmt_skip_existing, sq),
            daemon=True).start()
        st.rerun()

    if st.session_state['_stmt_running']:
        sq = st.session_state['_stmt_q']
        while not sq.empty():
            item = sq.get_nowait()
            if item.get('__DONE__'):
                st.session_state['_stmt_summary'] = item.get('summary')
                st.session_state['_stmt_running'] = False
            else:
                st.session_state['_stmt_results'].append(item)
        results_s = st.session_state['_stmt_results']
        pct_s = len(results_s) / max(total_stmt_tasks, 1)
        if st.session_state['_stmt_running']:
            st.progress(
                pct_s, text=f"Collecting… {len(results_s):,}/{total_stmt_tasks:,}")
            time.sleep(1)
            st.rerun()
        else:
            st.progress(1.0, text=f"✅ Complete — {len(results_s):,} tasks")

    summary_stmt = st.session_state.get('_stmt_summary')
    results_stmt = st.session_state.get('_stmt_results', [])
    if summary_stmt and not st.session_state['_stmt_running']:
        st.success(
            f"Statement collection complete — "
            f"✅ ok: **{summary_stmt.get('ok',0):,}**  "
            f"⏭️ skipped: **{summary_stmt.get('skipped',0):,}**  "
            f"❓ no CEO in DB: **{summary_stmt.get('no_ceo',0):,}**  "
            f"❌ errors: **{summary_stmt.get('error',0):,}**  "
            f"💬 statements saved: **{summary_stmt.get('statements',0):,}**"
        )
    if results_stmt:
        with st.expander(f"Last {min(len(results_stmt),500)} results", expanded=False):
            st.dataframe(pd.DataFrame(results_stmt[-500:]),
                         hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 - Delete Records
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🗑️ Delete Records")
    _del_companies = st.session_state.get('_ceo_sel_companies', [])
    _del_years = sorted(st.session_state.get('_ceo_sel_years', []))

    if not _del_companies or not _del_years:
        st.warning(
            "⚠️ No companies or years selected. "
            "Use the **🏢 Select Companies** and **📅 Select Years** tabs first."
        )
    else:
        _tickers = [c['ticker'] for c in _del_companies if c.get('ticker')]
        _co_names = [c['company_name'] for c in _del_companies]

        # ── shared preview ────────────────────────────────────────────────────
        try:
            import psycopg2
            import psycopg2.extras
            from Utilities.Lookups import DB_Connection
            _pc = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
            _pc.autocommit = True
            _pcu = _pc.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            _pcu.execute("""
                SELECT c.ceo_id, c.company_name, c.ticker, c.year,
                       c.ceo_name, c.source,
                       COUNT(s.statement_id) AS stmt_count
                FROM   t_ceo c
                LEFT JOIN t_ceo_statements s ON s.ceo_id = c.ceo_id
                WHERE  (c.ticker = ANY(%s) OR c.company_name = ANY(%s))
                  AND  c.year   = ANY(%s)
                GROUP BY c.ceo_id, c.company_name, c.ticker,
                         c.year, c.ceo_name, c.source
                ORDER BY c.year DESC, c.company_name
            """, (_tickers, _co_names, _del_years))
            _preview = [dict(r) for r in _pcu.fetchall()]
            _pcu.close()
            _pc.close()
        except Exception as _pe:
            _preview = []
            st.error(f"Preview query failed: {_pe}")

        _total_ceo = len(_preview)
        _total_stmt = sum(r.get('stmt_count', 0) for r in _preview)

        if _preview:
            with st.expander(
                    f"📋 {_total_ceo:,} CEO rows / {_total_stmt:,} statement rows in scope",
                    expanded=False):
                st.dataframe(pd.DataFrame(_preview),
                             hide_index=True, use_container_width=True)
        else:
            st.info("No matching records found for the current selection.")

        st.divider()

        del_section = st.radio(
            "What to delete?",
            ["Statements only (keep CEO records)",
             "CEO records + all their statements"],
            horizontal=True, key="del_section",
        )

        st.divider()

        # ── Section A: Statements only ─────────────────────────────────────────
        if del_section == "Statements only (keep CEO records)":
            st.markdown(
                f"⚠️ Deletes **{_total_stmt:,} statement rows** from `t_ceo_statements` only. "
                "CEO rows in `t_ceo` are kept intact."
            )
            if _total_stmt == 0:
                st.info("No statements to delete for the current selection.")
            else:
                if 'del_stmt_confirm' not in st.session_state:
                    st.session_state['del_stmt_confirm'] = False

                if not st.session_state['del_stmt_confirm']:
                    if st.button(
                        f"🗑️ Delete {_total_stmt:,} statements",
                        key="btn_del_stmt", type="primary",
                            use_container_width=True):
                        st.session_state['del_stmt_confirm'] = True
                        st.rerun()
                else:
                    st.error(
                        f"⚠️ Permanently delete **{_total_stmt:,} statement rows**? "
                        "CEO records are preserved."
                    )
                    sc1, sc2 = st.columns(2)
                    if sc1.button("✅ Yes, delete statements", key="btn_del_stmt_yes",
                                  type="primary", use_container_width=True):
                        try:
                            import psycopg2
                            from Utilities.Lookups import DB_Connection
                            _dc = psycopg2.connect(
                                DB_Connection().DB_CONNECTION_STRING)
                            _dc.autocommit = False
                            _dcu = _dc.cursor()
                            _dcu.execute("""
                                DELETE FROM t_ceo_statements
                                WHERE ceo_id IN (
                                    SELECT ceo_id FROM t_ceo
                                    WHERE (ticker = ANY(%s) OR company_name = ANY(%s))
                                      AND year = ANY(%s)
                                )
                            """, (_tickers, _co_names, _del_years))
                            deleted = _dcu.rowcount
                            _dc.commit()
                            _dcu.close()
                            _dc.close()
                            st.session_state['del_stmt_confirm'] = False
                            _load_ceo_coverage.clear()
                            st.success(
                                f"✅ Deleted **{deleted:,}** statement rows.")
                            st.rerun()
                        except Exception as _de:
                            st.error(f"Delete failed: {_de}")
                    if sc2.button("❌ Cancel", key="btn_del_stmt_cancel",
                                  use_container_width=True):
                        st.session_state['del_stmt_confirm'] = False
                        st.rerun()

        # ── Section B: CEO records + cascade ──────────────────────────────────
        else:
            st.markdown(
                f"⚠️ Deletes **{_total_ceo:,} CEO rows** from `t_ceo` AND **{_total_stmt:,} "
                "cascaded statement rows** from `t_ceo_statements`."
            )
            if _total_ceo == 0:
                st.info("No CEO records to delete for the current selection.")
            else:
                if 'del_ceo_confirm' not in st.session_state:
                    st.session_state['del_ceo_confirm'] = False

                if not st.session_state['del_ceo_confirm']:
                    if st.button(
                        f"🗑️ Delete {_total_ceo:,} CEO records + {_total_stmt:,} statements",
                        key="btn_del_ceo", type="primary",
                            use_container_width=True):
                        st.session_state['del_ceo_confirm'] = True
                        st.rerun()
                else:
                    st.error(
                        f"⚠️ Permanently delete **{_total_ceo:,} CEO records** "
                        f"and **{_total_stmt:,} statements**? This cannot be undone."
                    )
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Yes, delete all", key="btn_del_ceo_yes",
                                  type="primary", use_container_width=True):
                        try:
                            import psycopg2
                            from Utilities.Lookups import DB_Connection
                            _dc = psycopg2.connect(
                                DB_Connection().DB_CONNECTION_STRING)
                            _dc.autocommit = False
                            _dcu = _dc.cursor()
                            _dcu.execute("""
                                DELETE FROM t_ceo
                                WHERE (ticker = ANY(%s) OR company_name = ANY(%s))
                                  AND year = ANY(%s)
                            """, (_tickers, _co_names, _del_years))
                            deleted = _dcu.rowcount
                            _dc.commit()
                            _dcu.close()
                            _dc.close()
                            st.session_state['del_ceo_confirm'] = False
                            _load_ceo_coverage.clear()
                            st.success(
                                f"✅ Deleted **{deleted:,}** CEO records "
                                "(statements removed via cascade)."
                            )
                            st.rerun()
                        except Exception as _de:
                            st.error(f"Delete failed: {_de}")
                    if cc2.button("❌ Cancel", key="btn_del_ceo_cancel",
                                  use_container_width=True):
                        st.session_state['del_ceo_confirm'] = False
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 - Browse CEOs
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("CEO Records")

    b1, b2, b3 = st.columns(3)
    f_company = b1.text_input("Company", key="ceo_f_company")
    f_ceo = b2.text_input("CEO name", key="ceo_f_name")
    f_year = b3.number_input("Year (0 = all)", min_value=0,
                             max_value=2030, value=0, key="ceo_f_year")

    try:
        import psycopg2
        import psycopg2.extras
        from Utilities.Lookups import DB_Connection
        _conn2 = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
        _conn2.autocommit = True
        _cur2 = _conn2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        clauses2, params2 = [], []
        if f_company:
            clauses2.append("company_name ILIKE %s")
            params2.append(f'%{f_company}%')
        if f_ceo:
            clauses2.append("ceo_name ILIKE %s")
            params2.append(f'%{f_ceo}%')
        if f_year:
            clauses2.append("year = %s")
            params2.append(f_year)
        where2 = ('WHERE ' + ' AND '.join(clauses2)) if clauses2 else ''
        _cur2.execute(f"""
            SELECT ceo_id, company_name, ticker, year, ceo_name,
                   source, confidence_score, added_dt
            FROM t_ceo {where2}
            ORDER BY year DESC, company_name
            LIMIT 500
        """, params2)
        rows2 = [dict(r) for r in _cur2.fetchall()]
        _cur2.close()
        _conn2.close()
        st.dataframe(pd.DataFrame(rows2), hide_index=True,
                     use_container_width=True)
        st.caption(f"Showing {len(rows2):,} rows (max 500)")
    except Exception as e:
        st.error(f"Query failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 - Browse Statements
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.subheader("CEO Statements")

    c1, c2, c3, c4 = st.columns(4)
    sf_company = c1.text_input("Company", key="stmt_f_company")
    sf_ceo = c2.text_input("CEO name", key="stmt_f_ceo")
    sf_year = c3.number_input("Year (0 = all)", min_value=0,
                              max_value=2030, value=0, key="stmt_f_year")
    sf_type = c4.selectbox("Type", options=[
        '', 'earnings_call', 'article', 'interview',
        'press_release', 'speech'], key="stmt_f_type")

    if svc:
        try:
            rows3 = svc.search_statements(
                company=sf_company,
                ceo=sf_ceo,
                year=int(sf_year) if sf_year else None,
                stmt_type=sf_type,
                limit=300,
            )
            if rows3:
                df3 = pd.DataFrame(rows3)
                # Make source URL clickable
                if 'source_url' in df3.columns:
                    df3['source_url'] = df3['source_url'].apply(
                        lambda u: f'[link]({u})' if u else '')
                st.dataframe(
                    df3, hide_index=True, use_container_width=True,
                    column_config={
                        'source_url': st.column_config.LinkColumn('Source'),
                        'preview': st.column_config.TextColumn(
                            'Preview', width='large'),
                    }
                )
                st.caption(f"Showing {len(rows3):,} rows (max 300)")

                # Full statement viewer
                st.divider()
                st.subheader("Full Statement Viewer")
                stmt_ids = [r['statement_id'] for r in rows3]
                sel_id = st.selectbox(
                    "Select statement ID to read in full",
                    options=stmt_ids, key="stmt_sel_id")
                if sel_id:
                    sel_row = next((r for r in rows3
                                    if r['statement_id'] == sel_id), None)
                    if sel_row:
                        st.markdown(
                            f"**{sel_row['company_name']}** — "
                            f"**{sel_row['ceo_name']}** — "
                            f"**{sel_row['year']}** — "
                            f"`{sel_row['statement_type']}`"
                        )
                        # Fetch full text
                        try:
                            import psycopg2
                            import psycopg2.extras
                            from Utilities.Lookups import DB_Connection
                            _c3 = psycopg2.connect(
                                DB_Connection().DB_CONNECTION_STRING)
                            _c3.autocommit = True
                            _cu3 = _c3.cursor(
                                cursor_factory=psycopg2.extras.RealDictCursor)
                            _cu3.execute(
                                "SELECT statement_text, source_url "
                                "FROM t_ceo_statements "
                                "WHERE statement_id = %s", (sel_id,))
                            full = _cu3.fetchone()
                            _cu3.close()
                            _c3.close()
                            if full:
                                st.text_area("Statement text",
                                             value=full['statement_text'],
                                             height=400)
                                if full['source_url']:
                                    st.markdown(
                                        f"[🔗 Original source]({full['source_url']})")
                        except Exception as e:
                            st.error(f"Could not load full text: {e}")
            else:
                st.info(
                    "No statements found — run the pipeline first or adjust filters.")
        except Exception as e:
            st.error(f"Query failed: {e}")
    else:
        st.error(f"Service unavailable: {svc_error}")
