import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Services.SingletonServiceMgr import update_chart_tables, get_sector_list, get_year_list
from Dictionary.DictionaryManager import DictionaryManager
import streamlit as st
import ast



class StartUpClass:

    def __init__(self) -> None:
        pass

    def process_update_stats(self, DebugMode=False):
        update_chart_tables(
            database_context=self.database_context,
            generate_top10_exposure_chart_data=self.generate_top10_exposure_chart_data, 
            generate_triangulation_data=self.generate_triangulation_chart_data, generate_yoy_chart_data=self.generate_yoy_chart_data)

    def run_online_Mode(self):
        database_context = st.radio(
            "Database Context", ["Development", "Test"], index=0)
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"

        self.dataset_sector_sl = get_sector_list(
            database_context=self.database_context)
        self.sl_sector = st.selectbox(
            'Sector:', (self.dataset_sector_sl))

        self.dataset_year_sl = get_year_list(
            database_context=self.database_context)
        self.sl_year = st.selectbox(
            'Year:', (self.dataset_year_sl), index=0)
        
        self.generate_top10_exposure_chart_data = st.checkbox(
            "Top 10 Exposure Data", value=False)

        self.generate_triangulation_chart_data = st.checkbox(
            "Triangulation Data", value=False)
        
        self.generate_yoy_chart_data = st.checkbox(
            "Year Over Year Data", value=False)
        
        # self.generate_exp_sector_insights = st.checkbox(
        #     "Exposure", value=False)

        # self.generate_int_sector_insights = st.checkbox(
        #     "Exposure ->Internalization", value=False)

        # self.generate_mit_sector_insights = st.checkbox(
        #     "Exposure->Internalization->Mitigation", value=False)

        # update_all_setors_years = st.radio(
        #     "Update All Sectors & Years", ["Yes", "No"], index=1)

        # self.update_keywords_only = st.checkbox(
        #     "Update Keywords Only", value=True)

        # if (update_all_setors_years == 'Yes'):
        #     self.update_all = True
        # else:
        #     self.update_all = False

        st.button('Update Chart Tables',
                  on_click=self.process_update_stats)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()
