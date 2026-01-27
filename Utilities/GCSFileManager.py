"""
GCS File Manager - Centralized Google Cloud Storage file operations
Provides a unified interface for all GCS file operations across the application
"""
import os
from pathlib import Path
from typing import Optional, List, Tuple
from google.cloud import storage
from Utilities.PathConfiguration import PathConfiguration


class GCSFileManager:
    """
    Centralized manager for Google Cloud Storage operations
    Handles file upload, download, and management with environment-aware paths
    """

    def __init__(self, path_config: Optional[PathConfiguration] = None):
        """
        Initialize GCS File Manager

        Args:
            path_config: PathConfiguration instance. If None, creates a new one.
        """
        self.path_config = path_config or PathConfiguration()
        self.gcs_client = None
        self.bucket_name = None
        self.gcs_prefix = None

        # Initialize GCS client if enabled
        if self.path_config.should_use_gcs():
            try:
                self.gcs_client = storage.Client()
                self.bucket_name = self.path_config.get_gcs_bucket_name()
                self.gcs_prefix = self.path_config.get_gcs_prefix().rstrip('/')
                print(
                    f"GCSFileManager initialized: bucket={self.bucket_name}, prefix={self.gcs_prefix}")
            except Exception as e:
                print(f"Warning: Could not initialize GCS client: {e}")
                self.gcs_client = None

    def is_available(self) -> bool:
        """Check if GCS client is available and initialized"""
        return self.gcs_client is not None

    def _get_gcs_path(self, relative_path: str) -> str:
        """
        Construct full GCS path from relative path

        Args:
            relative_path: Relative path (e.g., 'Stage1CleanTextFiles/2022/file.txt')

        Returns:
            Full GCS path without gs:// prefix
        """
        relative = relative_path.lstrip('/')
        return f"{self.gcs_prefix}/data/{relative}"

    def download_file(self, gcs_relative_path: str, local_file_path: str,
                      overwrite: bool = True) -> bool:
        """
        Download file from GCS to local path

        Args:
            gcs_relative_path: Relative path in GCS (e.g., 'Stage1CleanTextFiles/2022/file.txt')
            local_file_path: Local file path where file will be saved
            overwrite: If False, skip download if file already exists locally (default: True)

        Returns:
            True if file is available locally (either existed or downloaded), False otherwise
        """
        # Check if file already exists locally
        if not overwrite and os.path.exists(local_file_path):
            print(f"File exists locally: {local_file_path}")
            return True

        # If GCS is not available, return False
        if not self.is_available():
            print("GCS client not available for download")
            return False

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            # Check if blob exists
            if not blob.exists():
                print(
                    f"File not found in GCS: gs://{self.bucket_name}/{gcs_path}")
                return False

            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download file
            print(
                f"Downloading from GCS: gs://{self.bucket_name}/{gcs_path} -> {local_file_path}")
            blob.download_to_filename(local_file_path)
            print(f"Successfully downloaded file from GCS: {local_file_path}")
            return True

        except Exception as e:
            print(f"Error downloading from GCS: {e}")
            return False

    def upload_file(self, local_file_path: str, gcs_relative_path: str) -> bool:
        """
        Upload file from local path to GCS

        Args:
            local_file_path: Local file path to upload
            gcs_relative_path: Relative path in GCS where file will be stored

        Returns:
            True if upload successful, False otherwise
        """
        # Check if local file exists
        if not os.path.exists(local_file_path):
            print(f"Local file not found: {local_file_path}")
            return False

        # If GCS is not available, return False
        if not self.is_available():
            print("GCS client not available for upload")
            return False

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            # Upload file
            print(
                f"Uploading to GCS: {local_file_path} -> gs://{self.bucket_name}/{gcs_path}")
            blob.upload_from_filename(local_file_path)
            print(
                f"Successfully uploaded file to GCS: gs://{self.bucket_name}/{gcs_path}")
            return True

        except Exception as e:
            print(f"Error uploading to GCS: {e}")
            return False

    def file_exists(self, gcs_relative_path: str) -> bool:
        """
        Check if file exists in GCS

        Args:
            gcs_relative_path: Relative path in GCS

        Returns:
            True if file exists, False otherwise
        """
        if not self.is_available():
            return False

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)
            return blob.exists()

        except Exception as e:
            print(f"Error checking file existence in GCS: {e}")
            return False

    def list_files(self, gcs_relative_path: str, recursive: bool = True) -> List[str]:
        """
        List files in GCS directory

        Args:
            gcs_relative_path: Relative directory path in GCS
            recursive: If True, list recursively; if False, list only immediate children

        Returns:
            List of file paths (relative to the input path)
        """
        if not self.is_available():
            return []

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)

            # Ensure path ends with / for directory listing
            if not gcs_path.endswith('/'):
                gcs_path += '/'

            if recursive:
                blobs = bucket.list_blobs(prefix=gcs_path)
            else:
                blobs = bucket.list_blobs(prefix=gcs_path, delimiter='/')

            files = []
            for blob in blobs:
                # Extract relative path from full blob name
                relative = blob.name.replace(gcs_path, '', 1)
                if relative:  # Skip empty string (the directory itself)
                    files.append(relative)

            return files

        except Exception as e:
            print(f"Error listing files in GCS: {e}")
            return []

    def delete_file(self, gcs_relative_path: str) -> bool:
        """
        Delete file from GCS

        Args:
            gcs_relative_path: Relative path in GCS

        Returns:
            True if deletion successful, False otherwise
        """
        if not self.is_available():
            print("GCS client not available for deletion")
            return False

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            if not blob.exists():
                print(
                    f"File not found in GCS: gs://{self.bucket_name}/{gcs_path}")
                return False

            blob.delete()
            print(
                f"Successfully deleted file from GCS: gs://{self.bucket_name}/{gcs_path}")
            return True

        except Exception as e:
            print(f"Error deleting file from GCS: {e}")
            return False

    def download_as_string(self, gcs_relative_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Download file from GCS directly to memory as string

        Args:
            gcs_relative_path: Relative path in GCS
            encoding: Text encoding to use

        Returns:
            File contents as string, or None if download failed
        """
        if not self.is_available():
            print("GCS client not available for download")
            return None

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            if not blob.exists():
                print(
                    f"File not found in GCS: gs://{self.bucket_name}/{gcs_path}")
                return None

            print(
                f"Downloading to memory from GCS: gs://{self.bucket_name}/{gcs_path}")
            content = blob.download_as_text(encoding=encoding)
            return content

        except Exception as e:
            print(f"Error downloading file as string from GCS: {e}")
            return None

    def download_as_bytes(self, gcs_relative_path: str) -> Optional[bytes]:
        """
        Download file from GCS directly to memory as bytes

        Args:
            gcs_relative_path: Relative path in GCS

        Returns:
            File contents as bytes, or None if download failed
        """
        if not self.is_available():
            print("GCS client not available for download")
            return None

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            if not blob.exists():
                print(
                    f"File not found in GCS: gs://{self.bucket_name}/{gcs_path}")
                return None

            print(
                f"Downloading to memory from GCS: gs://{self.bucket_name}/{gcs_path}")
            content = blob.download_as_bytes()
            return content

        except Exception as e:
            print(f"Error downloading file as bytes from GCS: {e}")
            return None

    def upload_from_string(self, content: str, gcs_relative_path: str,
                           encoding: str = 'utf-8') -> bool:
        """
        Upload string content directly to GCS

        Args:
            content: String content to upload
            gcs_relative_path: Relative path in GCS where content will be stored
            encoding: Text encoding to use

        Returns:
            True if upload successful, False otherwise
        """
        if not self.is_available():
            print("GCS client not available for upload")
            return False

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            print(
                f"Uploading string to GCS: gs://{self.bucket_name}/{gcs_path}")
            blob.upload_from_string(content, content_type='text/plain')
            print(
                f"Successfully uploaded string to GCS: gs://{self.bucket_name}/{gcs_path}")
            return True

        except Exception as e:
            print(f"Error uploading string to GCS: {e}")
            return False

    def get_file_info(self, gcs_relative_path: str) -> Optional[dict]:
        """
        Get file metadata from GCS

        Args:
            gcs_relative_path: Relative path in GCS

        Returns:
            Dictionary with file metadata (size, updated, etc.) or None if file not found
        """
        if not self.is_available():
            return None

        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_path(gcs_relative_path)
            blob = bucket.blob(gcs_path)

            if not blob.exists():
                return None

            blob.reload()
            return {
                'name': blob.name,
                'size': blob.size,
                'updated': blob.updated,
                'content_type': blob.content_type,
                'md5_hash': blob.md5_hash,
            }

        except Exception as e:
            print(f"Error getting file info from GCS: {e}")
            return None


# Global instance for convenience
gcs_manager = GCSFileManager()
