"""
validate_file_locations.py
--------------------------
Reads every 'file' row from t_data_source and confirms the physical file exists
at:  Stage0SourcePDFFiles/{year}/{source_url}

Reports:
  ✅ Found in correct year folder
  ❌ Missing entirely (not found anywhere)
  ⚠️  Found but in WRONG year folder (DB year ≠ folder year)

Uses 40 threads to parallelise GCS FUSE stat() calls.

Run on the VM:
    PYTHONPATH=/opt/avisk/app /opt/avisk/venv/bin/python3 \
        /opt/avisk/app/HelperFIles/validate_file_locations.py \
        --download-dir /opt/avisk/gcs-data/Development/data/Stage0SourcePDFFiles

Options:
    --download-dir   Path to Stage0SourcePDFFiles (default: GCS FUSE mount)
    --workers N      Parallel threads (default 40)
    --wrong-only     Only print mismatched/missing rows (suppress correct rows)
    --csv /tmp/validation.csv   Write full results to CSV
"""

import argparse
import csv
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
from Utilities.Lookups import DB_Connection


def find_actual_folder(download_dir: Path, db_year: int, filename: str):
    """
    Returns (actual_year_folder: str | None, status: str)
      status: 'correct', 'wrong_folder', 'missing'
    """
    # Check expected location first (fast path)
    expected = download_dir / str(db_year) / filename
    if expected.exists():
        return str(db_year), 'correct'

    # Scan all year folders for the file
    try:
        for year_dir in download_dir.iterdir():
            if not year_dir.is_dir():
                continue
            if not re.fullmatch(r'\d{4}', year_dir.name):
                continue
            if (year_dir / filename).exists():
                return year_dir.name, 'wrong_folder'
    except Exception:
        pass

    return None, 'missing'


def main():
    parser = argparse.ArgumentParser(description='Validate t_data_source file locations')
    parser.add_argument('--download-dir',
                        default='/opt/avisk/gcs-data/Development/data/Stage0SourcePDFFiles')
    parser.add_argument('--workers', type=int, default=40)
    parser.add_argument('--wrong-only', action='store_true',
                        help='Only print wrong/missing rows')
    parser.add_argument('--csv', default='', metavar='PATH',
                        help='Write results to CSV file')
    args = parser.parse_args()

    download_dir = Path(args.download_dir)
    if not download_dir.exists():
        print(f"❌ Download dir not found: {download_dir}")
        sys.exit(1)

    # Fetch all file rows from DB
    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT unique_id, company_name, year, source_url
        FROM   t_data_source
        WHERE  source_type = 'file'
          AND  source_url IS NOT NULL
          AND  source_url <> ''
        ORDER  BY unique_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total = len(rows)
    print(f"Validating {total:,} file records")
    print(f"  Download dir : {download_dir}")
    print(f"  Workers      : {args.workers}")
    print()

    # Thread-safe counters + results
    lock         = threading.Lock()
    correct      = [0]
    wrong_folder = [0]
    missing      = [0]
    done         = [0]
    results      = []          # list of dicts for CSV
    done_event   = threading.Event()
    t_start      = time.monotonic()

    def print_progress():
        with lock:
            n, c, w, m = done[0], correct[0], wrong_folder[0], missing[0]
        elapsed = time.monotonic() - t_start
        rate    = n / elapsed if elapsed > 0 else 0
        eta     = (total - n) / rate if rate > 0 else 0
        eta_s   = time.strftime('%H:%M:%S', time.gmtime(eta))
        print(f"  [{n:>6,}/{total:,}]  ✅ correct={c:,}  "
              f"⚠️  wrong_folder={w:,}  ❌ missing={m:,}  ETA {eta_s}",
              flush=True)

    def progress_printer():
        while not done_event.wait(timeout=10):
            print_progress()

    printer = threading.Thread(target=progress_printer, daemon=True)
    printer.start()

    def worker(row):
        uid      = row['unique_id']
        company  = row['company_name']
        db_year  = int(row['year'])
        filename = row['source_url']

        actual_folder, status = find_actual_folder(download_dir, db_year, filename)

        with lock:
            done[0] += 1
            if status == 'correct':
                correct[0] += 1
            elif status == 'wrong_folder':
                wrong_folder[0] += 1
                if not args.wrong_only:
                    pass
                print(f"  ⚠️  uid={uid:<6} | DB year={db_year} | actual={actual_folder} | "
                      f"{company[:30]} | {filename[:55]}", flush=True)
            else:  # missing
                missing[0] += 1
                print(f"  ❌ uid={uid:<6} | DB year={db_year} | NOT FOUND | "
                      f"{company[:30]} | {filename[:55]}", flush=True)

            if args.csv:
                results.append({
                    'uid':           uid,
                    'company':       company,
                    'db_year':       db_year,
                    'actual_folder': actual_folder or '',
                    'status':        status,
                    'filename':      filename,
                })

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(worker, row) for row in rows]
        for f in as_completed(futures):
            f.result()

    done_event.set()
    printer.join()
    print_progress()  # final line

    elapsed = time.monotonic() - t_start
    hh, rem = divmod(int(elapsed), 3600)
    mm, ss  = divmod(rem, 60)

    print()
    print(f"Done in {hh:02d}:{mm:02d}:{ss:02d}")
    print(f"  ✅ Correct location : {correct[0]:,}")
    print(f"  ⚠️  Wrong folder     : {wrong_folder[0]:,}")
    print(f"  ❌ Missing entirely  : {missing[0]:,}")

    if args.csv:
        csv_path = args.csv
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['uid', 'company', 'db_year',
                               'actual_folder', 'status', 'filename'])
            writer.writeheader()
            writer.writerows(results)
        print(f"\n  📄 Results written to: {csv_path}")

    if wrong_folder[0] > 0 or missing[0] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
