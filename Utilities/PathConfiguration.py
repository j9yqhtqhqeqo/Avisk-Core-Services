"""
Path Configuration Manager for Avisk Core Services
Handles environment-specific file paths for development and cloud deployments
Includes Google Cloud Storage configuration for different environments
"""
import os
from pathlib import Path
from enum import Enum


class Environment(Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class PathConfiguration:
    """
    Centralized path configuration for all file operations
    Automatically detects environment and provides appropriate paths
    """

    def __init__(self):
        # Detect environment
        self.environment = self._detect_environment()
        self.base_config = self._get_base_configuration()

    def _detect_environment(self) -> Environment:
        """Auto-detect environment based on system characteristics"""
        env_var = os.getenv('DEPLOYMENT_ENV', '').lower()

        # Check if running in actual cloud environment (not local)
        is_local = os.path.exists('/Users/mohanganadal')

        if is_local:
            # Local development
            return Environment.DEVELOPMENT
        elif env_var == 'production':
            return Environment.PRODUCTION
        elif env_var == 'test':
            return Environment.TEST
        elif env_var == 'development':
            # Cloud deployment with development data
            return Environment.DEVELOPMENT
        else:
            return Environment.PRODUCTION  # Default to production for cloud deployments

    def _get_base_configuration(self) -> dict:
        """Get base configuration based on environment"""
        is_local = os.path.exists('/Users/mohanganadal')

        if self.environment == Environment.DEVELOPMENT:
            if is_local:
                # Local development
                return {
                    'base_data_path': '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor',
                    'temp_path': '/tmp/avisk',
                    'log_base': '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log',
                    'project_root': '/Users/mohanganadal/Avisk/Avisk-Core-Services',
                    'gcs_bucket': os.getenv('GCS_BUCKET_DEVELOPMENT', 'avisk-app-data-eb7773c8'),
                    'gcs_prefix': 'Development/',
                    'use_gcs': os.getenv('USE_GCS', 'true').lower() == 'true'
                }
            else:
                # Cloud deployment with development data
                return {
                    'base_data_path': '/opt/avisk/data',
                    'temp_path': '/tmp/avisk',
                    'log_base': '/var/log/avisk',
                    'project_root': '/opt/avisk/app',
                    'gcs_bucket': os.getenv('GCS_BUCKET_DEVELOPMENT', 'avisk-app-data-eb7773c8'),
                    'gcs_prefix': 'Development/',
                    'use_gcs': True
                }
        elif self.environment == Environment.TEST:
            return {
                'base_data_path': '/tmp/avisk_test/data',
                'temp_path': '/tmp/avisk_test',
                'log_base': '/tmp/avisk_test/logs',
                'project_root': '/tmp/avisk_test/app',
                'gcs_bucket': os.getenv('GCS_BUCKET_TEST', 'avisk-app-data-eb7773c8'),
                'gcs_prefix': 'Test/',
                'use_gcs': True
            }
        elif self.environment == Environment.PRODUCTION:
            return {
                'base_data_path': '/opt/avisk/data',
                'temp_path': '/tmp/avisk',
                'log_base': '/var/log/avisk',
                'project_root': '/opt/avisk/app',
                'gcs_bucket': os.getenv('GCS_BUCKET_PRODUCTION', 'avisk-app-data-eb7773c8'),
                'gcs_prefix': 'Production/',
                'use_gcs': True
            }

    def _ensure_directory_exists(self, path: str) -> str:
        """Ensure directory exists, create if necessary"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return path
        except PermissionError:
            # In case of permission error (like /var/log on development machine),
            # fall back to temp directory
            if self.environment in [Environment.PRODUCTION, Environment.DEVELOPMENT, Environment.TEST] and '/var/log' in path:
                fallback_path = path.replace(
                    '/var/log/avisk', '/tmp/avisk/logs')
                try:
                    Path(fallback_path).mkdir(parents=True, exist_ok=True)
                    print(
                        f"⚠️  Permission denied for {path}, using fallback: {fallback_path}")
                    return fallback_path
                except Exception:
                    return path
            return path
        except Exception as e:
            print(f"⚠️  Could not create directory {path}: {e}")
            return path

    # InsightGenerator.py paths
    def get_insight_log_file_path(self) -> str:
        """Get path for insight generation log files"""
        path = f"{self.base_config['log_base']}/InsightGenLog/InsightLog"
        return self._ensure_directory_exists(os.path.dirname(path)) and path

    def get_new_include_dict_term_path(self) -> str:
        """Get path for new include dictionary terms"""
        path = f"{self.base_config['base_data_path']}/Dictionary/new_include_list.txt"
        return self._ensure_directory_exists(os.path.dirname(path)) and path

    def get_new_exclude_dict_term_path(self) -> str:
        """Get path for new exclude dictionary terms"""
        path = f"{self.base_config['base_data_path']}/Dictionary/new_exclude_list.txt"
        return self._ensure_directory_exists(os.path.dirname(path)) and path

    def get_validation_list_path(self) -> str:
        """Get path for validation dictionary files"""
        path = f"{self.base_config['base_data_path']}/Dictionary/DataTesting/"
        return self._ensure_directory_exists(path)

    def get_include_logs_path(self) -> str:
        """Get path for inclusion dictionary log files"""
        path = f"{self.base_config['base_data_path']}/Dictionary/IncludeLogs/"
        return self._ensure_directory_exists(path)

    def get_exclude_logs_path(self) -> str:
        """Get path for exclusion dictionary log files"""
        path = f"{self.base_config['base_data_path']}/Dictionary/ExcludeLogs/"
        return self._ensure_directory_exists(path)

    def get_tenk_output_path(self) -> str:
        """Get path for extracted 10K files"""
        path = f"{self.base_config['base_data_path']}/Extracted10K/"
        return self._ensure_directory_exists(path)

    def get_stage1_folder_path(self) -> str:
        """Get path for Stage1 clean text files"""
        path = f"{self.base_config['base_data_path']}/Stage1CleanTextFiles/"
        return self._ensure_directory_exists(path)

    # InsightGenDocumentLoader.py paths
    def get_document_loader_log_path(self) -> str:
        """Get path for document loader log files"""
        path = f"{self.base_config['log_base']}/InsightGenLog/"
        return self._ensure_directory_exists(path)

    def get_source_input_path(self) -> str:
        """Get path for source input 10K forms"""
        path = f"{self.base_config['base_data_path']}/FormDownloads/10K/"
        return self._ensure_directory_exists(path)

    def get_reprocess_path(self) -> str:
        """Get path for reprocess document headers"""
        path = f"{self.base_config['base_data_path']}/ReProcessDocHeaders/"
        return self._ensure_directory_exists(path)

    def get_processed_path(self) -> str:
        """Get path for processed 10K forms"""
        if self.environment == Environment.DEVELOPMENT:
            path = f"{self.base_config['project_root']}/FormDownloads/10KProcessed/"
        else:
            path = f"{self.base_config['base_data_path']}/FormDownloads/10KProcessed/"
        return self._ensure_directory_exists(path)

    def get_stage0_input_path(self) -> str:
        """Get path for Stage0 source PDF files (DataSourceProcessor input)"""
        path = f"{self.base_config['base_data_path']}/Stage0SourcePDFFiles/"
        return self._ensure_directory_exists(path)

    def get_stage1_output_path(self) -> str:
        """Get path for Stage1 clean text files (DataSourceProcessor output)"""
        path = f"{self.base_config['base_data_path']}/Stage1CleanTextFiles/"
        return self._ensure_directory_exists(path)

    def get_log_path(self, log_name: str) -> str:
        """Get path for a specific log file"""
        log_dir = f"{self.base_config['log_base']}/"
        self._ensure_directory_exists(log_dir)
        return f"{log_dir}{log_name}"

    # Google Cloud Storage methods
    def get_gcs_bucket_name(self) -> str:
        """Get Google Cloud Storage bucket name for current environment"""
        return self.base_config['gcs_bucket']

    def get_gcs_prefix(self) -> str:
        """Get Google Cloud Storage prefix for current environment"""
        return self.base_config['gcs_prefix']

    def should_use_gcs(self) -> bool:
        """Check if Google Cloud Storage should be used"""
        return self.base_config.get('use_gcs', False)

    def get_gcs_path(self, relative_path: str) -> str:
        """Get full GCS path for a relative path"""
        prefix = self.get_gcs_prefix().rstrip('/')
        relative = relative_path.lstrip('/')
        return f"gs://{self.get_gcs_bucket_name()}/{prefix}/{relative}"

    def get_gcs_credentials_path(self) -> str:
        """Get path to Google Cloud credentials file"""
        # Check environment variables first
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            return creds_path

        # Look for credentials in common locations
        if self.environment == Environment.DEVELOPMENT:
            possible_paths = [
                os.path.expanduser(
                    '~/.config/gcloud/application_default_credentials.json'),
                f"{self.base_config['project_root']}/credentials/gcp-credentials.json",
                '/Users/mohanganadal/.gcp/credentials.json'
            ]
        else:
            possible_paths = [
                '/opt/avisk/credentials/gcp-credentials.json',
                '/etc/gcp/credentials.json'
            ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    # Utility methods
    def get_temp_path(self) -> str:
        """Get temporary file path"""
        return self._ensure_directory_exists(self.base_config['temp_path'])

    def get_environment_name(self) -> str:
        """Get current environment name"""
        return self.environment.value

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    def is_test(self) -> bool:
        """Check if running in test environment"""
        return self.environment == Environment.TEST

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    def is_cloud(self) -> bool:
        """Check if running in cloud environment (legacy compatibility)"""
        # For backward compatibility, return True for non-development environments
        return not self.is_development() or not os.path.exists('/Users/mohanganadal')

    def get_all_paths(self) -> dict:
        """Get all configured paths for debugging"""
        paths = {
            'environment': self.environment.value,
            'base_config': self.base_config,
            'insight_log_file': self.get_insight_log_file_path(),
            'new_include_dict_term': self.get_new_include_dict_term_path(),
            'new_exclude_dict_term': self.get_new_exclude_dict_term_path(),
            'validation_list': self.get_validation_list_path(),
            'include_logs': self.get_include_logs_path(),
            'exclude_logs': self.get_exclude_logs_path(),
            'tenk_output': self.get_tenk_output_path(),
            'stage1_folder': self.get_stage1_folder_path(),
            'document_loader_log': self.get_document_loader_log_path(),
            'source_input': self.get_source_input_path(),
            'reprocess': self.get_reprocess_path(),
            'processed': self.get_processed_path(),
            'temp': self.get_temp_path(),
            # Google Cloud Storage configuration
            'gcs_bucket': self.get_gcs_bucket_name(),
            'gcs_prefix': self.get_gcs_prefix(),
            'use_gcs': self.should_use_gcs(),
            'gcs_credentials_path': self.get_gcs_credentials_path()
        }

        # Add sample GCS paths
        if self.should_use_gcs():
            paths['gcs_sample_paths'] = {
                'documents': self.get_gcs_path('documents/'),
                'logs': self.get_gcs_path('logs/'),
                'processed': self.get_gcs_path('processed/'),
                'temp': self.get_gcs_path('temp/')
            }

        return paths


# Global configuration instance
path_config = PathConfiguration()


# Legacy compatibility functions for existing code
def get_insight_log_file_path():
    return path_config.get_insight_log_file_path()


def get_new_include_dict_term_path():
    return path_config.get_new_include_dict_term_path()


def get_new_exclude_dict_term_path():
    return path_config.get_new_exclude_dict_term_path()


def get_validation_list_path():
    return path_config.get_validation_list_path()


def get_tenk_output_path():
    return path_config.get_tenk_output_path()


def get_stage1_folder_path():
    return path_config.get_stage1_folder_path()


def get_document_loader_log_path():
    return path_config.get_document_loader_log_path()


def get_source_input_path():
    return path_config.get_source_input_path()


def get_reprocess_path():
    return path_config.get_reprocess_path()


def get_processed_path():
    return path_config.get_processed_path()


if __name__ == "__main__":
    # Test the configuration
    config = PathConfiguration()
    print("=== Path Configuration Test ===")
    print(f"Environment: {config.get_environment_name()}")
    print("\nAll Paths:")
    for key, value in config.get_all_paths().items():
        print(f"  {key}: {value}")
