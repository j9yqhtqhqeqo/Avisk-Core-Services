from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from multiprocessing import Process, Queue, Pool
from streamlit_autorefresh import st_autorefresh
from DBEntities.LookupsDBManager import LookupsDBManager
from Services.SingletonServiceMgr import process_mitigation_document_list, process_internalization_document_list
from Services.SingletonServiceMgr import process_exposure_pathway_document_list
import threading
import streamlit as st
from Utilities.Lookups import Lookups, Processing_Type
from Services.InsightGenerator import triangulation_Insight_Generator
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import file_folder_keyWordSearchManager
import sys
from pathlib import Path
import os
import time
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

# Configure page
st.set_page_config(
    page_title="Keyword Map Generation",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page header
st.title("🗺️ Keyword Map Generation")
st.markdown("---")


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0

        # Initialize session state for processing status
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = []

    def generate_keyword_location_map(self, DebugMode=False):
        # Set processing flag
        st.session_state.processing = True
        st.session_state.processing_status = []

        # Create persistent progress containers
        status_container = st.empty()
        progress_container = st.empty()
        message_container = st.empty()

        with status_container.container():
            st.info("🚀 Starting keyword location map generation...")

        total_steps = sum([
            1 if self.ExposurePathwaySelected else 0,
            1 if self.InternalizationSelected else 0,
            1 if self.MitigationSelected else 0
        ])

        current_step = 0

        key_word_search_mgr = file_folder_keyWordSearchManager(
            folder_path=PARM_STAGE1_FOLDER)
        key_word_search_mgr.validation_mode = False

        if (self.ExposurePathwaySelected):
            current_step += 1
            progress_container.progress(current_step / total_steps,
                                        text=f"Step {current_step}/{total_steps}: Generating Exposure Pathway keyword maps...")
            with message_container.container():
                st.write("📍 Processing Exposure Pathway keyword location maps...")
                st.caption(
                    "This may take several minutes. Processing documents in batches...")

            process_exposure_pathway_document_list()

            st.session_state.processing_status.append(
                "✅ Exposure Pathway keyword maps completed")
            with message_container.container():
                st.success("✅ Exposure Pathway keyword maps completed")

        if (self.InternalizationSelected):
            current_step += 1
            progress_container.progress(current_step / total_steps,
                                        text=f"Step {current_step}/{total_steps}: Generating Internalization keyword maps...")
            with message_container.container():
                st.write("📍 Processing Internalization keyword location maps...")
                st.caption(
                    "This may take several minutes. Processing documents in batches...")

            process_internalization_document_list()

            st.session_state.processing_status.append(
                "✅ Internalization keyword maps completed")
            with message_container.container():
                st.success("✅ Internalization keyword maps completed")

        if (self.MitigationSelected):
            current_step += 1
            progress_container.progress(current_step / total_steps,
                                        text=f"Step {current_step}/{total_steps}: Generating Mitigation keyword maps...")
            with message_container.container():
                st.write("📍 Processing Mitigation keyword location maps...")
                st.caption(
                    "This may take several minutes. Processing documents in batches...")

            process_mitigation_document_list()

            st.session_state.processing_status.append(
                "✅ Mitigation keyword maps completed")
            with message_container.container():
                st.success("✅ Mitigation keyword maps completed")

        if (key_word_search_mgr.validation_mode):
            key_word_search_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

        # Final completion message
        progress_container.progress(
            1.0, text="✅ Keyword map generation complete!")
        with status_container.container():
            st.balloons()
            st.success("🎉 All keyword location maps generated successfully!")
            for status in st.session_state.processing_status:
                st.write(status)

        # Reset processing flag
        st.session_state.processing = False

    def run_online_Mode(self):
        # Show processing status if available
        if st.session_state.processing_status:
            with st.expander("📊 Previous Processing Status", expanded=False):
                for status in st.session_state.processing_status:
                    st.write(status)

        st.text("Select Keyword Location Map Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=False)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=False)
        self.MitigationSelected = st.checkbox("Mitigation", value=False)

        # Disable button during processing
        st.button('Generate Location Maps',
                  on_click=self.generate_keyword_location_map,
                  disabled=st.session_state.processing)

        if st.session_state.processing:
            st.warning("⚠️ Processing in progress... Please wait.")


# Only auto-refresh when not processing to avoid clearing progress messages
if not st.session_state.get('processing', False):
    st_autorefresh(interval=10000, key="fizzbuzzcounter")

startup = StartUpClass()
startup.run_online_Mode()
