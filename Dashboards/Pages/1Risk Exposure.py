from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity
from st_aggrid import GridOptionsBuilder, AgGrid, ColumnsAutoSizeMode, GridUpdateMode
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


exposure_list = DashboardDBManager("Test").get_exposure_insights()
df = pd.DataFrame([vars(exposure) for exposure in exposure_list])


class StartUpClass:

    def __init__(self) -> None:
        # df = pd.read_excel(
        #     "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")
        # self.dataset_original = df[["Company", "Year", "Document Type", "ESG Category",
        #                             "Exposure Pathway", "Clusters", "Score"]].round(2)

        self.dataset_original = df.round(2)

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

        self.draw_exposure_chart()

    def load_data_by_company(self):

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
        data_filter = self.dataset_original["Company"] == self.sl_company
        dataset_comp = self.dataset_original.where(data_filter).dropna()

        data_filter = dataset_comp["Document_Type"] == self.sl_doctype
        self.dataset = dataset_comp.where(data_filter).dropna()

        self.chart_header = 'Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start) + ', Document:'+self.sl_doctype

        # df = self.dataset.copy(deep=True)

        # print(df)
        # df['rank'] = df.groupby('Year')['Score'].rank('first')

        self.dataset["Rank"] = self.dataset.groupby('Year')["Score"].rank(
            ascending=False, method='first')

        data_filter = self.dataset["Rank"] <= 5
        self.dataset_ranked = self.dataset.where(data_filter).dropna().sort_values(by=[
            'Exposure_Pathway', 'Score'])

        print('Data Ranked')
        print(self.dataset_ranked)

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
        tab_titles = ['Company', 'Sector', 'Sector Vs. Company', 'Company Vs. Competitor',
                      "Top Exposure by Year", "Exposure Trend", "Financial Analysis"]
        company_tab,  sector_analysyis_tab, company_sector_tab, company_vs_company_tab, company_by_year_tab,  trend_tab, finance_tab = st.tabs(
            tab_titles)

        with company_tab:
            self.draw_summary_chart()

        with sector_analysyis_tab:
            self.create_sector_analysis()

        with company_sector_tab:
            self.create_company_sector_analysis()

        with company_vs_company_tab:
            self.create_competitor_analysis()

        with company_by_year_tab:
            self.draw_yoy_chart()

        with trend_tab:
            self.draw_trend_chart()

        with finance_tab:
            self.draw_financial_charts()

        css = '''
        <style>
            .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size:12px;
            font-weight: bold;
            }
        </style>
        '''
        st.markdown(css, unsafe_allow_html=True)

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
                y=alt.Y('Score',    axis=alt.Axis(title='Risk Exposure',
                        titleFontSize=12, titleFontWeight='bold')),
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

        if (not self.dataset_ranked.empty):
            chart_data = (alt.Chart(self.dataset_ranked)
                          .mark_bar(size=30, cornerRadiusTopLeft=3,
                                    cornerRadiusTopRight=3)
                          .encode(
                x=alt.X('Year:N', axis=alt.Axis(
                    title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                y=alt.Y('Score:Q',    axis=alt.Axis(
                    title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                color='ESG_Category',
                order=alt.Order(
                    'Rank',
                    sort='ascending'
                ),
                tooltip=["ESG_Category", "Exposure_Pathway", "Clusters", "Score"])
                # .properties(height=500,)
                .properties(width=250, height=250))
            st.altair_chart(chart_data, use_container_width=True)
        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_trend_chart(self):
        if (self.dataset_ranked.empty):
            self.load_data_by_year()

        if (not self.dataset_ranked.empty):
            click = alt.selection_single(encodings=['color'])

            exp_dataset = self.dataset_ranked[[
                "Exposure_Pathway"]].drop_duplicates()
            print('exp_dataset')
            print(exp_dataset)
            exp_dataset["Rank"] = exp_dataset.rank()["Exposure_Pathway"]
            exp_chart = (alt.Chart(data=exp_dataset)
                         .mark_square(size=200)
                         .encode(x=alt.X("Rank", axis=alt.Axis(title=None)), y=alt.Y("count(Exposure_Pathway)", title=None), color=alt.Color('Exposure_Pathway', legend=None), tooltip="Exposure_Pathway")
                         .properties(height=20, width=500, title=alt.Title(text="Exposure Pathway", font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
                         .add_selection(click)
                         )

            exp_trend_dataset = exp_dataset = self.dataset_ranked[[
                'Year', 'Exposure_Pathway', 'Score']]
            print('exp_trend_dataset')
            print(exp_trend_dataset)
            line_chart = (alt.Chart(exp_trend_dataset)
                          .mark_square(size=200)
                          .encode(x=alt.X('Year:N', axis=alt.Axis(title='Year', titleFontSize=12, titleFontWeight='bold', labelAngle=270)),
                                  y=alt.Y('Score:Q', axis=alt.Axis(
                                      title='Risk Exposure', titleFontSize=12, titleFontWeight='bold'), scale=alt.Scale(domain=[0, 100])),
                                  color='Exposure_Pathway', tooltip=["Score"])
                          .properties(height=250, width=500, title=alt.Title(text='Exposure Pathway Trend by Year', font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
                          .transform_filter(click)
                          )

            chart = exp_chart & line_chart
            chart.resolve = {
                "legend": {
                    "color": "independent",
                    "size": "independent"
                }
            }

            st.altair_chart((chart))
        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_summary_chart(self):

        # Risk Exposure Recognition
        # # of Recognized Pathways

        self.load_data_by_company()
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
                .properties(width=500, height=500, title=alt.Title(text=self.chart_title, font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
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

            source1 = self.dataset[["ESG_Category",
                                    "Exposure_Pathway", "Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            self.draw_AG_Grid(source, key='exp_summary1')
        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_sector_analysis(self):

        exposure_list = DashboardDBManager("Test").get_sector_exposure_insight(
            self.sl_sector, self.sl_year_start)

        df = pd.DataFrame([vars(exposure) for exposure in exposure_list])

        self.dataset = df.round(2)
        self.chart_title = 'Recognized Pathways Vs. Risk Exposure'

        self.chart_header = 'Sector:' + self.sl_sector + ', Year:' + \
            str(self.sl_year_start)

        if (not self.dataset.empty):

            sector_chart_data = ((alt.Chart(self.dataset)
                                 .mark_circle()
                                 .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                         y=alt.Y('Score',    axis=alt.Axis(
                                             title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                                         color=alt.Color('ESG_Category'),
                                         size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])
                                  ).properties(width=500, height=500,  title=alt.Title(text=self.chart_title, font='Courier', fontSize=20, subtitle=self.chart_header, subtitleFont='Courier', subtitleFontSize=12, anchor='middle'))
                                 ).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12)

            st.altair_chart(sector_chart_data, use_container_width=True)

            source1 = self.dataset[["ESG_Category",
                                    "Exposure_Pathway", "Score"]].round(2)
            source = source1.sort_values(by='Score', ascending=False)

            self.draw_AG_Grid(source, key='exp_sector_analysis')
        else:
            st.text('No Data Found for the Company & Year Combination')

    def create_competitor_analysis(self):
        self.data_set_competitor = self.dataset_comp_sl.copy(deep=True)
        self.sl_competitor = st.selectbox(
            'competitor:', (self.data_set_competitor), index=0)

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == 'Financial Report'):
            content_type = 2

        company_exposure_list = DashboardDBManager("Test").get_exposure_insights_by_company(
            self.sl_company, self.sl_year_start, content_type)
        df = pd.DataFrame([vars(exposure)
                          for exposure in company_exposure_list])
        self.company_dataset = df.round(2)
        self.company_chart_header = self.sl_company + \
            ' Year:' + str(self.sl_year_start)

        competitor_exposure_list = DashboardDBManager("Test").get_exposure_insights_by_company(
            self.sl_competitor, self.sl_year_start, content_type)
        df = pd.DataFrame([vars(exposure)
                          for exposure in competitor_exposure_list])

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
                                              title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                                          color=alt.Color('ESG_Category'),
                                          size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=300, height=300,
                                                                                                                           title=alt.Title(self.company_chart_header, fontSize=12, anchor='middle'))
        if (not self.competitor_dataset.empty):
            competitor_chart_data = (alt.Chart(self.competitor_dataset)
                                     .mark_circle()
                                     .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                             y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]),   axis=alt.Axis(
                                                 title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                                             color=alt.Color('ESG_Category'),
                                             size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=300, height=300, title=alt.Title(self.competitor_chart_header, fontSize=12, anchor='middle'))

        no_company_data = no_competitor_data = False
        if (self.company_dataset.empty):
            no_company_data = True
            st.text('No Data Found for the Company & Year Combination')

        if (self.competitor_dataset.empty):
            no_competitor_data = True
            st.text('No Data Found for the Competitor & Year Combination')

        if (not no_company_data and not no_competitor_data):
            # st.subheader('Recognized Pathways Vs. Risk Exposure')
            st.altair_chart((company_chart_data |
                            competitor_chart_data).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12).properties(title='Recognized Pathways Vs. Risk Exposure').configure_title(font='Courier', fontSize=20, anchor='middle'))

            copmany_table_header = 'Company Ranking: ' + self.sl_company
            st.subheader(copmany_table_header)
            ds2 = self.company_dataset[["ESG_Category", "Exposure_Pathway", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds2["Rank"] = ds2["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds2[["Rank", "ESG_Category", "Exposure_Pathway", "Score"]], key='exp_competetor1')

            competitor_table_header = 'Competitor Ranking: ' + self.sl_competitor
            st.subheader(competitor_table_header)

            ds = self.competitor_dataset[["ESG_Category", "Exposure_Pathway", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds["Rank"] = ds["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds[["Rank", "ESG_Category", "Exposure_Pathway", "Score"]], key='exp_competetor2')

            # print('Competitor Dataset')
            # print(self.competitor_dataset)

    def create_company_sector_analysis(self):

        if (self.sl_doctype == 'Sustainability Report'):
            content_type = 1
        elif (self.sl_doctype == 'Financial Report'):
            content_type = 2

        company_exposure_list = DashboardDBManager("Test").get_exposure_insights_by_company(
            self.sl_company, self.sl_year_start, content_type)

        df = pd.DataFrame([vars(exposure)
                          for exposure in company_exposure_list])

        self.company_dataset = df.round(2)

        self.company_chart_header = self.sl_company + \
            ' Year:' + str(self.sl_year_start)

        sector_exposure_list = DashboardDBManager("Test").get_sector_exposure_insight(
            self.sl_sector, self.sl_year_start)

        df = pd.DataFrame([vars(exposure)
                          for exposure in sector_exposure_list])

        self.sector_dataset = df.round(2)

        self.sector_chart_header = self.sl_sector + \
            '   Year:' + str(self.sl_year_start)

        if (not self.company_dataset.empty):
            company_chart_data = (alt.Chart(self.company_dataset)
                                  .mark_circle()
                                  .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                          y=alt.Y('Score',    axis=alt.Axis(
                                              title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                                          color=alt.Color('ESG_Category'),
                                          size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=300, height=300,
                                                                                                                           title=alt.Title(self.company_chart_header, fontSize=12, anchor='middle'))

        if (not self.sector_dataset.empty):
            sector_chart_data = (alt.Chart(self.sector_dataset)
                                 .mark_circle()
                                 .encode(x=alt.X('Clusters', axis=alt.Axis(title='Pathways', titleFontSize=12, titleFontWeight='bold')),
                                         y=alt.Y('Score',    axis=alt.Axis(
                                             title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                                         color=alt.Color('ESG_Category'),
                                         size="Score", tooltip=["ESG_Category", "Exposure_Pathway", "Score"])).properties(width=300, height=300, title=alt.Title(self.sector_chart_header, fontSize=12, anchor='middle'))

        if (not self.company_dataset.empty):
            st.altair_chart((sector_chart_data |
                            company_chart_data).configure_legend(
                strokeColor='gray',
                fillColor='#EEEEEE',
                padding=5,
                cornerRadius=2,
                labelFontSize=10, titleFontSize=12).properties(title='Recognized Pathways Vs. Risk Exposure').configure_title(font='Courier', fontSize=20, anchor='middle'))

            sector_table_header = 'Sector Ranking: ' + self.sl_sector
            st.subheader(sector_table_header)
            ds = self.sector_dataset[["ESG_Category", "Exposure_Pathway", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds["Rank"] = ds["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds[["Rank", "ESG_Category", "Exposure_Pathway"]], key='exp_sector1')

            copmany_table_header = 'Company Ranking: ' + self.sl_company
            st.subheader(copmany_table_header)
            ds2 = self.company_dataset[["ESG_Category", "Exposure_Pathway", "Score"]].sort_values(
                'Score', ascending=False).head(10)
            ds2["Rank"] = ds2["Score"].rank(ascending=False, method='first')
            self.draw_AG_Grid(
                ds2[["Rank", "ESG_Category", "Exposure_Pathway"]], key='exp_sector2')
        else:
            st.text('No Data Found for the Company & Year Combination')

    def draw_financial_charts(self):
        pass

    def draw_AG_Grid(self, data_source, key):
        gb = GridOptionsBuilder.from_dataframe(data_source)
        gb.configure_column(field='ESG_Category', header_name='ESG Catagory',)
        gb.configure_column(field='Exposure_Pathway',
                            header_name='Risk Exposure')
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
