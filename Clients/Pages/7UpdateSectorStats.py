from Services.SingletonServiceMgr import update_sector_stats, get_sector_list, get_year_list
from Dictionary.DictionaryManager import DictionaryManager
import streamlit as st
import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


class StartUpClass:

    def __init__(self) -> None:
         pass

    def process_update_stats(self, DebugMode=False):
        update_sector_stats(
            database_context=self.database_context, sector=self.sl_sector, year=self.sl_year)

    def run_online_Mode(self):
        database_context = st.radio(
            "Database Context", ["Development", "Test"], index=1)
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"

        self.dataset_sector_sl = get_sector_list(database_context=self.database_context)
        self.sl_sector = st.selectbox(
            'Sector:', (self.dataset_sector_sl))
        
        self.dataset_year_sl = get_year_list(database_context=self.database_context)
        self.sl_year = st.selectbox(
            'Year:', (self.dataset_year_sl), index=0)

        st.button('Update Sector Stats',
                  on_click=self.process_update_stats)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()
