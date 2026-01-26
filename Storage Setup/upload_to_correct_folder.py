#!/usr/bin/env python3
"""
Upload test file to existing Development folder in GCS bucket
"""
from Utilities.PathConfiguration import PathConfiguration
import os
import sys
from datetime import datetime

# Add the project root to path
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')


def upload_to_existing_development_folder():
    """Upload a test file to the existing Development folder"""
    print("=== Uploading to Existing Development Folder ===")

    # Force development environment
    os.environ['DEPLOYMENT_ENV'] = 'development'

    config = PathConfiguration()

    print(f"Environment: {config.get_environment_name()}")
    print(f"GCS Bucket: {config.get_gcs_bucket_name()}")
    print(f"GCS Prefix: {config.get_gcs_prefix()} (using existing folder)")

    # Create test content
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_content = f"""Avisk Development Environment - Existing Folder Test
===================================================

Created: {timestamp}
Environment: {config.get_environment_name()}
Bucket: {config.get_gcs_bucket_name()}
Prefix: {config.get_gcs_prefix()} ✅ EXISTING FOLDER

This file is stored in the existing Development/ folder
(not the new development/ folder that was created by mistake)

GCS Configuration:
- Bucket: {config.get_gcs_bucket_name()}
- Prefix: {config.get_gcs_prefix()}
- Full path: {config.get_gcs_path(f'corrected_test_{timestamp}.txt')}

Folder Structure:
- Development/ ← USING THIS (existing)
- Test/ (existing)
- Production/ (existing)

Previous incorrect folder: development/ (should be cleaned up)

Status: ✅ PERSISTENT - Stored in correct existing folder
"""

    try:
        from google.cloud import storage
        print("✅ Google Cloud Storage client available")

        # Initialize client and bucket
        client = storage.Client()
        bucket = client.bucket(config.get_gcs_bucket_name())

        # Create blob path in existing Development folder
        blob_path = f"{config.get_gcs_prefix()}corrected_test_{timestamp}.txt"
        blob = bucket.blob(blob_path)

        # Upload content
        blob.upload_from_string(test_content, content_type='text/plain')

        full_gcs_path = f"gs://{config.get_gcs_bucket_name()}/{blob_path}"
        print(f"✅ Successfully uploaded to existing Development folder!")
        print(f"📄 GCS Path: {full_gcs_path}")
        print(f"📊 Size: {len(test_content)} bytes")

        # List files in both folders to show the difference
        print(f"\n=== Files in Development/ (correct existing folder) ===")
        dev_blobs = bucket.list_blobs(prefix='Development/')
        dev_count = 0
        for blob in dev_blobs:
            dev_count += 1
            print(f"📄 {blob.name} ({blob.size} bytes)")

        print(f"\n=== Files in development/ (incorrect new folder) ===")
        lowercase_blobs = bucket.list_blobs(prefix='development/')
        lowercase_count = 0
        for blob in lowercase_blobs:
            lowercase_count += 1
            print(f"🗑️  {blob.name} ({blob.size} bytes) - TO BE CLEANED UP")

        print(f"\n📊 Summary:")
        print(f"   Development/ (correct): {dev_count} files")
        print(f"   development/ (incorrect): {lowercase_count} files")

        if lowercase_count > 0:
            print(f"\n⚠️  Note: The lowercase 'development/' folder should be cleaned up")
            print(f"   to avoid confusion with the existing 'Development/' folder")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = upload_to_existing_development_folder()
    if success:
        print(f"\n🎉 SUCCESS: File uploaded to correct existing Development/ folder!")
    else:
        print(f"\n❌ FAILED: Could not upload file")
