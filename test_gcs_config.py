#!/usr/bin/env python3
"""
Google Cloud Storage Configuration Test Script
Tests the PathConfiguration setup for Google Storage across different environments
"""

from Utilities.PathConfiguration import PathConfiguration, Environment
import os
import sys
sys.path.append('/Users/mohanganadal/Avisk/Avisk-Core-Services')


def test_environment_configuration(env_name: str):
    """Test configuration for a specific environment"""
    print(f"\n{'='*50}")
    print(f"Testing {env_name.upper()} Environment")
    print(f"{'='*50}")

    # Set environment
    os.environ['DEPLOYMENT_ENV'] = env_name

    # Create new config instance
    config = PathConfiguration()

    print(f"Detected Environment: {config.get_environment_name()}")
    print(f"GCS Enabled: {config.should_use_gcs()}")
    print(f"GCS Bucket: {config.get_gcs_bucket_name()}")
    print(f"GCS Prefix: {config.get_gcs_prefix()}")
    print(f"Credentials Path: {config.get_gcs_credentials_path()}")

    # Test sample paths
    print("\nSample GCS Paths:")
    sample_files = [
        'documents/10k/sample.txt',
        'logs/insight-gen/log.txt',
        'dictionary/include/terms.txt',
        'temp/processing.tmp'
    ]

    for file_path in sample_files:
        gcs_path = config.get_gcs_path(file_path)
        print(f"  {file_path} -> {gcs_path}")


def test_local_vs_gcs():
    """Test local vs GCS configuration in development"""
    print(f"\n{'='*50}")
    print("Testing Development: Local vs GCS")
    print(f"{'='*50}")

    os.environ['DEPLOYMENT_ENV'] = 'development'

    # Test with GCS disabled
    os.environ['USE_GCS'] = 'false'
    config = PathConfiguration()
    print(f"USE_GCS=false -> GCS Enabled: {config.should_use_gcs()}")

    # Test with GCS enabled
    os.environ['USE_GCS'] = 'true'
    config = PathConfiguration()
    print(f"USE_GCS=true -> GCS Enabled: {config.should_use_gcs()}")


def main():
    """Main test function"""
    print("Google Cloud Storage Configuration Test")
    print("======================================")

    # Store original environment
    original_env = os.environ.get('DEPLOYMENT_ENV')
    original_gcs = os.environ.get('USE_GCS')

    try:
        # Test each environment
        environments = ['development', 'test', 'production']
        for env in environments:
            test_environment_configuration(env)

        # Test local vs GCS
        test_local_vs_gcs()

        # Show full configuration for current environment
        print(f"\n{'='*50}")
        print("Current Environment Full Configuration")
        print(f"{'='*50}")

        config = PathConfiguration()
        all_paths = config.get_all_paths()

        for key, value in sorted(all_paths.items()):
            if key != 'base_config':  # Skip base config for cleaner output
                print(f"{key}: {value}")

    finally:
        # Restore original environment
        if original_env:
            os.environ['DEPLOYMENT_ENV'] = original_env
        elif 'DEPLOYMENT_ENV' in os.environ:
            del os.environ['DEPLOYMENT_ENV']

        if original_gcs:
            os.environ['USE_GCS'] = original_gcs
        elif 'USE_GCS' in os.environ:
            del os.environ['USE_GCS']


if __name__ == "__main__":
    main()
