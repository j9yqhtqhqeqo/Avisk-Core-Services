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

from Utilities.auth import require_login  # noqa: E402
from Utilities.mobile import inject_mobile_css  # noqa: E402
require_login(["admin", "validator"])
inject_mobile_css()

# Page header
st.title("✅ Keyword Validation")
st.markdown("---")


VALIDATION_CATEGORY_CONFIG: dict[str, dict[str, str]] = {
    'exp': {
        'label': 'Exposure Pathway',
        'column': 'exp_validation_completed_ind',
        'dictionary_query': """
            SELECT c.esg_category_name,
                   im.impact_category_name,
                   e.exposure_path_name,
                   d.keywords
            FROM t_exposure_pathway_dictionary d
            INNER JOIN t_exposure_pathway e ON e.exposure_path_id = d.exposure_path_id
            INNER JOIN t_impact_category im ON im.impact_category_id = e.impact_category_id
            INNER JOIN t_esg_category c ON c.esg_category_id = im.esg_category_id
            ORDER BY c.esg_category_name,
                     im.impact_category_name,
                     e.exposure_path_name,
                     d.keywords
        """,
    },
    'int': {
        'label': 'Internalization',
        'column': 'int_validation_completed_ind',
        'dictionary_query': """
            SELECT c.esg_category_name,
                   im.impact_category_name,
                   e.exposure_path_name,
                   i.internalization_name,
                   d.keywords
            FROM t_internalization_dictionary d
            INNER JOIN t_internalization i ON i.internalization_id = d.internalization_id
            INNER JOIN t_exposure_pathway e ON e.exposure_path_id = i.exposure_path_id
            INNER JOIN t_impact_category im ON im.impact_category_id = e.impact_category_id
            INNER JOIN t_esg_category c ON c.esg_category_id = im.esg_category_id
            ORDER BY c.esg_category_name,
                     im.impact_category_name,
                     e.exposure_path_name,
                     i.internalization_name,
                     d.keywords
        """,
    },
    'mit': {
        'label': 'Mitigation',
        'column': 'mit_validation_completed_ind',
        'dictionary_query': """
            SELECT class_name, sub_class_name, keywords
            FROM t_mitigation
            ORDER BY class_name, sub_class_name, keywords
        """,
    },
}


def get_db_connection() -> tuple[psycopg2.extensions.connection | None, str]:
    connection_string = DB_Connection().DB_CONNECTION_STRING
    if not connection_string:
        return None, 'DB_CONNECTION_STRING is not configured'

    try:
        return psycopg2.connect(connection_string), ''
    except Exception as exc:
        return None, str(exc)


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

    connection, error = get_db_connection()
    if not connection:
        status['error'] = error
        return status

    try:
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


def load_not_ready_validation_combinations() -> dict[str, Any]:
    combinations: dict[str, Any] = {
        'db_available': False,
        'error': '',
        'categories': {category_key: [] for category_key in VALIDATION_CATEGORY_CONFIG},
    }

    connection, error = get_db_connection()
    if not connection:
        combinations['error'] = error
        return combinations

    try:
        cursor = connection.cursor()
        for category_key, config in VALIDATION_CATEGORY_CONFIG.items():
            cursor.execute(
                f"""
                SELECT company_name, year, COUNT(*) AS document_count
                FROM t_document
                WHERE {config['column']} = -1
                GROUP BY company_name, year
                ORDER BY company_name, year DESC
                """
            )
            combinations['categories'][category_key] = [
                {
                    'company_name': row[0],
                    'year': row[1],
                    'document_count': row[2],
                }
                for row in cursor.fetchall()
            ]

        cursor.close()
        connection.close()
        combinations['db_available'] = True
        return combinations
    except Exception as exc:
        combinations['error'] = str(exc)
        return combinations


def mark_validation_pending(category_key: str, selections: list[tuple[str, int | str]]) -> tuple[bool, str, int]:
    config = VALIDATION_CATEGORY_CONFIG.get(category_key)
    if not config:
        return False, 'Unknown validation category selected.', 0
    if not selections:
        return False, 'Select at least one company and year combination.', 0

    connection, error = get_db_connection()
    if not connection:
        return False, error, 0

    try:
        cursor = connection.cursor()
        updated_count = 0
        for company_name, year in selections:
            cursor.execute(
                f"""
                UPDATE t_document
                SET {config['column']} = 0,
                    modify_dt = CURRENT_TIMESTAMP
                WHERE company_name = %s
                  AND year = %s
                  AND {config['column']} = -1
                """,
                (company_name, year),
            )
            updated_count += cursor.rowcount
        connection.commit()
        cursor.close()
        connection.close()

        if updated_count == 0:
            return False, 'No Not Ready documents matched the selected company and year combinations.', 0

        return True, '', updated_count
    except Exception as exc:
        connection.rollback()
        connection.close()
        return False, str(exc), 0


def render_not_ready_validation_tab() -> None:
    st.subheader('Manage Validation List')
    st.caption(
        'Review `-1` validation rows by category and move selected company/year combinations back to Pending (`0`).')

    combinations = load_not_ready_validation_combinations()
    if not combinations['db_available']:
        st.warning(
            f"⚠️ Not Ready validation data unavailable: {combinations['error']}")
        return

    category_options = list(VALIDATION_CATEGORY_CONFIG.keys())
    selected_category = st.selectbox(
        'Validation category',
        category_options,
        format_func=lambda category_key: VALIDATION_CATEGORY_CONFIG[category_key]['label'],
    )

    selected_rows = combinations['categories'][selected_category]
    if not selected_rows:
        st.info('No Not Ready documents were found for the selected category.')
        return

    st.dataframe(selected_rows, use_container_width=True, hide_index=True)

    selection_options = []
    selection_lookup = {}
    for row in selected_rows:
        option_label = f"{row['company_name']} ({row['year']}) - {row['document_count']} document(s)"
        selection_options.append(option_label)
        selection_lookup[option_label] = (
            str(row['company_name']),
            row['year'],
            int(row['document_count']),
        )

    selected_options = st.multiselect(
        'Company and year combinations',
        selection_options,
        key=f'{selected_category}_not_ready_combinations',
    )

    selected_combinations = [
        (selection_lookup[option][0], selection_lookup[option][1])
        for option in selected_options
    ]
    selected_document_count = sum(
        selection_lookup[option][2] for option in selected_options
    )

    if selected_options:
        st.caption(
            f"{selected_document_count} document(s) across {len(selected_options)} company/year combination(s) will move from Not Ready to Pending."
        )

    if st.button('Update selected combinations to Pending', key=f'{selected_category}_mark_pending'):
        success, error, updated_count = mark_validation_pending(
            selected_category,
            selected_combinations,
        )
        if success:
            st.success(
                f"Updated {updated_count} document(s) to Pending across {len(selected_options)} company/year combination(s) in {VALIDATION_CATEGORY_CONFIG[selected_category]['label']}."
            )
            st.rerun()
        else:
            st.error(f"Unable to update validation status: {error}")


def load_dictionary_terms() -> dict[str, Any]:
    dictionary_terms: dict[str, Any] = {
        'db_available': False,
        'error': '',
        'categories': {category_key: [] for category_key in VALIDATION_CATEGORY_CONFIG},
    }

    connection, error = get_db_connection()
    if not connection:
        dictionary_terms['error'] = error
        return dictionary_terms

    try:
        cursor = connection.cursor()
        for category_key, config in VALIDATION_CATEGORY_CONFIG.items():
            cursor.execute(config['dictionary_query'])
            column_names = [description[0]
                            for description in cursor.description]
            dictionary_terms['categories'][category_key] = [
                dict(zip(column_names, row)) for row in cursor.fetchall()
            ]

        cursor.close()
        connection.close()
        dictionary_terms['db_available'] = True
        return dictionary_terms
    except Exception as exc:
        dictionary_terms['error'] = str(exc)
        return dictionary_terms


def render_dictionary_terms_tab() -> None:
    st.subheader('Dictionary Terms')
    st.caption(
        'Browse all configured dictionary terms for Exposure Pathway, Internalization, and Mitigation.')

    dictionary_terms = load_dictionary_terms()
    if not dictionary_terms['db_available']:
        st.warning(
            f"⚠️ Dictionary terms unavailable: {dictionary_terms['error']}")
        return

    category_tabs = st.tabs([
        VALIDATION_CATEGORY_CONFIG['exp']['label'],
        VALIDATION_CATEGORY_CONFIG['int']['label'],
        VALIDATION_CATEGORY_CONFIG['mit']['label'],
    ])

    for tab, category_key in zip(category_tabs, VALIDATION_CATEGORY_CONFIG.keys()):
        with tab:
            terms = dictionary_terms['categories'][category_key]
            st.metric('Total terms', len(terms))
            if not terms:
                st.info('No dictionary terms were found for this category.')
            else:
                st.dataframe(terms, use_container_width=True, hide_index=True)


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

    def run_keyword_validations(self, DebugMode: bool = False):
        status_container = st.container()
        progress_container = st.container()

        with status_container:
            st.info(
                f"🚀 Starting validation process:")

        total_steps = sum([
            1 if self.ExposurePathwaySelected else 0,
            1 if self.InternalizationSelected else 0,
            1 if self.MitigationSelected else 0,
            1
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

        with progress_container:
            st.progress(1.0, text="Validation process complete!")
        with status_container:
            st.balloons()
            st.success(
                f"🎉 All validation tasks completed successfully!")

    def run_online_Mode(self):

        st.text("Select Keyword Validation Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=False)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=False)
        self.MitigationSelected = st.checkbox("Mitigation", value=False)

        st.button('Run Validations',
                  on_click=self.run_keyword_validations)


validation_tabs = st.tabs([
    'Run Validations',
    'Manage Validation List',
    'Dictionary Terms',
])

with validation_tabs[0]:
    render_validation_status()
    st.markdown("---")
    l_startup_class = StartUpClass()
    l_startup_class.run_online_Mode()

with validation_tabs[1]:
    render_not_ready_validation_tab()

with validation_tabs[2]:
    render_dictionary_terms_tab()


# l_startup_class.run_keyword_validations()
