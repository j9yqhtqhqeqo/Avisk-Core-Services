import datetime as dt
import os
from pathlib import Path


class logGenerator:
    def __init__(self, file_path) -> None:
        self.file_path = file_path
        # Files are directly accessible via FUSE mount - no GCS manager needed

    def log_details(self, message: str, stamp_date_time=True):
        # Ensure local directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Write to file and force sync to GCS FUSE
        with open(self.file_path, 'a') as f_log:
            if stamp_date_time:
                f_log.write(f'{dt.datetime.now()} : {message}')
            else:
                f_log.write(f'{message}')
            f_log.write('\n')
            f_log.flush()
            # Force OS-level sync to ensure GCS FUSE writes to bucket
            os.fsync(f_log.fileno())

        # Files written to FUSE mount are synced to GCS with fsync
