#!/usr/bin/env python3
"""
Simple test for development log file access
"""
import os
import sys

# Add the project root to path
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')

from Utilities.PathConfiguration import PathConfiguration

def test_development_log_access():
    """Test development log file access"""
    print("=== Development Log File Access Test ===")
    
    # Force development environment
    os.environ['DEPLOYMENT_ENV'] = 'development'
    
    config = PathConfiguration()
    
    print(f"Environment: {config.get_environment_name()}")
    print(f"Use GCS: {config.should_use_gcs()}")
    print(f"GCS Bucket: {config.get_gcs_bucket_name()}")
    
    # Test log paths
    log_dir = config.get_document_loader_log_path()
    insight_log = config.get_insight_log_file_path()
    
    print(f"\nLog Paths:")
    print(f"Document loader log dir: {log_dir}")
    print(f"Insight log file: {insight_log}")
    
    # Check if directories exist
    print(f"\nDirectory Status:")
    print(f"Log dir exists: {os.path.exists(log_dir)}")
    print(f"Log dir writable: {os.access(log_dir, os.W_OK) if os.path.exists(log_dir) else 'N/A'}")
    
    # Test GCS paths
    if config.should_use_gcs():
        print(f"\nGCS Paths:")
        print(f"GCS logs path: {config.get_gcs_path('logs/test.log')}")
        print(f"GCS insight path: {config.get_gcs_path('logs/insight-gen/test.log')}")
    
    # Test write access
    try:
        test_file = os.path.join(log_dir, "access_test.log")
        with open(test_file, 'w') as f:
            f.write("Development log test - success!\n")
        print(f"\n✅ Successfully wrote to: {test_file}")
        
        # Clean up
        os.remove(test_file)
        print("✅ Test file cleaned up")
        
    except Exception as e:
        print(f"\n❌ Error writing to log directory: {e}")

if __name__ == "__main__":
    test_development_log_access()