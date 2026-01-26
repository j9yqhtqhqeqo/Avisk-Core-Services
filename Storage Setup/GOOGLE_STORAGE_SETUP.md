# Google Cloud Storage Configuration

This document outlines the Google Cloud Storage setup for the Avisk Core Services project across different environments.

## Environment Setup

### Development Environment
- **Bucket Name**: `avisk-app-data-eb7773c8`
- **Prefix**: `Development/`
- **GCS Usage**: Enabled by default (can be disabled by setting `USE_GCS=false`)

### Test Environment  
- **Bucket Name**: `avisk-app-data-eb7773c8`
- **Prefix**: `Test/`
- **GCS Usage**: Enabled by default

### Production Environment
- **Bucket Name**: `avisk-app-data-eb7773c8`
- **Prefix**: `Production/`
- **GCS Usage**: Enabled by default

## Environment Variables

Set these environment variables to configure Google Cloud Storage:

```bash
# Environment specification
export DEPLOYMENT_ENV="development"  # or "test" or "production"

# Google Cloud Storage buckets (optional, defaults provided)
export GCS_BUCKET_DEVELOPMENT="avisk-app-data-eb7773c8"
export GCS_BUCKET_TEST="avisk-app-data-eb7773c8"  
export GCS_BUCKET_PRODUCTION="avisk-app-data-eb7773c8"

# For development, disable GCS usage if needed (enabled by default)
export USE_GCS="false"  # Set to "false" to use local storage in development instead

# Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

## Bucket Structure

Each environment uses the same bucket with different prefixes (using existing folders):

```
gs://avisk-app-data-eb7773c8/
├── Development/
│   ├── documents/
│   │   ├── 10k/                    # Original 10K forms
│   │   ├── processed/              # Processed documents
│   │   └── extracted/              # Extracted content
│   ├── logs/
│   │   ├── insight-gen/           # Insight generation logs
│   │   ├── document-loader/       # Document loader logs
│   │   └── application/           # General application logs
│   ├── dictionary/
│   │   ├── include/               # Include dictionary files
│   │   ├── exclude/               # Exclude dictionary files
│   │   └── validation/            # Validation files
│   ├── temp/                      # Temporary files
│   └── backup/                    # Backup files
├── Test/
│   └── [same structure as Development]
└── Production/
    └── [same structure as Development]
```

## Code Usage

The PathConfiguration class automatically handles GCS paths:

```python
from Utilities.PathConfiguration import PathConfiguration

config = PathConfiguration()

# Check if GCS is enabled
if config.should_use_gcs():
    # Get bucket and prefix
    bucket = config.get_gcs_bucket_name()
    prefix = config.get_gcs_prefix()
    
    # Get full GCS path
    document_path = config.get_gcs_path('documents/10k/company_filing.txt')
    # Returns: gs://avisk-{env}-data/{env}/documents/10k/company_filing.txt
```

## Credentials Setup

### Development (Local)
1. Install Google Cloud SDK: `gcloud auth application-default login`
2. Or set service account: `export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"`

### Cloud Deployment
1. Use service account with appropriate permissions
2. Store credentials securely in `/opt/avisk/credentials/gcp-credentials.json`
3. Set environment variable to point to credentials file

## Required Permissions

The service account needs the following permissions:
- `storage.buckets.get`
- `storage.objects.create`
- `storage.objects.delete`
- `storage.objects.get`
- `storage.objects.list`

## Migration Notes

- Local file paths are automatically used when `USE_GCS=false` in development
- All existing path methods remain unchanged for backward compatibility
- GCS integration is additive and doesn't break existing functionality

## Testing Configuration

To test the configuration:

```python
python -c "
from Utilities.PathConfiguration import PathConfiguration
config = PathConfiguration()
print('=== Google Storage Configuration ===')
for key, value in config.get_all_paths().items():
    if 'gcs' in key.lower():
        print(f'{key}: {value}')
"
```