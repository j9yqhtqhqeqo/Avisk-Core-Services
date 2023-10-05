import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import threading
import streamlit as st
from Utilities.Lookups import Lookups
from Services.InsightGenerator import triangulation_Insight_Generator
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import file_folder_keyWordSearchManager



class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

    def run_keyword_validations(self, DebugMode=False):

        key_word_search_mgr = file_folder_keyWordSearchManager(
            folder_path=PARM_STAGE1_FOLDER, database_context=self.database_context)
        key_word_search_mgr.validation_mode = True

        if (self.ExposurePathwaySelected):
            print('Validating Exposure Pathway Dictionary Terms:')
            key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway()
            
        if (self.InternalizationSelected):
            print('Validating Internalization Dictionary Terms:')
            key_word_search_mgr.generate_keyword_location_map_for_internalization()
        if (self.MitigationSelected):
            print('Validating Mitigation Dictionary Terms:')
            key_word_search_mgr.generate_keyword_location_map_for_mitigation()

        if (key_word_search_mgr.validation_mode):
            key_word_search_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

    def run_online_Mode(self):

        database_context = st.radio("Database Context",["Development","Test"], index=1)
        if(database_context == 'Development'):
            self.database_context='Development'
        else:
            self.database_context = "Test"

        st.text("Select Keyword Location Map Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=True)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=True)
        self.MitigationSelected = st.checkbox("Mitigation", value=True)

        st.button('Run Validations',
                  on_click=self.run_keyword_validations)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()

# l_startup_class.database_context = 'Test'
# l_startup_class.run_keyword_validations()