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
        self.generate_exp_insights = True
        self.generate_int_insights = True
        self.generate_exp_int_insights = True
        self.generate_exp_mitigation_insights = True
        self.generate_int_mitigation_insights = True
        self.generate_exp_int_mitigation_insights = True


    def generate_Insights(self, DebugMode=False):
        exp_int_insght_generator = Insight_Generator()
        triangulation_insight_gen = triangulation_Insight_Generator()

        if (self.generate_exp_insights):
            exp_int_insght_generator.generate_insights_with_2_factors(
                Lookups().Exposure_Pathway_Dictionary_Type)

        if (self.generate_int_insights):
            print("Generating Insights for Internalization Dictionary Terms")
            exp_int_insght_generator.generate_insights_with_2_factors(
                Lookups().Internalization_Dictionary_Type)

        if (self.generate_exp_int_insights):
            triangulation_insight_gen.generate_exp_int_insights()

        if (self.generate_exp_mitigation_insights):
            triangulation_insight_gen.generate_mitigation_exp_insights()
        
        if(self.generate_int_mitigation_insights):
            triangulation_insight_gen.generate_mitigation_int_insights()
        
        if(self.generate_exp_int_mitigation_insights):
            triangulation_insight_gen.generate_mitigation_exp_int_insights()

    def run_online_Mode(self):

        st.text("Select Insight Generation  Category:")

        self.generate_mitigation_exp_insights = st.checkbox(
            "Exposure Pathway", value=True)
        
        self.generate_mitigation_int_insights = st.checkbox(
            "Internalization", value=True)
       
        self.generate_exp_int_insights = st.checkbox("Exposure -> Internalization", value=True)
        
        self.generate_mitigation_exp_int_insights = st.checkbox("Exposure ->  Mitigation", value=True)
        
        self.generate_exp_int_insights = st.checkbox("Internalization ->Mitigation", value=True)
        
        self.generate_mitigation_exp_int_insights = st.checkbox("Exposure->Internalization->Mitigation", value=True)

        st.button('Generate Insights',
                  on_click=self.generate_Insights)
        

    def run_debug_mode(self):
        self.generate_Insights(DebugMode=True)

startup = StartUpClass()
startup.run_online_Mode()


# mitigation_insight_gen.generate_mitigation_exp_insights()
# mitigation_insight_gen.generate_mitigation_int_insights()
# mitigation_insight_gen.generate_mitigation_exp_int_insights()
