"""
Mobile-friendly responsive CSS for Streamlit pages.
Call inject_mobile_css() once per page, right after st.set_page_config().
"""
import streamlit as st


def inject_mobile_css() -> None:
    """Inject responsive CSS that makes multi-column layouts stack on small screens."""
    st.markdown("""
<style>
/* ── Mobile responsive overrides ─────────────────────────────────────────── */
@media (max-width: 768px) {

    /* Stack all columns vertically */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Wider sidebar on mobile */
    [data-testid="stSidebar"] {
        min-width: 80vw !important;
        max-width: 90vw !important;
    }

    /* Reduce page padding */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
        max-width: 100% !important;
    }

    /* Bigger touch targets for buttons */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
        width: 100% !important;
    }

    /* Sliders easier to grab */
    [data-testid="stSlider"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* Full-width select boxes and inputs */
    [data-testid="stSelectbox"],
    [data-testid="stMultiSelect"],
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"] {
        width: 100% !important;
    }

    /* Full-width dataframes / tables */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        width: 100% !important;
        overflow-x: auto !important;
    }

    /* Tabs: allow horizontal scroll rather than overflow */
    [data-testid="stTabs"] {
        overflow-x: auto !important;
    }

    /* Metric cards full width */
    [data-testid="metric-container"] {
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)
