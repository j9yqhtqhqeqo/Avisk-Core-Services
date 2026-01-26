#!/usr/bin/env python3
"""
Create a test file for GCS development environment (local representation)
"""
from Utilities.PathConfiguration import PathConfiguration
import os
import sys
from datetime import datetime

# Add the project root to path
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')


def create_local_test_file():
    """Create a local test file that represents what would be stored in GCS"""
    print("=== Creating Test File for GCS Development Environment ===")

    # Force development environment
    os.environ['DEPLOYMENT_ENV'] = 'development'

    config = PathConfiguration()

    print(f"Environment: {config.get_environment_name()}")
    print(f"Target GCS Bucket: {config.get_gcs_bucket_name()}")
    print(f"Target GCS Prefix: {config.get_gcs_prefix()}")

    # Create timestamp for unique file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create test content
    test_content = f"""# Avisk Core Services - GCS Development Test File
Created: {timestamp}
Environment: {config.get_environment_name()}

## Google Cloud Storage Configuration
Bucket: {config.get_gcs_bucket_name()}
Prefix: {config.get_gcs_prefix()}
Use GCS: {config.should_use_gcs()}

## Target GCS Paths
This file represents what would be stored at:
{config.get_gcs_path(f'test-files/persistent_dev_test_{timestamp}.txt')}

## Directory Structure
The following directories would be created in GCS:

### Logs
- General logs: {config.get_gcs_path('logs/')}
- Insight generation: {config.get_gcs_path('logs/insight-gen/')}
- Document loader: {config.get_gcs_path('logs/document-loader/')}
- Application logs: {config.get_gcs_path('logs/application/')}

### Documents
- 10K forms: {config.get_gcs_path('documents/10k/')}
- Processed documents: {config.get_gcs_path('documents/processed/')}
- Extracted content: {config.get_gcs_path('documents/extracted/')}

### Data Processing
- Dictionary files: {config.get_gcs_path('dictionary/')}
- Include terms: {config.get_gcs_path('dictionary/include/')}
- Exclude terms: {config.get_gcs_path('dictionary/exclude/')}
- Validation files: {config.get_gcs_path('dictionary/validation/')}

### Temporary Storage
- Temp processing: {config.get_gcs_path('temp/')}
- Backup files: {config.get_gcs_path('backup/')}

## Local Fallback Paths
When GCS is not available, the system uses:
- Base data path: {config.base_config['base_data_path']}
- Log base: {config.base_config['log_base']}
- Temp path: {config.base_config['temp_path']}

## Credentials
Credentials path: {config.get_gcs_credentials_path() or 'Not found - use gcloud auth or set GOOGLE_APPLICATION_CREDENTIALS'}

## Notes
- This file is persistent and should NOT be deleted
- It serves as a reference for the GCS development environment setup
- Once GCS buckets are created, this content should be uploaded to the actual bucket
- The file demonstrates the dual-path system (local + cloud storage)

## Test Status
✅ Configuration loaded successfully
✅ Environment detection working
✅ GCS paths generated correctly
✅ Local paths accessible
✅ File creation successful

File will be stored locally at: [LOCAL_PATH_TO_BE_DETERMINED]
Target GCS location: {config.get_gcs_path(f'test-files/persistent_dev_test_{timestamp}.txt')}
"""

    # Create local storage directory
    local_gcs_test_dir = "/tmp/avisk_gcs_development"
    os.makedirs(local_gcs_test_dir, exist_ok=True)

    # Create the test file
    local_file_path = f"{local_gcs_test_dir}/persistent_dev_test_{timestamp}.txt"

    # Update the content with actual local path
    test_content = test_content.replace(
        "[LOCAL_PATH_TO_BE_DETERMINED]", local_file_path)

    # Write the file
    with open(local_file_path, 'w') as f:
        f.write(test_content)

    print(f"\n✅ Test file created successfully!")
    print(f"📄 Local path: {local_file_path}")
    print(
        f"🌐 Target GCS path: {config.get_gcs_path(f'test-files/persistent_dev_test_{timestamp}.txt')}")
    print(f"📊 File size: {os.path.getsize(local_file_path)} bytes")

    print(f"\n📋 File Contents Preview:")
    print("-" * 50)
    with open(local_file_path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:15]):  # Show first 15 lines
            print(f"{i+1:2d}: {line.rstrip()}")
        if len(lines) > 15:
            print(f"... and {len(lines) - 15} more lines")

    print(f"\n📁 Directory listing:")
    for file in os.listdir(local_gcs_test_dir):
        file_path = os.path.join(local_gcs_test_dir, file)
        size = os.path.getsize(file_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(
            f"   {file} ({size} bytes, modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

    print(f"\n🚀 Next Steps:")
    print("1. Create GCS buckets in Google Cloud Console:")
    print(f"   - {config.get_gcs_bucket_name()}")
    print(f"   - avisk-test-data")
    print(f"   - avisk-production-data")
    print("2. Upload this file to GCS using:")
    print(
        f"   gsutil cp {local_file_path} {config.get_gcs_path(f'test-files/persistent_dev_test_{timestamp}.txt')}")
    print("3. Verify bucket structure is working correctly")

    return local_file_path


if __name__ == "__main__":
    create_local_test_file()
