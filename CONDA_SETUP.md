# Conda Environment Setup Guide

## 📋 **Prerequisites**
- Anaconda or Miniconda installed
- Python 3.11 (recommended)

## 🚀 **Quick Setup**

### 1. Create the Environment
```bash
conda env create -f environment.yml
```

### 2. Activate the Environment
```bash
conda activate data-company-gcc
```

### 3. Verify Installation
```bash
# Test Python and key packages
python -c "import pandas, numpy, tensorflow, torch, streamlit, psycopg2; print('✅ All core dependencies installed successfully!')"

# Test database connection
python test_db_connection.py
```

## 🔧 **Environment Variables Setup**

Create a `.env` file in the project root:
```bash
# Database Configuration
DB_PASSWORD="your-actual-database-password"
ENVIRONMENT="local"  # or "cloud"

# Optional: OpenAI API (if using GPT features)
OPENAI_API_KEY="your-openai-api-key"

# Google Cloud (for Secret Manager in production)
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
```

## 📦 **Key Dependencies Included**

### **Data Science & ML**
- **pandas** (1.5.0+) - Data manipulation and analysis
- **numpy** (1.24.0+) - Numerical computing
- **scikit-learn** (1.3.0+) - Machine learning
- **tensorflow** (2.13.0+) - Deep learning framework
- **keras** (2.13.0+) - High-level neural networks API
- **pytorch** (2.0.0+) - Deep learning framework

### **Visualization**
- **matplotlib** (3.6.0+) - Basic plotting
- **plotly** (5.15.0+) - Interactive visualizations
- **altair** (5.0.0+) - Statistical visualizations
- **streamlit** (1.25.0+) - Web applications

### **Database & Cloud**
- **psycopg2** (2.9.0+) - PostgreSQL adapter
- **google-cloud-secret-manager** (2.16.0+) - Secure credential management

### **Web & Document Processing**
- **requests** (2.31.0+) - HTTP library
- **beautifulsoup4** (4.12.0+) - HTML/XML parsing
- **openai** (1.0.0+) - OpenAI API client

### **Development Tools**
- **jupyter** - Jupyter Notebook environment
- **jupyterlab** - Enhanced Jupyter interface
- **ipykernel** - Jupyter kernel for Python

## 🔄 **Environment Management**

### Update Environment
```bash
# Update from environment.yml
conda env update -f environment.yml

# Install additional packages
conda install package_name
# or
pip install package_name
```

### Export Current Environment
```bash
# Export to new yml file
conda env export > environment_backup.yml

# Export only explicitly installed packages
conda env export --from-history > environment_minimal.yml
```

### Remove Environment
```bash
conda env remove -n data-company-gcc
```

## 🚨 **Troubleshooting**

### Common Issues:

1. **TensorFlow/CUDA Issues**:
   ```bash
   # For GPU support (if needed)
   conda install tensorflow-gpu
   ```

2. **PostgreSQL Connection Issues**:
   ```bash
   # Alternative psycopg2 installation
   pip install psycopg2-binary --force-reinstall
   ```

3. **Streamlit Import Errors**:
   ```bash
   # Reinstall streamlit
   pip install streamlit --upgrade
   ```

4. **Google Cloud Authentication**:
   ```bash
   # Install and authenticate gcloud CLI
   gcloud auth application-default login
   ```

## 🧪 **Testing Your Setup**

Run these commands to verify everything works:

```bash
# Activate environment
conda activate data-company-gcc

# Test core functionality
python -c "
import pandas as pd
import numpy as np
import tensorflow as tf
import torch
import streamlit as st
import psycopg2
import plotly.express as px
import sklearn
print('✅ All major packages imported successfully!')
print(f'📊 Pandas version: {pd.__version__}')
print(f'🧠 TensorFlow version: {tf.__version__}')
print(f'🔥 PyTorch version: {torch.__version__}')
"

# Test database connection
python test_db_connection.py

# Test Streamlit (opens web browser)
streamlit hello
```

## 📝 **Next Steps**

1. Set up your environment variables
2. Configure Google Cloud authentication (for production)
3. Test database connectivity
4. Start developing!

For any issues, check the individual package documentation or create a new issue in the project repository.