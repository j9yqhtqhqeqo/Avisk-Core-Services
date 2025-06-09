import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
import streamlit as st

from Dictionary.DictionaryManager import DictionaryManager
from Services.SingletonServiceMgr import update_validation_completed_status



class StartUpClass:

    def __init__(self) -> None:
        pass
    
    def process_include_exclude_terms(self, DebugMode=False):
        DictionaryManager().update_Dictionary()
        update_validation_completed_status(database_context=self.database_context)


    def run_online_Mode(self):
        database_context = st.radio("Database Context",["Development","Test"], index=0)
        if(database_context == 'Development'):
            self.database_context='Development'
        else:
            self.database_context = "Test"

        st.button('Process Dictionary Terms',
                  on_click=self.process_include_exclude_terms)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()


