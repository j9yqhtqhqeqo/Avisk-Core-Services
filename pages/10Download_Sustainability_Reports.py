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

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))


# Page configuration
st.set_page_config(
    page_title="Sustainability Report Downloader",
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
st.title("📊 Sustainability Report Downloader")
st.markdown("Download sustainability/ESG reports from S&P 500 company websites")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

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

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📋 Company List Source")

        upload_option = st.radio(
            "Select company list source:",
            ["Fetch S&P 500 from Wikipedia", "Upload Custom CSV"],
            help="Wikipedia provides the latest S&P 500 list"
        )

    with col2:
        if st.button("🔄 Load Company List", type="primary"):
            with st.spinner("Loading companies..."):
                try:
                    downloader = SustainabilityReportDownloader(
                        download_dir=output_dir,
                        use_storage=use_storage
                    )
                    st.session_state.companies_df = downloader.load_sp500_companies()
                    st.success(
                        f"✅ Loaded {len(st.session_state.companies_df)} companies")
                except Exception as e:
                    st.error(f"Failed to load companies: {e}")

    if upload_option == "Upload Custom CSV":
        uploaded_file = st.file_uploader(
            "Upload CSV with company data",
            type=['csv'],
            help="CSV should have columns: Symbol, Company"
        )

        if uploaded_file:
            st.session_state.companies_df = pd.read_csv(uploaded_file)
            st.success(
                f"✅ Loaded {len(st.session_state.companies_df)} companies from CSV")

    # Display and select companies
    if st.session_state.companies_df is not None:
        df = st.session_state.companies_df

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
                ["Custom Selection", "All Companies", "Top 10", "Top 50",
                    "Top 100", "Tech Companies", "Energy Companies"]
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

        # Apply quick select
        if quick_select == "Top 10":
            filtered_df = filtered_df.head(10)
        elif quick_select == "Top 50":
            filtered_df = filtered_df.head(50)
        elif quick_select == "Top 100":
            filtered_df = filtered_df.head(100)
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

        st.markdown(f"**Showing {len(filtered_df)} companies**")

        # Company selection with checkboxes
        col1, col2 = st.columns([3, 1])

        with col1:
            # Multi-select for companies
            company_options = filtered_df.apply(
                lambda row: f"{row['Symbol']} - {row['Company']}", axis=1
            ).tolist()

            selected = st.multiselect(
                "Select Companies to Download",
                options=company_options,
                default=st.session_state.selected_companies if st.session_state.selected_companies else [],
                help="Select one or more companies"
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
                selected_symbols = [c.split(' - ')[0]
                                    for c in st.session_state.selected_companies]
                selected_df = df[df['Symbol'].isin(selected_symbols)]
                st.dataframe(
                    selected_df[['Symbol', 'Company']], use_container_width=True)

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

    col1, col2, col3 = st.columns(3)

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

        # Initialize downloader with year filter
        downloader = SustainabilityReportDownloader(
            download_dir=output_dir,
            delay_seconds=delay_seconds,
            current_sector_id=current_sector_id,
            use_storage=use_storage,
            year_filter=years_filter
        )

        if years_filter:
            st.info(f"📅 Filtering downloads to years: {years_filter}")

        # Create progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()

        col1, col2, col3, col4 = st.columns(4)
        metric_processed = col1.empty()
        metric_found = col2.empty()
        metric_downloaded = col3.empty()
        metric_failed = col4.empty()

        # Get selected companies data
        if st.session_state.companies_df is not None:
            df = st.session_state.companies_df
            selected_symbols = [c.split(' - ')[0]
                                for c in st.session_state.selected_companies]
            companies_to_process = df[df['Symbol'].isin(selected_symbols)]
        else:
            st.error("Please load company list first")
            st.stop()

        total = len(companies_to_process)
        results = []

        status_text.info(f"Processing {total} companies...")

        for idx, row in companies_to_process.iterrows():
            symbol = row['Symbol']
            company = row['Company']

            # Get website
            website = downloader.get_company_website(symbol, company)

            # Update progress
            progress = (len(results) + 1) / total
            progress_bar.progress(progress)
            status_text.info(
                f"Processing {len(results) + 1}/{total}: {company} ({symbol})")

            # Process company (year filtering happens automatically in downloader)
            result = downloader.process_company(symbol, company, website)
            results.append(result)

            # Update metrics
            metric_processed.metric("Processed", f"{len(results)}/{total}")
            metric_found.metric("Reports Found", sum(
                r.get('reports_found', 0) for r in results))
            metric_downloaded.metric(
                "Downloaded", len(downloader.downloaded_reports))
            metric_failed.metric("Failed", len(downloader.failed_downloads))

        # Complete
        progress_bar.progress(1.0)
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
        st.subheader("📁 Yearly Folders")

        year_folders = sorted([f for f in output_path.iterdir() if f.is_dir() and f.name.isdigit()],
                              key=lambda x: x.name, reverse=True)

        if year_folders:
            # Summary metrics
            total_files = sum(len(list(f.glob("*.pdf"))) for f in year_folders)
            st.success(
                f"Found **{total_files}** reports across **{len(year_folders)}** years")

            # Year filter
            selected_years = st.multiselect(
                "Filter by Year",
                options=[f.name for f in year_folders],
                # Show recent 3 years by default
                default=[f.name for f in year_folders[:3]]
            )

            # Display by year
            for folder in year_folders:
                if folder.name not in selected_years:
                    continue

                pdf_files = list(folder.glob("*.pdf"))

                with st.expander(f"📅 {folder.name} ({len(pdf_files)} reports)", expanded=False):
                    if pdf_files:
                        for file in sorted(pdf_files):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.text(
                                    file.name[:50] + "..." if len(file.name) > 50 else file.name)
                            with col2:
                                size_mb = file.stat().st_size / (1024 * 1024)
                                st.text(f"{size_mb:.2f} MB")
                            with col3:
                                with open(file, 'rb') as f:
                                    st.download_button(
                                        label="⬇️",
                                        data=f,
                                        file_name=file.name,
                                        mime="application/pdf",
                                        key=str(file)
                                    )
                    else:
                        st.caption("No PDF files in this folder")
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
