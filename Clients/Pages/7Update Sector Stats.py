from Services.SingletonServiceMgr import update_sector_stats, get_sector_list, get_year_list, get_pending_sector_updates
from Dictionary.DictionaryManager import DictionaryManager
import streamlit as st
import pandas as pd
import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

# Configure page
st.set_page_config(
    page_title="Update Sector Stats",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from Utilities.mobile import inject_mobile_css  # noqa: E402
inject_mobile_css()

# Page header
st.title("📊 Update Sector Statistics")
st.markdown("---")


class StartUpClass:

    def __init__(self) -> None:
        pass

    def process_update_stats(self, DebugMode=False):
        update_sector_stats(sector=self.sl_sector, year=self.sl_year,
                            generate_exp_sector_insights=self.generate_exp_sector_insights,
                            generate_int_sector_insights=self.generate_int_sector_insights, generate_exp_mit_sector_insights=self.generate_exp_mit_sector_insights,
                            generate_exp_int_mit_sector_insights=self.generate_exp_int_mit_sector_insights, update_all=self.update_all)

    def run_online_Mode(self):
        # Display pending sector updates
        st.subheader("📋 Pending Sector Updates")
        pending_updates = get_pending_sector_updates()

        if pending_updates and len(pending_updates) > 0:
            # Convert to DataFrame for better display
            data = [[item.SectorId, item.Year] for item in pending_updates]
            df = pd.DataFrame(data, columns=['Sector ID', 'Year'])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.info(f"📊 Total pending updates: {len(pending_updates)}")
        else:
            st.success("✅ No pending sector updates")

        st.markdown("---")
        st.subheader("🔧 Update Settings")

        self.dataset_sector_sl = get_sector_list()
        self.sl_sector = st.selectbox(
            'Sector:', (self.dataset_sector_sl))

        self.dataset_year_sl = get_year_list()
        self.sl_year = st.selectbox(
            'Year:', (self.dataset_year_sl), index=0)

        self.generate_exp_sector_insights = st.checkbox(
            "Exposure", value=False)

        self.generate_int_sector_insights = st.checkbox(
            "Exposure ->Internalization", value=False)

        self.generate_exp_mit_sector_insights = st.checkbox(
            "Exposure ->Mitigation", value=False)

        self.generate_exp_int_mit_sector_insights = st.checkbox(
            "Exposure->Internalization->Mitigation", value=False)

        update_all_setors_years = st.radio(
            "Update All Sectors & Years", ["Yes", "No"], index=1)
        if (update_all_setors_years == 'Yes'):
            self.update_all = True
        else:
            self.update_all = False

        st.button('Update Sector Stats',
                  on_click=self.process_update_stats)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()
