import altair as alt
import streamlit.components.v1 as components
import mpld3
from pylab import *
import plotly.express as px
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


# Configure page - must be first Streamlit command
st.set_page_config(
    page_title="Avisk Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional styling with visual enhancements
st.markdown("""
<style>
    /* Main container with gradient background */
    .stApp { 
        padding-top: 0rem !important; 
        margin-top: 0rem !important;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 2rem !important; 
        padding-left: 2rem !important; 
        padding-right: 2rem !important; 
        margin-top: 0rem !important; 
        max-width: 100% !important; 
    }
    
    .main { padding-top: 0rem !important; }
    .main .block-container { padding-top: 0rem !important; margin-top: 0rem !important; }
    header { padding-top: 0rem !important; margin-top: 0rem !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; margin-top: 0rem !important; }
    [data-testid="stHeader"] { display: none !important; }
    section.main { padding-top: 0rem !important; }
    section.main > div { padding-top: 0rem !important; margin-top: 0rem !important; }
    
    /* Professional Headers with gradient */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-top: 0rem !important;
        padding-top: 0rem !important;
        text-align: center;
        letter-spacing: -1px;
    }
    
    h2, h3 {
        color: #2c3e50;
        font-weight: 700;
    }
    
    /* Chart container with cards */
    .stVega, .stPlotlyChart, .stAltairChart {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .stVega:hover, .stPlotlyChart:hover, .stAltairChart:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    
    /* Info banner with gradient */
    .info-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 16px;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
    }
    
    .info-banner h3 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
    }
    
    .info-banner p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# import mplcursors


def st_altair_chart():
    # Professional dashboard header with icons
    st.markdown('<h1>🌍 ESG Insights Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<div class="info-banner"><h3>🌱 Environmental, Social & Governance Analytics</h3><p>📊 Comprehensive ESG risk analysis and insights powered by AI 🤖</p></div>', unsafe_allow_html=True)
    
    # Add tabs for better organization
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🎯 Risk Analysis", "📑 Detailed Reports"])
    
    with tab1:
        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")

    dataset_original = df[["Company", "Year", "Document Type", "ESG Category",
                           "Exposure Pathway", "Clusters", "Score"]].round(2)

    data_filter = dataset_original["Company"] == 'Chesapeake Energy'
    dataset_comp = dataset_original.where(data_filter).dropna()
    data_filter = dataset_comp["Year"] == 2022
    dataset_year = dataset_comp.where(data_filter).dropna()
    data_filter = dataset_year["Document Type"] == 'Sustainability Report'
    dataset = dataset_year.where(data_filter).dropna()

    c = (
        alt.Chart(dataset_original)
        .mark_circle()
        .encode(alt.X("Clusters").scale(domain=(0, 100)), y="Score", size="Score", color='ESG Category', tooltip=["ESG Category", "Exposure Pathway", "Clusters", "Score"])
        .properties(height=600,
                    title='ESG Insights.ai').configure_title(
            fontSize=20,
            font='Courier',
            anchor='middle')
        .configure_axis(grid=True)
        .interactive()
        .configure_range(
            category={'scheme': 'dark2'})
    )

    st.altair_chart(c, use_container_width=True)


st_altair_chart()
