# Storage Setup Files

This directory contains all the files related to Google Cloud Storage configuration and testing for the Avisk Core Services project.

## Files Description

### Documentation
- **GOOGLE_STORAGE_SETUP.md** - Complete documentation for GCS configuration, environment variables, and bucket structure

### Configuration Tests
- **test_gcs_config.py** - Tests the PathConfiguration class across all environments (development, test, production)
- **test_dev_log_access.py** - Tests development environment log file access and permissions

### Upload Tests
- **test_gcs_upload.py** - Basic GCS upload test (initial version)
- **upload_to_existing_bucket.py** - Tests uploading to the existing `avisk-app-data-eb7773c8` bucket
- **upload_to_correct_folder.py** - Tests uploading to the correct existing folders (Development/, Test/, Production/)

### Setup Scripts
- **create_persistent_test_file.py** - Creates local test files representing GCS structure

## Current Configuration

The system is configured to use:
- **Bucket**: `avisk-app-data-eb7773c8` (managed by infrastructure project)
- **Development**: `Development/` folder
- **Test**: `Test/` folder  
- **Production**: `Production/` folder

**Note**: GCS buckets are created and managed by the infrastructure project, not by application code.

## Running Tests

From the project root directory:

```bash
# Test the configuration
python "Storage Setup/test_gcs_config.py"

# Test development log access
python "Storage Setup/test_dev_log_access.py"

# Test upload to correct folder
python "Storage Setup/upload_to_correct_folder.py"
```

## Integration

The main PathConfiguration class in `/Utilities/PathConfiguration.py` is configured to use the existing GCS bucket structure. All applications should use this class for consistent path management across local and cloud storage.