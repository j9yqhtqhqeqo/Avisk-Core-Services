#!/usr/bin/env python3
"""
Test uploading a file to Google Cloud Storage Development bucket
"""
from Utilities.PathConfiguration import PathConfiguration
import os
import sys
from datetime import datetime

# Add the project root to path
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')


def upload_test_file_to_gcs():
    """Upload a test file to GCS development bucket"""
    print("=== Uploading Test File to GCS Development Bucket ===")

    # Force development environment
    os.environ['DEPLOYMENT_ENV'] = 'development'

    config = PathConfiguration()

    print(f"Environment: {config.get_environment_name()}")
    print(f"GCS Bucket: {config.get_gcs_bucket_name()}")
    print(f"GCS Prefix: {config.get_gcs_prefix()}")

    # Create test content
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_content = f"""Test file uploaded to GCS Development Environment
Timestamp: {timestamp}
Environment: {config.get_environment_name()}
Bucket: {config.get_gcs_bucket_name()}
Prefix: {config.get_gcs_prefix()}

This file was created to test Google Cloud Storage integration
for the Avisk Core Services development environment.

File structure test:
- Development bucket: {config.get_gcs_bucket_name()}
- Test file path: {config.get_gcs_path(f'test-files/dev_test_{timestamp}.txt')}
"""

    try:
        # Try to import Google Cloud Storage client
        from google.cloud import storage
        print("✅ Google Cloud Storage client available")

        # Initialize the client
        client = storage.Client()
        bucket = client.bucket(config.get_gcs_bucket_name())

        # Create the blob path
        blob_path = f"{config.get_gcs_prefix()}test-files/dev_test_{timestamp}.txt"
        blob = bucket.blob(blob_path)

        # Upload the content
        blob.upload_from_string(test_content, content_type='text/plain')

        print(f"✅ Successfully uploaded test file to GCS!")
        print(f"   GCS Path: gs://{config.get_gcs_bucket_name()}/{blob_path}")
        print(f"   File Size: {len(test_content)} bytes")
        print(f"   Content Type: text/plain")

        # Verify the upload
        if blob.exists():
            print("✅ File verified to exist in GCS")

            # Get file info
            blob.reload()
            print(f"   Created: {blob.time_created}")
            print(f"   Updated: {blob.updated}")
            print(f"   Size: {blob.size} bytes")
        else:
            print("❌ File upload verification failed")

    except ImportError:
        print("❌ Google Cloud Storage client not available")
        print("   Install with: pip install google-cloud-storage")
        print("   Or: conda install google-cloud-storage")

        # Create local test file as fallback
        print("\n📁 Creating local test file as fallback...")
        local_test_dir = "/tmp/avisk_gcs_test"
        os.makedirs(local_test_dir, exist_ok=True)

        local_file_path = f"{local_test_dir}/dev_test_{timestamp}.txt"
        with open(local_file_path, 'w') as f:
            f.write(test_content)

        print(f"✅ Local test file created: {local_file_path}")
        print(f"   This file represents what would be uploaded to:")
        print(f"   {config.get_gcs_path(f'test-files/dev_test_{timestamp}.txt')}")

    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")

        # Check credentials
        creds_path = config.get_gcs_credentials_path()
        if creds_path:
            print(f"   Credentials found at: {creds_path}")
        else:
            print("   No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'")


def list_gcs_test_files():
    """List test files in the GCS bucket"""
    try:
        from google.cloud import storage

        config = PathConfiguration()
        client = storage.Client()
        bucket = client.bucket(config.get_gcs_bucket_name())

        print(
            f"\n=== Files in {config.get_gcs_bucket_name()}/{config.get_gcs_prefix()}test-files/ ===")

        prefix = f"{config.get_gcs_prefix()}test-files/"
        blobs = bucket.list_blobs(prefix=prefix)

        found_files = False
        for blob in blobs:
            print(f"📄 {blob.name}")
            print(f"   Size: {blob.size} bytes")
            print(f"   Created: {blob.time_created}")
            found_files = True

        if not found_files:
            print("   No test files found")

    except Exception as e:
        print(f"❌ Error listing files: {e}")


if __name__ == "__main__":
    upload_test_file_to_gcs()
    list_gcs_test_files()
