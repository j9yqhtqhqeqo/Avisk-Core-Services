"""
Sustainability Report Downloader UI

Streamlit interface for downloading sustainability reports from S&P 500 companies.
"""

from Services.SustainabilityReportDownloader import SustainabilityReportDownloader
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import sys
import os

# Add parent directory to path - must be before local imports
sys.path.append(str(Path(__file__).resolve().parent.parent))


@st.cache_data(ttl=3600, show_spinner=False)
def _load_sp500_rank_map() -> dict:
    """Load symbol→rank map from sp500_market_cap_ranked.csv (all 500 companies)."""
    csv_path = Path(__file__).resolve().parent.parent / \
        "Clients" / "sp500_market_cap_ranked.csv"
    try:
        _df = pd.read_csv(str(csv_path))
        return {str(row['symbol']).upper().strip(): int(row['rank']) for _, row in _df.iterrows()}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _load_sp500_csv_df() -> pd.DataFrame:
    """Load full S&P 500 ranked CSV (rank, symbol, company, market_cap, sector)."""
    csv_path = Path(__file__).resolve().parent.parent / \
        "Clients" / "sp500_market_cap_ranked.csv"
    df = pd.read_csv(str(csv_path))
    df.columns = [c.strip().lower() for c in df.columns]
    df['symbol'] = df['symbol'].str.upper().str.strip()
    df['company'] = df['company'].str.strip()
    df['rank'] = pd.to_numeric(
        df['rank'], errors='coerce').fillna(999).astype(int)
    return df


def get_market_cap_rank(symbol: str) -> int:
    """Get market cap rank from CSV (all 500 S&P 500 companies). Returns 999 for unknown symbols."""
    return _load_sp500_rank_map().get(str(symbol).upper().strip(), 999)


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


@st.cache_data(show_spinner=False)
def _read_file_bytes(path: str) -> bytes:
    """
    Read a file from disk and cache the result across Streamlit re-runs.

    Using @st.cache_data ensures that Streamlit registers the media file once
    and reuses the same content hash, preventing MediaFileStorageError when
    the page re-runs while a download button is still visible in the browser.
    """
    with open(path, 'rb') as f:
        return f.read()


@st.cache_data(ttl=60, show_spinner=False)
def _check_company_coverage(
    symbols_tuple: tuple,          # tuple so it's hashable for cache
    company_names_tuple: tuple,
    years_tuple: tuple,
    content_types_tuple: tuple,
) -> dict:
    """
    Query t_data_source and return a per-company coverage summary.
    Returns dict keyed by symbol:
      {
        'symbol': str,
        'company': str,
        'covered_combos': int,   # (year, ct) pairs already in DB
        'total_combos': int,     # total requested (year, ct) pairs
        'status': 'full' | 'partial' | 'new',
        'covered_years': list[int],
        'missing_years': list[int],
      }
    """
    import psycopg2
    from Utilities.Lookups import DB_Connection

    symbols = list(symbols_tuple)
    companies = list(company_names_tuple)
    years = list(years_tuple)
    content_types = list(content_types_tuple)

    # Build lookup: lower(company_name) → {(year, ct), ...}
    db_index: dict = {}
    try:
        conn_str = DB_Connection().DB_CONNECTION_STRING
        if conn_str:
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT LOWER(TRIM(company_name)), year, content_type
                FROM t_data_source
                WHERE year = ANY(%s) AND content_type = ANY(%s)
                """,
                (years, content_types)
            )
            for (name_lower, yr, ct) in cur.fetchall():
                db_index.setdefault(name_lower, set()).add((yr, ct))
            cur.close()
            conn.close()
    except Exception:
        pass  # If DB is unreachable return empty → all companies flagged as 'new'

    total_combos = len(years) * len(content_types)
    result = {}
    for sym, company in zip(symbols, companies):
        name_lower = company.lower().strip()
        # fuzzy match: check if any DB key is a substring or superset of name
        matched_combos: set = set()
        for db_name, combos in db_index.items():
            if name_lower in db_name or db_name in name_lower:
                matched_combos |= combos

        covered = sum(1 for yr in years for ct in content_types if (
            yr, ct) in matched_combos)
        covered_years = sorted({yr for yr in years if any(
            (yr, ct) in matched_combos for ct in content_types)})
        missing_years = sorted(set(years) - set(covered_years))

        if covered == 0:
            status = 'new'
        elif covered >= total_combos:
            status = 'full'
        else:
            status = 'partial'

        result[sym] = {
            'symbol': sym,
            'company': company,
            'covered_combos': covered,
            'total_combos': total_combos,
            'status': status,
            'covered_years': covered_years,
            'missing_years': missing_years,
        }
    return result


# Page configuration
st.set_page_config(
    page_title="Document Downloader",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'companies_df' not in st.session_state:
    st.session_state.companies_df = None
if 'selected_companies' not in st.session_state:
    st.session_state.selected_companies = []
if 'download_results' not in st.session_state:
    st.session_state.download_results = None
if 'is_downloading' not in st.session_state:
    st.session_state.is_downloading = False
if 'download_complete' not in st.session_state:
    st.session_state.download_complete = False

# ── Auto-restore active download job after browser reconnect ─────────────────
# session_state is wiped when the tab closes; re-populate from DB on every
# fresh page load so the live status panel reappears automatically.
if not st.session_state.get("active_dl_job_id"):
    try:
        from Services.JobQueue import get_recent_jobs as _init_rj, ensure_jobs_table as _init_et
        _init_et()
        for _init_r in _init_rj(job_type="document_download", limit=5):
            if _init_r["status"] in ("running", "queued", "cancelling"):
                st.session_state["active_dl_job_id"] = str(_init_r["job_id"])
                break
    except Exception:
        pass

# Title
st.title("📊 Document Downloader")
st.markdown("Download sustainability reports, annual reports/10K filings, and earnings transcripts from S&P 500 companies")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

# Content Type Selection
st.sidebar.subheader("📄 Content Types to Download")
download_sustainability = st.sidebar.checkbox(
    "🌱 Sustainability/ESG Reports",
    value=False,
    help="Download sustainability reports, ESG reports, corporate responsibility reports"
)
download_annual = st.sidebar.checkbox(
    "📊 Annual Reports/10K Filings",
    value=False,
    help="Download annual reports, 10-K SEC filings"
)
download_other = st.sidebar.checkbox(
    "📁 Other Filings (EDGAR)",
    value=False,
    help="Download other EDGAR filings and miscellaneous company documents (content type 3)"
)
download_transcripts = st.sidebar.checkbox(
    "🎙️ Earnings Call Transcripts",
    value=False,
    help="Download earnings call transcripts, investor call transcripts"
)

# Reload mode — shown indented under Investor Transcripts
reload_mode = st.sidebar.radio(
    "Reload mode",
    options=["⏭️ Skip already processed", "🔄 Re-download all"],
    index=0,
    help=("⏭️ Skip already processed: bypass companies/years that already have "
          "records in the database (faster, avoids duplicates). \n"
          "🔄 Re-download all: force re-download even when records exist."),
)
force_reload = reload_mode == "🔄 Re-download all"

# Build content_types list based on selections
content_types = []
if download_sustainability:
    content_types.append(1)
if download_annual:
    content_types.append(2)
if download_other:
    content_types.append(3)  # 3 = Other EDGAR filings
if download_transcripts:
    content_types.append(4)  # 4 = Earnings Transcripts

# Warn if nothing selected
if not content_types:
    st.sidebar.warning("⚠️ Please select at least one content type")

st.sidebar.markdown("---")

# Use storage path toggle
use_storage = st.sidebar.checkbox(
    "Use Cloud Storage Path",
    value=True,
    help="Use PathConfiguration for Stage0SourcePDFFiles (recommended for production)"
)

if not use_storage:
    output_dir = st.sidebar.text_input(
        "Output Directory",
        value="./sustainability_reports",
        help="Directory where reports will be saved"
    )
else:
    output_dir = None
    st.sidebar.info("📁 Using Stage0SourcePDFFiles path")

delay_seconds = st.sidebar.slider(
    "Delay Between Requests (seconds)",
    min_value=0.5,
    max_value=5.0,
    value=2.0,
    step=0.5,
    help="Time to wait between requests to be respectful to servers"
)

# Sector ID configuration
st.sidebar.subheader("🏷️ Sector Mapping")
enable_sector_mapping = st.sidebar.checkbox(
    "Enable Sector Mapping",
    value=True,
    help="Map downloaded reports to sector in database"
)

if enable_sector_mapping:
    current_sector_id = st.sidebar.number_input(
        "Current Sector ID",
        min_value=1,
        max_value=9999,
        value=1007,
        help="Sector ID for database mapping (e.g., 1007)"
    )
else:
    current_sector_id = None

# Main content
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["🏢 Select Companies", "📅 Select Years", "📥 Download", "📁 Files", "📊 Today's Downloads", "🔍 Missing Reports", "📈 S&P 500 Overview"])

with tab1:
    st.header("Select Companies to Download")

    # Auto-load companies on first visit
    if st.session_state.companies_df is None:
        with st.spinner("Loading S&P 500 companies..."):
            try:
                downloader = SustainabilityReportDownloader(
                    download_dir=output_dir,
                    use_storage=use_storage
                )
                st.session_state.companies_df = downloader.load_sp500_companies()
            except Exception as e:
                st.error(f"Failed to load companies: {e}")

    # Display and select companies
    if st.session_state.companies_df is not None:
        df = st.session_state.companies_df

        # Add market cap rank using pre-built list (instant, no API calls)
        if 'market_cap_rank' not in df.columns:
            df['market_cap_rank'] = df['Symbol'].apply(get_market_cap_rank)
            st.session_state.companies_df = df  # Save back to session state

        st.markdown("---")
        st.subheader("🔍 Filter & Select Companies")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            # Search by name/symbol
            search_term = st.text_input(
                "Search by Name or Symbol",
                placeholder="e.g., Apple, AAPL",
                help="Filter companies by name or symbol"
            )

        with col2:
            # Filter by sector if available
            if 'Sector' in df.columns or 'GICS Sector' in df.columns:
                sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
                sectors = ['All Sectors'] + \
                    sorted(df[sector_col].dropna().unique().tolist())
                selected_sector = st.selectbox("Filter by Sector", sectors)
            else:
                selected_sector = 'All Sectors'

        with col3:
            # Quick select options
            quick_select = st.selectbox(
                "Quick Select",
                ["Custom Selection", "All Companies",
                 "Top 10 (by Market Cap)", "Top 50 (by Market Cap)",
                 "Top 100 (by Market Cap)", "Top 200 (by Market Cap)",
                 "Top 500 (All S&P 500)",
                 "Tech Companies", "Energy Companies", "Healthcare Companies",
                 "Financial Companies", "Industrial Companies",
                 "Real Estate Companies", "Consumer Companies",
                 "Communication Services", "Utilities"]
            )

        # Apply filters
        filtered_df = df.copy()

        if search_term:
            mask = (
                filtered_df['Symbol'].str.contains(search_term, case=False, na=False) |
                filtered_df['Company'].str.contains(
                    search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        if selected_sector != 'All Sectors':
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            filtered_df = filtered_df[filtered_df[sector_col]
                                      == selected_sector]

        # Apply quick select - sort by market cap rank (lower rank = higher market cap)
        if quick_select == "Top 10 (by Market Cap)":
            filtered_df = filtered_df.sort_values('market_cap_rank').head(10)
        elif quick_select == "Top 50 (by Market Cap)":
            filtered_df = filtered_df.sort_values('market_cap_rank').head(50)
        elif quick_select == "Top 100 (by Market Cap)":
            filtered_df = filtered_df.sort_values('market_cap_rank').head(100)
        elif quick_select == "Top 200 (by Market Cap)":
            filtered_df = filtered_df.sort_values('market_cap_rank').head(200)
        elif quick_select in ("Top 500 (All S&P 500)", "All Companies"):
            filtered_df = filtered_df.sort_values('market_cap_rank')
        elif quick_select == "Tech Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Technology|Information', case=False, na=False)]
        elif quick_select == "Energy Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Energy', case=False, na=False)]
        elif quick_select == "Healthcare Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Health', case=False, na=False)]
        elif quick_select == "Financial Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Financ', case=False, na=False)]
        elif quick_select == "Industrial Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Industrial', case=False, na=False)]
        elif quick_select == "Real Estate Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Real Estate', case=False, na=False)]
        elif quick_select == "Consumer Companies":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Consumer|Discretionary|Staples|Cyclical|Defensive', case=False, na=False)]
        elif quick_select == "Communication Services":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Communication', case=False, na=False)]
        elif quick_select == "Utilities":
            sector_col = 'Sector' if 'Sector' in df.columns else 'GICS Sector'
            if sector_col in df.columns:
                filtered_df = filtered_df[filtered_df[sector_col].str.contains(
                    'Utilities|Utility', case=False, na=False)]

        # Always sort by market cap rank for display
        filtered_df = filtered_df.sort_values('market_cap_rank')

        st.markdown(
            f"**Showing {len(filtered_df)} companies** (sorted by market cap)")

        # Company selection with checkboxes
        col1, col2 = st.columns([3, 1])

        _CKEY = 'tab1_companies_select'
        _PENDING = 'tab1_companies_pending'  # staging key for button actions

        # Apply any pending action from the PREVIOUS render (before the widget
        # is instantiated — Streamlit forbids writing to a widget key after it
        # has been rendered in the current pass).
        if _PENDING in st.session_state:
            st.session_state[_CKEY] = st.session_state.pop(_PENDING)

        # Build options from the filtered view.
        company_options = filtered_df.apply(
            lambda row: f"#{int(row['market_cap_rank'])} {row['Symbol']} - {row['Company']}", axis=1
        ).tolist()

        # Seed the key on first load from any pre-existing selection.
        if _CKEY not in st.session_state:
            st.session_state[_CKEY] = [
                c for c in st.session_state.get('selected_companies', [])
                if c in company_options
            ]

        # Always inject currently-selected items back into options so they are
        # never stripped when the "Search" text input filters the list.
        # This lets the user search for "DIS", add it, then clear the search
        # without losing previously selected companies like GOOG.
        all_options = list(company_options)
        for item in st.session_state[_CKEY]:
            if item not in all_options:
                all_options.insert(0, item)  # keep at top so they're visible

        with col1:
            st.multiselect(
                "Select Companies to Download",
                options=all_options,
                key=_CKEY,
                help="Select one or more companies (ranked by market cap)"
            )
            st.session_state.selected_companies = st.session_state[_CKEY]

        with col2:
            st.markdown("### Quick Actions")
            if st.button("Select All Shown"):
                # Write to pending, not _CKEY — widget already rendered above
                st.session_state[_PENDING] = list(company_options)
                st.rerun()

            if st.button("Clear Selection"):
                st.session_state[_PENDING] = []
                st.rerun()

        # Show selected count
        st.info(
            f"📌 **{len(st.session_state.selected_companies)}** companies selected")

        # Preview selected companies
        if st.session_state.selected_companies:
            with st.expander("📋 View Selected Companies", expanded=False):
                # Extract symbol from format: "#1 AAPL - Apple Inc."
                selected_symbols = []
                for c in st.session_state.selected_companies:
                    # Split by ' - ' and take first part, then extract symbol after #rank
                    parts = c.split(' - ')[0]  # "#1 AAPL"
                    symbol = parts.split(' ')[-1]  # "AAPL"
                    selected_symbols.append(symbol)
                selected_df = df[df['Symbol'].isin(
                    selected_symbols)].sort_values('market_cap_rank')
                st.dataframe(
                    selected_df[['market_cap_rank', 'Symbol', 'Company']].rename(
                        columns={'market_cap_rank': 'Rank'}), use_container_width=True)

with tab2:
    st.header("Select Years to Download")

    st.markdown("""
    Filter reports by year. The downloader will search for reports from the selected year range
    and organize them into yearly folders.
    """)

    col1, col2 = st.columns(2)

    current_year = datetime.now().year

    with col1:
        st.subheader("📅 Year Range")

        year_selection_mode = st.radio(
            "Year Selection Mode",
            ["All Available Years", "Specific Year Range", "Single Year"],
            help="Choose how to filter reports by year"
        )

        try:
            _ds_years = _load_ds_years()
        except Exception as _ye:
            st.error(f"⚠️ Cannot load years — database inaccessible: {_ye}")
            st.stop()

        _yr_min = int(_ds_years[-1]) if _ds_years else 2000
        _yr_max = int(_ds_years[0]) if _ds_years else current_year

        if year_selection_mode == "Specific Year Range":
            start_year = st.slider(
                "Start Year",
                min_value=_yr_min,
                max_value=_yr_max,
                value=min(_yr_min + 2, _yr_max),
                help="Download reports from this year onwards"
            )

            end_year = st.slider(
                "End Year",
                min_value=start_year,
                max_value=_yr_max,
                value=_yr_max,
                help="Download reports up to this year"
            )

            years_to_download = list(range(start_year, end_year + 1))

        elif year_selection_mode == "Single Year":
            single_year = st.selectbox(
                "Select Year",
                options=_ds_years,
                index=0,
                help="Download reports only from this specific year"
            )
            years_to_download = [single_year]

        else:
            years_to_download = None  # All years

    with col2:
        st.subheader("📊 Year Summary")

        if years_to_download:
            st.success(
                f"**Selected Years:** {min(years_to_download)} - {max(years_to_download)}")
            st.metric("Number of Years", len(years_to_download))

            # Display year badges
            year_badges = " ".join([f"`{y}`" for y in years_to_download])
            st.markdown(f"**Years:** {year_badges}")
        else:
            st.info("📅 **All available years** will be downloaded")
            st.caption(
                "Reports will be automatically organized into yearly folders based on their publication date.")

    # Store years in session state
    if 'years_to_download' not in st.session_state:
        st.session_state.years_to_download = years_to_download
    st.session_state.years_to_download = years_to_download

    st.markdown("---")
    st.markdown("""
    **📁 Folder Structure:**
    Reports will be saved in yearly folders:
    ```
    Stage0SourcePDFFiles/
    ├── 2024/
    │   ├── AAPL_Sustainability_Report-2024.pdf
    │   └── MSFT_ESG_Report-2024.pdf
    ├── 2023/
    │   └── ...
    └── 2022/
        └── ...
    ```
    """)

with tab3:
    st.header("Download Reports")

    # Summary of selections
    st.subheader("📋 Download Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        company_count = len(
            st.session_state.selected_companies) if st.session_state.selected_companies else 0
        st.metric("Companies Selected", company_count)

    with col2:
        if st.session_state.get('years_to_download'):
            year_count = len(st.session_state.years_to_download)
            st.metric(
                "Years Selected", f"{year_count} ({min(st.session_state.years_to_download)}-{max(st.session_state.years_to_download)})")
        else:
            st.metric("Years Selected", "All Available")

    with col3:
        # Show content types
        content_type_names = []
        if 1 in content_types:
            content_type_names.append("🌱 ESG")
        if 2 in content_types:
            content_type_names.append("📊 10K")
        if 4 in content_types:
            content_type_names.append("🎙️ Transcripts")
        st.metric("Content Types", len(content_types))
        st.caption(" ".join(content_type_names))

    with col4:
        st.metric(
            "Sector ID", current_sector_id if enable_sector_mapping else "Not Set")

    # ── Coverage pre-flight check ─────────────────────────────────────────
    _tab3_years = st.session_state.get('years_to_download')
    _tab3_syms: list = []
    _tab3_names: list = []
    if st.session_state.selected_companies:
        for _c3 in st.session_state.selected_companies:
            _p3 = _c3.split(' - ')[0]
            _tab3_syms.append(_p3.split(' ')[-1])
            _tab3_names.append(_c3.split(' - ', 1)
                               [1] if ' - ' in _c3 else _p3.split(' ')[-1])

    _show_coverage = (
        not force_reload
        and len(_tab3_syms) > 0
        and content_types
        and _tab3_years
    )

    _coverage_data: dict = {}
    _companies_to_skip: set = set()   # symbols fully covered → skip entirely
    _companies_partial: set = set()   # symbols partially covered
    _companies_new: set = set()       # symbols with no data yet

    if _show_coverage:
        with st.spinner("🔍 Checking database coverage..."):
            try:
                _coverage_data = _check_company_coverage(
                    tuple(_tab3_syms),
                    tuple(_tab3_names),
                    tuple(sorted(_tab3_years)),
                    tuple(sorted(content_types)),
                )
                for _sym, _info in _coverage_data.items():
                    if _info['status'] == 'full':
                        _companies_to_skip.add(_sym)
                    elif _info['status'] == 'partial':
                        _companies_partial.add(_sym)
                    else:
                        _companies_new.add(_sym)
            except Exception as _cov_e:
                st.caption(f"Coverage check unavailable: {_cov_e}")

        st.markdown("---")
        st.subheader("📊 Pre-Download Coverage Check")

        _cv1, _cv2, _cv3, _cv4 = st.columns(4)
        _cv1.metric("🆕 Will Download", len(_companies_new),
                    help="No records in DB — full download needed")
        _cv2.metric("⚡ Partial Update", len(_companies_partial),
                    help="Some years present — only missing years will be fetched")
        _cv3.metric("⏭️ Will Skip", len(_companies_to_skip),
                    help="All requested year/content combinations already in DB")
        _actual_to_run = len(_tab3_syms) - len(_companies_to_skip)
        _cv4.metric("▶️ Effective Run", _actual_to_run,
                    help="Companies that will actually be processed")

        if _companies_to_skip:
            with st.expander(
                f"⏭️ {len(_companies_to_skip)} companies will be **skipped** (all years already in DB)",
                expanded=len(_companies_to_skip) <= 20,
            ):
                _skip_rows = [
                    {"Symbol": s, "Company": _coverage_data[s]['company'],
                     "Covered Years": ", ".join(str(y) for y in _coverage_data[s]['covered_years'])}
                    for s in sorted(_companies_to_skip)
                ]
                st.dataframe(pd.DataFrame(_skip_rows),
                             hide_index=True, use_container_width=True)
                st.caption(
                    "Switch sidebar to **🔄 Re-download all** to force re-processing these companies.")

        if _companies_partial:
            with st.expander(
                f"⚡ {len(_companies_partial)} companies need **partial update** (some years missing)",
                expanded=False,
            ):
                _partial_rows = [
                    {"Symbol": s,
                     "Company": _coverage_data[s]['company'],
                     "Already Have": ", ".join(str(y) for y in _coverage_data[s]['covered_years']),
                     "Will Fetch": ", ".join(str(y) for y in _coverage_data[s]['missing_years'])}
                    for s in sorted(_companies_partial)
                ]
                st.dataframe(pd.DataFrame(_partial_rows),
                             hide_index=True, use_container_width=True)

    # Validation
    can_download = True
    warnings = []

    if company_count == 0:
        warnings.append(
            "⚠️ No companies selected. Go to 'Select Companies' tab to select companies.")
        can_download = False

    if not content_types:
        warnings.append(
            "⚠️ No content type selected. Please tick at least one option "
            "(Sustainability/ESG, Annual Reports/10K, or Earnings Call Transcripts) in the sidebar.")
        can_download = False

    for warning in warnings:
        st.warning(warning)

    # Download button
    st.markdown("---")

    # ── Active job check ─────────────────────────────────────────────────────
    _dl_active_job = st.session_state.get("active_dl_job_id")

    if not _dl_active_job and can_download:
        _effective = company_count - \
            len(_companies_to_skip) if not force_reload else company_count
        col1, col2 = st.columns([2, 1])
        with col1:
            if _companies_to_skip and not force_reload:
                st.markdown(
                    f"**Ready!** **{len(_companies_to_skip)}** fully-covered companies will be "
                    f"skipped. **{_effective}** companies will be queued."
                )
            else:
                st.markdown(
                    "**Ready to queue!** Click the button below to submit a background job."
                )
        with col2:
            estimated_time = max(_effective, 1) * delay_seconds * 10
            st.caption(f"⏱️ Estimated time: ~{estimated_time/60:.1f} minutes")

    if not _dl_active_job:
        if st.button("🚀 Queue Background Download", type="primary", use_container_width=True,
                     disabled=not can_download):
            try:
                from Services.JobQueue import submit_job, ensure_jobs_table
                ensure_jobs_table()
                _dl_payload = {
                    "companies": [
                        {"symbol": _s, "company_name": _n}
                        for _s, _n in zip(_tab3_syms, _tab3_names)
                    ],
                    "years":             list(_tab3_years) if _tab3_years else [],
                    "content_types":     list(content_types),
                    "force_reload":      force_reload,
                    "use_storage":       use_storage,
                    "output_dir":        output_dir,
                    "current_sector_id": current_sector_id,
                    "delay_seconds":     delay_seconds,
                    "bypass_symbols":    list(_companies_to_skip) if not force_reload else [],
                }
                _dl_jid = submit_job("document_download", _dl_payload)
                st.session_state["active_dl_job_id"] = _dl_jid
                st.success(
                    f"✅ Download job queued! ID: `{_dl_jid}`  \n"
                    "The background worker will process it server-side — "
                    "**you can safely close this browser tab** and return later."
                )
                st.rerun()
            except Exception as _dje:
                st.error(f"Failed to queue download job: {_dje}")

    # ── Live download job status panel ──────────────────────────────────────
    if _dl_active_job:
        import time as _dl_time
        from Services.JobQueue import get_job as _dl_get_job, cancel_job as _dl_cancel_job

        try:
            _djdata = _dl_get_job(_dl_active_job)
        except Exception as _dgje:
            st.error(f"Could not fetch job status: {_dgje}")
            _djdata = {}

        _djstatus = _djdata.get("status", "unknown")
        _djprog = _djdata.get("progress", 0)
        _djtotal = _djdata.get("total", 0)
        _djcurrent = _djdata.get("current_item", "")
        _djlog = _djdata.get("log_lines", "")
        _djerr = _djdata.get("error_msg", "")
        _djcreated = _djdata.get("created_at")

        _dj_icon = {
            "queued":      "🔵",
            "running":     "⏳",
            "cancelling":  "🛑",
            "completed":   "✅",
            "failed":      "❌",
            "cancelled":   "🚫",
        }.get(_djstatus, "❓")

        st.markdown(
            f"### {_dj_icon} Download Job Status: **{_djstatus.title()}**")
        st.caption(f"Job ID: `{_dl_active_job}`")

        _djc1, _djc2, _djc3, _djc4 = st.columns(4)
        _djc1.metric(
            "Progress",  f"{_djprog}/{_djtotal}" if _djtotal else str(_djprog))
        _djc2.metric("Current",   (_djcurrent or "—")[:40])
        _djc3.metric("Status",    _djstatus.title())
        _djc4.metric("Queued",    str(_djcreated)[:16] if _djcreated else "—")

        if _djtotal > 0:
            st.progress(min(_djprog / _djtotal, 1.0))

        with st.expander("📋 Live Log", expanded=_djstatus == "running"):
            st.text(_djlog[-6000:] if _djlog else "(no log yet)")

        _djbtn1, _djbtn2 = st.columns(2)

        if _djstatus in ("running", "queued", "cancelling"):
            if _djstatus == "cancelling":
                st.warning(
                    "🛑 **Stop requested** — the worker will finish the current "
                    "company then halt. This page auto-refreshes."
                )
            else:
                st.info(
                    "🔄 Auto-refreshing every 5 seconds — "
                    "**safe to close this browser tab and return later.**"
                )
                with _djbtn1:
                    if st.button("🚫 Cancel Job", key="dl_cancel_job"):
                        _dcr = _dl_cancel_job(_dl_active_job)
                        if _dcr == "cancelled":
                            st.success("✅ Job removed from queue.")
                        elif _dcr == "cancelling":
                            st.info(
                                "🛑 Stop requested — worker will halt "
                                "after the current company."
                            )
                        else:
                            st.warning("Job not in a cancellable state.")
                        st.rerun()
            _dl_time.sleep(5)
            st.rerun()

        elif _djstatus == "completed":
            st.success(
                "✅ Download job completed! "
                "Switch to the 📁 Files tab to view downloaded reports."
            )
            if _djbtn1.button("🗑️ Clear & Start New Job", key="dl_clear_job"):
                del st.session_state["active_dl_job_id"]
                st.rerun()

        elif _djstatus in ("failed", "cancelled"):
            if _djerr:
                st.error(f"Job {_djstatus}: {_djerr}")
            if _djbtn1.button("🗑️ Clear & Retry", key="dl_clear_job_err"):
                del st.session_state["active_dl_job_id"]
                st.rerun()

    # ── Recent download jobs history ─────────────────────────────────────────
    st.markdown("---")
    with st.expander("📋 Recent Download Jobs", expanded=False):
        try:
            from Services.JobQueue import get_recent_jobs as _dl_recent, ensure_jobs_table as _dl_ensure
            _dl_ensure()
            _dl_hist = _dl_recent(job_type="document_download", limit=20)
            if _dl_hist:
                _dl_rows = []
                for _dh in _dl_hist:
                    _ddur = "—"
                    if _dh.get("started_at") and _dh.get("completed_at"):
                        _dsec = (_dh["completed_at"] -
                                 _dh["started_at"]).total_seconds()
                        _ddur = f"{int(_dsec // 60)}m {int(_dsec % 60)}s"
                    _dl_rows.append({
                        "Job ID":   str(_dh["job_id"])[:8] + "…",
                        "Status":   _dh["status"],
                        "Progress": f"{_dh['progress']}/{_dh['total']}",
                        "Current":  (_dh["current_item"] or "")[:35],
                        "Queued":   str(_dh["created_at"])[:16],
                        "Duration": _ddur,
                    })
                st.dataframe(pd.DataFrame(_dl_rows),
                             hide_index=True, use_container_width=True)
                _dlhcol1, _dlhcol2 = st.columns(2)

                # Reattach
                _dl_resume_opts = {
                    f"{str(h['job_id'])[:8]}… — {h['status']} @ {str(h['created_at'])[:16]}": str(h["job_id"])
                    for h in _dl_hist if h["status"] in ("running", "queued", "cancelling", "completed")
                }
                with _dlhcol1:
                    if _dl_resume_opts:
                        _dl_resume_sel = st.selectbox(
                            "📎 Reattach to a previous job",
                            ["(none)"] + list(_dl_resume_opts.keys()),
                            key="dl_resume_sel",
                        )
                        if _dl_resume_sel != "(none)" and st.button("Reattach", key="dl_reattach"):
                            st.session_state["active_dl_job_id"] = _dl_resume_opts[_dl_resume_sel]
                            st.rerun()

                # Cancel from history
                _dl_cancel_hist_opts = {
                    f"{str(h['job_id'])[:8]}… — {h['status']} @ {str(h['created_at'])[:16]}": str(h["job_id"])
                    for h in _dl_hist if h["status"] in ("queued", "running")
                }
                with _dlhcol2:
                    if _dl_cancel_hist_opts:
                        _dl_cancel_hist_sel = st.selectbox(
                            "🚫 Cancel a job",
                            ["(none)"] + list(_dl_cancel_hist_opts.keys()),
                            key="dl_cancel_hist_sel",
                        )
                        if _dl_cancel_hist_sel != "(none)" and st.button(
                            "Cancel Selected", key="dl_cancel_hist", type="secondary"
                        ):
                            from Services.JobQueue import cancel_job as _dlhcj
                            _dlhcr = _dlhcj(
                                _dl_cancel_hist_opts[_dl_cancel_hist_sel])
                            if _dlhcr == "cancelled":
                                st.success("✅ Job removed from queue.")
                            elif _dlhcr == "cancelling":
                                st.info(
                                    "🛑 Stop requested — worker halts after current item.")
                            else:
                                st.warning("Job not in a cancellable state.")
                            st.rerun()
            else:
                st.info("No download jobs have been run yet.")
        except Exception as _dl_he:
            st.caption(f"Job history unavailable: {_dl_he}")

    # Show any persisted download results from a previous job
    if st.session_state.get("download_results") is not None:
        st.markdown("---")
        st.subheader("📋 Previous Download Results")
        st.dataframe(st.session_state.download_results,
                     use_container_width=True)
        csv = st.session_state.download_results.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv,
            file_name="download_results.csv",
            mime="text/csv"
        )

with tab4:
    st.header("Downloaded Files")

    # Function to classify report type based on filename
    def classify_report_type(filename: str) -> str:
        """Classify a report as Sustainability, Annual/10K, Earnings Transcript, or Other EDGAR filing based on filename."""
        filename_lower = filename.lower()

        # Earnings Transcript / Press Release patterns
        transcript_patterns = [
            'pressrelease', 'press_release', 'press-release',
            'transcript', 'earnings_call', 'earnings-call', 'earningscall',
            'conference_call', 'conference-call', 'earnings_transcript'
        ]

        # Annual Report / 10K patterns
        annual_patterns = [
            '10k', '10-k', 'annual_report', 'annual-report', 'annualreport',
            'form10k', 'form-10k', 'form_10k', '_ar_', '-ar-', '_ar.', '-ar.',
            'proxy', 'def14a', '10q', '10-q', 'quarterly'
        ]

        # Sustainability / ESG patterns
        sustainability_patterns = [
            'sustainability', 'esg', 'csr', 'corporate_responsibility',
            'corporate-responsibility', 'corporateresponsibility',
            'environmental', 'social_responsibility', 'social-responsibility',
            'impact_report', 'impact-report', 'impactreport',
            'citizenship', 'climate', 'carbon', 'emissions',
            'responsible', 'stewardship', 'green', 'progress_report',
            'progress-report', 'cdp', 'tcfd', 'sasb', 'gri'
        ]

        # Check transcripts / press releases first
        for pattern in transcript_patterns:
            if pattern in filename_lower:
                return "🎙️ Earnings Transcripts/Press Releases"

        # Check sustainability (prioritize if both match)
        for pattern in sustainability_patterns:
            if pattern in filename_lower:
                return "🌱 Sustainability/ESG"

        # Check annual/10K
        for pattern in annual_patterns:
            if pattern in filename_lower:
                return "📊 Annual/10K"

        # Default to Other EDGAR
        return "📁 Other Filings (EDGAR)"

    # Get the storage path
    if use_storage:
        try:
            from Utilities.PathConfiguration import PathConfiguration
            path_config = PathConfiguration()
            output_path = Path(path_config.get_stage0_input_path())
            st.info(f"📁 Storage Path: `{output_path}`")
        except:
            output_path = Path('./sustainability_reports')
    else:
        output_path = Path(output_dir) if output_dir else Path(
            './sustainability_reports')

    if output_path.exists():
        # Show yearly folder structure
        st.subheader("📁 Filter Downloaded Reports")

        year_folders = sorted([f for f in output_path.iterdir() if f.is_dir() and f.name.isdigit()],
                              key=lambda x: x.name, reverse=True)

        if year_folders:
            # Collect all PDF files first
            all_files = []
            for folder in year_folders:
                for report_file in list(folder.glob("*.pdf")) + list(folder.glob("*.txt")):
                    # Extract company symbol from filename (format: SYMBOL_filename.pdf or SYMBOL-filename.pdf)
                    filename = report_file.name
                    symbol = filename.split('_')[0].split('-')[0].upper()
                    report_type = classify_report_type(filename)
                    all_files.append({
                        'year': folder.name,
                        'symbol': symbol,
                        'filename': filename,
                        'path': report_file,
                        'size_mb': report_file.stat().st_size / (1024 * 1024),
                        'report_type': report_type
                    })

            # Get report types from filesystem
            unique_types = sorted(set(f['report_type'] for f in all_files))

            # Load distinct years and companies from t_data_source
            unique_years = []
            unique_symbols = []          # display: full company names
            company_name_to_ticker = {}  # company_name -> ticker
            try:
                import psycopg2
                from Utilities.Lookups import DB_Connection
                _conn_str = DB_Connection().DB_CONNECTION_STRING
                if not _conn_str:
                    raise ValueError("DB_CONNECTION_STRING is not configured")
                _dsconn = psycopg2.connect(_conn_str)
                _dscur = _dsconn.cursor()
                _dscur.execute(
                    "SELECT DISTINCT year FROM t_data_source ORDER BY year DESC")
                unique_years = [str(row[0]) for row in _dscur.fetchall()]
                _dscur.execute("""
                    SELECT DISTINCT company_name, ticker
                    FROM t_data_source
                    ORDER BY company_name
                """)
                for row in _dscur.fetchall():
                    _cname, _ticker = row[0], row[1]
                    unique_symbols.append(_cname)
                    if _ticker:
                        company_name_to_ticker[_cname] = _ticker.upper()
                _dscur.close()
                _dsconn.close()
            except Exception as _dse:
                st.error(
                    f"⚠️ Cannot load filters — database is inaccessible: {_dse}")
                st.stop()

            # Count by type
            type_counts = {}
            for t in unique_types:
                type_counts[t] = len(
                    [f for f in all_files if f['report_type'] == t])

            # Summary metrics
            st.success(
                f"Found **{len(all_files)}** reports across **{len(year_folders)}** years from **{len(unique_symbols)}** companies")

            # Show type breakdown
            type_cols = st.columns(len(unique_types))
            for i, report_type in enumerate(unique_types):
                with type_cols[i]:
                    st.metric(report_type, type_counts[report_type])

            # Filter controls
            col1, col2, col3 = st.columns(3)

            with col1:
                # Company filter — options are full company names from t_data_source
                # Pre-select based on session state: format "#1 AAPL - Apple Inc."
                default_companies = []
                if st.session_state.selected_companies:
                    for c in st.session_state.selected_companies:
                        # Extract company name from format: "#1 AAPL - Apple Inc."
                        name_part = c.split(
                            ' - ', 1)[-1].strip() if ' - ' in c else ''
                        if name_part and name_part in unique_symbols:
                            default_companies.append(name_part)

                filter_by_company = st.checkbox(
                    "🏢 Filter by Selected Companies",
                    value=len(default_companies) > 0,
                    help="Show only files for companies selected in the 'Select Companies' tab"
                )

                if filter_by_company:
                    company_filter = st.multiselect(
                        "Companies",
                        options=unique_symbols,
                        default=default_companies if default_companies else [],
                        help="Filter files by company name"
                    )
                else:
                    company_filter = unique_symbols  # Show all

            with col2:
                # Year filter - use selected years from tab2 as default if available
                years_from_session = st.session_state.get(
                    'years_to_download', None)
                if years_from_session:
                    default_years = [
                        str(y) for y in years_from_session if str(y) in unique_years]
                else:
                    # Default to recent 3 years
                    default_years = unique_years[:3]

                filter_by_year = st.checkbox(
                    "📅 Filter by Selected Years",
                    value=years_from_session is not None,
                    help="Show only files for years selected in the 'Select Years' tab"
                )

                if filter_by_year:
                    year_filter = st.multiselect(
                        "Years",
                        options=unique_years,
                        default=default_years if default_years else unique_years[:3],
                        help="Filter files by year"
                    )
                else:
                    year_filter = unique_years  # Show all

            with col3:
                # Report type filter
                filter_by_type = st.checkbox(
                    "📋 Filter by Report Type",
                    value=False,
                    help="Show only specific report types"
                )

                if filter_by_type:
                    # Fixed order for the 4 content types
                    ordered_types = [
                        "🌱 Sustainability/ESG",
                        "📊 Annual/10K",
                        "📁 Other Filings (EDGAR)",
                        "🎙️ Earnings Transcripts/Press Releases"
                    ]
                    available_types = [
                        t for t in ordered_types if t in unique_types]
                    # Fall back to any types not in the ordered list
                    for t in unique_types:
                        if t not in available_types:
                            available_types.append(t)
                    default_type = [
                        "🌱 Sustainability/ESG"] if "🌱 Sustainability/ESG" in available_types else available_types[:1]
                    type_filter = st.multiselect(
                        "Report Types",
                        options=available_types,
                        default=default_type,
                        help="Filter by report type"
                    )
                else:
                    type_filter = unique_types  # Show all

            # Apply filters
            # Resolve selected company names -> tickers via the DB-sourced map.
            # Fall back to the name itself (upper) if ticker wasn't in the DB.
            selected_tickers = set(
                company_name_to_ticker.get(name, name.upper())
                for name in company_filter
            )
            filtered_files = [
                f for f in all_files
                if f['symbol'].upper() in selected_tickers
                and f['year'] in year_filter
                and f['report_type'] in type_filter
            ]

            st.markdown("---")

            if filtered_files:
                st.subheader(
                    f"📄 Showing {len(filtered_files)} of {len(all_files)} reports")

                # ── Flat table (no per-row download buttons → no media file
                # registration on every re-run, eliminating MediaFileStorageError)
                table_rows = [
                    {
                        "Year": f["year"],
                        "Symbol": f["symbol"],
                        "Filename": f["filename"],
                        "Type": f["report_type"],
                        "Size (MB)": round(f["size_mb"], 2),
                    }
                    for f in sorted(
                        filtered_files,
                        key=lambda x: (x["year"], x["symbol"], x["filename"]),
                        reverse=True,
                    )
                ]
                files_df = pd.DataFrame(table_rows)
                st.dataframe(files_df, use_container_width=True,
                             hide_index=True)

                # ── Single on-demand download: user selects one file at a time.
                # Only ONE media file is ever registered in Streamlit's
                # MediaFileStorage, which eliminates the race-condition error.
                st.markdown("---")
                st.markdown("#### ⬇️ Download a File")

                file_options = {
                    f"{f['year']} / {f['symbol']} / {f['filename']}": f
                    for f in sorted(
                        filtered_files,
                        key=lambda x: (x["year"], x["symbol"], x["filename"]),
                    )
                }
                selected_label = st.selectbox(
                    "Select a file to download",
                    options=list(file_options.keys()),
                    index=None,
                    placeholder="Choose a file…",
                )
                if selected_label:
                    chosen = file_options[selected_label]
                    st.download_button(
                        label=f"⬇️ Download {chosen['filename']}",
                        data=_read_file_bytes(str(chosen["path"])),
                        file_name=chosen["filename"],
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
            else:
                st.warning(
                    "No files match the selected filters. Try adjusting your company or year selection.")
        else:
            st.info(
                "No yearly folders found yet. Download reports to see them organized by year.")
    else:
        st.warning(
            f"Output directory does not exist yet. Start a download to create it.")


# --- Today's Downloads Tab ---
with tab5:
    st.header("📊 Today's Downloads Summary")
    today = datetime.now().date()

    col_refresh, col_spacer = st.columns([1, 8])
    with col_refresh:
        refresh_today = st.button("🔄 Refresh", key="refresh_today")

    # ── 1. Try database first ────────────────────────────────────────────────
    db_rows = None
    db_error = None
    try:
        import psycopg2
        import psycopg2.extras
        from Utilities.Lookups import DB_Connection
        conn_str = DB_Connection().DB_CONNECTION_STRING
        if conn_str:
            _conn = psycopg2.connect(conn_str)
            _cur = _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            _cur.execute("""
                SELECT
                    ds.unique_id,
                    ds.company_name,
                    ds.year,
                    ds.content_type,
                    COALESCE(dl.data_lookups_description, ds.content_type::TEXT) AS content_type_label,
                    ds.source_url                   AS document_name,
                    ds.source_domain,
                    ds.is_official_source,
                    ds.source_confidence_score,
                    ds.verification_status,
                    ds.file_size_bytes,
                    ds.http_response_code,
                    ds.original_source_url,
                    ds.sec_verified,
                    ds.download_timestamp
                FROM t_data_source ds
                LEFT JOIN t_data_lookups dl
                    ON dl.data_lookups_id = ds.content_type
                WHERE ds.download_timestamp >= %s
                  AND ds.download_timestamp <  %s
                ORDER BY ds.download_timestamp DESC
            """, (today, today + __import__('datetime').timedelta(days=1)))
            db_rows = _cur.fetchall()
            _cur.close()
            _conn.close()
    except Exception as _db_exc:
        db_error = str(_db_exc)

    VERIFICATION_LABELS = {
        0: "⬜ Unverified",
        1: "✅ Auto-Verified",
        2: "🔵 Manually Verified",
        3: "⚠️ Flagged",
        4: "❌ Rejected",
    }
    CONTENT_TYPE_LABELS = {
        1: "🌱 Sustainability/ESG",
        2: "📊 Annual/10K",
        3: "📄 Other",
        4: "🎙️ Transcripts",
    }

    if db_rows is not None:
        # ── DB path ─────────────────────────────────────────────────────────
        if db_rows:
            total = len(db_rows)
            official = sum(1 for r in db_rows if r['is_official_source'])
            avg_conf = sum(r['source_confidence_score']
                           or 0 for r in db_rows) / total

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📥 Total Downloads", total)
            m2.metric("🏛️ Official Sources", f"{official} / {total}")
            m3.metric("⭐ Avg Confidence", f"{avg_conf:.0f} / 100")
            m4.metric("📅 Date", today.strftime("%b %d, %Y"))

            st.markdown("---")

            rows_display = []
            for r in db_rows:
                conf = r['source_confidence_score'] or 0
                conf_display = (
                    f"🟢 {conf}" if conf >= 70 else
                    f"🟡 {conf}" if conf >= 50 else
                    f"🔴 {conf}"
                )
                rows_display.append({
                    "Time": r['download_timestamp'].strftime('%H:%M:%S') if r['download_timestamp'] else "—",
                    "Company": r['company_name'] or "—",
                    "Year": r['year'] or "—",
                    "Content Type": CONTENT_TYPE_LABELS.get(r['content_type'],
                                                            r['content_type_label'] or "—"),
                    "Document": r['document_name'] or "—",
                    "Domain": r['source_domain'] or "—",
                    "Official": "✅" if r['is_official_source'] else "—",
                    "Confidence": conf_display,
                    "Status": VERIFICATION_LABELS.get(r['verification_status'], "—"),
                    "Size (MB)": f"{r['file_size_bytes'] / 1024 / 1024:.2f}" if r['file_size_bytes'] else "—",
                    "HTTP": r['http_response_code'] or "—",
                    "SEC ✓": "✅" if r['sec_verified'] else "—",
                })

            df_today = pd.DataFrame(rows_display)
            st.dataframe(df_today, hide_index=True, use_container_width=True)

            # Download CSV
            csv_data = df_today.to_csv(index=False)
            st.download_button(
                label="⬇️ Export to CSV",
                data=csv_data,
                file_name=f"downloads_{today}.csv",
                mime="text/csv",
            )
        else:
            st.info(
                f"No downloads recorded in the database for {today.strftime('%B %d, %Y')}.")
            if db_error is None:
                st.caption(
                    "Downloads are logged automatically when you use the Download tab.")

    else:
        # ── Filesystem fallback ──────────────────────────────────────────────
        if db_error:
            st.warning(
                f"⚠️ Could not connect to database ({db_error}). Falling back to filesystem scan.")

        output_path = Path(output_dir) if output_dir else Path('.')
        today_files = []
        if output_path.exists():
            for pdf in output_path.rglob('*.pdf'):
                try:
                    mtime = datetime.fromtimestamp(pdf.stat().st_mtime)
                    if mtime.date() == today:
                        today_files.append({
                            "Time": mtime.strftime('%H:%M:%S'),
                            "Filename": pdf.name,
                            "Size (MB)": f"{pdf.stat().st_size / 1024 / 1024:.2f}",
                            "Path": str(pdf.relative_to(output_path)),
                        })
                except Exception:
                    continue

        if today_files:
            st.dataframe(pd.DataFrame(today_files),
                         hide_index=True, use_container_width=True)
            st.success(f"{len(today_files)} file(s) found on disk for today.")
        else:
            st.info(f"No downloads found for {today.strftime('%B %d, %Y')}.")

# --- Missing Reports Tab ---
with tab6:
    st.header("🔍 Missing Reports")

    # ── Read selections directly from tab1 & tab2 ────────────────────────
    _tab1_companies = st.session_state.get('selected_companies') or []
    _tab2_years = st.session_state.get('years_to_download')

    # Derive symbols + names from tab1 selection
    miss_syms, miss_names = [], []
    for c in _tab1_companies:
        parts = c.split(' - ')[0]
        miss_syms.append(parts.split(' ')[-1])
        miss_names.append(
            c.split(' - ', 1)[1] if ' - ' in c else parts.split(' ')[-1])

    # Derive year list from tab2
    years_sorted_miss = sorted(_tab2_years) if _tab2_years else []

    # ── Context summary strip ─────────────────────────────────────────────
    si1, si2, si3 = st.columns(3)
    si1.info(f"🏢 **{len(miss_syms)}** companies from Tab 1")
    si2.info(
        f"📅 **{len(years_sorted_miss)}** years from Tab 2"
        + (f" ({years_sorted_miss[0]}–{years_sorted_miss[-1]})" if years_sorted_miss else "")
    )
    CT_NAMES = {1: "🌱 ESG", 2: "📊 Annual/10K", 4: "🎙️ Transcripts"}
    si3.info(
        f"📄 **Content:** {', '.join(CT_NAMES.get(ct, str(ct)) for ct in content_types) or 'None'}")

    # ── Guard: prompt user to configure missing inputs ────────────────────
    guards = []
    if not miss_syms:
        guards.append(
            "⚠️ No companies selected — go to **Tab 1** and select companies.")
    if not years_sorted_miss:
        guards.append(
            "⚠️ No year range set — go to **Tab 2** and choose a specific year range.")
    if not content_types:
        guards.append(
            "⚠️ No content types selected — tick at least one option in the sidebar.")

    for g in guards:
        st.warning(g)

    if not guards:
        col_ref_miss, _ = st.columns([1, 8])
        with col_ref_miss:
            st.button("🔄 Refresh", key="refresh_missing")

        # ── Query DB ──────────────────────────────────────────────────────
        db_error_miss = None
        db_existing: set = set()

        try:
            import psycopg2
            from collections import defaultdict as _defaultdict
            from Utilities.Lookups import DB_Connection
            _conn_str = DB_Connection().DB_CONNECTION_STRING
            if _conn_str:
                _conn_m = psycopg2.connect(_conn_str)
                _cur_m = _conn_m.cursor()
                _cur_m.execute(
                    """
                    SELECT LOWER(company_name), year, content_type
                    FROM t_data_source
                    WHERE year = ANY(%s)
                      AND content_type = ANY(%s)
                    """,
                    (years_sorted_miss, content_types)
                )
                db_idx = _defaultdict(set)
                for (db_name, db_year, db_ct) in _cur_m.fetchall():
                    db_idx[(db_year, db_ct)].add(db_name)
                _cur_m.close()
                _conn_m.close()

                for sym, company_name in zip(miss_syms, miss_names):
                    name_lower = company_name.lower()
                    for year in years_sorted_miss:
                        for ct in content_types:
                            if any(name_lower in n or n in name_lower
                                   for n in db_idx.get((year, ct), set())):
                                db_existing.add((sym, year, ct))
        except Exception as _e_miss:
            db_error_miss = str(_e_miss)

        if db_error_miss:
            st.error(f"❌ Database error: {db_error_miss}")
        else:
            all_combos = {(sym, year, ct)
                          for sym in miss_syms for year in years_sorted_miss for ct in content_types}
            missing_combos = all_combos - db_existing
            total_combos = len(all_combos)
            missing_count = len(missing_combos)
            existing_count = len(db_existing)
            coverage_pct = (existing_count / total_combos *
                            100) if total_combos > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📋 Total Combinations", total_combos)
            m2.metric("✅ Existing in DB", existing_count)
            m3.metric("❌ Missing", missing_count)
            m4.metric("📈 Coverage", f"{coverage_pct:.1f}%")

            st.markdown("---")

            # ── Missing records grid ──────────────────────────────────────
            if missing_count == 0:
                st.success("✅ All combinations are present in the database!")
            else:
                sym_to_name = dict(zip(miss_syms, miss_names))
                missing_rows = [
                    {"Symbol": sym, "Company": sym_to_name.get(sym, sym),
                     "Year": year, "Content Type": CT_NAMES.get(ct, str(ct))}
                    for (sym, year, ct) in sorted(missing_combos, key=lambda x: (x[0], x[1], x[2]))
                ]
                missing_df = pd.DataFrame(missing_rows)

                st.subheader(f"❌ Missing Records ({missing_count})")
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    filt_syms = st.multiselect("Symbol", sorted(missing_df["Symbol"].unique(
                    )), default=[], placeholder="All", key="miss_filt_sym")
                with fc2:
                    filt_years = st.multiselect("Year", sorted(missing_df["Year"].unique()), default=[
                    ], placeholder="All", key="miss_filt_year")
                with fc3:
                    filt_ct = st.multiselect("Content Type", sorted(
                        missing_df["Content Type"].unique()), default=[], placeholder="All", key="miss_filt_ct")

                fdf = missing_df.copy()
                if filt_syms:
                    fdf = fdf[fdf["Symbol"].isin(filt_syms)]
                if filt_years:
                    fdf = fdf[fdf["Year"].isin(filt_years)]
                if filt_ct:
                    fdf = fdf[fdf["Content Type"].isin(filt_ct)]

                st.caption(
                    f"Showing **{len(fdf)}** of **{missing_count}** missing records")
                st.dataframe(fdf, hide_index=True, use_container_width=True)
                st.download_button("⬇️ Export to CSV", fdf.to_csv(index=False),
                                   "missing_reports.csv", "text/csv")

            # ── Company × Year matrix ─────────────────────────────────────
            st.markdown("---")
            st.subheader("🗓️ Company × Year Matrix")

            mf1, mf2 = st.columns([2, 3])
            with mf1:
                matrix_sym_filter = st.multiselect(
                    "Filter by Symbol",
                    options=sorted(miss_syms), default=[],
                    placeholder="All symbols", key="miss_matrix_sym")
            with mf2:
                show_only_incomplete = st.checkbox(
                    "Show only rows with at least one ❌ or ⚠️",
                    value=False, key="miss_matrix_incomplete")

            matrix_data = []
            for sym, company_name in zip(miss_syms, miss_names):
                if matrix_sym_filter and sym not in matrix_sym_filter:
                    continue
                row_data = {"Symbol": sym, "Company": company_name}
                for year in years_sorted_miss:
                    present = [ct for ct in content_types if (
                        sym, year, ct) in db_existing]
                    if len(present) == len(content_types):
                        row_data[str(year)] = "✅"
                    elif len(present) == 0:
                        row_data[str(year)] = "❌"
                    else:
                        row_data[str(year)] = "⚠️ " + \
                            " ".join(CT_NAMES.get(ct, str(ct))
                                     for ct in present)
                matrix_data.append(row_data)

            matrix_df = pd.DataFrame(matrix_data)
            if show_only_incomplete:
                yr_cols = [c for c in matrix_df.columns if c not in (
                    "Symbol", "Company")]
                mask = matrix_df[yr_cols].apply(
                    lambda row: any("❌" in str(v) or "⚠️" in str(v) for v in row), axis=1)
                matrix_df = matrix_df[mask]

            st.caption(
                f"Showing **{len(matrix_df)}** companies  |  ✅ All types present  |  ⚠️ Partial  |  ❌ None")
            st.dataframe(matrix_df, hide_index=True, use_container_width=True)

# --- S&P 500 Overview Tab ---
with tab7:
    st.header("📈 S&P 500 Overview")
    st.markdown(
        "Full S&P 500 universe — market cap rankings, sectors, and document download coverage.")

    # Load S&P 500 CSV
    try:
        _sp5_df = _load_sp500_csv_df()
    except Exception as _sp5_e:
        st.error(f"❌ Failed to load S&P 500 data: {_sp5_e}")
        st.stop()

    # Load DB coverage (which tickers have any record in t_data_source)
    _sp5_in_db: set = set()
    _sp5_db_err = None
    try:
        import psycopg2
        from Utilities.Lookups import DB_Connection as _OvDBConn
        _sp5_cs = _OvDBConn().DB_CONNECTION_STRING
        if _sp5_cs:
            _sp5_conn = psycopg2.connect(_sp5_cs)
            _sp5_cur = _sp5_conn.cursor()
            _sp5_cur.execute(
                "SELECT DISTINCT UPPER(TRIM(ticker)) FROM t_data_source "
                "WHERE ticker IS NOT NULL AND TRIM(ticker) != ''"
            )
            _sp5_in_db = {row[0] for row in _sp5_cur.fetchall()}
            _sp5_cur.close()
            _sp5_conn.close()
    except Exception as _sp5_dbe:
        _sp5_db_err = str(_sp5_dbe)

    if _sp5_db_err:
        st.warning(f"⚠️ Could not load DB coverage data: {_sp5_db_err}")

    # Add coverage flag
    _sp5_view = _sp5_df.copy()
    _sp5_view['has_data'] = _sp5_view['symbol'].isin(_sp5_in_db)
    _sp5_view['Status'] = _sp5_view['has_data'].apply(
        lambda x: "✅ In DB" if x else "❌ Missing")

    # Summary metrics
    _sp5_total = len(_sp5_view)
    _sp5_in_n = int(_sp5_view['has_data'].sum())
    _sp5_miss_n = _sp5_total - _sp5_in_n
    _sp5_cov = _sp5_in_n / _sp5_total * 100 if _sp5_total > 0 else 0

    ov_c1, ov_c2, ov_c3, ov_c4 = st.columns(4)
    ov_c1.metric("🏢 S&P 500 Universe", _sp5_total)
    ov_c2.metric("✅ Has Downloads", _sp5_in_n)
    ov_c3.metric("❌ No Downloads", _sp5_miss_n)
    ov_c4.metric("📈 Coverage", f"{_sp5_cov:.1f}%")

    st.markdown("---")

    # Sector breakdown table with inline progress bars
    st.subheader("📊 Coverage by Sector")

    _sec_grp = (
        _sp5_view.groupby('sector')
        .agg(Companies=('symbol', 'count'), In_DB=('has_data', 'sum'))
        .reset_index()
    )
    _sec_grp['Missing'] = _sec_grp['Companies'] - _sec_grp['In_DB']
    _sec_grp['Coverage %'] = (
        _sec_grp['In_DB'] / _sec_grp['Companies'] * 100).round(1)
    _sec_grp['Progress'] = _sec_grp['Coverage %'].apply(
        lambda p: "█" * int(p / 5) + "░" * (20 - int(p / 5))
    )
    _sec_grp = _sec_grp.sort_values(
        'Companies', ascending=False).reset_index(drop=True)
    _sec_display = _sec_grp.rename(columns={
        'sector': 'Sector', 'In_DB': 'In Database'
    })[['Sector', 'Companies', 'In Database', 'Missing', 'Coverage %', 'Progress']]
    st.dataframe(_sec_display, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Top 25 by market cap with status
    st.subheader("🏆 Top 25 Companies by Market Cap")
    _top25 = _sp5_view.sort_values('rank').head(25)[
        ['rank', 'symbol', 'company', 'market_cap', 'sector', 'Status']
    ].rename(columns={
        'rank': '#', 'symbol': 'Symbol', 'company': 'Company',
        'market_cap': 'Market Cap', 'sector': 'Sector'
    })
    st.dataframe(_top25, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Full S&P 500 browser
    st.subheader("🔍 S&P 500 Company Browser")

    ov_f1, ov_f2, ov_f3 = st.columns(3)
    with ov_f1:
        _ov_sectors = ["All Sectors"] + \
            sorted(_sp5_df['sector'].dropna().unique().tolist())
        _ov_sec_sel = st.selectbox(
            "Filter by Sector", _ov_sectors, key="ov_sector_sel")
    with ov_f2:
        _ov_stat_sel = st.selectbox(
            "Filter by Status", ["All", "✅ In Database", "❌ No Downloads"], key="ov_status_sel")
    with ov_f3:
        _ov_srch = st.text_input(
            "Search Symbol or Company", placeholder="e.g. AAPL, Apple", key="ov_search")

    _ov_filt = _sp5_view.copy()
    if _ov_sec_sel != "All Sectors":
        _ov_filt = _ov_filt[_ov_filt['sector'] == _ov_sec_sel]
    if _ov_stat_sel == "✅ In Database":
        _ov_filt = _ov_filt[_ov_filt['has_data']]
    elif _ov_stat_sel == "❌ No Downloads":
        _ov_filt = _ov_filt[~_ov_filt['has_data']]
    if _ov_srch:
        _ov_filt = _ov_filt[
            _ov_filt['symbol'].str.contains(_ov_srch, case=False, na=False) |
            _ov_filt['company'].str.contains(_ov_srch, case=False, na=False)
        ]

    st.caption(
        f"Showing **{len(_ov_filt)}** of **{_sp5_total}** S&P 500 companies")

    st.dataframe(
        _ov_filt[['rank', 'symbol', 'company', 'market_cap', 'sector', 'Status']].rename(columns={
            'rank': '#', 'symbol': 'Symbol', 'company': 'Company',
            'market_cap': 'Market Cap', 'sector': 'Sector'
        }),
        hide_index=True, use_container_width=True
    )

    # Export missing list
    _sp5_missing_df = _sp5_view[~_sp5_view['has_data']][
        ['rank', 'symbol', 'company', 'market_cap', 'sector']
    ].rename(columns={'rank': 'Rank', 'symbol': 'Symbol', 'company': 'Company',
                      'market_cap': 'Market Cap', 'sector': 'Sector'})
    if len(_sp5_missing_df) > 0:
        st.markdown("---")
        st.download_button(
            label=f"⬇️ Export {len(_sp5_missing_df)} Missing Companies to CSV",
            data=_sp5_missing_df.to_csv(index=False),
            file_name="sp500_missing_downloads.csv",
            mime="text/csv",
        )


# Footer
st.markdown("---")
st.markdown("""
**📌 Usage Tips:**
- Select companies in the **Select Companies** tab using filters and search
- Optionally filter by year range in the **Select Years** tab
- Start the download in the **Download** tab
- View organized files in the **Files** tab
- See today's downloads in the **Today's Downloads** tab

**Note:** This tool searches company websites for publicly available sustainability reports.
Please respect website terms of service and rate limits.
""")
