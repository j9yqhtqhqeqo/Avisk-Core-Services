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
from DBEntities.DashboardDBEntitties import InternalizationDBEntity
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity



# internalization_list = DashboardDBManager("Test").get_mitigation_insights()
# df = pd.DataFrame([vars(internalization) for internalization in internalization_list])

st.set_page_config(layout="wide")


class StartUpClass:

    def __init__(self) -> None:

        # self.dataset_original = df.round(2)

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

        self.draw_mitigation_chart()

    def load_data_by_company(self, all_years=False):

        content_type: int
        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        else:
            content_type = 2

        if (all_years):
            internalization_list = DashboardDBManager("Test").get_mitigation_insights(
                self.sl_company, 0, content_type)
        else:
            internalization_list = DashboardDBManager("Test").get_mitigation_insights(
                self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(internalization)
                          for internalization in internalization_list])

        self.dataset = df.round(2)

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype
        # print('=======================INT DATASET========================')
        # print(self.dataset)

    def draw_mitigation_chart(self):
        tab_titles = ['Company', 'Sector',
                      'Sector Vs. Company', 'Company Vs. Competitor']
        # ,
        #               'By ESG Category', 'Year Over Year']
        company_tab,  sector_analysyis_tab, company_sector_tab, company_vs_company_tab = st.tabs(
            tab_titles)

        with company_tab:
            self.draw_summary_chart()

        with sector_analysyis_tab:
            self.create_sector_analysis()

        with company_sector_tab:
            self.create_company_sector_analysis()

        with company_vs_company_tab:
            self.create_competitor_analysis()

        # with details_tab:
        #     self.draw_details()

        # with yoy_tab:
        #     self.draw_yoy_chart()

    def draw_details(self):
        self.load_data_by_company()
        if (not self.dataset.empty):
            chart_data = (alt.Chart(self.dataset)
                          .mark_circle()
                          .encode(
                x=alt.X('Clusters', axis=alt.Axis(title='Pathways',
                        titleFontSize=12, titleFontWeight='bold')),
                y=alt.Y('Score',    axis=alt.Axis(title='Risk Internalization',
                        titleFontSize=12, titleFontWeight='bold')),
                color=alt.Color(
                    'ESG_Category', scale=alt.Scale(scheme="set1")),
                size="Score",
                tooltip=["ESG_Category", "Internalization", "Clusters", "Score"])
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
        self.load_data_by_company(all_years=True)
        if (not self.dataset.empty):
            chart_data = (alt.Chart(self.dataset)
                          .mark_circle()
                          .encode(
                x=alt.X('Clusters', axis=alt.Axis(
                    title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                y=alt.Y('Score',    axis=alt.Axis(
                    title='Risk Internalization', titleFontSize=12, titleFontWeight='bold')),
                color=alt.Color(
                    'ESG_Category', scale=alt.Scale(scheme="set1")),
                size="Score",
                tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Clusters", "Score"])
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

        # Risk Internalization Recognition
        # # of Recognized Pathways

        self.load_data_by_company()
        self.chart_title = 'Recognized Pathways Vs. Risk Mitigation'
        if (not self.dataset.empty):

            chart_data = ((
                alt.Chart(self.dataset)
                .mark_circle()
                .encode(
                    x=alt.X('Clusters', axis=alt.Axis(
                        title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                    y=alt.Y('Score',  axis=alt.Axis(
                        title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                    color=alt.Color(
                        'ESG_Category', scale=alt.Scale(scheme="set1")),
                    size="Score",
                    tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Clusters", "Score"])
            ).properties(width=500, height=500, title=alt.Title(text=self.chart_title, font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
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

            source1 = self.dataset[["ESG_Category", "Exposure_Pathway",
                                    "Internalization",  "Mitigation_Class", "Mitigation_Sub_Class","Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            self.draw_AG_Grid(source, key='int_summary1')
        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_sector_analysis(self):

        internalization_list = DashboardDBManager("Test").get_sector_mitigation_insight(
            self.sl_sector, self.sl_year_start)

        df = pd.DataFrame([vars(internalization)
                          for internalization in internalization_list])

        self.dataset = df.round(2)
        self.chart_title = 'Recognized Pathways Vs. Risk Mitigation'

        self.chart_header = 'Sector:' + "Upstream OIl & Gas Producer" + ', Year:' + \
            str(self.sl_year_start)

        if (not self.dataset.empty):

            sector_chart_data = ((alt.Chart(self.dataset)
                                 .mark_circle()
                                 .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                         y=alt.Y('Score',    axis=alt.Axis(
                                             title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                                         color=alt.Color(
                                             'ESG_Category', scale=alt.Scale(scheme="set1")),
                                         size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"])
                                  ).properties(width=500, height=500,  title=alt.Title(text=self.chart_title, font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
                                 ).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12)

            st.altair_chart(sector_chart_data, use_container_width=True)

            source1 = self.dataset[["ESG_Category", "Exposure_Pathway",
                                    "Internalization",  "Mitigation_Class", "Mitigation_Sub_Class", "Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            self.draw_AG_Grid(source, key='int_sector_analysis1')
        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_competitor_analysis(self):
        self.data_set_competitor = self.dataset_comp_sl.copy(deep=True)
        self.sl_competitor = st.selectbox(
            'Competitor:', (self.data_set_competitor), index=0)

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == 'Financial Report'):
            content_type = 2

        company_internalization_list = DashboardDBManager("Test").get_mitigation_insights(
            self.sl_company, self.sl_year_start, content_type)
        df = pd.DataFrame([vars(internalization)
                          for internalization in company_internalization_list])
        self.company_dataset = df.round(2)
        self.company_chart_header = self.sl_company + \
            ' Year:' + str(self.sl_year_start)

        competitor_internalization_list = DashboardDBManager("Test").get_mitigation_insights(
            self.sl_competitor, self.sl_year_start, content_type)
        df = pd.DataFrame([vars(internalization)
                          for internalization in competitor_internalization_list])

        self.competitor_dataset = df.round(2)
        # print('Competitor')
        # print(self.competitor_dataset)
        self.competitor_chart_header = self.sl_competitor + \
            ' Year:' + str(self.sl_year_start)

        if (not self.company_dataset.empty):
            company_chart_data = (alt.Chart(self.company_dataset)
                                  .mark_circle()
                                  .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                          y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]),   axis=alt.Axis(
                                              title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                                          color=alt.Color(
                                              'ESG_Category', scale=alt.Scale(scheme="set1")),
                                          size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Clusters", "Score"])).properties(width=300, height=300,
                                                                                                                                              title=alt.Title(self.company_chart_header, fontSize=12, anchor='middle'))
        if (not self.competitor_dataset.empty):
            competitor_chart_data = (alt.Chart(self.competitor_dataset)
                                     .mark_circle()
                                     .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                             y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]),   axis=alt.Axis(
                                                 title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                                             color=alt.Color(
                                                 'ESG_Category', scale=alt.Scale(scheme="set1")),
                                             size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Clusters", "Score"])).properties(width=300, height=300, title=alt.Title(self.competitor_chart_header, fontSize=12, anchor='middle'))

        no_company_data = no_competitor_data = False
        if (self.company_dataset.empty):
            no_company_data = True
            st.text('No Data Found for the Company & Year Combination')

        if (self.competitor_dataset.empty):
            no_competitor_data = True
            st.text('No Data Found for the Competitor & Year Combination')

        if (not no_company_data and not no_competitor_data):
            # st.subheader('Recognized Pathways Vs. Risk Internalization')
            st.altair_chart((company_chart_data |
                            competitor_chart_data).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12).properties(title='Recognized Pathways Vs. Risk Internalization').configure_title(font='Courier', fontSize=20, anchor='middle'))

            # Configure Data Grids

            copmany_table_header = 'Company: ' + self.sl_company
            st.subheader(copmany_table_header)
            ds2 = self.company_dataset[["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds2["Rank"] = ds2["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds2[["Rank", "ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"]], key='int_comppetitor1')

            competitor_table_header = 'Competitor: ' + self.sl_competitor
            st.subheader(competitor_table_header)

            ds = self.competitor_dataset[["ESG_Category", "Exposure_Pathway", "Mitigation_Class", "Mitigation_Sub_Class", "Internalization", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds["Rank"] = ds["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds[["Rank", "ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"]], key='int_comppetitor2')

    def create_company_sector_analysis(self):

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == 'Financial Report'):
            content_type = 2

        company_internalization_list = DashboardDBManager("Test").get_mitigation_insights(
            self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(internalization)
                          for internalization in company_internalization_list])

        self.company_dataset = df.round(2)

        self.company_chart_header = self.sl_company + \
            ' Year:' + str(self.sl_year_start)

        sector_internalization_list = DashboardDBManager("Test").get_sector_mitigation_insight(
            self.sl_sector, self.sl_year_start)

        df = pd.DataFrame([vars(internalization)
                          for internalization in sector_internalization_list])

        self.sector_dataset = df.round(2)

        # Configure Charts
        self.sector_chart_header = self.sl_sector + \
            '   Year:' + str(self.sl_year_start)

        if (not self.company_dataset.empty):
            company_chart_data = (alt.Chart(self.company_dataset)
                                  .mark_circle()
                                  .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                          y=alt.Y('Score',    axis=alt.Axis(
                                              title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                                          color=alt.Color(
                                              'ESG_Category', scale=alt.Scale(scheme="set1")),
                                          size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"])).properties(width=300, height=300,
                                                                                                                                              title=alt.Title(self.company_chart_header, fontSize=12, anchor='middle'))
        print('Sector Data==========================')
        print(self.sector_dataset)
        if (not self.sector_dataset.empty):
            sector_chart_data = (alt.Chart(self.sector_dataset)
                                 .mark_circle()
                                 .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                         y=alt.Y('Score',    axis=alt.Axis(
                                             title='Risk Mitigation', titleFontSize=12, titleFontWeight='bold')),
                                         color=alt.Color(
                                             'ESG_Category', scale=alt.Scale(scheme="set1")),
                                         size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class", "Score"])).properties(width=300, height=300, title=alt.Title(self.sector_chart_header, fontSize=12, anchor='middle'))



        if (not self.company_dataset.empty):
            st.altair_chart((sector_chart_data |
                            company_chart_data).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12).properties(title='Recognized Pathways Vs. Risk Mitigation').configure_title(font='Courier', fontSize=20, anchor='middle'))

            # Configure Data Grids

            sector_table_header = 'Sector Ranking: ' + self.sl_sector
            st.subheader(sector_table_header)

            ds = self.sector_dataset[["ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class" ,"Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds["Rank"] = ds["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds[["Rank", "ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class"]], key='int_sector1')

            copmany_table_header = 'Company Ranking: ' + self.sl_company
            st.subheader(copmany_table_header)
            ds2 = self.company_dataset[["ESG_Category", "Exposure_Pathway", "Internalization","Mitigation_Class", "Mitigation_Sub_Class", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds2["Rank"] = ds2["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds2[["Rank", "ESG_Category", "Exposure_Pathway", "Internalization", "Mitigation_Class", "Mitigation_Sub_Class"]], key='int_sector2')

        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_AG_Grid(self, data_source, key):
        gb = GridOptionsBuilder.from_dataframe(data_source)
        gb.configure_column(field='ESG_Category',
                            header_name='ESG Catagory')
        gb.configure_column(field='Exposure_Pathway',
                            header_name='Risk Exposure')
        # other_options = {'suppressColumnVirtualisation': True}
        # gb.configure_grid_options(**other_options)
        gb.configure_default_column(
            flex=1,
            minWidth=20,
            maxWidth=1000,
            resizable=True,
        )
        gridOptions = gb.build()

        AgGrid(
            data_source,
            gridOptions=gridOptions, reload_data=True,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW, key=key
        )


startup = StartUpClass()
