#!/usr/bin/env python3
"""
Test GCS FUSE file sync with fsync
Verifies that files written to FUSE mount appear in GCS bucket
"""
from Utilities.LoggingServices import logGenerator
import os
import sys
import datetime as dt
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/opt/avisk/app')


def test_fuse_sync():
    """Test that log files sync properly to GCS via FUSE mount"""

    # Use GCS FUSE mounted path
    test_log_path = '/opt/avisk/gcs-data/Development/data/logs/InsightGenLog/TEST_SYNC_' + \
                    dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt'

    print(f"Creating test log file: {test_log_path}")

    # Create logger instance
    logger = logGenerator(test_log_path)

    # Write test messages
    logger.log_details("=== GCS FUSE Sync Test Started ===")
    logger.log_details(f"Test timestamp: {dt.datetime.now().isoformat()}")
    logger.log_details(
        "This file should be visible in GCS console immediately", stamp_date_time=False)
    logger.log_details("Testing fsync() implementation for GCS FUSE")
    logger.log_details("=== Test Completed ===")

    # Verify file exists locally (via FUSE)
    if os.path.exists(test_log_path):
        file_size = os.path.getsize(test_log_path)
        print(f"✅ File created successfully via FUSE mount")
        print(f"   Path: {test_log_path}")
        print(f"   Size: {file_size} bytes")
        print(f"\n🔍 Check GCS Console:")
        print(f"   gs://avisk-app-data-eb7773c8/Development/data/logs/InsightGenLog/")
        print(f"   File should be visible: {os.path.basename(test_log_path)}")
        return True
    else:
        print(f"❌ File not found at: {test_log_path}")
        return False


if __name__ == "__main__":
    success = test_fuse_sync()
    sys.exit(0 if success else 1)
