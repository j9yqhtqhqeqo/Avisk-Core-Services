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
from st_aggrid import AgGrid
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity



class StartUpClass:

    def __init__(self) -> None:

        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/ARInternalization Data_AR.xlsx")
        self.dataset_original = df[["Company", "Year", "Document_Type", "ESG_Category",
                                    "Exposure_Pathway","Internalization", "Clusters", "Score"]].round(2)


        # internalization_list = DashboardDBManager("Test").get_internalization_insights()

        # df = pd.DataFrame([vars(item) for item in internalization_list])

        self.dataset_original = df.round(2)

        # print(self.dataset_original)

        self.dataset_comp_sl = self.dataset_original["Company"].drop_duplicates(
        ).dropna()
        self.dataset_year_sl = self.dataset_original["Year"].drop_duplicates(
        ).dropna().sort_values()

        self.dataset_doctype = self.dataset_original["Document_Type"].drop_duplicates(
        ).dropna()

        with st.sidebar:
            self.sl_company = st.selectbox(
                'Company:', (self.dataset_comp_sl), index=0)

            self.sl_year_start = st.selectbox(
                'Year:', (self.dataset_year_sl), index=0)

            # self.sl_year_end = st.selectbox(
            #     'End Year:', (self.dataset_year_sl), index=0)

            self.sl_doctype = st.selectbox(
                'Document Type:', (self.dataset_doctype), index=0)

        self.draw_exposure_chart()

    def load_data_by_company(self):
        # 'Chesapeake Energy'
        data_filter = self.dataset_original["Company"] == self.sl_company
        dataset_comp = self.dataset_original.where(data_filter).dropna()

        data_filter = dataset_comp["Year"] == self.sl_year_start  # 2022
        dataset_year = dataset_comp.where(data_filter).dropna()

        # 'Sustainability Report'
        data_filter = dataset_year["Document_Type"] == self.sl_doctype
        self.dataset = dataset_year.where(data_filter).dropna()

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype

    def load_data_by_year(self):
        # 'Chesapeake Energy'
        data_filter = self.dataset_original["Company"] == self.sl_company
        dataset_comp = self.dataset_original.where(data_filter).dropna()

        # 'Sustainability Report'
        data_filter = dataset_comp["Document_Type"] == self.sl_doctype
        self.dataset = dataset_comp.where(data_filter).dropna()

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype

    def draw_exposure_chart(self):
        tab_titles = ['Summary', 'Details', 'YoY View']
        tab1,  tab2, tab4 = st.tabs(tab_titles)

        with tab1:
            self.draw_summary_chart()
        # with tab2:
        #     self.draw_subplots()

        with tab2:
            self.draw_details()

        with tab4:
            self.draw_yoy_chart()

    def draw_details(self):
        self.load_data_by_company()
        chart_data = (alt.Chart(self.dataset)
                      .mark_circle()
                      .encode(
            x='Clusters',
            y='Score',
            color='ESG_Category',
            size="Score",
            tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
            .properties(height=500,)
            .properties(
            width=250,
            height=250)
            .facet(
            facet='ESG_Category',
            columns=3))
        st.altair_chart(chart_data, use_container_width=True)

    def draw_yoy_chart(self):
        self.load_data_by_year()
        chart_data = (alt.Chart(self.dataset)
                      .mark_circle()
                      .encode(
            x='Clusters',
            y='Score',
            color='ESG_Category',
            size="Score",
            tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
            .properties(height=500,)
            .properties(
            width=250,
            height=250)
            .facet(
            facet='Year',
            columns=3))
        st.altair_chart(chart_data, use_container_width=True)

    def draw_summary_chart(self):

        # Financial Implication Recognition
        self.load_data_by_company()
        print("Data Used in Chart")
        print(self.dataset)
        chart_data = (
            alt.Chart(self.dataset)
            .mark_circle()
            .encode(alt.X("Clusters").scale(domain=(0, 100)), alt.Y("Score").scale(domain=(0, 100)), size="Score", color='ESG_Category', tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Clusters", "Score"])
            .properties(height=500,width = 1000,
                        title=alt.Title('Internalization Clusters vs. Score', subtitle=self.chart_header)).configure_title(fontSize=20, font='Courier', anchor='middle', subtitleFontSize=10, subtitleFont='Courier')
            .configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12)
            .configure_header()
            .configure_axis(grid=True)
            .interactive()
            # .configure_range(
            #     category={'scheme': 'dark2'})
        )
        st.altair_chart(chart_data, use_container_width=True)

        source1 = self.dataset[["ESG_Category",
                                "Exposure_Pathway", "Internalization","Score"]].round(2)
        source = source1.sort_values(by='Score', ascending=False)
        # st.dataframe(source,
        #              column_config={
        #                  "widgets": st.column_config.TextColumn(
        #                      label ="ESG_Category",
        #                      width="large",
        #                  )
        #              },
        #              hide_index=True,)

        AgGrid(source)


# display only 15 rows
startup = StartUpClass()
# # startup.populate_filters()
