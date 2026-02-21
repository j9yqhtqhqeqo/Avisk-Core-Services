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


# Top 150 S&P 500 by market cap - scraped from marketcap.company (Feb 2026)
# Companies ranked #1-150 by market capitalization
TOP_SP500_MARKET_CAP_ORDER = [
    # 1-50
    'NVDA', 'AAPL', 'GOOG', 'MSFT', 'AMZN', 'META', 'TSLA', 'LLY', 'JPM', 'XOM',
    'JNJ', 'V', 'MA', 'MU', 'COST', 'ABBV', 'BAC', 'HD', 'GE', 'PG',
    'AMD', 'CVX', 'PLTR', 'NFLX', 'KO', 'CSCO', 'LRCX', 'PM', 'WFC', 'AMAT',
    'CAT', 'ORCL', 'UNH', 'MRK', 'IBM', 'GS', 'RTX', 'MCD', 'LIN', 'MS',
    'C', 'PEP', 'ABT', 'TMO', 'DIS', 'AXP', 'KLAC', 'GILD', 'T', 'AMGN',
    # 51-100
    'BA', 'NEE', 'GEV', 'TJX', 'ISRG', 'APH', 'INTC', 'CRM', 'VZ', 'DE',
    'ADI', 'SCHW', 'LOW', 'BLK', 'QCOM', 'ANET', 'TXN', 'HON', 'UBER', 'PFE',
    'WELL', 'UNP', 'ACN', 'AVGO', 'BKNG', 'ETN', 'DHR', 'SYK', 'PLD', 'COF',
    'SPGI', 'PH', 'COP', 'BMY', 'PGR', 'CB', 'MDT', 'TMUS', 'VRTX', 'PANW',
    'BSX', 'CMCSA', 'CME', 'MCK', 'ADBE', 'LMT', 'INTU', 'CRWD', 'GLW', 'CVS',
    # 101-150
    'SO', 'BX', 'SBUX', 'MO', 'DUK', 'NEM', 'STX', 'PNC', 'MMC', 'WM',
    'CEG', 'MMM', 'GD', 'USB', 'UPS', 'ICE', 'TT', 'ADP', 'MAR', 'AMT',
    'SHW', 'RCL', 'HCA', 'EQIX', 'BK', 'ECL', 'NOC', 'SNPS', 'REGN', 'ITW',
    'ORLY', 'CDNS', 'EMR', 'CSX', 'NKE', 'ELV', 'JCI', 'MDLZ', 'WDC', 'WMB',
    'TDG', 'FDX', 'CI', 'CMI', 'NSC', 'HLT', 'KKR', 'MCO', 'FCX', 'RSG'
]


def get_market_cap_rank(symbol: str) -> int:
    """Get market cap rank from pre-built list. Returns 999 for unknown symbols."""
    try:
        return TOP_SP500_MARKET_CAP_ORDER.index(symbol) + 1
    except ValueError:
        return 999  # Not in top 150


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
download_transcripts = st.sidebar.checkbox(
    "🎙️ Earnings Call Transcripts",
    value=False,
    help="Download earnings call transcripts, investor call transcripts"
)

# Reload mode — shown indented under Investor Transcripts
reload_mode = st.sidebar.radio(
    "Reload",
    options=["Skip existing", "Re-download existing"],
    index=0,
    help="Skip existing: skip companies/years already in the database (default). "
         "Re-download existing: force re-download even when records already exist.",
)
force_reload = reload_mode == "Re-download existing"

# Build content_types list based on selections
content_types = []
if download_sustainability:
    content_types.append(1)
if download_annual:
    content_types.append(2)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏢 Select Companies", "📅 Select Years", "📥 Download", "📁 Files", "📊 Today's Downloads"])

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
                ["Custom Selection", "All Companies", "Top 10 (by Market Cap)", "Top 50 (by Market Cap)",
                    "Top 100 (by Market Cap)", "Tech Companies", "Energy Companies"]
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

        # Always sort by market cap rank for display
        filtered_df = filtered_df.sort_values('market_cap_rank')

        st.markdown(
            f"**Showing {len(filtered_df)} companies** (sorted by market cap)")

        # Company selection with checkboxes
        col1, col2 = st.columns([3, 1])

        with col1:
            # Multi-select for companies - include rank number
            company_options = filtered_df.apply(
                lambda row: f"#{int(row['market_cap_rank'])} {row['Symbol']} - {row['Company']}", axis=1
            ).tolist()

            selected = st.multiselect(
                "Select Companies to Download",
                options=company_options,
                default=st.session_state.selected_companies if st.session_state.selected_companies else [],
                help="Select one or more companies (ranked by market cap)"
            )
            st.session_state.selected_companies = selected

        with col2:
            st.markdown("### Quick Actions")
            if st.button("Select All Shown"):
                st.session_state.selected_companies = company_options
                st.rerun()

            if st.button("Clear Selection"):
                st.session_state.selected_companies = []
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

        if year_selection_mode == "Specific Year Range":
            start_year = st.slider(
                "Start Year",
                min_value=2000,
                max_value=current_year,
                value=2012,
                help="Download reports from this year onwards"
            )

            end_year = st.slider(
                "End Year",
                min_value=start_year,
                max_value=current_year,
                value=current_year,
                help="Download reports up to this year"
            )

            years_to_download = list(range(start_year, end_year + 1))

        elif year_selection_mode == "Single Year":
            single_year = st.selectbox(
                "Select Year",
                options=list(range(current_year, 1999, -1)),
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

    if st.session_state.is_downloading:
        st.info("⏳ Download in progress — please wait...")
    elif can_download:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Ready to download!** Click the button below to start downloading sustainability reports 
            for the selected companies.
            """)
        with col2:
            estimated_time = company_count * delay_seconds * 10  # rough estimate
            st.caption(f"⏱️ Estimated time: ~{estimated_time/60:.1f} minutes")

    # Button click only sets state and triggers a rerun so the button
    # renders as disabled BEFORE the (blocking) download loop starts.
    if st.button("🚀 Start Download", type="primary", use_container_width=True,
                 disabled=not can_download or st.session_state.is_downloading):
        st.session_state.is_downloading = True
        st.session_state.download_complete = False
        st.rerun()

    # Run the download on the render where is_downloading=True and the
    # button is already shown as disabled.
    if st.session_state.is_downloading and not st.session_state.download_complete:
        download_banner = st.empty()  # placeholder cleared when done

        # Get year filter from session state
        years_filter = st.session_state.get('years_to_download')

        # Initialize downloader with year filter and content types
        downloader = SustainabilityReportDownloader(
            download_dir=output_dir,
            delay_seconds=delay_seconds,
            current_sector_id=current_sector_id,
            use_storage=use_storage,
            year_filter=years_filter,
            content_types=content_types,
            force_reload=force_reload
        )

        if years_filter:
            st.info(f"📅 Filtering downloads to years: {years_filter}")

        # Show content types being downloaded
        type_names = {1: 'Sustainability/ESG',
                      2: 'Annual/10K', 3: 'Other', 4: 'Earnings Transcripts'}
        selected_types = [type_names.get(
            ct, f'Type {ct}') for ct in content_types]
        st.info(f"📄 Downloading: {', '.join(selected_types)}")

        # Create progress containers
        st.subheader("📊 Progress")

        # Year progress (show when years are filtered, or track years found for "all years")
        year_progress_label = st.empty()
        if years_filter:
            year_progress_bar = st.progress(0)
        else:
            year_progress_bar = None  # Will show "Years found" metric instead

        # Company progress
        company_progress_label = st.empty()
        company_progress_bar = st.progress(0)
        status_text = st.empty()

        col1, col2, col3, col4 = st.columns(4)
        metric_processed = col1.empty()
        metric_found = col2.empty()
        metric_downloaded = col3.empty()
        metric_failed = col4.empty()

        # Get selected companies data
        if st.session_state.companies_df is not None:
            df = st.session_state.companies_df
            # Extract symbol from format: "#1 AAPL - Apple Inc."
            selected_symbols = []
            for c in st.session_state.selected_companies:
                parts = c.split(' - ')[0]  # "#1 AAPL"
                symbol = parts.split(' ')[-1]  # "AAPL"
                selected_symbols.append(symbol)
            companies_to_process = df[df['Symbol'].isin(selected_symbols)]
        else:
            st.error("Please load company list first")
            st.stop()

        total_companies = len(companies_to_process)
        total_years = len(years_filter) if years_filter else 1
        results = []

        status_text.info(
            f"Processing {total_companies} companies across {total_years} year(s)...")

        # OPTIMIZED: Process each company ONCE and filter for ALL years at once
        # This avoids re-crawling the same website for each year
        if years_filter:
            years_filter_sorted = sorted(years_filter)
            year_progress_label.markdown(
                f"**📅 Years:** {years_filter_sorted[0]}-{years_filter_sorted[-1]} "
                f"({total_years} years) — 0/{total_years} complete")
            year_progress_bar.progress(0)

            # Create single downloader with ALL years and content types
            multi_year_downloader = SustainabilityReportDownloader(
                download_dir=output_dir,
                delay_seconds=delay_seconds,
                current_sector_id=current_sector_id,
                use_storage=use_storage,
                year_filter=years_filter,  # ALL years at once
                content_types=content_types,
                force_reload=force_reload
            )

            years_seen: set = set()  # years that have appeared in at least one download

            for company_idx, (_, row) in enumerate(companies_to_process.iterrows()):
                symbol = row['Symbol']
                company = row['Company']

                # Get website
                website = multi_year_downloader.get_company_website(
                    symbol, company)

                # Update company progress
                company_progress_bar.progress(
                    (company_idx + 1) / total_companies)
                company_progress_label.markdown(
                    f"**🏢 Company Progress:** {company_idx + 1}/{total_companies}")
                status_text.info(
                    f"Processing {company_idx + 1}/{total_companies}: {company} ({symbol}) "
                    f"— years {years_filter_sorted[0]}-{years_filter_sorted[-1]}")

                # Process company ONCE for ALL years
                result = multi_year_downloader.process_company(
                    symbol, company, website)
                results.append(result)

                # ── Year progress: scan downloaded reports for newly covered years ──
                for report in multi_year_downloader.downloaded_reports:
                    fp_parent = Path(report.get('filepath', '')).parent.name
                    if re.fullmatch(r'20\d{2}', fp_parent):
                        years_seen.add(int(fp_parent))

                # Count how many of the requested years are now covered
                years_covered = [y for y in years_filter if y in years_seen]
                year_pct = len(years_covered) / \
                    total_years if total_years > 0 else 1.0
                year_progress_bar.progress(min(year_pct, 1.0))
                if years_covered:
                    year_progress_label.markdown(
                        f"**📅 Years:** {years_filter_sorted[0]}-{years_filter_sorted[-1]} "
                        f"— {len(years_covered)}/{total_years} complete "
                        f"({', '.join(str(y) for y in sorted(years_covered))})")
                else:
                    year_progress_label.markdown(
                        f"**📅 Years:** {years_filter_sorted[0]}-{years_filter_sorted[-1]} "
                        f"({total_years} years) — searching...")

                # Update metrics
                total_downloaded = len(
                    multi_year_downloader.downloaded_reports)
                total_failed = len(multi_year_downloader.failed_downloads)
                metric_processed.metric(
                    "Processed", f"{company_idx + 1}/{total_companies}")
                metric_found.metric(
                    "Years covered", f"{len(years_covered)}/{total_years}")
                metric_downloaded.metric("Downloaded", total_downloaded)
                metric_failed.metric("Failed", total_failed)

            # Final year progress
            year_progress_bar.progress(1.0)
            years_covered_final = sorted(
                y for y in years_filter if y in years_seen)
            missing_years = sorted(
                y for y in years_filter if y not in years_seen)
            summary = f"{len(years_covered_final)}/{total_years} years with downloads"
            if missing_years:
                summary += f" (no files found for: {', '.join(str(y) for y in missing_years)})"
            year_progress_label.markdown(
                f"**📅 Years:** {years_filter_sorted[0]}-{years_filter_sorted[-1]} "
                f"— ✅ {summary}")

            # Close downloader
            multi_year_downloader.close()

        else:
            # Original flow for all years (no filter) - track years found
            years_found = set()
            for idx, row in companies_to_process.iterrows():
                symbol = row['Symbol']
                company = row['Company']

                # Get website
                website = downloader.get_company_website(symbol, company)

                # Update progress
                progress = (len(results) + 1) / total_companies
                company_progress_bar.progress(progress)
                company_progress_label.markdown(
                    f"**🏢 Company Progress:** {len(results) + 1}/{total_companies}")
                status_text.info(
                    f"Processing {len(results) + 1}/{total_companies}: {company} ({symbol})")

                # Process company (year filtering happens automatically in downloader)
                result = downloader.process_company(symbol, company, website)
                results.append(result)

                # Track years found from downloaded reports
                for report in downloader.downloaded_reports:
                    if 'year' in report:
                        years_found.add(report['year'])

                # Update year label with years found so far
                if years_found:
                    sorted_years = sorted(years_found)
                    year_progress_label.markdown(
                        f"**📅 Years Found:** {len(years_found)} years ({min(sorted_years)}-{max(sorted_years)})")
                else:
                    year_progress_label.markdown(
                        "**📅 Years Found:** Searching...")

                # Update metrics
                metric_processed.metric(
                    "Processed", f"{len(results)}/{total_companies}")
                metric_found.metric("Reports Found", sum(
                    r.get('reports_found', 0) for r in results))
                metric_downloaded.metric(
                    "Downloaded", len(downloader.downloaded_reports))
                metric_failed.metric("Failed", len(
                    downloader.failed_downloads))

            # Final year summary
            if years_found:
                sorted_years = sorted(years_found)
                year_progress_label.markdown(
                    f"**📅 Years Found:** {len(years_found)} years ({min(sorted_years)}-{max(sorted_years)}) - ✅ Complete")

        # Complete
        company_progress_bar.progress(1.0)
        company_progress_label.markdown(
            f"**🏢 Company Progress:** {total_companies}/{total_companies} - ✅ Complete")
        status_text.success("✅ Download complete!")

        st.session_state.is_downloading = False
        st.session_state.download_complete = True
        download_banner.empty()

        # Save results
        downloader._save_metadata()
        st.session_state.download_results = pd.DataFrame(results)

        # Display summary
        st.subheader("📊 Download Summary")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Companies Processed", len(results))
        with col2:
            st.metric("Reports Found", sum(r.get('reports_found', 0)
                      for r in results))
        with col3:
            st.metric("Reports Downloaded", len(downloader.downloaded_reports))
        with col4:
            st.metric("Failed", len(downloader.failed_downloads))

        # Display results table
        st.subheader("📋 Detailed Results")
        st.dataframe(st.session_state.download_results,
                     use_container_width=True)

        # Download results as CSV
        csv = st.session_state.download_results.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv,
            file_name="download_results.csv",
            mime="text/csv"
        )

        # Close downloader
        downloader.close()

    # Completion banner (persists across re-runs until a new download starts)
    if st.session_state.download_complete and not st.session_state.is_downloading:
        st.success(
            "✅ **Download complete!** All selected companies have been processed. "
            "Check the results table above or switch to the 📁 Files tab to view downloaded reports."
        )

    # Show previous results if available
    elif st.session_state.download_results is not None:
        st.subheader("📋 Previous Download Results")
        st.dataframe(st.session_state.download_results,
                     use_container_width=True)

with tab4:
    st.header("Downloaded Files")

    # Function to classify report type based on filename
    def classify_report_type(filename: str) -> str:
        """Classify a report as Sustainability, Annual/10K, or Other based on filename."""
        filename_lower = filename.lower()

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

        # Check sustainability first (prioritize if both match)
        for pattern in sustainability_patterns:
            if pattern in filename_lower:
                return "🌱 Sustainability/ESG"

        # Check annual/10K
        for pattern in annual_patterns:
            if pattern in filename_lower:
                return "📊 Annual/10K"

        # Default to Other
        return "📄 Other"

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
                for pdf_file in folder.glob("*.pdf"):
                    # Extract company symbol from filename (format: SYMBOL_filename.pdf or SYMBOL-filename.pdf)
                    filename = pdf_file.name
                    symbol = filename.split('_')[0].split('-')[0].upper()
                    report_type = classify_report_type(filename)
                    all_files.append({
                        'year': folder.name,
                        'symbol': symbol,
                        'filename': filename,
                        'path': pdf_file,
                        'size_mb': pdf_file.stat().st_size / (1024 * 1024),
                        'report_type': report_type
                    })

            # Get unique symbols, years, and report types
            unique_symbols = sorted(set(f['symbol'] for f in all_files))
            unique_years = sorted(set(f['year']
                                  for f in all_files), reverse=True)
            unique_types = sorted(set(f['report_type'] for f in all_files))

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
                # Company filter - use selected companies from tab1 as default if available
                # selected_companies format: "#1 AAPL - Apple Inc."
                selected_companies_symbols = []
                if st.session_state.selected_companies:
                    for c in st.session_state.selected_companies:
                        # Extract symbol from format: "#1 AAPL - Company Name"
                        parts = c.split(' - ')[0]  # "#1 AAPL"
                        symbol = parts.split(' ')[-1]  # "AAPL"
                        if symbol in unique_symbols:
                            selected_companies_symbols.append(symbol)

                filter_by_company = st.checkbox(
                    "🏢 Filter by Selected Companies",
                    value=len(selected_companies_symbols) > 0,
                    help="Show only files for companies selected in the 'Select Companies' tab"
                )

                if filter_by_company:
                    if selected_companies_symbols:
                        company_filter = st.multiselect(
                            "Companies",
                            options=unique_symbols,
                            default=selected_companies_symbols,
                            help="Filter files by company symbol"
                        )
                    else:
                        company_filter = st.multiselect(
                            "Companies",
                            options=unique_symbols,
                            default=[],
                            help="Select companies to filter (or select companies in the 'Select Companies' tab first)"
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
                    type_filter = st.multiselect(
                        "Report Types",
                        options=unique_types,
                        default=[
                            "🌱 Sustainability/ESG"] if "🌱 Sustainability/ESG" in unique_types else unique_types,
                        help="Filter by report type"
                    )
                else:
                    type_filter = unique_types  # Show all

            # Apply filters
            filtered_files = [
                f for f in all_files
                if f['symbol'] in company_filter and f['year'] in year_filter and f['report_type'] in type_filter
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
