#!/usr/bin/env python3
"""
Create Dictionary folder structure in GCS
Creates the following folders under data/Dictionary/:
- IncludeLogs/
- ExcludeLogs/
- DataTesting/

Usage:
  python create_gcs_dictionary_folders.py [environment]
  
  environment: development, test, production, or all (default: all)
"""
from Utilities.PathConfiguration import PathConfiguration, Environment
from Utilities.GCSFileManager import GCSFileManager
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))


def create_gcs_dictionary_folders(environment: str = None):
    """Create dictionary folder structure in GCS for specified environment"""

    # Create a custom PathConfiguration with the specified environment
    original_env = os.environ.get('DEPLOYMENT_ENV')

    try:
        # Set environment variable if specified
        if environment:
            os.environ['DEPLOYMENT_ENV'] = environment

        # Force cloud mode by temporarily removing local path check
        import Utilities.PathConfiguration as pc_module
        original_detect = pc_module.PathConfiguration._detect_environment

        def force_environment(self):
            env_var = os.getenv('DEPLOYMENT_ENV', '').lower()
            if env_var == 'production':
                return pc_module.Environment.PRODUCTION
            elif env_var == 'test':
                return pc_module.Environment.TEST
            elif env_var == 'development':
                return pc_module.Environment.DEVELOPMENT
            return pc_module.Environment.PRODUCTION

        # Temporarily override detection
        pc_module.PathConfiguration._detect_environment = force_environment

        # Reinitialize with the specified environment
        path_config = PathConfiguration()
        gcs_manager = GCSFileManager(path_config)

        # Restore original method
        pc_module.PathConfiguration._detect_environment = original_detect

        if not gcs_manager.is_available():
            print(
                f"❌ GCS is not available for {environment or 'current'} environment. Please configure GCS first.")
            return False

        # Define the folders to create
        folders = [
            'Dictionary/IncludeLogs/',
            'Dictionary/ExcludeLogs/',
            'Dictionary/DataTesting/'
        ]

        print(
            f"🚀 Creating Dictionary folder structure in GCS [{environment or 'current'}]...")
        print(f"   Environment: {path_config.get_environment_name()}")
        print(f"   Bucket: {gcs_manager.bucket_name}")
        print(f"   Prefix: {gcs_manager.gcs_prefix}")
        print()

        # GCS doesn't have actual folders, but we can create a placeholder file
        # to ensure the "folder" exists
        import tempfile

        for folder in folders:
            try:
                # Create a .keep file to ensure the folder exists
                gcs_path = f"{folder}.keep"

                # Upload a minimal placeholder file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.keep') as f:
                    f.write("# This file ensures the folder exists in GCS\n")
                    temp_path = f.name

                try:
                    success = gcs_manager.upload_file(temp_path, gcs_path)
                    if success:
                        print(f"✅ Created folder: {folder}")
                    else:
                        print(f"⚠️  Failed to create folder: {folder}")
                finally:
                    os.unlink(temp_path)

            except Exception as e:
                print(f"❌ Error creating folder {folder}: {e}")
                return False

        print()
        print(
            f"✅ Dictionary folder structure created successfully for {environment or 'current'} environment!")
        print()
        print("📁 Folder structure:")
        print(f"   {gcs_manager.gcs_prefix}data/Dictionary/")
        print("   ├── IncludeLogs/")
        print("   ├── ExcludeLogs/")
        print("   └── DataTesting/")
        print()

    finally:
        # Restore original environment variable
        if original_env is not None:
            os.environ['DEPLOYMENT_ENV'] = original_env
        elif 'DEPLOYMENT_ENV' in os.environ:
            del os.environ['DEPLOYMENT_ENV']

    return True


if __name__ == "__main__":
    # Get environment from command line argument
    env_arg = sys.argv[1].lower() if len(sys.argv) > 1 else 'all'

    if env_arg == 'all':
        # Create folders for all environments
        environments = ['development', 'test', 'production']
        all_success = True

        for env in environments:
            success = create_gcs_dictionary_folders(env)
            all_success = all_success and success
            if success:
                print()

        if all_success:
            print("=" * 60)
            print("✅ All environments configured successfully!")
            print("=" * 60)
        sys.exit(0 if all_success else 1)
    else:
        # Create folders for specific environment
        success = create_gcs_dictionary_folders(env_arg)
        sys.exit(0 if success else 1)
