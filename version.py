"""
Version and Build Information for Avisk Core Services
"""
import os
from datetime import datetime

# Base version
BASE_VERSION = "1.0"

# Get build information from environment
BUILD_ID = os.getenv('BUILD_ID', 'local')
BUILD_DATE = os.getenv(
    'BUILD_DATE', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
ENVIRONMENT = os.getenv('DEPLOYMENT_ENV', 'development')

# Generate version from build ID if available
if BUILD_ID and BUILD_ID != 'local':
    # Extract date portion from BUILD_ID (format: YYYYMMDDHHMMSS)
    # Use the date as patch version for auto-incrementing
    try:
        # Take last 6 digits as patch number (HHMMSS)
        patch = int(BUILD_ID[-6:])
        VERSION = f"{BASE_VERSION}.{patch}"
    except:
        VERSION = f"{BASE_VERSION}.0"
else:
    VERSION = f"{BASE_VERSION}.0"


def get_version_string():
    """Get formatted version string"""
    return f"v{VERSION}"


def get_build_string():
    """Get formatted build string"""
    if BUILD_ID == 'local':
        return f"Build: Local Dev"
    return f"Build #{BUILD_ID}"


def get_build_date_string():
    """Get formatted build date string"""
    return f"Build Date: {BUILD_DATE}"


def get_full_version_info():
    """Get complete version information"""
    return {
        'version': VERSION,
        'build_number': BUILD_ID,
        'build_date': BUILD_DATE,
        'environment': ENVIRONMENT
    }
