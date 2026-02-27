from Services.SingletonServiceMgr import process_mitigation_document_list
from Services.SingletonServiceMgr import process_internalization_document_list
from Services.SingletonServiceMgr import process_exposure_pathway_document_list
from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.Lookups import Lookups
import streamlit as st
import threading
import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

# Configure page
st.set_page_config(
    page_title="Validation",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

from Utilities.mobile import inject_mobile_css  # noqa: E402
inject_mobile_css()

# Page header
st.title("✅ Keyword Validation")
st.markdown("---")


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

    def run_keyword_validations(self, DebugMode=False):
        # Create progress containers
        status_container = st.container()
        progress_container = st.container()

        with status_container:
            st.info(
                f"🚀 Starting validation process:")

        total_steps = sum([
            1 if self.ExposurePathwaySelected else 0,
            1 if self.InternalizationSelected else 0,
            1 if self.MitigationSelected else 0,
            1  # Final step for sending validation files
        ])

        current_step = 0

        key_word_search_mgr = file_folder_keyWordSearchManager(
            folder_path=PARM_STAGE1_FOLDER)
        key_word_search_mgr.validation_mode = True

        if (self.ExposurePathwaySelected):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Validating Exposure Pathway Dictionary Terms...")
            with status_container:
                st.write("📝 Validating Exposure Pathway Dictionary Terms...")
            print('Validating Exposure Pathway Dictionary Terms:')
            process_exposure_pathway_document_list(validation_mode=True)
            with status_container:
                st.success("✅ Exposure Pathway validation completed")

        if (self.InternalizationSelected):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Validating Internalization Dictionary Terms...")
            with status_container:
                st.write("📝 Validating Internalization Dictionary Terms...")
            print('Validating Internalization Dictionary Terms:')
            process_internalization_document_list(validation_mode=True)
            with status_container:
                st.success("✅ Internalization validation completed")

        if (self.MitigationSelected):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Validating Mitigation Dictionary Terms...")
            with status_container:
                st.write("📝 Validating Mitigation Dictionary Terms...")
            print('Validating Mitigation Dictionary Terms:')
            process_mitigation_document_list(
                validation_mode=True)
            with status_container:
                st.success("✅ Mitigation validation completed")

        if (key_word_search_mgr.validation_mode):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Sending validation files...")
            with status_container:
                st.write(
                    "📤 Sending Include/Exclude Dictionary Files for Validation...")
            print(
                'Sending Include/Exclude Dictionary Files for Validation to keyword search manager...')
            key_word_search_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()
            with status_container:
                st.success("✅ Validation files sent successfully")

        # Final completion message
        with progress_container:
            st.progress(1.0, text="Validation process complete!")
        with status_container:
            st.balloons()
            st.success(
                f"🎉 All validation tasks completed successfully!")

    # def run_thread_mode(self, DebugMode=False):
    #     process_exposure_pathway_document_list()

    def run_online_Mode(self):

        st.text("Select Keyword Validation Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=False)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=False)
        self.MitigationSelected = st.checkbox("Mitigation", value=False)

        st.button('Run Validations',
                  on_click=self.run_keyword_validations)

        # st.button('Run Thread Mode',
        #           on_click=self.run_thread_mode)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()


# l_startup_class.run_keyword_validations()
