
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import ast
import datetime as dt
import os

import streamlit as st
from Services.DataSourceProcessor import DataSourceProcessor
import pandas as pd
import numpy as np



class StartUpClass:

    def __init__(self) -> None:
        self.unprocessed_document_list = []
    
    def load_unprocessed_data_list(self):
        self.unprocessed_document_list = (DataSourceProcessor(self.database_context)).get_unprocessed_source_document_list()
        print(self.unprocessed_document_list)

        [x.as_dict() for x in self.unprocessed_document_list]

        df = pd.DataFrame([x.as_dict() for x in self.unprocessed_document_list])
        st.dataframe(data=df)
    
    def extract_source_data(self):
        (DataSourceProcessor(self.database_context)).download_content_from_source_and_process_text()

    def run_online_Mode(self):
        database_context = st.radio("Database Context",["Development","Test"])
        if(database_context == 'Development'):
            self.database_context='Development'
        else:
            self.database_context = "Test"

        st.button('Load Unprocessed Source List',
                  on_click=self.load_unprocessed_data_list)
        
        st.button('Extract Source Data',
                  on_click=self.extract_source_data)


# (DataSourceProcessor()).get_unprocessed_source_document_list()

l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()


