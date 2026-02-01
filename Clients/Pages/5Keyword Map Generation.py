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


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0

    def generate_keyword_location_map(self, DebugMode=False):
        # Create progress containers
        status_container = st.container()
        progress_container = st.container()

        with status_container:
            st.info(
                f"🚀 Starting keyword location map generation for :")

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
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating Exposure Pathway keyword maps...")
            with status_container:
                st.write("📍 Processing Exposure Pathway keyword location maps...")
            process_exposure_pathway_document_list()
            with status_container:
                st.success("✅ Exposure Pathway keyword maps completed")

        if (self.InternalizationSelected):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating Internalization keyword maps...")
            with status_container:
                st.write("📍 Processing Internalization keyword location maps...")
            process_internalization_document_list()
            with status_container:
                st.success("✅ Internalization keyword maps completed")

        if (self.MitigationSelected):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating Mitigation keyword maps...")
            with status_container:
                st.write("📍 Processing Mitigation keyword location maps...")
            process_mitigation_document_list()
            with status_container:
                st.success("✅ Mitigation keyword maps completed")

        if (key_word_search_mgr.validation_mode):
            key_word_search_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

        # Final completion message
        with progress_container:
            st.progress(1.0, text="Keyword map generation complete!")
        with status_container:
            st.balloons()
            st.success(
                f"🎉 All keyword location maps generated successfully!")

    def run_online_Mode(self):


        st.text("Select Keyword Location Map Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=False)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=False)
        self.MitigationSelected = st.checkbox("Mitigation", value=False)

        st.button('Generate Location Maps',
                  on_click=self.generate_keyword_location_map)


st_autorefresh(interval=5000, key="fizzbuzzcounter")
startup = StartUpClass()
startup.run_online_Mode()
