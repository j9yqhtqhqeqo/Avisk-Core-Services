from version import get_version_string, get_build_string, ENVIRONMENT
from Utilities.Lookups import Lookups, Processing_Type
from DBEntities.LookupsDBManager import LookupsDBManager
import streamlit as st
import sys
from pathlib import Path
import os
sys.path.append(str(Path(__file__).resolve().parent.parent))


# Configure page
st.set_page_config(
    page_title="Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    # Page title
    st.title("🌍 Avisk Core Services Dashboard")
    st.markdown("---")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh (20s)", value=False)

    if auto_refresh:
        # Only import autorefresh if enabled
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=5000, key="dashboard_refresh")
        except ImportError:
            st.sidebar.warning("Auto-refresh not available")

    # Main content
    st.header("📋 Processing Status Overview")

    # Create columns for better layout
    st.subheader('🔍 Keyword Search', divider='blue')

    keyword_col1, keyword_col2, keyword_col3 = st.columns(3)

    with keyword_col1:
        st.markdown("**Exposure Pathway**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_EXP
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with keyword_col2:
        st.markdown("**Internalization**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_INT
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with keyword_col3:
        st.markdown("**Mitigation**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().KEYWORD_GEN_MIT
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    # Additional insight generation sections
    st.subheader('🧠 Advanced Insight Generation', divider='green')

    # First row - Basic insights
    insight_row1_col1, insight_row1_col2, insight_row1_col3 = st.columns(3)

    with insight_row1_col1:
        st.markdown("**Exposure Insights**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with insight_row1_col2:
        st.markdown("**Internalization Insights**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
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

    with insight_row1_col3:
        st.markdown("**Exposure → Internalization**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
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

    # Second row - Mitigation insights
    insight_row2_col1, insight_row2_col2, insight_row2_col3 = st.columns(3)

    with insight_row2_col1:
        st.markdown("**Exposure → Mitigation**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().Mitigation_Exp_Insight_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with insight_row2_col2:
        st.markdown("**Internalization → Mitigation**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                processing_type=Processing_Type().Mitigation_Int_Insight_GEN
            )
            if pending_docs == 0 and failed_docs == 0:
                st.success('✅ Ready')
            else:
                st.info(f"📄 Pending: {pending_docs}")
                if failed_docs > 0:
                    st.error(f"❌ Failed: {failed_docs}")
        except Exception as e:
            st.error("Error loading status")

    with insight_row2_col3:
        st.markdown("**Exposure → Internalization → Mitigation**")
        try:
            failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
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

    # Status bar at the bottom
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns([1, 1, 1])
    with footer_col1:
        st.caption(f"🏷️ {get_version_string()}")
    with footer_col2:
        st.caption(f"🔨 {get_build_string()}")
    with footer_col3:
        st.caption(f"🌍 Environment: {ENVIRONMENT.title()}")


if __name__ == "__main__":
    main()
