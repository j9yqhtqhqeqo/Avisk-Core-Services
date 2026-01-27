"""
Version and Build Information for Avisk Core Services
"""
import os
from datetime import datetime

VERSION = "1.0.0"
BUILD_NUMBER = os.getenv('BUILD_ID', 'local')
BUILD_DATE = os.getenv(
    'BUILD_DATE', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
ENVIRONMENT = os.getenv('DEPLOYMENT_ENV', 'development')


def get_version_string():
    """Get formatted version string"""
    return f"v{VERSION}"


def get_build_string():
    """Get formatted build string"""
    if BUILD_NUMBER == 'local':
        return f"Build: Local Dev"
    return f"Build: {BUILD_NUMBER}"


def get_full_version_info():
    """Get complete version information"""
    return {
        'version': VERSION,
        'build_number': BUILD_NUMBER,
        'build_date': BUILD_DATE,
        'environment': ENVIRONMENT
    }
