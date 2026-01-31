import datetime as dt
import os
from pathlib import Path


class logGenerator:
    def __init__(self, file_path) -> None:
        self.file_path = file_path

    def log_details(self, message: str, stamp_date_time=True):
        # Ensure local directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Write to local file (now using VM storage instead of GCS FUSE for performance)
        with open(self.file_path, 'a') as f_log:
            if stamp_date_time:
                f_log.write(f'{dt.datetime.now()} : {message}')
            else:
                f_log.write(f'{message}')
            f_log.write('\n')
            f_log.flush()
            os.fsync(f_log.fileno())  # Force immediate sync to GCS FUSE
