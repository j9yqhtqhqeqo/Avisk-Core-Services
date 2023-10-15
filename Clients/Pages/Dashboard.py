import sys
from pathlib import Path
import os,time
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Utilities.Lookups import Lookups, Processing_Type
import streamlit as st
from DBEntities.LookupsDBManager import LookupsDBManager
from streamlit_autorefresh import st_autorefresh



class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0


    def run_online_Mode(self):

        database_context = st.radio("Database Context",["Development","Test"], index=0)
        if(database_context == 'Development'):
            self.database_context='Development'
        else:
            self.database_context = "Test"
        

        pending_documents_exp = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_EXP)
        if(pending_documents_exp == 0):
            st.text('Awaiting Batch Process Scheduling for Exposure Pathway')
        else:
            st.text("Documents Pending to be processed for Exposure Pathway:" + str(pending_documents_exp))
        
        pending_documents_int = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_INT)     
        if(pending_documents_int == 0):
            st.text('Awaiting Batch Process Scheduling for Internalization')
        else:
            st.text("Documents Pending to be processed for Internalization:" + str(pending_documents_int))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_MIT)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Mitigation')
        else:
            st.text("Documents Pending to be processed for Mitigation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Exposure Insight Generation')
        else:
            st.text("Documents Pending to be processed for Exposure Insight Generation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().INTERNALIZATION_INSIGHTS_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Internalization Insight Generation')
        else:
            st.text("Documents Pending to be processed for Internalization Insight Generation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().Exp_Int_Insight_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Exposure ->Internalization Insight Generation')
        else:
            st.text("Documents Pending to be processed for Exposure ->Internalizationation Insight Generation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().Mitigation_Exp_Insight_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Exposure ->Mitigation Insight Generation')
        else:
            st.text("Documents Pending to be processed for Exposure ->Mitigation Insight Generation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().Mitigation_Int_Insight_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Internalization ->Mitigation Insight Generation')
        else:
            st.text("Documents Pending to be processed for Internalization ->Mitigation Insight Generation:" + str(pending_documents_mit))

        pending_documents_mit = LookupsDBManager(self.database_context).get_current_processing_status(processing_type=Processing_Type().Mitigation_Exp_INT_Insight_GEN)
        if(pending_documents_mit == 0):
            st.text('Awaiting Batch Process Scheduling for Exposure ->Internalization ->Mitigation Insight Generation')
        else:
            st.text("Documents Pending to be processed for Exposure ->Internalization ->Mitigation Insight Generation:" + str(pending_documents_mit))



st_autorefresh(interval=5000, key="fizzbuzzcounter")
startup = StartUpClass()
startup.run_online_Mode()
