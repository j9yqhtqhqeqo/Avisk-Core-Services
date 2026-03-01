"""
move_files_to_correct_year.py
-----------------------------
Moves files to their corrected year folders after fix_all_years.py updated the DB.

Uses the google-cloud-storage Python library directly — native GCS API calls,
no subprocess overhead, far faster than gsutil or GCS FUSE shutil.

A GCS "move" = copy_blob() (server-side rewrite, no data transfer) + delete.
For same-bucket moves this is essentially instant metadata only.

Run on the VM:
    python3 /opt/avisk/app/HelperFIles/move_files_to_correct_year.py \\
        --audit-csv /tmp/fix_all_years_audit.csv \\
        --bucket avisk-app-data-eb7773c8 \\
        --gcs-prefix Development/data/Stage0SourcePDFFiles \\
        --workers 40

Add --dry-run to preview without making changes.
"""

import argparse
import csv
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.cloud import storage as gcs


def move_blob(bucket, src_blob_name: str, dst_blob_name: str, dry_run: bool) -> str:
    """
    Server-side GCS move: copy_blob (no data transfer) then delete source.
    Returns 'moved', 'dry_run', 'src_missing', or 'error:<msg>'.
    """
    if dry_run:
        return 'dry_run'
    try:
        src_blob = bucket.blob(src_blob_name)
        if not src_blob.exists():
            # Already moved or never there
            dst_blob = bucket.blob(dst_blob_name)
            return 'already_correct' if dst_blob.exists() else 'src_missing'

        # Server-side copy (rewrite) — no data egress, just metadata
        bucket.copy_blob(src_blob, bucket, dst_blob_name)
        src_blob.delete()
        return 'moved'
    except Exception as e:
        return f'error:{e}'


def main():
    parser = argparse.ArgumentParser(description='Move files to corrected GCS year folders')
    parser.add_argument('--audit-csv', default='/tmp/fix_all_years_audit.csv')
    parser.add_argument('--bucket', default='avisk-app-data-eb7773c8')
    parser.add_argument('--gcs-prefix',
                        default='Development/data/Stage0SourcePDFFiles',
                        help='Path within bucket to Stage0SourcePDFFiles')
    parser.add_argument('--workers', type=int, default=40,
                        help='Parallel threads (default 40)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without making changes')
    args = parser.parse_args()

    audit_csv = Path(args.audit_csv)
    if not audit_csv.exists():
        print(f"❌ Audit CSV not found: {audit_csv}")
        sys.exit(1)

    prefix = args.gcs_prefix.rstrip('/')

    # Read rows — skip dry-run entries from previous runs
    rows = []
    with open(audit_csv, newline='') as f:
        for row in csv.DictReader(f):
            if row.get('dry_run', 'False').strip().lower() == 'true':
                continue
            rows.append(row)

    total = len(rows)
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Moving files via GCS API (copy_blob+delete)")
    print(f"  Bucket     : {args.bucket}")
    print(f"  GCS prefix : {prefix}")
    print(f"  Records    : {total:,}")
    print(f"  Workers    : {args.workers}")
    print()

    # Init GCS client (uses VM service account automatically)
    client = gcs.Client()
    bucket = client.bucket(args.bucket)

    # Thread-safe counters
    lock           = threading.Lock()
    done_count     = [0]
    moved_count    = [0]
    skip_count     = [0]   # src_missing + already_correct
    error_count    = [0]
    error_log      = []
    done_event     = threading.Event()
    t_start        = time.monotonic()

    def print_progress():
        with lock:
            n, mv, sk, er = done_count[0], moved_count[0], skip_count[0], error_count[0]
        elapsed = time.monotonic() - t_start
        rate    = n / elapsed if elapsed > 0 else 0
        eta     = (total - n) / rate if rate > 0 else 0
        eta_s   = time.strftime('%H:%M:%S', time.gmtime(eta))
        print(f"  [{n:>6,}/{total:,}]  moved={mv:,}  skipped={sk:,}  "
              f"errors={er}  rate={rate:.0f}/s  ETA {eta_s}", flush=True)

    def progress_printer():
        while not done_event.wait(timeout=10):
            print_progress()

    printer = threading.Thread(target=progress_printer, daemon=True)
    printer.start()

    def worker(row):
        filename = row['filename']
        src_blob = f"{prefix}/{row['old_year']}/{filename}"
        dst_blob = f"{prefix}/{row['new_year']}/{filename}"
        result   = move_blob(bucket, src_blob, dst_blob, args.dry_run)

        with lock:
            done_count[0] += 1
            if result in ('moved', 'dry_run'):
                moved_count[0] += 1
            elif result in ('src_missing', 'already_correct'):
                skip_count[0] += 1
            else:
                error_count[0] += 1
                error_log.append(f"uid={row['uid']} | {row['old_year']}→{row['new_year']} "
                                  f"| {filename[:60]} | {result}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(worker, row) for row in rows]
        for f in as_completed(futures):
            f.result()

    done_event.set()
    printer.join()
    print_progress()  # Final line

    elapsed = time.monotonic() - t_start
    hh, rem = divmod(int(elapsed), 3600)
    mm, ss  = divmod(rem, 60)

    print()
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Done in {hh:02d}:{mm:02d}:{ss:02d}")
    print(f"  Moved   : {moved_count[0]:,}")
    print(f"  Skipped : {skip_count[0]:,}  (src missing or already in correct folder)")
    print(f"  Errors  : {error_count[0]:,}")

    if error_log:
        print()
        print("Errors:")
        for e in error_log[:30]:
            print(f"  {e}")
        if len(error_log) > 30:
            print(f"  ... and {len(error_log) - 30} more")
        sys.exit(1)


if __name__ == '__main__':
    main()
