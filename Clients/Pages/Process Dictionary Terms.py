import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
import streamlit as st

from Dictionary.DictionaryManager import DictionaryManager



class StartUpClass:

    def __init__(self) -> None:
        pass
    
    def process_include_exclude_terms(self, DebugMode=False):

        dict_mgr = DictionaryManager()
        dict_mgr.update_Dictionary()
      

    def run_online_Mode(self):

        st.button('Process Dictionary Terms',
                  on_click=self.process_include_exclude_terms)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()


