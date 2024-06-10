import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import altair as alt


import pandas as pd
import numpy as np

import matplotlib as mpl
import matplotlib.patches as patches
from matplotlib import pyplot as plt



from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity
from DBEntities.DashboardDBManager import DashboardDBManager, Triangle_Chart_DB_Entity
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity, InternalizationDBEntity, MitigationDBEntity, Top10_Chart_DB_Entity, Triangle_Chart_DB_Entity, YOY_DB_Entity, Exposure_Control_Chart_DB_Entity

from Utilities.TriangleChartHelper import radar_factory

class StartUpClass:

    def __init__(self) -> None:

        # Global Variables
        self.exposure_list = []
        self.triangle_data_list = []
        self.yoy_exposure_list =[]
        self.exposure_vs_control_list =[]


        with st.sidebar:

            self.dataset_sector_sl = []
            self.dataset_sector_sl.append('Upstream Oil & Gas')
            self.dataset_sector_sl.append('Mining and Metals(ICMM)')

            self.dataset_year_sl=[]
            for year in range(2023,2010, -1):
                self.dataset_year_sl.append(year)


            self.sl_sector = st.selectbox(
                'Sector:', (self.dataset_sector_sl))
            
            df = pd.read_excel(
                "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/ESGInsights/Pages/CompanyList.xlsx")
   
            self.dataset_sector_comp_df = df[["Company", "Sector"]]


            data_filter = self.dataset_sector_comp_df["Sector"] == self.sl_sector
            self.dataset_comp_sector_selected_df = self.dataset_sector_comp_df[[
                "Sector", "Company"]].where(data_filter).dropna()

            self.dataset_comp_sl = self.dataset_comp_sector_selected_df[[
                "Company"]].drop_duplicates().dropna()

            self.sl_company = st.selectbox(
                'Company:', (self.dataset_comp_sl), index=0)

            self.sl_year_start = st.selectbox(
                'Year:', (self.dataset_year_sl), index=0)

        # self.load_data_by_company()
        # self.draw_exposure_chart()
        self.create_tabs()

    def create_tabs(self):

        tab_titles = ['Top 10 Exposures', 'Triangles', 'YOY Exposure', 'Exposure Vs. Control']
        top10_exposures,  triangles, yoy, exposure_control = st.tabs(
            tab_titles)

        with top10_exposures:
            self.load_data_for_top10_chart(from_file=True)
            self.draw_top10_exposure_plot()

        with triangles:
            self.load_data_for_triangles_chart()
            self.draw_triangle_charts()

        with yoy:
            self.load_data_for_yoy_chart()
            self.draw_yoy_chart()

        with exposure_control:
            self.load_data_for_exposure_control_chart()
            self.draw_exposure_control_chart()


        css = '''
        <style>
            .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size:12px;
            font-weight: bold;
            }
        </style>
        '''
        st.markdown(css, unsafe_allow_html=True)

    def load_data_for_top10_chart(self, from_file=False):

        if(from_file == True):
            
            self.exposure_list = self.get_exposure_list_from_file()
            df = pd.DataFrame([vars(exposure)
                               for exposure in self.exposure_list])
            self.dataset = df.round(2)

        else:
            self.exposure_list = DashboardDBManager("Test").get_top10_exposure_control_measures(
            self.sl_year_start, self.sl_company)
            df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])
            self.dataset = df.round(2)

        self.chart_header = 'Sector:'+self.sl_sector +', Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start)
        
    def load_data_for_triangles_chart(self):
        # self.exposure_list = DashboardDBManager("Test").get_triangle_measures(
        # self.sl_year_start, self.sl_company)
        self.exposure_list= self.get_triangulation_data_from_file()

        df = pd.DataFrame([vars(exposure)
                          for exposure in self.exposure_list])

        self.triangle_dataset = df.round(2)
        print('Selected Triangle Data...')
        print(self.triangle_dataset)

        self.chart_header = 'Sector:'+self.sl_sector +', Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start)

    def load_data_for_yoy_chart(self):

        # self.exposure_list = DashboardDBManager("Test").get_yoy_measures(self.sl_company)
        self.exposure_list = self.get_yoy_data_from_file()

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.yoy_dataset = df.round(2)
        self.dataset_ranked = None
        if (not self.yoy_dataset is None and self.yoy_dataset.size >0):
            # print(self.yoy_dataset)

            self.chart_header = 'Sector:'+self.sl_sector + ', Company:' + self.sl_company 
            
            self.yoy_dataset["Rank"] = self.yoy_dataset.groupby('year')["exposure_score"].rank(
                ascending=False, method='first')
            
            data_filter = self.yoy_dataset["Rank"] <= 5

            self.dataset_ranked = self.yoy_dataset.where(data_filter).dropna().sort_values(by=[
                'sector_exposure_path_name', 'exposure_score'])

    def load_data_for_exposure_control_chart(self):

        # self.exposure_list = DashboardDBManager(
        #     "Test").get_exposure_vs_control_measures(self.sl_year_start,self.sl_company)
        self.exposure_list = self.get_exposure_vs_control_data_from_file()

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.exp_control_dataset = df.round(2)
        if (not self.exp_control_dataset is None and self.exp_control_dataset.size > 0):
            # print(self.exp_control_dataset)
            self.chart_header = 'Sector:'+self.sl_sector + ', Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start)

    def get_exposure_list_from_file(self):
        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/ESGInsights/Pages/Top10ChartData.xlsx")
        self.dataset_all = df[["year", "company_name", "top10_sector_exposure", "degree_of_control_sector_normalized", "degree_of_control_company_normalized",
                               "top10_company_exposure"]].round(2)

        data_filter = self.dataset_all["year"] == self.sl_year_start
        self.dataset_year = self.dataset_all.where(data_filter).dropna()

        data_filter = self.dataset_year["company_name"] == self.sl_company
        self.dataset = self.dataset_year.where(data_filter).dropna()
        # print(self.dataset)

        for index, row in self.dataset.iterrows():
            dashboard_entity = Top10_Chart_DB_Entity(
                top10_sector_exposure=row['top10_sector_exposure'],
                degree_of_control_sector_normalized=row['degree_of_control_sector_normalized'],
                degree_of_control_company_normalized=row['degree_of_control_company_normalized'],
                top10_company_exposure=row['top10_company_exposure']
            )
            self.exposure_list.append(dashboard_entity)
        return self.exposure_list

    def get_triangulation_data_from_file(self):
        # print('Loading Triangulation data from File.....')

        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/ESGInsights/Pages/TriangulationData.xlsx")
        self.dataset_all = df[["company_name", "year", "sector_exposure_path_name", "Sector_EI",
                               "Compnay_EI", "Sector_EM", "Company_EM", "Sector_IM", "Company_IM"]].round(2)

        data_filter = self.dataset_all["year"] == self.sl_year_start
        self.dataset_year = self.dataset_all.where(data_filter).dropna()

        data_filter = self.dataset_year["company_name"] == self.sl_company
        self.dataset = self.dataset_year.where(data_filter).dropna()

        self.triangle_data_list =[]
        for index, row in self.dataset.iterrows():
            dashboard_entity = Triangle_Chart_DB_Entity(
                sector_exposure_path_name=row['sector_exposure_path_name'],
                Sector_EI=row['Sector_EI'],
                Compnay_EI=row['Compnay_EI'],
                Sector_EM=row['Sector_EM'],
                Company_EM=row['Company_EM'],
                Sector_IM=row['Sector_IM'],
                Company_IM=row['Company_IM']
            )
            self.triangle_data_list.append(dashboard_entity)
        return self.triangle_data_list

    def get_yoy_data_from_file(self):
        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/ESGInsights/Pages/YearOverYear.xlsx")
        self.dataset_all = df[["year", "company_name", "exposure_path_name",
                               "exposure_score", "exposure_score_normalized"]].round(2)

        # data_filter = self.dataset_all["year"] == self.sl_year_start
        # self.dataset_year = self.dataset_all.where(data_filter).dropna()

        data_filter = self.dataset_all["company_name"] == self.sl_company
        self.dataset = self.dataset_all.where(data_filter).dropna()
        print('Year Over Year Data....')
        print(self.dataset)

        for index, row in self.dataset.iterrows():
            dashboard_entity = YOY_DB_Entity(
                company_name=row['company_name'],
                sector_exposure_path_name=row['exposure_path_name'],
                exposure_score=row['exposure_score'],
                exposure_score_normalized=row['exposure_score_normalized'],
                year = row["year"]
            )
            self.yoy_exposure_list.append(dashboard_entity)
        return self.yoy_exposure_list
 
    def get_exposure_vs_control_data_from_file(self):
        df = pd.read_excel(
            "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/ESGInsights/Pages/ExposureVsControl.xlsx")
        self.dataset_all = df[["year", "company_name", "exposure_path_name", "exposure_score", "exposure_control_score"]].round(2)

        data_filter = self.dataset_all["year"] == self.sl_year_start
        self.dataset_year = self.dataset_all.where(data_filter).dropna()

        data_filter = self.dataset_year["company_name"] == self.sl_company
        self.dataset = self.dataset_year.where(data_filter).dropna()

        for index, row in self.dataset.iterrows():
            dashboard_entity = Exposure_Control_Chart_DB_Entity(
                company_name=row['company_name'],
                sector_exposure_path_name=row['exposure_path_name'],
                exposure_score=row['exposure_score'],
                exposure_control_score=row['exposure_control_score'],
                year=row['year']
            )
            self.exposure_vs_control_list.append(dashboard_entity)
        return self.exposure_vs_control_list

    def draw_top10_exposure_plot(self):
        # print('Chart 1 - Inside Draw')

        fig, ax = plt.subplots(figsize=(20, 6))

        ax.set_title(
                    self.chart_header,
                    loc='center',
                    fontsize=10,
                    weight='bold'
                )
        
        rows = 10
        cols = 20

        ax.set_ylim(-1, rows + 1)
        ax.set_xlim(0, cols + .5)

        list_length = len(self.exposure_list)

        # Add Header
        ax.text(0.0, 10.5, 'Sector Exposure', weight='bold', ha='left')
        ax.text(8, 10.5, 'Sector Degree of Control',
                weight='bold', ha='center')
        ax.text(12, 10.5, 'Company Degree of Control',
                weight='bold', ha='center')
        ax.text(15, 10.5, 'Company Top 10 Exposure',
                weight='bold', ha='left')
        
        ax.plot([0.0, 30], [list_length+0.4, list_length+0.4], lw='.5', c='black')


        list_length = len(self.exposure_list)
        row = list_length
        for d in self.exposure_list:
            # print(d)
            row = list_length
            list_length = list_length - 1
        	# extract the row data from the list

            # the y (row) coordinate is based on the row index (loop)

            # the x (column) coordinate is defined based on the order I want to display the data in

            # print(d.top10_sector_exposure)

            ax.text(x=.0, y=row,
                    s= d.top10_sector_exposure, va='center', ha='left')

            if (d.degree_of_control_sector_normalized is None):
                sector_score =0
            else:
                sector_score = d.degree_of_control_sector_normalized
            
            # ax.text(x=8, y=row, s=round(sector_score, 0),
            #         va='center', ha='right', weight='bold')
            ax.text(x=8, y=row, s=round(sector_score, 0),
                        va='center', ha='right')

            if (d.degree_of_control_company_normalized is None):
                comp_score =0
            else:
                comp_score = d.degree_of_control_company_normalized
             
            ax.text(x=12, y=row, s=round(comp_score,2), va='center', ha='right')

            ax.text(
                x=15, y=row, s=d.top10_company_exposure, va='center', ha='left')
 
            if (comp_score >= 50):
                rect = patches.Rectangle(
                    (0.0, row-0.4),  # bottom left starting position (x,y)

                    14,  # width

                    0.65,  # height

                    ec='none',
                    fc='green',
                    alpha=.2,
                    zorder=-1
                )
            else:
                rect = patches.Rectangle(
                    (0.0, row-0.4),  # bottom left starting position (x,y)

                    14,  # width

                    0.65,  # height

                    ec='none',
                    fc='red',
                    alpha=.2,
                    zorder=-1
                )
            ax.add_patch(rect)

        ax.axis('off')

        st.pyplot(fig)

    def draw_triangle_charts(self):

        if (not self.triangle_dataset is None and len(self.triangle_dataset)>0):
            # print('Triangle Selection Box')

            # print(self.triangle_dataset.loc[:, 'sector_exposure_path_name'])
            self.dataset_exposure = self.triangle_dataset['sector_exposure_path_name']
            self.sl_exposure_selected = st.selectbox(
                'Exposure Pathway:', (self.dataset_exposure), index=0)
            print(self.sl_exposure_selected)

            data_filter = self.triangle_dataset["sector_exposure_path_name"] == self.sl_exposure_selected
            dataset_exp_selected = self.triangle_dataset.where(
                data_filter).dropna()
            print(dataset_exp_selected)

            comp_exp_values = dataset_exp_selected[
                ['Compnay_EI', 'Company_EM', 'Company_IM']].values.flatten()
            sector_exp_values = dataset_exp_selected[
                ['Sector_EI', 'Sector_EM', 'Sector_IM']].values.flatten()
            
            # print(comp_exp_values)
            # print(sector_exp_values)

            categories = ['Exposure - Internalization', 'Exposure-Mitigation', 'Internalization-Mitigation']

            fig = go.Figure()

            fig.add_trace(go.Scatterpolar(
                r=sector_exp_values,
                theta=categories,
                fill='toself',
                # fillcolor='orange',
                name='Sector'
            ))

            fig.add_trace(go.Scatterpolar(
                r=comp_exp_values,
                theta=categories,
                fill='toself',
                # fillcolor='blue',
                name='Company'
            ))
          
            st.plotly_chart(fig)
        else:
            st.write('No Data Found')

    def draw_yoy_chart(self):
      
        if (not self.dataset_ranked is None and not self.dataset_ranked.empty):
                # st.write(self.chart_header)

                yoy_chart = (alt.Chart(self.dataset_ranked)
                            .mark_bar(size=30, cornerRadiusTopLeft=3,
                                        cornerRadiusTopRight=3)
                            .encode(
                    x=alt.X('year:N', axis=alt.Axis(
                        title='Year', titleFontSize=12, titleFontWeight='bold')),
                    y=alt.Y('exposure_score:Q',    axis=alt.Axis(
                        title='Risk Exposure', titleFontSize=12, titleFontWeight='bold')),
                    color=alt.Color(
                        'sector_exposure_path_name'),
                    order=alt.Order(
                        'Rank',
                        sort='ascending'
                    ),
                    tooltip=["sector_exposure_path_name", "exposure_score"])
                    .properties(width=250, height=250,title=alt.Title(self.chart_header, fontSize=12, anchor='middle')))

                st.altair_chart(yoy_chart, use_container_width=True)
        else:
            st.write('No Data Found for the Company')

    def draw_exposure_control_chart(self):

        # make the chart
        if (not self.exp_control_dataset.empty):

            exp_control_chart = (alt.Chart(self.exp_control_dataset)
                                .mark_circle()
                                  .encode(x=alt.X('exposure_score', axis=alt.Axis(title='Exposure Score', titleFontSize=12, titleFontWeight='bold')),
                                          y=alt.Y('exposure_control_score',  axis=alt.Axis(
                                            title='Exposure Control Score', titleFontSize=12, titleFontWeight='bold')),
                                          color=alt.Color(
                                              'sector_exposure_path_name'),
                                          size="exposure_control_score", tooltip=["sector_exposure_path_name", "exposure_score", "exposure_control_score"])).properties( title=alt.Title(self.chart_header, fontSize=12, anchor='middle'))

        # exp_control_chart =    alt.Chart(self.exp_control_dataset).mark_point().encode(
        #         x='exposure_score',
        #         y='exposure_control_score',
        #         color='sector_exposure_path_name',
        #     ).interactive()
        
            st.altair_chart(exp_control_chart, use_container_width=True)
        else:
            st.write('No Data Found for the Company')


startup = StartUpClass()
