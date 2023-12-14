import sys
from pathlib import Path
import os
import time
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from streamlit_autorefresh import st_autorefresh
from DBEntities.LookupsDBManager import LookupsDBManager
import streamlit as st
from Utilities.Lookups import Lookups, Processing_Type



class StartUpClass:

    def __init__(self) -> None:
        self.ExposurePathwaySelected = True
        self.InternalizationSelected = True
        self.MitigationSelected = True

        self.exp_queue_size = 0

        self.counter = 0

    def run_online_Mode(self):

        database_context = st.radio(
            "Database Context", ["Development", "Test"], index=0)
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"

        st.subheader('Exposure Pathway Keyword Search', divider='blue')
        failed_documents, pending_documents = LookupsDBManager(
            self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_EXP)
        if (pending_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))
            st.text("Documents in Failed Status - " + str(failed_documents))

        st.subheader('Internalization Keyword Search', divider='blue')
        failed_documents, pending_documents = LookupsDBManager(
            self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_INT)
        if (pending_documents == 0 and failed_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))
            st.text("Documents in Failed Status - " + str(failed_documents))

        st.subheader('Mitigation Keyword Search', divider='blue')
        failed_documents, pending_documents = LookupsDBManager( 
            self.database_context).get_current_processing_status(processing_type=Processing_Type().KEYWORD_GEN_MIT)
        if (pending_documents == 0 and failed_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))
            st.text(" Documents in Failed Status - " + str(failed_documents))
 
     
        st.subheader('Exposure Insight Generation', divider='blue')
        failed_documents, pending_documents  = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))

        st.subheader('Internalization Insight Generation', divider='blue')
        failed_documents, pending_documents = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().INTERNALIZATION_INSIGHTS_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text('No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))

        st.subheader('Exposure ->Internalization Insight Generation',divider='blue')
        failed_documents, pending_documents = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().Exp_Int_Insight_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))

        st.subheader('Exposure ->Mitigation Insight Generation',divider='blue')
        failed_documents, pending_documents = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().Mitigation_Exp_Insight_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text(
                'No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))

        st.subheader('Internalization ->Mitigation Insight Generation',divider='blue')
        failed_documents, pending_documents = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().Mitigation_Int_Insight_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text('No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))

        st.subheader('Exposure ->Internalization ->Mitigation Insight Generation',divider='blue')
        failed_documents, pending_documents = LookupsDBManager(self.database_context).get_current_processing_status(
            processing_type=Processing_Type().Mitigation_Exp_INT_Insight_GEN)
        if (pending_documents == 0 and failed_documents == 0):
            st.text('No New Documents to Process:Awaiting Batch Process Scheduling')
        else:
            st.text("Documents Pending to be processed - " +
                    str(pending_documents))


st_autorefresh(interval=20000, key="fizzbuzzcounter")
startup = StartUpClass()
startup.run_online_Mode()
