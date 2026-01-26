from Utilities.Lookups import Lookups, Processing_Type
from DBEntities.LookupsDBManager import LookupsDBManager
import streamlit as st
import sys
from pathlib import Path
import os
sys.path.append(str(Path(__file__).resolve().parent.parent))


# Configure page
st.set_page_config(
    page_title="Avisk Core Services",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    # Page title
    st.title("🌍 Avisk Core Services Dashboard")
    st.markdown("---")

    # Sidebar navigation
    st.sidebar.title("📊 Navigation")

    # Database context selection
    database_context = st.sidebar.radio(
        "Database Context",
        ["Development", "Test"],
        index=0,
        help="Select the database environment"
    )

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh (20s)", value=False)

    if auto_refresh:
        # Only import autorefresh if enabled
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=20000, key="dashboard_refresh")
        except ImportError:
            st.sidebar.warning("Auto-refresh not available")

    # Main content
    st.header("📋 Processing Status Overview")

    # Create columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('🔍 Exposure Pathway Keyword Search', divider='blue')
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_EXP
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success(
                    '✅ No New Documents to Process: Awaiting Batch Process Scheduling')
            else:
                st.info(f"📄 Documents Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Documents Failed: {failed_docs}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

        st.subheader('🔗 Internalization Keyword Search', divider='blue')
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_INT
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success(
                    '✅ No New Documents to Process: Awaiting Batch Process Scheduling')
            else:
                st.info(f"📄 Documents Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Documents Failed: {failed_docs}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

    with col2:
        st.subheader('🛡️ Mitigation Keyword Search', divider='blue')
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_MIT
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success(
                    '✅ No New Documents to Process: Awaiting Batch Process Scheduling')
            else:
                st.info(f"📄 Documents Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Documents Failed: {failed_docs}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

        st.subheader('💡 Exposure Insight Generation', divider='blue')
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success(
                    '✅ No New Documents to Process: Awaiting Batch Process Scheduling')
            else:
                st.info(f"📄 Documents Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Documents Failed: {failed_docs}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

    # Additional insight generation sections
    st.subheader('🧠 Advanced Insight Generation', divider='green')

    insight_col1, insight_col2, insight_col3 = st.columns(3)

    with insight_col1:
        st.markdown("**Internalization Insights**")
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().INTERNALIZATION_INSIGHTS_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with insight_col2:
        st.markdown("**Exposure → Internalization**")
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().Exp_Int_Insight_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with insight_col3:
        st.markdown("**Mitigation Insights**")
        try:
            failed_docs, pending_docs = LookupsDBManager(database_context).get_current_processing_status(
                processing_type=Processing_Type().Mitigation_Exp_INT_Insight_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    # Footer
    st.markdown("---")
    st.markdown(
        "**💡 Tip:** Use the sidebar to navigate between sections and toggle auto-refresh")


if __name__ == "__main__":
    main()
