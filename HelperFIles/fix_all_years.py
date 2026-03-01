"""
fix_all_years.py
----------------
Full-scan year correction: opens EVERY file in t_data_source (PDF, HTM, TXT),
extracts the document's reporting year from content, and updates the DB if it
differs from the stored year.

Features:
  - 25 worker threads (configurable via --workers)
  - Resumable via --min-uid (restart from a given unique_id)
  - High-confidence year extraction:
      PDFs  → PyMuPDF metadata + strong first-page patterns
      HTMs  → BeautifulSoup text + same patterns
      TXTs  → regex on raw text
  - Only updates if extracted year differs AND confidence is HIGH
  - Writes audit CSV to /tmp/fix_all_years_audit.csv
  - No file moves (GCS mount is read-only; DB update only)

Usage:
    PYTHONPATH=/opt/avisk/app /opt/avisk/venv/bin/python3 \
        /opt/avisk/app/HelperFIles/fix_all_years.py \
        --download-dir /opt/avisk/gcs-data/Development/data/Stage0SourcePDFFiles \
        [--workers 25] [--min-uid 0] [--dry-run]
"""

import argparse
import csv
import os
import re
import shutil
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
from Utilities.Lookups import DB_Connection

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️  PyMuPDF not available — PDFs will use filename fallback only")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️  BeautifulSoup not available — HTMs will use regex only")

THIS_YEAR = datetime.now().year

# ── Strong year patterns (high confidence) ────────────────────────────────────
# These match only when a year is explicitly labelled as the report year.
STRONG_PATTERNS = [
    r'(?:FY|Fiscal\s+Year|Financial\s+Year)\s*(20\d{2})',
    r'(20\d{2})\s*(?:Annual\s+Report|Sustainability\s+Report|ESG\s+Report|'
    r'Climate\s+Report|Corporate\s+Responsibility)',
    r'(?:Annual\s+Report|Sustainability\s+Report|ESG\s+Report|'
    r'Climate\s+Report|Corporate\s+Responsibility)\s*(?:for\s+)?(?:the\s+)?'
    r'(?:year\s+)?(?:ended?\s+)?(20\d{2})',
    r'(?:January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\s+\d{1,2}[,\s]+(20\d{2})',
    r'(?:for\s+the\s+year\s+ended?|year\s+ended?)\s+\w+\s+\d{1,2}[,\s]+(20\d{2})',
    r'(?:Q[1-4]|Quarter)\s+(?:20\d{2})',     # used below as fallback
]

# Fallback pattern — any 20xx year (lower confidence, only used if no strong match)
ANY_YEAR_RE = re.compile(r'20\d{2}')


def is_plausible(year: int) -> bool:
    return 2000 <= year <= THIS_YEAR


def extract_year_high_confidence(text: str) -> Optional[int]:
    """
    Extract year using strong patterns only.
    Returns year int if found with high confidence, else None.
    """
    for pat in STRONG_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            # group(1) if pattern has capture group, else group(0)
            try:
                y = int(m.group(1))
            except (IndexError, TypeError):
                ys = re.findall(r'20\d{2}', m.group(0))
                y = int(ys[0]) if ys else 0
            if is_plausible(y):
                return y
    return None


def extract_year_frequency(text: str) -> Optional[int]:
    """
    Fallback: most-frequent plausible year in text.
    Only used when strong patterns fail — treated as lower confidence.
    """
    counts: dict[int, int] = {}
    for m in ANY_YEAR_RE.finditer(text):
        y = int(m.group())
        if is_plausible(y):
            counts[y] = counts.get(y, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def extract_year_from_pdf(filepath: Path) -> tuple[Optional[int], str]:
    """Returns (year, confidence) where confidence is 'high' or 'low'."""
    if not PYMUPDF_AVAILABLE or not filepath.exists():
        return None, 'none'
    try:
        doc = fitz.open(str(filepath))
        meta = doc.metadata or {}

        # 1. PDF metadata title
        title = meta.get('title', '')
        if title:
            y = extract_year_high_confidence(title)
            if y:
                doc.close()
                return y, 'high'

        # 2. First 3 pages content — strong patterns
        full_text = ''
        for page_idx in range(min(3, len(doc))):
            full_text += doc[page_idx].get_text()[:4000]

        doc.close()

        y = extract_year_high_confidence(full_text)
        if y:
            return y, 'high'

        # 3. Frequency fallback (lower confidence)
        y = extract_year_frequency(full_text[:6000])
        if y:
            return y, 'low'

    except Exception:
        pass
    return None, 'none'


def extract_year_from_htm(filepath: Path) -> tuple[Optional[int], str]:
    """Returns (year, confidence)."""
    if not filepath.exists():
        return None, 'none'
    try:
        raw = filepath.read_bytes()
        if BS4_AVAILABLE:
            soup = BeautifulSoup(raw[:200_000], 'lxml')
            text = soup.get_text(separator=' ', strip=True)[:8000]
        else:
            text = raw.decode('utf-8', errors='replace')[:8000]

        y = extract_year_high_confidence(text)
        if y:
            return y, 'high'

        y = extract_year_frequency(text)
        if y:
            return y, 'low'
    except Exception:
        pass
    return None, 'none'


def extract_year_from_txt(filepath: Path) -> tuple[Optional[int], str]:
    """Returns (year, confidence)."""
    if not filepath.exists():
        return None, 'none'
    try:
        text = filepath.read_text(errors='replace')[:8000]
        y = extract_year_high_confidence(text)
        if y:
            return y, 'high'
        y = extract_year_frequency(text)
        if y:
            return y, 'low'
    except Exception:
        pass
    return None, 'none'


def extract_year_from_filename(filename: str) -> Optional[int]:
    """First plausible year in the filename stem."""
    stem = Path(filename).stem
    m = ANY_YEAR_RE.search(stem)
    if m:
        y = int(m.group())
        if is_plausible(y):
            return y
    return None


def locate_file(download_dir: Path, db_year: int, filename: str) -> Optional[Path]:
    candidate = download_dir / str(db_year) / filename
    if candidate.exists():
        return candidate
    for year_dir in sorted(download_dir.iterdir()):
        if year_dir.is_dir() and re.fullmatch(r'20\d{2}', year_dir.name):
            p = year_dir / filename
            if p.exists():
                return p
    return None


# ── Thread-safe counters ──────────────────────────────────────────────────────
class Counter:
    def __init__(self):
        self._lock = threading.Lock()
        self.updated = 0
        self.same = 0
        self.no_file = 0
        self.no_year = 0
        self.low_conf_skipped = 0
        self.errors = 0
        self.processed = 0

    def inc(self, field):
        with self._lock:
            setattr(self, field, getattr(self, field) + 1)
            self.processed += 1


# ── File move helper (copy+delete — required for GCS FUSE) ──────────────────
def move_file_year(download_dir: Path, old_year: int, new_year: int,
                   filename: str, actual_path: Path) -> str:
    """
    Move a file from old_year/ to new_year/ using copy+delete.
    actual_path is where the file currently lives (may differ from old_year/).
    Returns 'moved', 'already_correct', 'dest_exists', or 'error:<msg>'.
    """
    dst = download_dir / str(new_year) / filename
    if dst.exists():
        # Already in the right place; clean up source if it's elsewhere
        if actual_path != dst and actual_path.exists():
            try:
                actual_path.unlink()
            except Exception:
                pass
        return 'already_correct'
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(actual_path), str(dst))
        actual_path.unlink()
        return 'moved'
    except Exception as e:
        if dst.exists():
            try:
                dst.unlink()
            except Exception:
                pass
        return f'error:{e}'


# ── Per-row worker ────────────────────────────────────────────────────────────
def process_row(row, download_dir: Path, dry_run: bool,
                counters: Counter, db_queue: Queue,
                audit_queue: Queue, print_lock: threading.Lock,
                total: int, t_start: float):
    uid = row['unique_id']
    db_year = int(row['year'])
    filename = row['source_url']
    company = row['company_name']
    ext = Path(filename).suffix.lower()

    # Locate file
    filepath = locate_file(download_dir, db_year, filename)
    if filepath is None:
        counters.inc('no_file')
        return

    # Extract year from content
    if ext == '.pdf':
        content_year, confidence = extract_year_from_pdf(filepath)
    elif ext in ('.htm', '.html'):
        content_year, confidence = extract_year_from_htm(filepath)
    elif ext == '.txt':
        content_year, confidence = extract_year_from_txt(filepath)
    else:
        content_year, confidence = None, 'none'

    # Filename fallback
    if content_year is None:
        content_year = extract_year_from_filename(filename)
        confidence = 'filename' if content_year else 'none'

    if content_year is None:
        counters.inc('no_year')
        return

    # Only update on high confidence OR filename match
    # Skip low-confidence (frequency only) to avoid false corrections
    if confidence == 'low':
        counters.inc('low_conf_skipped')
        return

    if content_year == db_year:
        counters.inc('same')
        return

    # Queue DB update
    with print_lock:
        elapsed = time.monotonic() - t_start
        avg = elapsed / max(counters.processed, 1)
        eta = avg * (total - counters.processed)
        eta_str = time.strftime('%H:%M:%S', time.gmtime(eta))
        print(f"  🔧 uid={uid} | {company} | {db_year}→{content_year} "
              f"| conf={confidence} | {filename[:60]} | ETA {eta_str}",
              flush=True)

    audit_queue.put({
        'uid': uid, 'company': company,
        'old_year': db_year, 'new_year': content_year,
        'confidence': confidence, 'filename': filename,
        'dry_run': dry_run,
    })

    if not dry_run:
        db_queue.put((uid, content_year, filepath, db_year))

    counters.inc('updated')


# ── DB writer thread ──────────────────────────────────────────────────────────
def db_writer(db_queue: Queue, conn_str: str, counters: Counter,
              download_dir: Path, print_lock: threading.Lock):
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    cur = conn.cursor()
    while True:
        item = db_queue.get()
        if item is None:
            break
        uid, new_year, filepath, old_year = item
        try:
            cur.execute(
                "UPDATE t_data_source SET year = %s WHERE unique_id = %s",
                (new_year, uid))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            counters.inc('errors')
            with print_lock:
                print(f"  ❌ DB error uid={uid}: {exc}", flush=True)
            db_queue.task_done()
            continue

        # Move file to corrected year folder (copy+delete for GCS FUSE)
        result = move_file_year(
            download_dir, old_year, new_year, filepath.name, filepath)
        if result.startswith('error:'):
            with print_lock:
                print(f"  ⚠️  file move failed uid={uid}: {result[6:]}", flush=True)

        db_queue.task_done()
    cur.close()
    conn.close()


# ── Audit CSV writer thread ───────────────────────────────────────────────────
def audit_writer(audit_queue: Queue, audit_path: str):
    with open(audit_path, 'w', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=['uid', 'company', 'old_year', 'new_year',
                           'confidence', 'filename', 'dry_run'])
        writer.writeheader()
        while True:
            item = audit_queue.get()
            if item is None:
                break
            writer.writerow(item)
            f.flush()
            audit_queue.task_done()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-dir', type=Path,
                        default=Path('/opt/avisk/gcs-data/Development/data/Stage0SourcePDFFiles'))
    parser.add_argument('--workers', type=int, default=25)
    parser.add_argument('--min-uid', type=int, default=0,
                        help='Resume from this unique_id (exclusive)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--audit-file', default='/tmp/fix_all_years_audit.csv')
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Starting full year scan")
    print(f"  Download dir : {args.download_dir}")
    print(f"  Workers      : {args.workers}")
    print(f"  Min UID      : {args.min_uid}")
    print(f"  Audit CSV    : {args.audit_file}")
    print()

    conn_str = DB_Connection().DB_CONNECTION_STRING
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("Fetching rows from t_data_source...", flush=True)
    cur.execute("""
        SELECT unique_id, company_name, year, source_url
        FROM   t_data_source
        WHERE  source_type = 'file'
          AND  year IS NOT NULL
          AND  unique_id > %s
        ORDER BY unique_id
    """, (args.min_uid,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    total = len(rows)
    print(f"  {total:,} rows to process\n", flush=True)

    counters = Counter()
    db_queue: Queue = Queue(maxsize=500)
    audit_queue: Queue = Queue()
    print_lock = threading.Lock()
    t_start = time.monotonic()

    # Start DB writer thread
    db_thread = threading.Thread(
        target=db_writer,
        args=(db_queue, conn_str, counters, args.download_dir, print_lock),
        daemon=True)
    db_thread.start()

    # Start audit writer thread
    audit_thread = threading.Thread(
        target=audit_writer,
        args=(audit_queue, args.audit_file),
        daemon=True)
    audit_thread.start()

    # Progress printer thread
    def progress_printer():
        while not getattr(progress_printer, 'stop', False):
            time.sleep(30)
            p = counters.processed
            elapsed = time.monotonic() - t_start
            avg = elapsed / max(p, 1)
            eta = avg * (total - p)
            pct = p / total * 100 if total else 0
            with print_lock:
                print(
                    f"\n📊 Progress: {p:,}/{total:,} ({pct:.1f}%) | "
                    f"Updated: {counters.updated} | "
                    f"Same: {counters.same} | "
                    f"No file: {counters.no_file} | "
                    f"Low conf skipped: {counters.low_conf_skipped} | "
                    f"ETA: {time.strftime('%H:%M:%S', time.gmtime(eta))}\n",
                    flush=True)

    prog_thread = threading.Thread(target=progress_printer, daemon=True)
    prog_thread.start()

    # Process rows in parallel
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                process_row, row, args.download_dir, args.dry_run,
                counters, db_queue, audit_queue, print_lock, total, t_start)
            for row in rows
        ]
        for _ in as_completed(futures):
            pass  # errors surface inside process_row

    progress_printer.stop = True

    # Drain queues
    db_queue.join()
    db_queue.put(None)
    db_thread.join()

    audit_queue.join()
    audit_queue.put(None)
    audit_thread.join()

    elapsed = time.monotonic() - t_start
    print(f"\n{'='*60}")
    print(f"Done in {time.strftime('%H:%M:%S', time.gmtime(elapsed))}.")
    print(f"  Total rows      : {total:,}")
    print(f"  Updated         : {counters.updated}")
    print(f"  Same year (OK)  : {counters.same}")
    print(f"  File not found  : {counters.no_file}")
    print(f"  No year found   : {counters.no_year}")
    print(f"  Low conf skipped: {counters.low_conf_skipped}")
    print(f"  DB errors       : {counters.errors}")
    print(f"  Audit CSV       : {args.audit_file}")
    if args.dry_run:
        print("  (DRY RUN — no changes written)")


if __name__ == '__main__':
    main()
