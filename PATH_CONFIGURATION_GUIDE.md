# Path Configuration Migration Guide

## Overview
This guide describes the new environment-aware path configuration system that replaces hardcoded development paths with flexible, environment-specific configurations.

## 🔧 Configuration System

### Files Updated
- **Services/InsightGenerator.py** - Updated to use `path_config`
- **Services/InsightGenDocumentLoader.py** - Updated to use `path_config`
- **NEW: Utilities/PathConfiguration.py** - Central configuration manager

### Environment Detection
The system automatically detects the environment:
- **Development**: When `/Users/mohanganadal` exists
- **Cloud**: When `DEPLOYMENT_ENV=cloud` environment variable is set
- **Test**: When `DEPLOYMENT_ENV=test` environment variable is set

## 🚀 Cloud Deployment Setup

### 1. Set Environment Variable
```bash
# On cloud VM
export DEPLOYMENT_ENV=cloud

# Add to ~/.bashrc or service configuration
echo 'export DEPLOYMENT_ENV=cloud' >> ~/.bashrc
```

### 2. Cloud Directory Structure
```
/opt/avisk/
├── app/                    # Application code
├── data/                   # Data processing files
│   ├── Dictionary/
│   ├── Extracted10K/
│   ├── FormDownloads/
│   ├── Stage1CleanTextFiles/
│   └── Validation/
└── /var/log/avisk/         # Log files
    └── InsightGenLog/
```

### 3. Setup Script for Cloud VM
```bash
#!/bin/bash
# Cloud VM setup script

# Create directory structure
sudo mkdir -p /opt/avisk/{app,data}
sudo mkdir -p /opt/avisk/data/{Dictionary,Extracted10K,FormDownloads,Stage1CleanTextFiles,Validation}
sudo mkdir -p /var/log/avisk/InsightGenLog

# Set permissions
sudo chown -R avisk:avisk /opt/avisk
sudo chown -R avisk:avisk /var/log/avisk

# Set environment
echo 'export DEPLOYMENT_ENV=cloud' >> ~/.bashrc
export DEPLOYMENT_ENV=cloud

# Install dependencies
pip install -r requirements.txt
```

## 🏠 Local Development

### Default Behavior
- No environment variable needed
- Uses existing development paths under `/Users/mohanganadal/`
- Automatically creates missing directories

### Testing Path Configuration
```bash
# Run the test script
python test_path_config.py

# Should show:
# Environment Detected: development
# Is Development: True
# Is Cloud: False
```

## 🧪 Testing Environment

### Set Test Environment
```bash
export DEPLOYMENT_ENV=test
```

### Test Directory Structure
```
/tmp/avisk_test/
├── app/
├── data/
└── logs/
```

## 📋 Path Mapping

| Component | Development Path | Cloud Path |
|-----------|------------------|------------|
| **Logs** | `/Users/mohanganadal/Data Company/.../Log/InsightGenLog/` | `/var/log/avisk/InsightGenLog/` |
| **Dictionary** | `/Users/mohanganadal/Data Company/.../Dictionary/` | `/opt/avisk/data/Dictionary/` |
| **Extracted10K** | `/Users/mohanganadal/Data Company/.../Extracted10K/` | `/opt/avisk/data/Extracted10K/` |
| **Stage1Files** | `/Users/mohanganadal/Data Company/.../Stage1CleanTextFiles/` | `/opt/avisk/data/Stage1CleanTextFiles/` |
| **FormDownloads** | `/Users/mohanganadal/Data Company/.../FormDownloads/` | `/opt/avisk/data/FormDownloads/` |

## 🔄 Migration Benefits

### Before (Hardcoded)
```python
PARM_LOGFILE = r'/Users/mohanganadal/Data Company/Text Processing/...'
PARM_TENK_OUTPUT_PATH = r'/Users/mohanganadal/Data Company/Text Processing/...'
```

### After (Configuration-Based)
```python
from Utilities.PathConfiguration import path_config

PARM_LOGFILE = path_config.get_insight_log_file_path()
PARM_TENK_OUTPUT_PATH = path_config.get_tenk_output_path()
```

### Advantages
- ✅ **Environment-aware** - Automatically adapts to deployment environment
- ✅ **Auto-directory creation** - Creates missing directories automatically
- ✅ **Backward compatible** - Works with existing development setup
- ✅ **Cloud ready** - No code changes needed for cloud deployment
- ✅ **Testable** - Separate test environment configuration

## 🐛 Troubleshooting

### Check Configuration
```python
from Utilities.PathConfiguration import PathConfiguration
config = PathConfiguration()
print(config.get_all_paths())
```

### Verify Environment
```bash
echo $DEPLOYMENT_ENV
python -c "from Utilities.PathConfiguration import path_config; print(f'Environment: {path_config.get_environment_name()}')"
```

### Manual Directory Creation
```bash
# If directories don't auto-create, create manually:
# Development (usually not needed)
mkdir -p "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog"

# Cloud
sudo mkdir -p /opt/avisk/data/{Dictionary,Extracted10K,FormDownloads,Stage1CleanTextFiles}
sudo mkdir -p /var/log/avisk/InsightGenLog
sudo chown -R $USER:$USER /opt/avisk /var/log/avisk
```

## 🔧 Advanced Configuration

### Custom Environment Variables
You can override specific paths using environment variables:
```bash
export AVISK_BASE_DATA_PATH="/custom/data/path"
export AVISK_LOG_BASE="/custom/log/path"
```

### Adding New Paths
To add new paths, update `PathConfiguration.py`:
```python
def get_new_path(self) -> str:
    """Get path for new component"""
    path = f"{self.base_config['base_data_path']}/NewComponent/"
    return self._ensure_directory_exists(path)
```

## ✅ Verification Checklist

### Development Setup
- [ ] Existing code still works without changes
- [ ] Log files created in expected locations
- [ ] Data processing paths accessible

### Cloud Deployment
- [ ] `DEPLOYMENT_ENV=cloud` environment variable set
- [ ] Directory structure created (`/opt/avisk/`, `/var/log/avisk/`)
- [ ] Permissions set correctly
- [ ] Test script runs successfully
- [ ] Application can read/write to configured paths

This configuration system ensures smooth deployment across different environments while maintaining backward compatibility with your existing development setup.