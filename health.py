"""
Health check endpoint for Cloud Run deployment
"""
import streamlit as st
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def main():
    """Simple health check page for Cloud Run"""
    st.set_page_config(
        page_title="Health Check",
        page_icon="✅",
        layout="centered"
    )

    st.title("🏥 Health Check")
    st.success("Service is healthy and running!")

    # Basic system info
    st.subheader("System Information")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Python Version",
                  f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        st.metric("Working Directory", str(Path.cwd()))

    with col2:
        st.metric("Environment", os.getenv("DEPLOYMENT_ENV", "unknown"))
        st.metric("GCS Enabled", os.getenv("USE_GCS", "false"))

    # Return 200 status for health checks
    return True


if __name__ == "__main__":
    main()
