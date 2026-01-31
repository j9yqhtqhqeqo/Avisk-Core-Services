from Utilities.PathConfiguration import path_config
from Services.SingletonServiceMgr import update_validation_completed_status
from Dictionary.DictionaryManager import DictionaryManager, DuplicateDictionaryTermsError
import pandas as pd
import streamlit as st
import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


class StartUpClass:

    def __init__(self) -> None:
        # Initialize session state for term management
        if 'terms_df' not in st.session_state:
            st.session_state.terms_df = None
        if 'terms_loaded' not in st.session_state:
            st.session_state.terms_loaded = False

    def process_include_exclude_terms(self, DebugMode=False):
        try:
            DictionaryManager().update_Dictionary()
            # print("✅ Processed Dictionary Terms Successfully - DEBUG - CLIENT")
            update_validation_completed_status(
                database_context=self.database_context)
            st.success("✅ Dictionary terms processed successfully!")
        except DuplicateDictionaryTermsError as e:
            st.error(f"❌ Error: {str(e)}")
            st.warning("""**Action Required:**
            
1. Review the duplicate keywords shown above
2. Decide which keywords should be INCLUDED vs EXCLUDED
3. Remove duplicates from one of the files (keep in only ONE file)
4. Try processing again
            """)
            if e.duplicate_terms:
                st.markdown("**Duplicate Keywords Found:**")
                for term in e.duplicate_terms:
                    st.code(term)
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

    def load_terms_from_files(self):
        """Load terms from both include and exclude files into a DataFrame"""
        include_path = path_config.get_new_include_dict_term_path()
        exclude_path = path_config.get_new_exclude_dict_term_path()

        terms_data = []

        # Load include terms
        if os.path.exists(include_path):
            with open(include_path, 'r') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            terms_data.append({
                                'Keyword': parts[0].strip(),
                                'Related Term': parts[1].strip(),
                                'Action': 'Include'
                            })

        # Load exclude terms
        if os.path.exists(exclude_path):
            with open(exclude_path, 'r') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            # Check if this term already exists from include file
                            existing = next((t for t in terms_data if t['Keyword'] == parts[0].strip(
                            ) and t['Related Term'] == parts[1].strip()), None)
                            if not existing:
                                terms_data.append({
                                    'Keyword': parts[0].strip(),
                                    'Related Term': parts[1].strip(),
                                    'Action': 'Exclude'
                                })

        if terms_data:
            return pd.DataFrame(terms_data)
        return None

    def save_terms_to_files(self, df):
        """Save the edited terms back to include and exclude files"""
        include_path = path_config.get_new_include_dict_term_path()
        exclude_path = path_config.get_new_exclude_dict_term_path()

        # Separate terms by action
        include_terms = df[df['Action'] == 'Include']
        exclude_terms = df[df['Action'] == 'Exclude']

        # Write include file
        with open(include_path, 'w') as f:
            for _, row in include_terms.iterrows():
                f.write(f"{row['Keyword']}:{row['Related Term']}\n")

        # Write exclude file
        with open(exclude_path, 'w') as f:
            for _, row in exclude_terms.iterrows():
                f.write(f"{row['Keyword']}:{row['Related Term']}\n")

        return len(include_terms), len(exclude_terms)

    def show_dictionary_file_info(self):
        """Display interactive grid for managing dictionary terms"""
        st.markdown("### 📋 Dictionary Terms Management")
        st.info("""
        **Instructions:** Review the keywords below and decide whether each should be **Included** or **Excluded**.
        - **Include**: Add to InclusionDictionary (term is considered a match)
        - **Exclude**: Add to ExclusionDictionary (term is filtered out)
        """)

        # Load terms button
        if st.button("🔄 Load/Reload Terms from Files"):
            st.session_state.terms_df = self.load_terms_from_files()
            st.session_state.terms_loaded = True
            st.rerun()

        # Display terms if loaded
        if st.session_state.terms_loaded and st.session_state.terms_df is not None:
            st.markdown(
                f"**Total Terms Found:** {len(st.session_state.terms_df)}")

            # Use data editor for interactive editing
            edited_df = st.data_editor(
                st.session_state.terms_df,
                column_config={
                    "Keyword": st.column_config.TextColumn(
                        "Keyword",
                        help="The main keyword",
                        disabled=True,
                        width="medium"
                    ),
                    "Related Term": st.column_config.TextColumn(
                        "Related Term",
                        help="The related term found in validation",
                        disabled=True,
                        width="medium"
                    ),
                    "Action": st.column_config.SelectboxColumn(
                        "Action",
                        help="Choose whether to Include or Exclude this term",
                        options=["Include", "Exclude"],
                        required=True,
                        width="small"
                    )
                },
                hide_index=True,
                use_container_width=True,
                key="terms_editor"
            )

            # Save button
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    include_count, exclude_count = self.save_terms_to_files(
                        edited_df)
                    st.success(
                        f"✅ Saved! {include_count} terms to Include, {exclude_count} to Exclude")
                    st.session_state.terms_df = edited_df

            with col2:
                if st.button("🗑️ Clear All"):
                    st.session_state.terms_df = None
                    st.session_state.terms_loaded = False
                    st.rerun()

            # Show summary
            include_count = len(edited_df[edited_df['Action'] == 'Include'])
            exclude_count = len(edited_df[edited_df['Action'] == 'Exclude'])

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Terms to Include", include_count)
            with col_b:
                st.metric("Terms to Exclude", exclude_count)

        elif st.session_state.terms_loaded and st.session_state.terms_df is None:
            st.warning("⚠️ No new terms found in validation files.")
        else:
            st.info(
                "👆 Click 'Load/Reload Terms from Files' to start reviewing terms.")

    def run_online_Mode(self):
        st.title("Process Dictionary Terms")

        database_context = st.radio(
            "Database Context", ["Development", "Test"], index=0)
        if (database_context == 'Development'):
            self.database_context = 'Development'
        else:
            self.database_context = "Test"

        # Show file information before processing
        self.show_dictionary_file_info()

        st.markdown("---")
        st.button('Process Dictionary Terms',
                  on_click=self.process_include_exclude_terms)


l_startup_class = StartUpClass()
l_startup_class.run_online_Mode()
