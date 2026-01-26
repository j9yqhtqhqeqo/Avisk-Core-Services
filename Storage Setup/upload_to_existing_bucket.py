#!/usr/bin/env python3
"""
Upload test file to existing GCS bucket: avisk-app-data-eb7773c8
"""
from Utilities.PathConfiguration import PathConfiguration
import os
import sys
from datetime import datetime

# Add the project root to path
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')


def upload_to_existing_bucket():
    """Upload a test file to the existing GCS bucket"""
    print("=== Uploading Test File to Existing GCS Bucket ===")

    # Force development environment
    os.environ['DEPLOYMENT_ENV'] = 'development'

    config = PathConfiguration()

    print(f"Environment: {config.get_environment_name()}")
    print(f"GCS Bucket: {config.get_gcs_bucket_name()}")
    print(f"GCS Prefix: {config.get_gcs_prefix()}")

    # Create test content
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_content = f"""Avisk Development Environment Test File
====================================

Created: {timestamp}
Environment: {config.get_environment_name()}
Bucket: {config.get_gcs_bucket_name()}
Prefix: {config.get_gcs_prefix()}

This is a PERSISTENT test file that demonstrates:
1. Google Cloud Storage integration with existing bucket
2. Development environment configuration
3. File structure for Avisk Core Services

GCS Configuration:
- Bucket: {config.get_gcs_bucket_name()} ✅ (existing)
- Full path: {config.get_gcs_path(f'test-files/persistent_dev_test_{timestamp}.txt')}
- Use GCS: {config.should_use_gcs()}

Directory Structure Test:
- Documents: {config.get_gcs_path('documents/10k/')}
- Logs: {config.get_gcs_path('logs/insight-gen/')}
- Processed: {config.get_gcs_path('processed/')}
- Dictionary: {config.get_gcs_path('dictionary/include/')}
- Temp: {config.get_gcs_path('temp/')}

Local Paths (fallback):
- Base data: {config.base_config['base_data_path']}
- Logs: {config.base_config['log_base']}
- Temp: {config.base_config['temp_path']}

Status: ✅ PERSISTENT - DO NOT DELETE
Purpose: Development environment verification
"""

    try:
        from google.cloud import storage
        print("✅ Google Cloud Storage client available")

        # Initialize client and bucket
        client = storage.Client()
        bucket = client.bucket(config.get_gcs_bucket_name())

        # Verify bucket exists
        if not bucket.exists():
            print(f"❌ Bucket {config.get_gcs_bucket_name()} does not exist!")
            return False

        print(f"✅ Confirmed bucket exists: {config.get_gcs_bucket_name()}")

        # Create blob path
        blob_path = f"{config.get_gcs_prefix()}test-files/persistent_dev_test_{timestamp}.txt"
        blob = bucket.blob(blob_path)

        # Upload content
        blob.upload_from_string(test_content, content_type='text/plain')

        # Confirm upload
        full_gcs_path = f"gs://{config.get_gcs_bucket_name()}/{blob_path}"
        print(f"✅ Successfully uploaded persistent test file!")
        print(f"📄 GCS Path: {full_gcs_path}")
        print(f"📊 Size: {len(test_content)} bytes")

        # Get file info
        blob.reload()
        print(f"📅 Created: {blob.time_created}")
        print(f"🔧 Content Type: {blob.content_type}")

        # Create additional demo files for directory structure
        demo_files = {
            'logs/insight-gen/demo.log': 'Demo log file for insight generation\\n',
            'logs/document-loader/demo.log': 'Demo log file for document loader\\n',
            'documents/10k/demo.txt': 'Demo 10K document file\\n',
            'dictionary/include/demo_terms.txt': 'demo\\ntest\\nexample\\n',
            'temp/demo.tmp': 'Temporary demo file\\n'
        }

        print(f"\\n=== Creating Directory Structure Demo Files ===")
        for relative_path, content in demo_files.items():
            try:
                demo_blob_path = f"{config.get_gcs_prefix()}{relative_path}"
                demo_blob = bucket.blob(demo_blob_path)
                demo_blob.upload_from_string(
                    content, content_type='text/plain')
                print(
                    f"✅ Created: gs://{config.get_gcs_bucket_name()}/{demo_blob_path}")
            except Exception as e:
                print(f"❌ Error creating {relative_path}: {e}")

        # List all files in development prefix
        print(f"\\n=== Development Environment Files ===")
        blobs = bucket.list_blobs(prefix=config.get_gcs_prefix())
        file_count = 0
        for blob in blobs:
            file_count += 1
            print(f"📄 {blob.name} ({blob.size} bytes)")

        print(f"\\n📈 Total files in development environment: {file_count}")
        print(f"🌐 Bucket: {config.get_gcs_bucket_name()}")
        print(f"📁 Prefix: {config.get_gcs_prefix()}")

        return True

    except ImportError:
        print("❌ Google Cloud Storage client not installed")
        print("   Install: pip install google-cloud-storage")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")

        # Check credentials
        creds = config.get_gcs_credentials_path()
        if creds:
            print(f"   Credentials found: {creds}")
        else:
            print("   No credentials found")
            print("   Run: gcloud auth application-default login")
        return False


if __name__ == "__main__":
    success = upload_to_existing_bucket()
    if success:
        print(f"\\n🎉 SUCCESS: Test file uploaded to existing bucket!")
        print(f"   The file is persistent and demonstrates the GCS integration.")
    else:
        print(f"\\n❌ FAILED: Could not upload to bucket.")
