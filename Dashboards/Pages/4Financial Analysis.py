import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.DashboardDBManager import DashboardDBManager
import math as Math
import altair as alt
import streamlit.components.v1 as components
import mpld3
import streamlit as st
import mplcursors
from pylab import *
import plotly.express as px
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from st_aggrid import GridOptionsBuilder, AgGrid, ColumnsAutoSizeMode
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity,InternalizationDBEntity, MitigationDBEntity


st.set_page_config(layout="wide")

class StartUpClass:

    def __init__(self) -> None:

        with st.sidebar:

            self.dataset_sector_sl, self.dataset_sector_comp_sl, self.dataset_year_sl, self.dataset_doctype_sl = DashboardDBManager(
                "Test").get_sector_company_year_doctype_list()

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

        exposure_list = DashboardDBManager("Test").get_exposure_insights_by_company(
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


            financial_data = DashboardDBManager('Test').get_financial_metrics(self.sl_company, self.sl_year_start)

            df = pd.DataFrame([vars(metric) for metric in financial_data])

            self.dataset = df.round(2)

            st.table(self.dataset)


    def draw_internalization_financial_analysis_chart(self):
        pass
    
    def draw_mitigation_financial_analysis_chart(self):
        pass

startup = StartUpClass()
