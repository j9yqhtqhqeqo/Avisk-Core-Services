import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exposure
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_internalization
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exposure_internalization

from DBEntities.ProximityEntity import DocumentEntity

from Utilities.Lookups import Lookups
import streamlit as st
import threading

class StartUpClass:

    def generate_Insights(self, DebugMode=False):
        exp_int_insght_generator = Insight_Generator(self.database_context)
        triangulation_insight_gen = triangulation_Insight_Generator(self.database_context)

        if (self.generate_exp_insights):
           batch_process_generate_insights_for_exposure(self.database_context)
        if (self.generate_int_insights):
            print("Generating Insights for Internalization Dictionary Terms")
            batch_process_generate_insights_for_internalization(self.database_context)

        if (self.generate_exp_int_insights):
            print("Generating EXP->INT Insights")
            batch_process_generate_insights_for_exposure_internalization(self.database_context)

        if (self.generate_exp_mitigation_insights):
            print("Generating EXP->MIT Insights")
            triangulation_insight_gen.generate_mitigation_exp_insights()
        
        if(self.generate_int_mitigation_insights):
            print("Generating INT->MIT Insights")
            triangulation_insight_gen.generate_mitigation_int_insights()
        
        if(self.generate_exp_int_mitigation_insights):
            print("Generating EXP->INT->MIT Insights")
            triangulation_insight_gen.generate_mitigation_exp_int_insights()

    def run_online_Mode(self):

        database_context = st.radio("Database Context",["Development","Test"], index=0)
        if(database_context == 'Development'):
            self.database_context='Development'
        else:
            self.database_context = "Test"

        st.text("Select Insight Generation  Category:")

        self.generate_exp_insights = st.checkbox(
            "Exposure Pathway", value=False)
        
        self.generate_int_insights = st.checkbox(
            "Internalization", value=False)
       
        self.generate_exp_int_insights = st.checkbox("Exposure -> Internalization", value=False)
        
        self.generate_exp_mitigation_insights = st.checkbox("Exposure ->  Mitigation", value=False)
        
        self.generate_int_mitigation_insights = st.checkbox("Internalization ->Mitigation", value=False)
        
        self.generate_exp_int_mitigation_insights = st.checkbox("Exposure->Internalization->Mitigation", value=False)

        st.button('Generate Insights',
                  on_click=self.generate_Insights)
        

    def run_debug_mode(self):
        self.generate_Insights(DebugMode=True)

startup = StartUpClass()
startup.run_online_Mode()


# mitigation_insight_gen.generate_mitigation_exp_insights()
# mitigation_insight_gen.generate_mitigation_int_insights()
# mitigation_insight_gen.generate_mitigation_exp_int_insights()
