#!/usr/bin/env python3
"""
Test script to verify PathConfiguration is working correctly
Run this to check path configuration in different environments
"""

from Utilities.PathConfiguration import PathConfiguration
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))


def test_path_configuration():
    """Test the path configuration system"""
    print("=" * 60)
    print("🔧 AVISK PATH CONFIGURATION TEST")
    print("=" * 60)

    # Test configuration
    config = PathConfiguration()

    print(f"Environment Detected: {config.get_environment_name()}")
    print(f"Is Development: {config.is_development()}")
    print(f"Is Cloud: {config.is_cloud()}")
    print()

    print("📂 CONFIGURED PATHS:")
    print("-" * 40)

    paths = config.get_all_paths()
    for key, value in paths.items():
        if key != 'base_config':
            status = "✅ EXISTS" if os.path.exists(
                os.path.dirname(value)) else "⚠️  MISSING"
            print(f"{key:25}: {value}")
            print(f"{' ':25}  {status}")
            print()

    print("🏗️  BASE CONFIGURATION:")
    print("-" * 40)
    for key, value in paths['base_config'].items():
        print(f"{key:15}: {value}")

    print()
    print("=" * 60)
    print("✅ Configuration test completed!")
    print("=" * 60)


def test_environment_simulation():
    """Test different environment configurations"""
    print("\n🌍 TESTING ENVIRONMENT SIMULATION:")
    print("-" * 40)

    # Test different environments
    environments = ['development', 'cloud', 'test']

    for env in environments:
        print(f"\n🔍 Testing {env.upper()} environment:")
        # Set environment variable
        os.environ['DEPLOYMENT_ENV'] = env

        # Create new config instance to pick up the change
        config = PathConfiguration()
        print(f"   Environment: {config.get_environment_name()}")
        print(f"   Log Path: {config.get_insight_log_file_path()}")
        print(f"   Data Path: {config.get_tenk_output_path()}")
        print(f"   Temp Path: {config.get_temp_path()}")

    # Reset environment
    if 'DEPLOYMENT_ENV' in os.environ:
        del os.environ['DEPLOYMENT_ENV']


if __name__ == "__main__":
    test_path_configuration()
    test_environment_simulation()

    print("\n💡 USAGE INSTRUCTIONS:")
    print("-" * 40)
    print("To deploy to cloud, set environment variable:")
    print("   export DEPLOYMENT_ENV=cloud")
    print()
    print("For local development (default):")
    print("   unset DEPLOYMENT_ENV")
    print()
    print("For testing:")
    print("   export DEPLOYMENT_ENV=test")
