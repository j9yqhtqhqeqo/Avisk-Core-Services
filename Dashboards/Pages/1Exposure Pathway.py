from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity
from st_aggrid import AgGrid
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from pylab import *
import mplcursors
import streamlit as st
import mpld3
import streamlit.components.v1 as components
import altair as alt
import math as Math
from DBEntities.DashboardDBManager import DashboardDBManager
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


class StartUpClass:

    def __init__(self) -> None:
        # df = pd.read_excel(
        #     "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")
        # self.dataset_original = df[["Company", "Year", "Document Type", "ESG Category",
        #                             "Exposure Pathway", "Clusters", "Score"]].round(2)

        exposure_list = DashboardDBManager("Test").get_exposure_insights()

        df = pd.DataFrame([vars(exposure) for exposure in exposure_list])

        self.dataset_original = df.round(2)

        print(self.dataset_original)

        self.dataset_sector_sl = self.dataset_original["Sector"].drop_duplicates(
        ).dropna()

        self.dataset_comp_sl = self.dataset_original["Company"].drop_duplicates(
        ).dropna()
        self.dataset_year_sl = self.dataset_original["Year"].drop_duplicates(
        ).dropna().sort_values(ascending=False)

        self.dataset_doctype = self.dataset_original["Document_Type"].drop_duplicates(
        ).dropna()

        with st.sidebar:
            self.sl_sector = st.selectbox(
                'Sector:', (self.dataset_sector_sl), index=0)

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

        # # 'Chesapeake Energy'
        # data_filter = self.dataset_original["Company"] == self.sl_company
        # dataset_comp = self.dataset_original.where(data_filter).dropna()

        # data_filter = dataset_comp["Year"] == self.sl_year_start  # 2022
        # dataset_year = dataset_comp.where(data_filter).dropna()

        # # 'Sustainability Report'
        # data_filter = dataset_year["Document_Type"] == self.sl_doctype
        # self.dataset = dataset_year.where(data_filter).dropna()

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

    def load_data_by_year(self):
        # 'Chesapeake Energy'
        data_filter = self.dataset_original["Company"] == self.sl_company
        dataset_comp = self.dataset_original.where(data_filter).dropna()

        # 'Sustainability Report'
        data_filter = dataset_comp["Document_Type"] == self.sl_doctype
        self.dataset = dataset_comp.where(data_filter).dropna()

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype

    def load_chart_data_start_end_year(self):
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

    def draw_exposure_chart(self):
        tab_titles = ['Company', 'Sector', 'Company - Sector Analysis',
                      'Company Details', 'Year Over Year']
        company_tab,  sector_analysyis_tab, company_sector_tab, details_tab, yoy_tab = st.tabs(
            tab_titles)

        with company_tab:
            self.draw_summary_chart()
        with sector_analysyis_tab:
            self.create_sector_analysis()

        with company_sector_tab:
            self.create_company_sector_analysis()

        with details_tab:
            self.draw_details()

        with yoy_tab:
            self.draw_yoy_chart()

    def draw_details(self):
        self.load_data_by_company()
        if (not self.dataset.empty):
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
        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_yoy_chart(self):
        self.load_data_by_year()
        if (not self.dataset.empty):
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
        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_summary_chart(self):

        # Risk Exposure Recognition
        # # of Recognized Pathways

        self.load_data_by_company()

        if (not self.dataset.empty):

            chart_data = (
                alt.Chart(self.dataset)
                .mark_circle()
                .encode(alt.X("Clusters").scale(domain=(0, 100)), alt.Y("Score").scale(domain=(0, 100)), size="Score", color='ESG_Category', tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
                .properties(height=500,
                            title=alt.Title('Exposure Pathway Clusters vs. Score', subtitle=self.chart_header)).configure_title(fontSize=20, font='Courier', anchor='middle', subtitleFontSize=10, subtitleFont='Courier')
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
                                    "Exposure_Pathway", "Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            AgGrid(source)
        else:
            st.text('No Data Found for the Company & Year Combination')

        # print(source)
        # fig, ax = plt.subplots()

        # # hide axes
        # fig.patch.set_visible(False)
        # ax.axis('off')
        # ax.axis('tight')

        # the_table = ax.table(cellText=source.values, colLabels=source.columns, loc='left')
        # the_table.auto_set_font_size(False)
        # the_table.set_fontsize(10)

        # the_table.width = 1500
        # # fig.tight_layout()

        # st.pyplot(fig)

        # table_data = self.table(source[:15]).properties(width=1500)
        # table_data = self.table(source).properties(width=1000)

        # st.altair_chart(table_data)

    def create_sector_analysis(self):

        exposure_list = DashboardDBManager("Test").get_sector_exposure_insight(
            self.sl_company, self.sl_year_start)

        df = pd.DataFrame([vars(exposure) for exposure in exposure_list])

        self.dataset = df.round(2)

        self.chart_header = 'Sector:' + "Upstream OIl & Gas Producer" + ', Year:' + \
            str(self.sl_year_start)

        if (not self.dataset.empty):

            chart_data = (
                alt.Chart(self.dataset)
                .mark_circle()
                .encode(alt.X("Clusters"), alt.Y("Score"), size="Score", color='ESG_Category', tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
                .properties(height=500,
                            title=alt.Title('Exposure Pathway Clusters vs. Score', subtitle=self.chart_header)).configure_title(fontSize=20, font='Courier', anchor='middle', subtitleFontSize=10, subtitleFont='Courier')
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
                                    "Exposure_Pathway", "Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            AgGrid(source)
        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_company_sector_analysis2(self):

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == '10K'):
            content_type = 2

        exposure_list = DashboardDBManager("Test").get_sector_exposure_company_insight(
            self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(exposure) for exposure in exposure_list])

        self.dataset = df.round(2)

        print(self.dataset)

        self.chart_header = 'Sector:' + "Upstream OIl & Gas Producer" + ', Year:' + \
            str(self.sl_year_start)

        if (not self.dataset.empty):
            chart_data = (alt.Chart(self.dataset)
                          .mark_circle()
                          .encode(
                x='Clusters',
                y='Score',
                color='ESG_Category',
                size="Score",
                tooltip=["ESG_Category", "Exposure_Pathway", "Score"])
                .properties(height=500,)
                .properties(
                width=250,
                height=250)
                .facet(
                facet='Document_Type',
                columns=2))
            st.altair_chart(chart_data, use_container_width=True)

        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_company_sector_analysis(self):

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == '10K'):
            content_type = 2

        company_exposure_list = DashboardDBManager("Test").get_exposure_insights_by_company(
            self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(exposure)
                          for exposure in company_exposure_list])

        self.company_dataset = df.round(2)

        self.company_chart_header = self.sl_company + ', Year:' + \
            str(self.sl_year_start)

        sector_exposure_list = DashboardDBManager("Test").get_sector_exposure_insight(
            self.sl_company, self.sl_year_start)

        df = pd.DataFrame([vars(exposure)
                          for exposure in sector_exposure_list])

        self.sector_dataset = df.round(2)

        self.sector_chart_header = 'Sector:' + 'Test' + ', Year:' + \
            str(self.sl_year_start)

        if (not self.company_dataset.empty):
            company_chart_data = (alt.Chart(self.company_dataset)
                                  .mark_circle()
                                  .encode(x=alt.X('Clusters', axis=alt.Axis(title='Recognized Pathways', titleFontSize=12)),
                                          y=alt.Y('Score',    axis=alt.Axis(
                                              title='Risk Exposure Recognition', titleFontSize=12)),
                                          color=alt.Color('ESG_Category'),
                                          size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=250, height=250,
                                                                                                                           title=alt.Title(self.company_chart_header, fontSize=12, anchor='middle'))

        if (not self.sector_dataset.empty):
            sector_chart_data = (alt.Chart(self.sector_dataset, title=self.sector_chart_header)
                                 .mark_circle()
                                 .encode(x=alt.X('Clusters', axis=alt.Axis(title='Recognized Pathways', titleFontSize=12)),
                                         y=alt.Y('Score',    axis=alt.Axis(
                                             title='Risk Exposure Recognition', titleFontSize=12)),
                                         color=alt.Color('ESG_Category'),
                                         size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=250, height=250)

        if (not self.company_dataset.empty):
            st.altair_chart((sector_chart_data |
                            company_chart_data).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12))

        else:
            st.text('No Data Found for the Company & Year Combination')


# display only 15 rows
startup = StartUpClass()
# # startup.populate_filters()
