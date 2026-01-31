
import numpy as np
import pandas as pd
from Services.DataSourceProcessor import DataSourceProcessor
import streamlit as st
import os
import datetime as dt
import ast
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


class StartUpClass:

    def __init__(self) -> None:
        self.unprocessed_document_list = []

    def load_unprocessed_data_list(self):
        """Load and display unprocessed documents with summary metrics"""
        with st.spinner('Loading unprocessed documents...'):
            self.unprocessed_document_list = (DataSourceProcessor(
                self.database_context)).get_unprocessed_source_document_list()

            if len(self.unprocessed_document_list) == 0:
                st.success(
                    "✅ All documents have been processed! No pending items.")
                return

            # Display summary metrics
            st.markdown("### 📊 Data Summary")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Pending Documents", len(
                    self.unprocessed_document_list))

            with col2:
                years = list(
                    set([x.year for x in self.unprocessed_document_list]))
                st.metric("Years Covered", len(years))

            with col3:
                companies = list(
                    set([x.company_name for x in self.unprocessed_document_list]))
                st.metric("Unique Companies", len(companies))

            # Display detailed table
            st.markdown("### 📋 Unprocessed Documents")
            df = pd.DataFrame([x.as_dict()
                              for x in self.unprocessed_document_list])
            st.dataframe(data=df, use_container_width=True, height=400)

    def extract_source_data(self):
        """Extract and process source data with progress tracking"""
        import time

        st.markdown("### 🚀 Processing Documents")

        # Get initial count
        processor = DataSourceProcessor(self.database_context)
        document_list = processor.datasourceDBMgr.get_unprocessed_content_list()

        if len(document_list) == 0:
            st.warning("No unprocessed documents found.")
            return

        total_documents = len(document_list)

        # Show initial metrics
        st.info(f"📄 Starting processing of {total_documents} document(s)...")

        # Create progress indicator
        with st.spinner('Processing documents...'):
            start_time = time.time()

            # Call the actual processing method
            result = processor.download_content_from_source_and_process_text()

            elapsed_time = time.time() - start_time

        # Show completion metrics
        st.markdown("### ✅ Processing Complete!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", total_documents)
        with col2:
            st.metric("⏱️ Time Elapsed", f"{int(elapsed_time)}s")
        with col3:
            avg_time = elapsed_time / total_documents if total_documents > 0 else 0
            st.metric("⚡ Avg Time/Doc", f"{avg_time:.1f}s")

        st.success(
            f"🎉 Successfully processed {total_documents} document(s) in {int(elapsed_time)} seconds!")
        st.balloons()

    def run_online_Mode(self):
        database_context = st.radio(
            "Database Context", ["Development", "Test"], index=0)
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"

        if st.button('Load Unprocessed Source List'):
            self.load_unprocessed_data_list()

        if st.button('Extract Source Data'):
            self.extract_source_data()


# (DataSourceProcessor()).get_unprocessed_source_document_list()

l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()
