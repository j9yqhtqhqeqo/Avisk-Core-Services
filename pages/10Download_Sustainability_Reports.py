"""
Sustainability Report Downloader UI

Streamlit interface for downloading sustainability reports from S&P 500 companies.
"""

from Services.SustainabilityReportDownloader import SustainabilityReportDownloader
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
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

# Title
st.title("📊 Document Downloader")
st.markdown("Download sustainability reports, annual reports/10K filings, and earnings transcripts from S&P 500 companies")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

# Content Type Selection
st.sidebar.subheader("📄 Content Types to Download")
download_sustainability = st.sidebar.checkbox(
    "🌱 Sustainability/ESG Reports",
    value=True,
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
    content_types = [1]  # Default to sustainability

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
tab1, tab2, tab3, tab4 = st.tabs(
    ["🏢 Select Companies", "📅 Select Years", "📥 Download", "📁 Files"])

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
                value=current_year - 5,
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

    for warning in warnings:
        st.warning(warning)

    # Download button
    st.markdown("---")

    if can_download:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("""
            **Ready to download!** Click the button below to start downloading sustainability reports 
            for the selected companies.
            """)

        with col2:
            estimated_time = company_count * delay_seconds * 10  # rough estimate
            st.caption(f"⏱️ Estimated time: ~{estimated_time/60:.1f} minutes")

    if st.button("🚀 Start Download", type="primary", use_container_width=True, disabled=not can_download):

        # Get year filter from session state
        years_filter = st.session_state.get('years_to_download')

        # Initialize downloader with year filter and content types
        downloader = SustainabilityReportDownloader(
            download_dir=output_dir,
            delay_seconds=delay_seconds,
            current_sector_id=current_sector_id,
            use_storage=use_storage,
            year_filter=years_filter,
            content_types=content_types
        )

        if years_filter:
            st.info(f"📅 Filtering downloads to years: {years_filter}")

        # Show content types being downloaded
        type_names = {1: 'Sustainability/ESG',
                      2: 'Annual/10K', 3: 'Other', 4: 'Earnings Transcripts'}
        selected_types = [type_names.get(ct, f'Type {ct}') for ct in content_types]
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
            year_progress_label.markdown(
                f"**📅 Years:** {min(years_filter)}-{max(years_filter)} ({total_years} years)")

            # Create single downloader with ALL years and content types
            multi_year_downloader = SustainabilityReportDownloader(
                download_dir=output_dir,
                delay_seconds=delay_seconds,
                current_sector_id=current_sector_id,
                use_storage=use_storage,
                year_filter=years_filter,  # ALL years at once
                content_types=content_types
            )

            for company_idx, (_, row) in enumerate(companies_to_process.iterrows()):
                symbol = row['Symbol']
                company = row['Company']

                # Get website
                website = multi_year_downloader.get_company_website(
                    symbol, company)

                # Update progress
                progress = (company_idx + 1) / total_companies
                company_progress_bar.progress(progress)
                company_progress_label.markdown(
                    f"**🏢 Company Progress:** {company_idx + 1}/{total_companies}")
                status_text.info(
                    f"Processing {company_idx + 1}/{total_companies}: {company} ({symbol}) - Searching for years {min(years_filter)}-{max(years_filter)}")

                # Process company ONCE for ALL years
                result = multi_year_downloader.process_company(
                    symbol, company, website)
                results.append(result)

                # Update metrics
                total_downloaded = len(
                    multi_year_downloader.downloaded_reports)
                total_failed = len(multi_year_downloader.failed_downloads)
                metric_processed.metric(
                    "Processed", f"{company_idx + 1}/{total_companies}")
                metric_found.metric(
                    "Years", f"{min(years_filter)}-{max(years_filter)}")
                metric_downloaded.metric("Downloaded", total_downloaded)
                metric_failed.metric("Failed", total_failed)

            # Collect all results
            for r in multi_year_downloader.downloaded_reports:
                if r not in results:
                    pass  # Results already tracked via process_company

            # Final progress
            year_progress_bar.progress(1.0)
            year_progress_label.markdown(
                f"**📅 Years:** {min(years_filter)}-{max(years_filter)} ({total_years} years) - ✅ Complete")

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

                # Group by year for display
                from collections import defaultdict
                files_by_year = defaultdict(list)
                for f in filtered_files:
                    files_by_year[f['year']].append(f)

                # Display by year
                for year in sorted(files_by_year.keys(), reverse=True):
                    year_files = files_by_year[year]

                    with st.expander(f"📅 {year} ({len(year_files)} reports)", expanded=len(files_by_year) <= 3):
                        # Group by company within year
                        files_by_company = defaultdict(list)
                        for f in year_files:
                            files_by_company[f['symbol']].append(f)

                        for symbol in sorted(files_by_company.keys()):
                            company_files = files_by_company[symbol]
                            st.markdown(
                                f"**{symbol}** ({len(company_files)} file{'s' if len(company_files) > 1 else ''})")

                            for file_info in sorted(company_files, key=lambda x: x['filename']):
                                col1, col2, col3, col4 = st.columns(
                                    [3, 1, 1, 1])
                                with col1:
                                    display_name = file_info['filename']
                                    st.text(
                                        display_name[:55] + "..." if len(display_name) > 55 else display_name)
                                with col2:
                                    # Show report type badge
                                    st.caption(file_info['report_type'])
                                with col3:
                                    st.text(f"{file_info['size_mb']:.2f} MB")
                                with col4:
                                    with open(file_info['path'], 'rb') as f:
                                        st.download_button(
                                            label="⬇️",
                                            data=f,
                                            file_name=file_info['filename'],
                                            mime="application/pdf",
                                            key=str(file_info['path'])
                                        )
                            st.markdown("")  # Add spacing between companies
            else:
                st.warning(
                    "No files match the selected filters. Try adjusting your company or year selection.")
        else:
            st.info(
                "No yearly folders found yet. Download reports to see them organized by year.")
    else:
        st.warning(
            f"Output directory does not exist yet. Start a download to create it.")

# Footer
st.markdown("---")
st.markdown("""
**📌 Usage Tips:**
- Select companies in the **Select Companies** tab using filters and search
- Optionally filter by year range in the **Select Years** tab
- Start the download in the **Download** tab
- View organized files in the **Files** tab

**Note:** This tool searches company websites for publicly available sustainability reports.
Please respect website terms of service and rate limits.
""")
