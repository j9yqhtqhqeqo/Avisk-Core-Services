import sys
from pathlib import Path
import os,time
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.Lookups import Lookups, Processing_Type
import streamlit as st
import threading
from Services.SingletonServiceMgr import process_exposure_pathway_document_list
from Services.SingletonServiceMgr import process_mitigation_document_list, process_internalization_document_list
from DBEntities.LookupsDBManager import LookupsDBManager
from streamlit_autorefresh import st_autorefresh
from multiprocessing import Process, Queue, Pool
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager


class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0

    def generate_keyword_location_map(self, DebugMode=False):

        key_word_search_mgr = file_folder_keyWordSearchManager(
            folder_path=PARM_STAGE1_FOLDER,database_context=self.database_context)
        key_word_search_mgr.validation_mode = False

        if (self.ExposurePathwaySelected):
           process_exposure_pathway_document_list(self.database_context)
          
        if (self.InternalizationSelected):
           process_internalization_document_list(self.database_context)
      

        if (self.MitigationSelected):
            process_mitigation_document_list(self.database_context)
          
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
            "Exposure Pathway", value=False)
        self.InternalizationSelected = st.checkbox(
            "Internalization", value=False)
        self.MitigationSelected = st.checkbox("Mitigation", value=False)

        st.button('Generate Location Maps',
                  on_click=self.generate_keyword_location_map)
        
        # if (self.ExposurePathwaySelected):
        #     pending_documents_exp = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_EXP)
        #     if(pending_documents_exp == 0):
        #         st.text('Awaiting Batch Process Scheduling for Exposure Pathway')
        #     else:
        #         st.text("Documents Pending to be processed for Exposure Pathway:" + str(pending_documents_exp))
        
        # if (self.InternalizationSelected):
        #     pending_documents_int = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_INT)     
        #     if(pending_documents_int == 0):
        #         st.text('Awaiting Batch Process Scheduling for Internalization')
        #     else:
        #         st.text("Documents Pending to be processed for Internalization:" + str(pending_documents_int))
        
        # if (self.MitigationSelected):          
        #     pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_MIT)
        #     if(pending_documents_mit == 0):
        #         st.text('Awaiting Batch Process Scheduling for Mitigation')
        #     else:
        #         st.text("Documents Pending to be processed for Mitigation:" + str(pending_documents_mit))
         
st_autorefresh(interval=5000, key="fizzbuzzcounter")
startup = StartUpClass()
startup.run_online_Mode()
