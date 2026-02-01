"""
Sustainability Report Downloader UI

Streamlit interface for downloading sustainability reports from S&P 500 companies.
"""

from Services.SustainabilityReportDownloader import SustainabilityReportDownloader
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))


# Page configuration
st.set_page_config(
    page_title="Sustainability Report Downloader",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Sustainability Report Downloader")
st.markdown("Download sustainability/ESG reports from S&P 500 company websites")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

output_dir = st.sidebar.text_input(
    "Output Directory",
    value="./sustainability_reports",
    help="Directory where reports will be saved"
)

delay_seconds = st.sidebar.slider(
    "Delay Between Requests (seconds)",
    min_value=0.5,
    max_value=5.0,
    value=2.0,
    step=0.5,
    help="Time to wait between requests to be respectful to servers"
)

limit_companies = st.sidebar.checkbox(
    "Test Mode (Limit Companies)",
    value=False,
    help="Enable to test with a limited number of companies"
)

if limit_companies:
    num_companies = st.sidebar.number_input(
        "Number of Companies",
        min_value=1,
        max_value=100,
        value=5,
        help="Number of companies to process in test mode"
    )
else:
    num_companies = None

# Main content
tab1, tab2, tab3 = st.tabs(["📥 Download Reports", "📊 Progress", "📁 Files"])

with tab1:
    st.header("Download Sustainability Reports")

    st.markdown("""
    This tool will:
    1. Load the S&P 500 company list
    2. Search each company's website for sustainability/ESG reports
    3. Download PDF reports automatically
    4. Save metadata and track progress
    """)

    # Option to upload custom company list
    st.subheader("Company List")

    upload_option = st.radio(
        "Select company list source:",
        ["Fetch from Wikipedia", "Upload CSV file"],
        help="Wikipedia provides the latest S&P 500 list"
    )

    companies_df = None
    csv_path = None

    if upload_option == "Upload CSV file":
        uploaded_file = st.file_uploader(
            "Upload CSV with company data",
            type=['csv'],
            help="CSV should have columns: Symbol, Company, Website"
        )

        if uploaded_file:
            companies_df = pd.read_csv(uploaded_file)
            st.success(f"Loaded {len(companies_df)} companies")
            st.dataframe(companies_df.head(10))

    # Start download button
    if st.button("🚀 Start Download", type="primary", use_container_width=True):

        # Initialize downloader
        downloader = SustainabilityReportDownloader(
            download_dir=output_dir,
            delay_seconds=delay_seconds
        )

        # Create progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

        with st.spinner("Loading company list..."):
            if companies_df is None:
                companies_df = downloader.load_sp500_companies(csv_path)

            st.success(f"Loaded {len(companies_df)} companies")

        # Process companies
        if limit_companies:
            companies_to_process = companies_df.head(num_companies)
        else:
            companies_to_process = companies_df

        total = len(companies_to_process)
        results = []

        status_text.info(f"Processing {total} companies...")

        for idx, row in companies_to_process.iterrows():
            symbol = row['Symbol']
            company = row['Company']
            website = row.get('Website', row.get('website', None))

            # Update progress
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.info(
                f"Processing {idx + 1}/{total}: {company} ({symbol})")

            # Process company
            result = downloader.process_company(symbol, company, website)
            results.append(result)

            # Update metrics
            with metrics_col1:
                st.metric("Processed", f"{idx + 1}/{total}")
            with metrics_col2:
                st.metric("Reports Found", sum(
                    r['reports_found'] for r in results))
            with metrics_col3:
                st.metric("Downloaded", len(downloader.downloaded_reports))

        # Complete
        progress_bar.progress(1.0)
        status_text.success("✅ Download complete!")

        # Save results
        downloader._save_metadata()
        results_df = pd.DataFrame(results)

        # Display summary
        st.subheader("📊 Summary")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Companies Processed", len(results_df))
        with col2:
            st.metric("Reports Found", results_df['reports_found'].sum())
        with col3:
            st.metric("Reports Downloaded",
                      results_df['reports_downloaded'].sum())
        with col4:
            st.metric("Failed", len(downloader.failed_downloads))

        # Display results table
        st.subheader("📋 Detailed Results")
        st.dataframe(results_df, use_container_width=True)

        # Download results as CSV
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv,
            file_name="download_results.csv",
            mime="text/csv"
        )

with tab2:
    st.header("Download Progress")

    progress_file = Path(output_dir) / 'download_progress.csv'
    downloads_file = Path(output_dir) / 'downloaded_reports.csv'
    failures_file = Path(output_dir) / 'failed_downloads.csv'

    if progress_file.exists():
        progress_df = pd.read_csv(progress_file)

        st.subheader("📊 Overall Progress")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Companies", len(progress_df))
        with col2:
            completed = len(progress_df[progress_df['status'] == 'completed'])
            st.metric("Completed", completed)
        with col3:
            failed = len(progress_df[progress_df['status'] == 'error'])
            st.metric("Failed", failed)

        st.dataframe(progress_df, use_container_width=True)
    else:
        st.info("No progress data available. Start a download to see progress.")

    if downloads_file.exists():
        st.subheader("✅ Downloaded Reports")
        downloads_df = pd.read_csv(downloads_file)
        st.dataframe(downloads_df, use_container_width=True)

    if failures_file.exists():
        st.subheader("❌ Failed Downloads")
        failures_df = pd.read_csv(failures_file)
        st.dataframe(failures_df, use_container_width=True)

with tab3:
    st.header("Downloaded Files")

    output_path = Path(output_dir)

    if output_path.exists():
        # List all downloaded PDFs
        pdf_files = list(output_path.glob("**/*.pdf"))

        if pdf_files:
            st.success(f"Found {len(pdf_files)} downloaded reports")

            # Group by company
            companies = {}
            for pdf in pdf_files:
                company_folder = pdf.parent.name
                if company_folder not in companies:
                    companies[company_folder] = []
                companies[company_folder].append(pdf)

            # Display by company
            for company, files in sorted(companies.items()):
                with st.expander(f"📁 {company} ({len(files)} reports)"):
                    for file in files:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(file.name)
                        with col2:
                            size_mb = file.stat().st_size / (1024 * 1024)
                            st.text(f"{size_mb:.2f} MB")
                        with col3:
                            with open(file, 'rb') as f:
                                st.download_button(
                                    label="Download",
                                    data=f,
                                    file_name=file.name,
                                    mime="application/pdf",
                                    key=str(file)
                                )
        else:
            st.info(
                "No reports downloaded yet. Use the 'Download Reports' tab to start.")
    else:
        st.warning(f"Output directory '{output_dir}' does not exist yet.")

# Footer
st.markdown("---")
st.markdown("""
**Note:** This tool searches company websites for publicly available sustainability reports.
Please respect website terms of service and rate limits.
""")
