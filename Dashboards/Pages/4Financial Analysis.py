from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity, InternalizationDBEntity, MitigationDBEntity
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from st_aggrid import GridOptionsBuilder, AgGrid, ColumnsAutoSizeMode
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from pylab import *
import streamlit as st
import mpld3
import streamlit.components.v1 as components
import altair as alt
import math as Math
from DBEntities.DashboardDBManager import DashboardDBManager
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

# import mplcursors

# Professional compact styling
st.markdown("""
<style>
    .stApp { padding-top: 0rem !important; margin-top: 0rem !important; }
    .block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; padding-left: 1rem !important; padding-right: 1rem !important; margin-top: 0rem !important; max-width: 100% !important; }
    .main { padding-top: 0rem !important; }
    .main .block-container { padding-top: 0rem !important; margin-top: 0rem !important; }
    header { padding-top: 0rem !important; margin-top: 0rem !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; margin-top: 0rem !important; }
    [data-testid="stHeader"] { display: none !important; }
    section.main { padding-top: 0rem !important; }
    section.main > div { padding-top: 0rem !important; margin-top: 0rem !important; }
    h1 { color: #0068C9; font-weight: 700; font-size: 1.8rem; margin-top: 0rem !important; padding-top: 0rem !important; }
    h2 { color: #262730; font-weight: 600; font-size: 1.2rem; }
    h3 { color: #4A4A4A; font-weight: 500; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# st.set_page_config removed - configured in Home.py

class StartUpClass:

    def __init__(self) -> None:

        with st.sidebar:

            self.dataset_sector_sl, self.dataset_sector_comp_sl, self.dataset_year_sl, self.dataset_doctype_sl = DashboardDBManager(
                "Development").get_sector_company_year_doctype_list()

            self.sl_sector = st.selectbox(
                'Sector:', (self.dataset_sector_sl))

            self.dataset_sector_comp_df = pd.DataFrame(
                [vars(comp_sector) for comp_sector in self.dataset_sector_comp_sl])

            data_filter = self.dataset_sector_comp_df["Sector"] == self.sl_sector
            self.dataset_comp_sector_selected_df = self.dataset_sector_comp_df[[
                "Sector", "Company"]].where(data_filter).dropna()

            self.dataset_comp_sl = self.dataset_comp_sector_selected_df[[
                "Company"]].drop_duplicates().dropna()

            self.sl_company = st.selectbox(
                'Company:', (self.dataset_comp_sl), index=0)

            self.sl_year_start = st.selectbox(
                'Year:', (self.dataset_year_sl), index=0)

            self.sl_doctype = st.selectbox(
                'Document Type:', (self.dataset_doctype_sl), index=0)

        self.draw_financial_analysis_chart()

    def draw_financial_analysis_chart(self):
        tab_titles = ['Exposure', 'Internalization', 'Mitigation']

        exposure_tab,  internalization_tab,  mitigation_tab = st.tabs(
            tab_titles)

        with exposure_tab:
            self.draw_expoure_financial_analysis_chart()

        with internalization_tab:
            self.draw_internalization_financial_analysis_chart()

        with mitigation_tab:
            self.draw_mitigation_financial_analysis_chart()

    def draw_expoure_financial_analysis_chart(self):
        content_type: int
        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        else:
            content_type = 2

        exposure_list = DashboardDBManager("Development").get_exposure_insights_by_company(
            self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(exposure) for exposure in exposure_list])

        self.dataset = df.round(2)

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype

        self.chart_title = 'Recognized Pathways Vs. Risk Exposure Recognition'
        if (not self.dataset.empty):

            chart_data = ((
                alt.Chart(self.dataset)
                .mark_circle()
                .encode(
                    x=alt.X('Clusters', axis=alt.Axis(
                        title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                    y=alt.Y('Score',  axis=alt.Axis(
                        title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                    color=alt.Color('ESG_Category'),
                    size="Score",
                    tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
            )
                .properties(width=200, height=400, title=alt.Title(text=self.chart_title, font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
                .configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12)
                .configure_header()
                .configure_axis(grid=True)
                .interactive()
            )
            st.altair_chart(chart_data, use_container_width=True)

            financial_data = DashboardDBManager('Development').get_financial_metrics(
                self.sl_company, self.sl_year_start)

            df = pd.DataFrame([vars(metric) for metric in financial_data])

            self.dataset = df.round(2)

            st.table(self.dataset)

    def draw_internalization_financial_analysis_chart(self):
        pass

    def draw_mitigation_financial_analysis_chart(self):
        pass


startup = StartUpClass()
