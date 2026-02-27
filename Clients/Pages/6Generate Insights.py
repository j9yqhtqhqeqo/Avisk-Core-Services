import threading
import streamlit as st
from Utilities.Lookups import Lookups
from DBEntities.ProximityEntity import DocumentEntity
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exp_int_mitigation_insights
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_internalization_mitigation_insights
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exposure_mitigation_insights
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exposure_internalization
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_internalization
from Services.InsightGenSingletonServiceMgr import batch_process_generate_insights_for_exposure
from Services.InsightGenerator import triangulation_Insight_Generator
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import file_folder_keyWordSearchManager
import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

# Configure page
st.set_page_config(
    page_title="Generate Insights",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

from Utilities.mobile import inject_mobile_css  # noqa: E402
inject_mobile_css()

# Page header
st.title("💡 Generate Insights")
st.markdown("---")


class InsightGenerationClient:

    def generate_Insights(self, DebugMode=False):
        # Create progress containers
        status_container = st.container()
        progress_container = st.container()

        with status_container:
            st.info("🚀 Starting insight generation process:")

        # Count total steps
        total_steps = sum([
            1 if self.generate_exp_insights else 0,
            1 if self.generate_int_insights else 0,
            1 if self.generate_exp_int_insights else 0,
            1 if self.generate_exp_mitigation_insights else 0,
            1 if self.generate_int_mitigation_insights else 0,
            1 if self.generate_exp_int_mitigation_insights else 0
        ])

        current_step = 0

        exp_int_insght_generator = Insight_Generator()
        triangulation_insight_gen = triangulation_Insight_Generator()

        if (self.generate_exp_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating Exposure Pathway Insights...")
            with status_container:
                st.write("📝 Generating Insights for Exposure Pathway...")
            print("Generating Insights for Exposure Pathway")
            batch_process_generate_insights_for_exposure()
            with status_container:
                st.success("✅ Exposure Pathway insights generated")

        if (self.generate_int_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating Internalization Insights...")
            with status_container:
                st.write(
                    "📝 Generating Insights for Internalization Dictionary Terms...")
            print("Generating Insights for Internalization Dictionary Terms")
            batch_process_generate_insights_for_internalization()
            with status_container:
                st.success("✅ Internalization insights generated")

        if (self.generate_exp_int_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating EXP->INT Insights...")
            with status_container:
                st.write("📝 Generating EXP->INT Insights...")
            print("Generating EXP->INT Insights")
            batch_process_generate_insights_for_exposure_internalization()
            with status_container:
                st.success("✅ EXP->INT insights generated")

        if (self.generate_exp_mitigation_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating EXP->MIT Insights...")
            with status_container:
                st.write("📝 Generating EXP->MIT Insights...")
            print("Generating EXP->MIT Insights")
            batch_process_generate_insights_for_exposure_mitigation_insights()
            with status_container:
                st.success("✅ EXP->MIT insights generated")

        if (self.generate_int_mitigation_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating INT->MIT Insights...")
            with status_container:
                st.write("📝 Generating INT->MIT Insights...")
            print("Generating INT->MIT Insights")
            batch_process_generate_insights_for_internalization_mitigation_insights()
            with status_container:
                st.success("✅ INT->MIT insights generated")

        if (self.generate_exp_int_mitigation_insights):
            current_step += 1
            with progress_container:
                st.progress(current_step / total_steps,
                            text=f"Step {current_step}/{total_steps}: Generating EXP->INT->MIT Insights...")
            with status_container:
                st.write("📝 Generating EXP->INT->MIT Insights...")
            print("Generating EXP->INT->MIT Insights")
            batch_process_generate_insights_for_exp_int_mitigation_insights()
            with status_container:
                st.success("✅ EXP->INT->MIT insights generated")

        # Final completion message
        with progress_container:
            st.progress(1.0, text="Insight generation complete!")
        with status_container:
            st.balloons()
            st.success("🎉 All insight generation tasks completed successfully!")

    def run_online_Mode(self):
        # Display current queue status
        st.subheader("📊 Current Processing Queue Status", divider='green')

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**💡 Exposure Insights**")
            try:
                from DBEntities.LookupsDBManager import LookupsDBManager
                from Utilities.Lookups import Processing_Type
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().EXPOSURE_INSIGHTS_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

            st.markdown("**🔗 Internalization Insights**")
            try:
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().INTERNALIZATION_INSIGHTS_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

            st.markdown("**🔀 Exposure → Internalization**")
            try:
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().Exp_Int_Insight_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

        with col2:
            st.markdown("**🛡️ Exposure → Mitigation**")
            try:
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().Mitigation_Exp_Insight_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

            st.markdown("**🔗 Internalization → Mitigation**")
            try:
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().Mitigation_Int_Insight_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

            st.markdown("**🔀 Exposure → Internalization → Mitigation**")
            try:
                failed_docs, pending_docs = LookupsDBManager().get_current_processing_status(
                    processing_type=Processing_Type().Mitigation_Exp_INT_Insight_GEN
                )
                if pending_docs == 0 and failed_docs == 0:
                    st.success('✅ No documents pending')
                else:
                    st.info(f"📄 Pending: {pending_docs}")
                    if failed_docs > 0:
                        st.error(f"❌ Failed: {failed_docs}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

        st.markdown("---")
        st.text("Select Insight Generation  Category:")

        self.generate_exp_insights = st.checkbox(
            "Exposure Pathway", value=False)

        self.generate_int_insights = st.checkbox(
            "Internalization", value=False)

        self.generate_exp_int_insights = st.checkbox(
            "Exposure -> Internalization", value=False)

        self.generate_exp_mitigation_insights = st.checkbox(
            "Exposure ->  Mitigation", value=False)

        self.generate_int_mitigation_insights = st.checkbox(
            "Internalization ->Mitigation", value=False)

        self.generate_exp_int_mitigation_insights = st.checkbox(
            "Exposure->Internalization->Mitigation", value=False)

        st.button('Generate Insights',
                  on_click=self.generate_Insights)

    def run_debug_mode(self):
        self.generate_Insights(DebugMode=True)


startup = InsightGenerationClient()
startup.run_online_Mode()


# mitigation_insight_gen.generate_mitigation_exp_insights()
# mitigation_insight_gen.generate_mitigation_int_insights()
# mitigation_insight_gen.generate_mitigation_exp_int_insights()
