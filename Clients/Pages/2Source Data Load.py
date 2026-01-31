
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import ast
import datetime as dt
import os
import time

import streamlit as st
from Services.DataSourceProcessor import DataSourceProcessor
import pandas as pd
import numpy as np


class StartUpClass:

    def __init__(self) -> None:
        self.unprocessed_document_list = []
        # Initialize session state for progress tracking
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = None
        if 'current_document' not in st.session_state:
            st.session_state.current_document = None
        if 'total_documents' not in st.session_state:
            st.session_state.total_documents = 0
        if 'processed_count' not in st.session_state:
            st.session_state.processed_count = 0
        if 'failed_count' not in st.session_state:
            st.session_state.failed_count = 0
        if 'processing_logs' not in st.session_state:
            st.session_state.processing_logs = []
    
    def load_unprocessed_data_list(self):
        """Load and display unprocessed documents"""
        with st.spinner('Loading unprocessed documents...'):
            self.unprocessed_document_list = (DataSourceProcessor(self.database_context)).get_unprocessed_source_document_list()
            
            if len(self.unprocessed_document_list) == 0:
                st.success("✅ All documents have been processed! No pending items.")
                return
            
            st.session_state.total_documents = len(self.unprocessed_document_list)
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pending", len(self.unprocessed_document_list))
            with col2:
                years = list(set([x.year for x in self.unprocessed_document_list]))
                st.metric("Years", len(years))
            with col3:
                companies = list(set([x.company_name for x in self.unprocessed_document_list]))
                st.metric("Companies", len(companies))
            
            # Display detailed table
            df = pd.DataFrame([x.as_dict() for x in self.unprocessed_document_list])
            st.dataframe(data=df, use_container_width=True, height=400)
    
    def extract_source_data(self):
        """Extract and process source data with real-time progress updates"""
        st.session_state.processing_status = "running"
        st.session_state.processed_count = 0
        st.session_state.failed_count = 0
        st.session_state.processing_logs = []
        
        processor = DataSourceProcessor(self.database_context)
        document_list = processor.datasourceDBMgr.get_unprocessed_content_list()
        
        if len(document_list) == 0:
            st.warning("No unprocessed documents found.")
            st.session_state.processing_status = "complete"
            return
        
        st.session_state.total_documents = len(document_list)
        
        # Create placeholders for real-time updates
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        metrics_placeholder = st.empty()
        log_placeholder = st.empty()
        
        start_time = time.time()
        
        for idx, document in enumerate(document_list, 1):
            st.session_state.current_document = f"{document.company_name} {document.year} {document.content_type_desc}"
            
            # Update progress
            progress = idx / len(document_list)
            progress_placeholder.progress(progress, text=f"Processing {idx}/{len(document_list)}: {st.session_state.current_document}")
            
            # Update status
            status_placeholder.info(f"🔄 Processing: {st.session_state.current_document}")
            
            try:
                # Process document
                unique_id = document.unique_id
                company_name = document.company_name
                year = document.year
                content_type_desc = document.content_type_desc
                source_type = document.source_type
                source_url = document.source_url
                
                if source_type == 'file':
                    source_type_ext = 'pdf'
                else:
                    source_type_ext = source_type
                
                file_name = f"{company_name} {year} {content_type_desc}.{source_type_ext}"
                l_file_location = os.path.join(processor.pdf_in_folder, str(year), file_name)
                
                # Create directory
                os.makedirs(os.path.dirname(l_file_location), exist_ok=True)
                
                # Download/locate file
                if source_type == 'pdf':
                    processor.download_single_file(url=source_url, f_name=l_file_location, f_log=processor.logfile)
                elif source_type == 'webpage':
                    processor.download_webpage_as_pdf_file(url=source_url, f_name=l_file_location, f_log=processor.logfile)
                elif source_type == 'file':
                    l_file_location = os.path.join(processor.pdf_in_folder, 'ManualDownloads', source_url)
                    if not os.path.exists(l_file_location):
                        raise FileNotFoundError(f'Manual file not found: {l_file_location}')
                
                # Convert to text
                output_folder = os.path.join(processor.pdf_out_folder, str(year))
                os.makedirs(output_folder, exist_ok=True)
                output_file_name = f"{company_name} {year} {content_type_desc}.txt"
                output_path = os.path.join(output_folder, output_file_name)
                
                import fitz
                doc = fitz.open(l_file_location)
                with open(output_path, "wb") as out:
                    for page in doc:
                        text = page.get_text().encode("utf8")
                        out.write(text)
                        out.write(bytes((12,)))
                doc.close()
                
                # Check file size
                file_stats = os.stat(output_path)
                flagged = file_stats.st_size < 10000
                
                # Update database
                document.document_name = output_file_name
                processor.datasourceDBMgr.add_stage1_processed_files_to_t_document(document, flagged)
                
                st.session_state.processed_count += 1
                log_msg = f"✅ {st.session_state.current_document} ({file_stats.st_size:,} bytes)"
                if flagged:
                    log_msg += " ⚠️ FLAGGED FOR REVIEW"
                st.session_state.processing_logs.append(log_msg)
                
            except Exception as e:
                st.session_state.failed_count += 1
                st.session_state.processing_logs.append(f"❌ {st.session_state.current_document}: {str(e)}")
            
            # Update metrics
            elapsed = time.time() - start_time
            with metrics_placeholder.container():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("✅ Processed", st.session_state.processed_count)
                with col2:
                    st.metric("❌ Failed", st.session_state.failed_count)
                with col3:
                    st.metric("⏱️ Time Elapsed", f"{int(elapsed)}s")
                with col4:
                    avg_time = elapsed / idx if idx > 0 else 0
                    remaining = avg_time * (len(document_list) - idx)
                    st.metric("⏳ Est. Remaining", f"{int(remaining)}s")
            
            # Update logs
            with log_placeholder.container():
                with st.expander("📋 Processing Log", expanded=True):
                    for log in st.session_state.processing_logs[-10:]:  # Show last 10 entries
                        st.text(log)
        
        # Processing complete
        st.session_state.processing_status = "complete"
        progress_placeholder.progress(1.0, text="✅ Processing Complete!")
        
        total_time = time.time() - start_time
        
        # Final status
        if st.session_state.failed_count == 0:
            status_placeholder.success(f"🎉 All {st.session_state.processed_count} documents processed successfully in {int(total_time)}s!")
        else:
            status_placeholder.warning(f"⚠️ Processing completed: {st.session_state.processed_count} successful, {st.session_state.failed_count} failed ({int(total_time)}s)")
        
        # Show completion summary
        st.balloons()

    def run_online_Mode(self):
        st.title("📥 Source Data Load")
        st.markdown("---")
        
        # Database context selection
        col1, col2 = st.columns([1, 3])
        with col1:
            database_context = st.radio(
                "Environment", 
                ["Development", "Test"], 
                index=0,
                help="Select the database environment to use"
            )
        
        if database_context == 'Development':
            self.database_context = 'Development'
        else:
            self.database_context = "Test"
        
        with col2:
            st.info(f"🗄️ Current Environment: **{self.database_context}**")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button('📋 Load Unprocessed Source List', use_container_width=True, type="secondary"):
                self.load_unprocessed_data_list()
        
        with col2:
            # Disable button if processing is running
            disabled = st.session_state.processing_status == "running"
            if st.button('🚀 Extract & Process Source Data', use_container_width=True, type="primary", disabled=disabled):
                self.extract_source_data()
        
        # Show help section
        with st.expander("ℹ️ How to use this page"):
            st.markdown("""
            ### Instructions:
            1. **Select Environment**: Choose Development or Test database
            2. **Load Unprocessed List**: View all pending documents waiting to be processed
            3. **Extract & Process**: Download source files, convert to text, and update database
            
            ### Features:
            - ✅ Real-time progress tracking
            - 📊 Processing metrics and statistics
            - 📋 Live processing logs
            - ⚠️ Automatic flagging of small files for review
            - 🎯 Estimated time remaining
            """)


# Initialize and run
