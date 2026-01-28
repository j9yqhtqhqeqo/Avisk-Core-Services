import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import time
from streamlit_autorefresh import st_autorefresh
from DBEntities.LookupsDBManager import LookupsDBManager
import streamlit as st
from Utilities.Lookups import Lookups, Processing_Type

# Professional styling with enhanced visual design
st.markdown("""
<style>
    /* Target root container */
    .stApp {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Remove ALL block container padding */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        margin-top: 0rem !important;
        max-width: 100% !important;
    }
    
    /* Remove main container padding */
    .main {
        padding-top: 0rem !important;
    }
    
    .main .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Remove header spacing */
    header {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Remove all CSS class variants */
    div[class*="css-"] {
        padding-top: 0rem !important;
    }
    
    /* Remove app view padding */
    [data-testid="stAppViewContainer"] {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Remove main content padding */
    section.main {
        padding-top: 0rem !important;
    }
    
    section.main > div {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Professional Title with gradient */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.8rem;
        margin-top: 0rem !important;
        padding-top: 0rem !important;
        text-align: left;
        letter-spacing: -0.5px;
    }
    
    /* Enhanced headers */
    h2 {
        color: #2c3e50;
        font-weight: 700;
        font-size: 1.4rem;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid;
        border-image: linear-gradient(90deg, #667eea 0%, #764ba2 100%) 1;
    }
    
    h3 {
        color: #34495e;
        font-weight: 600;
        font-size: 1.1rem;
        margin: 0.5rem 0;
    }
    
    h4 {
        color: #2c3e50;
        font-weight: 600;
        margin-top: 0rem;
        margin-bottom: 0.5rem;
        font-size: 1.05rem;
    }
    
    /* Professional info cards */
    .stInfo {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%) !important;
        border-left: 4px solid #667eea !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, #11998e15 0%, #38ef7d15 100%) !important;
        border-left: 4px solid #11998e !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    
    /* Enhanced metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        font-weight: 600;
        color: #5a6c7d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Card-like containers */
    div[data-testid="column"] {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    div[data-testid="column"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    }
    
    /* Dividers */
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    [data-testid="stSidebar"] .stRadio label {
        color: #2c3e50;
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] p {
        color: #495057;
    }
    
    /* Icon styling for better visual hierarchy */
    .icon-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.3rem;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .badge-ready {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
    }
    
    .badge-processing {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0

    def run_online_Mode(self):
        # Professional dashboard header with icon
        st.markdown('<h1>🌐 Avisk Core Services Dashboard</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color: #5a6c7d; font-size: 1.1rem; margin-top: -0.5rem;">Real-time document processing & AI insights monitoring</p>', unsafe_allow_html=True)
        
        # Database context in sidebar
        st.sidebar.markdown("### ⚙️ Configuration")
        database_context = st.sidebar.radio(
            "Database Environment", ["Development", "Test"], index=0)
        
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Quick Stats")
        st.sidebar.info("Monitor your pipeline status in real-time")

        st.markdown("---")
        st.markdown('<h2>📋 Processing Status Overview</h2>', unsafe_allow_html=True)
        
        # 2x2 Grid for main processes with enhanced cards
        col1, col2 = st.columns(2, gap="medium")
        
        with col1:
            st.markdown('<div class="icon-header"><span style="font-size: 1.8rem;">🔍</span><h4 style="margin: 0;">Exposure Pathway Keyword Search</h4></div>', unsafe_allow_html=True)
            failed_exp, pending_exp = LookupsDBManager(
                self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_EXP)
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("📄 Pending", pending_exp)
            with metric_col2:
                st.metric("⚠️ Failed", failed_exp)
            
            if pending_exp == 0 and failed_exp == 0:
                st.success("✅ All documents processed successfully", icon="✅")
            else:
                st.info(f"⏳ Processing {pending_exp} documents...")
        
        with col2:
            st.markdown('<div class="icon-header"><span style="font-size: 1.8rem;">🛡️</span><h4 style="margin: 0;">Mitigation Keyword Search</h4></div>', unsafe_allow_html=True)
            failed_mit, pending_mit = LookupsDBManager(
                self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_MIT)
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("📄 Pending", pending_mit)
            with metric_col2:
                st.metric("⚠️ Failed", failed_mit)
            
            if pending_mit == 0 and failed_mit == 0:
                st.success("✅ All documents processed successfully", icon="✅")
            else:
                st.info(f"⏳ Processing {pending_mit} documents...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col3, col4 = st.columns(2, gap="medium")
        
        with col3:
            st.markdown('<div class="icon-header"><span style="font-size: 1.8rem;">🔗</span><h4 style="margin: 0;">Internalization Keyword Search</h4></div>', unsafe_allow_html=True)
            failed_int, pending_int = LookupsDBManager(
                self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_INT)
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("📄 Pending", pending_int)
            with metric_col2:
                st.metric("⚠️ Failed", failed_int)
            
            if pending_int == 0 and failed_int == 0:
                st.success("✅ All documents processed successfully", icon="✅")
            else:
                st.info(f"⏳ Processing {pending_int} documents...")
        
        with col4:
            st.markdown('<div class="icon-header"><span style="font-size: 1.8rem;">💡</span><h4 style="margin: 0;">Exposure Insight Generation</h4></div>', unsafe_allow_html=True)
            failed_exp_ins, pending_exp_ins = LookupsDBManager(self.database_context).get_current_processing_status(
                processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN)
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("📄 Pending", pending_exp_ins)
            with metric_col2:
                st.metric("⚠️ Failed", failed_exp_ins)
            
            if pending_exp_ins == 0 and failed_exp_ins == 0:
                st.success("✅ All insights generated successfully", icon="✅")
            else:
                st.info(f"🔄 Generating insights for {pending_exp_ins} documents...")
        
        # Advanced Insight Generation Section with gradient header
        st.markdown("")
        st.markdown('<h2>🧠 Advanced Insight Generation</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #5a6c7d; margin-top: -0.5rem;">Multi-stage AI-powered insight pipelines</p>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3, gap="medium")
        
        with col1:
            st.markdown('<div class="icon-header"><span style="font-size: 1.6rem;">🎯</span><span style="font-weight: 600; color: #2c3e50;">Internalization Insights</span></div>', unsafe_allow_html=True)
            failed_int_ins, pending_int_ins = LookupsDBManager(self.database_context).get_current_processing_status(
                processing_type=Processing_Type().INTERNALIZATION_INSIGHTS_GEN)
            st.metric("Pending Documents", pending_int_ins, delta=f"-{failed_int_ins} failed" if failed_int_ins > 0 else None)
            if pending_int_ins == 0 and failed_int_ins == 0:
                st.success("Complete ✓")
        
        with col2:
            st.markdown('<div class="icon-header"><span style="font-size: 1.6rem;">🔄</span><span style="font-weight: 600; color: #2c3e50;">Exposure → Internalization</span></div>', unsafe_allow_html=True)
            failed_exp_int, pending_exp_int = LookupsDBManager(self.database_context).get_current_processing_status(
                processing_type=Processing_Type().Exp_Int_Insight_GEN)
            st.metric("Pending Documents", pending_exp_int, delta=f"-{failed_exp_int} failed" if failed_exp_int > 0 else None)
            if pending_exp_int == 0 and failed_exp_int == 0:
                st.success("Complete ✓")
        
        with col3:
            st.markdown('<div class="icon-header"><span style="font-size: 1.6rem;">🚀</span><span style="font-weight: 600; color: #2c3e50;">Mitigation Insights</span></div>', unsafe_allow_html=True)
            failed_mit_exp, pending_mit_exp = LookupsDBManager(self.database_context).get_current_processing_status(
                processing_type=Processing_Type().Mitigation_Exp_Insight_GEN)
            st.metric("Pending Documents", pending_mit_exp, delta=f"-{failed_mit_exp} failed" if failed_mit_exp > 0 else None)
            if pending_mit_exp == 0 and failed_mit_exp == 0:
                st.success("Complete ✓")
        
        # Footer tip with enhanced styling
        st.markdown("")
        st.markdown("---")
        st.info("💡 **Pro Tip:** Use the sidebar to switch environments and navigate between sections. Enable auto-refresh for real-time monitoring.", icon="💡")


st_autorefresh(interval=20000, key="fizzbuzzcounter")
startup = StartUpClass()
startup.run_online_Mode()
