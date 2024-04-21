import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import pandas as pd
import numpy as np

import matplotlib as mpl
import matplotlib.patches as patches
from matplotlib import pyplot as plt

import streamlit as st

from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity
from DBEntities.DashboardDBManager import DashboardDBManager

class StartUpClass:

    def __init__(self) -> None:

        # Global Variables
        self.exposure_list = []

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

        self.load_data_by_company()
        # self.draw_exposure_chart()
        self.create_tabs()

    def load_data_by_company(self):

        self.exposure_list = DashboardDBManager("Test").get_top10_exposure_control_measures(
        self.sl_year_start, self.sl_company)

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.dataset = df.round(2)

        self.chart_header = 'Sector:'+self.sl_sector +', Company:' + self.sl_company + ', Year:' + \
            str(self.sl_year_start)

    def create_tabs(self):
        
        tab_titles = ['Top 10 Exposures', 'Chart 2', 'Chart 3', 'Chart 4',
                      "Chart 5" ]
        top10_exposures,  chart2, chart3, chart4, chart5= st.tabs(
            tab_titles)

        with top10_exposures:
             self.load_data_by_company()
             self.draw_top10_exposure_plot()
        with chart2:
            print('Chart 2 - To be implemented')

        with chart3:
            print('Chart 3 - To be implemented')

        with chart4:
            print('Chart 4 - To be implemented')

        with chart5:
            print('Chart 1 - To be implemented')

        css = '''
        <style>
            .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size:12px;
            font-weight: bold;
            }
        </style>
        '''
        st.markdown(css, unsafe_allow_html=True)


    def draw_top10_exposure_plot(self):
        print('Chart 1 - Inside Draw')


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
            row = list_length
            list_length = list_length - 1
        	# extract the row data from the list

            # the y (row) coordinate is based on the row index (loop)

            # the x (column) coordinate is defined based on the order I want to display the data in

            print(d.top10_sector_exposure)

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

startup = StartUpClass()
