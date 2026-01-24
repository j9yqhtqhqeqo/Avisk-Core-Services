#!/bin/bash

# Avisk Core Services Launch Script
# This script activates the conda environment and launches the Streamlit application

echo "🚀 Starting Avisk Core Services..."
echo "=================================="

# Set working directory to script location
cd "$(dirname "$0")"
echo "📁 Working directory: $(pwd)"

# Set environment variables
export DB_PASSWORD="avisk123"
export ENVIRONMENT="local"
echo "🔧 Environment variables set"

# Activate conda environment using full path
echo "🐍 Activating conda environment: data-company-gcc"
source /Users/mohanganadal/Library/spyder-6/etc/profile.d/conda.sh
conda activate /Users/mohanganadal/Library/spyder-6/envs/data-company-gcc

# Verify environment activation
if [[ "$CONDA_DEFAULT_ENV" == *"data-company-gcc"* ]]; then
    echo "✅ Conda environment activated successfully"
else
    echo "⚠️  Using direct Python path as fallback"
fi

# Launch Streamlit application
echo "🌐 Launching Streamlit application..."
echo "📍 Local URL: http://localhost:8501"
echo "📍 Network URL: http://192.168.1.189:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo "=================================="

# Suppress Streamlit warnings
export PYTHONWARNINGS="ignore::UserWarning"

# Run Streamlit with the correct Python interpreter
/Users/mohanganadal/Library/spyder-6/envs/data-company-gcc/bin/python -m streamlit run Clients/Home.py --logger.level=error

echo ""
echo "👋 Avisk Core Services stopped"