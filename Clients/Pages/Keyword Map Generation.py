import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.Lookups import Lookups
import streamlit as st
import threading

class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.counter = 0

    def generate_keyword_location_map(self, DebugMode=False):

        key_word_search_mgr = file_folder_keyWordSearchManager(
            folder_path=PARM_STAGE1_FOLDER)

        if (not DebugMode):
            key_word_search_mgr.validation_mode = self.validation_mode
        else:
            key_word_search_mgr.validation_mode = True

        if (self.ExposurePathwaySelected):
            key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway()
        if (self.InternalizationSelected):
            key_word_search_mgr.generate_keyword_location_map_for_internalization()
        if (self.MitigationSelected):
            key_word_search_mgr.generate_keyword_location_map_for_mitigation()

        if (key_word_search_mgr.validation_mode):
            key_word_search_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

    def run_online_Mode(self):

        # self.validation_mode = st.checkbox("Validation Only", value=True)
        st.text("Select Keyword Location Map Category:")
        self.ExposurePathwaySelected = st.checkbox(
            "Exposure Pathway", value=True)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=True)
        self.MitigationSelected = st.checkbox("Mitigation", value=True)

        st.button('Generate Location Maps',
                  on_click=self.generate_keyword_location_map)
        

    def run_debug_mode(self):
        self.generate_keyword_location_map(DebugMode=True)


    def run_interact_mode(self):
        # st.text(key ='status')
        st.text_input("Your name", key="status")

        t1 = threading.Thread(target=self.run_count_thread)
        t2 = threading.Thread(target=self.run_refresh_thread,)
    
        # starting thread 1
        t1.start()
        # starting thread 2
        t2.start()
    
        # wait until thread 1 is completely executed
        t1.join()
        # wait until thread 2 is completely executed
        t2.join()
    

    def run_count_thread(self):
        for i in range(1000):
            print(i)
            self.counter = self.counter+1

    def run_refresh_thread(self):
            st.session_state.status = self.counter
         

startup = StartUpClass()

# startup.run_interact_mode()
startup.run_online_Mode()
