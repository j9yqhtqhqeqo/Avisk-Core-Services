import datetime as dt
import os
from pathlib import Path


class logGenerator:
    def __init__(self, file_path) -> None:
        self.file_path = file_path
        self.gcs_manager = None
        self._gcs_relative_path = None

        # Initialize GCS manager for cloud sync
        try:
            from Utilities.GCSFileManager import gcs_manager
            if gcs_manager.is_available():
                self.gcs_manager = gcs_manager
                # Extract relative path for GCS (remove base paths)
                # Log files typically go to logs/InsightGenLog/
                path_str = str(file_path)
                if 'InsightGenLog' in path_str:
                    # Extract path after InsightGenLog for GCS storage
                    parts = path_str.split('InsightGenLog')
                    if len(parts) > 1:
                        self._gcs_relative_path = f"logs/InsightGenLog{parts[1]}"
                elif 'Dictionary' in path_str:
                    # Dictionary logs
                    parts = path_str.split('Dictionary')
                    if len(parts) > 1:
                        self._gcs_relative_path = f"logs/Dictionary{parts[1]}"
                else:
                    # Fallback - use filename only
                    self._gcs_relative_path = f"logs/{Path(file_path).name}"
        except Exception as e:
            # GCS not available, will write to local only
            print(f"GCS logging disabled: {e}")

    def log_details(self, message: str, stamp_date_time=True):
        # Ensure local directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Write to local file
        with open(self.file_path, 'a') as f_log:
            if stamp_date_time:
                f_log.write(f'{dt.datetime.now()} : {message}')
            else:
                f_log.write(f'{message}')
            f_log.write('\n')
            f_log.flush()

        # Sync to GCS if available
        if self.gcs_manager and self._gcs_relative_path:
            try:
                self.gcs_manager.upload_file(
                    self.file_path, self._gcs_relative_path)
            except Exception as e:
                # Don't fail logging if GCS upload fails
                print(f"Warning: Failed to sync log to GCS: {e}")
