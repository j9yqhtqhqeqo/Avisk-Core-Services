from Services.SingletonServiceMgr import process_mitigation_document_list
from Services.SingletonServiceMgr import process_internalization_document_list
from Services.SingletonServiceMgr import process_exposure_pathway_document_list
from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.Lookups import Lookups
from Utilities.Lookups import DB_Connection
import streamlit as st
import threading
from streamlit_autorefresh import st_autorefresh
import sys
from pathlib import Path
import os
import psycopg2
from typing import Any
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


def load_validation_status() -> dict[str, int | bool | str]:
    status: dict[str, int | bool | str] = {
        'db_available': False,
        'error': '',
        'exp_running': 0,
        'exp_pending': 0,
        'int_running': 0,
        'int_pending': 0,
        'mit_running': 0,
        'mit_pending': 0,
    }

    connection_string = DB_Connection().DB_CONNECTION_STRING
    if not connection_string:
        status['error'] = 'DB_CONNECTION_STRING is not configured'
        return status

    try:
        connection = psycopg2.connect(connection_string)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE exp_validation_completed_ind = 2
                      AND exp_pathway_keyword_search_completed_ind IN (0, 2)
                ) AS exp_running,
                COUNT(*) FILTER (
                    WHERE exp_validation_completed_ind = 0
                      AND exp_pathway_keyword_search_completed_ind IN (0, 2)
                ) AS exp_pending,
                COUNT(*) FILTER (
                    WHERE int_validation_completed_ind = 2
                      AND internalization_keyword_search_completed_ind IN (0, 2)
                ) AS int_running,
                COUNT(*) FILTER (
                    WHERE int_validation_completed_ind = 0
                      AND internalization_keyword_search_completed_ind IN (0, 2)
                ) AS int_pending,
                COUNT(*) FILTER (
                    WHERE mit_validation_completed_ind = 2
                      AND mitigation_search_completed_ind IN (0, 2)
                ) AS mit_running,
                COUNT(*) FILTER (
                    WHERE mit_validation_completed_ind = 0
                      AND mitigation_search_completed_ind IN (0, 2)
                ) AS mit_pending
            FROM t_document
            """
        )
        row = cursor.fetchone()
        cursor.close()
        connection.close()

        if row is None:
            status.update({'db_available': True})
            return status

        status.update({
            'db_available': True,
            'exp_running': row[0] or 0,
            'exp_pending': row[1] or 0,
            'int_running': row[2] or 0,
            'int_pending': row[3] or 0,
            'mit_running': row[4] or 0,
            'mit_pending': row[5] or 0,
        })
        return status
    except Exception as exc:
        status['error'] = str(exc)
        return status


def render_validation_status() -> None:
    status = load_validation_status()
    if not status['db_available']:
        st.warning(f"⚠️ Validation status unavailable: {status['error']}")
        return

    running_total = int(status['exp_running']) + \
        int(status['int_running']) + int(status['mit_running'])
    pending_total = int(status['exp_pending']) + \
        int(status['int_pending']) + int(status['mit_pending'])

    st.subheader("Background Validation Status")
    if running_total > 0:
        st_autorefresh(interval=5000, limit=None,
                       key='validation_status_refresh')
        st.info(
            f"🔄 Validation is currently running in the background. "
            f"{running_total} document(s) are in progress."
        )
    else:
        st.caption("No background validation is currently in progress.")

    metric_cols = st.columns(3)
    metric_cols[0].metric('Exposure Pathway', int(
        status['exp_running']), f"{int(status['exp_pending'])} pending")
    metric_cols[1].metric('Internalization', int(
        status['int_running']), f"{int(status['int_pending'])} pending")
    metric_cols[2].metric('Mitigation', int(
        status['mit_running']), f"{int(status['mit_pending'])} pending")

    if pending_total > 0 and running_total == 0:
        st.warning(
            f"⏸️ {pending_total} validation-ready document(s) are pending, but no background validation is currently active."
        )


render_validation_status()
st.markdown("---")


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

    def run_keyword_validations(self, DebugMode: bool = False):
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
