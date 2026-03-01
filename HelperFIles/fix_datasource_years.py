"""
fix_datasource_years.py
-----------------------
One-shot repair script: finds t_data_source rows whose `year` column is likely
wrong because the source URL contained two different years (e.g. a 2025 folder
path but a 2021 document year), then re-derives the correct year by:

  1. Collecting all distinct plausible 20xx years from original_source_url.
  2. If only one year  → already unambiguous, skip.
  3. If two or more   → open the local PDF file (via file path reconstructed
                        from the download directory + year + source_url filename)
                        and extract the year from PDF metadata / first-page text.
  4. If PDF year differs from DB year → update t_data_source.year and move
     the local file to the correct year sub-folder.

Usage:
    conda run -n data-company-gcc python3 HelperFIles/fix_datasource_years.py [--dry-run]

    --dry-run : print proposed changes without writing anything to DB or disk.
    --limit N : process at most N rows (default: unlimited).
"""

from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
import argparse
import os
import re
import sys
import shutil
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# ── Bootstrap path so local modules import cleanly ────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️  PyMuPDF not installed — PDF content extraction unavailable. "
          "Will fall back to filename-stem heuristic only.")


# ── Config ────────────────────────────────────────────────────────────────────
# Base directory where PDFs are stored (year sub-folders live here)
DEFAULT_DOWNLOAD_DIR = Path(
    os.environ.get("AVISK_DOWNLOAD_DIR",
                   "/opt/avisk/sustainability_reports")
)
THIS_YEAR = 2026


# ── Helpers ───────────────────────────────────────────────────────────────────

def plausible_years(text: str) -> list[int]:
    """Return sorted list of distinct plausible 20xx years found in text."""
    return sorted({int(m) for m in re.findall(r'20\d{2}', text or '')
                   if 2000 <= int(m) <= THIS_YEAR})


def extract_year_from_pdf(filepath: Path) -> Optional[int]:
    """Open a local PDF and return the best-guess reporting year, or None."""
    if not PYMUPDF_AVAILABLE or not filepath.exists():
        return None
    try:
        doc = fitz.open(str(filepath))
        meta = doc.metadata or {}

        # 1. Metadata dates
        for key in ('creationDate', 'modDate', 'title'):
            val = meta.get(key, '')
            m = re.search(r'20\d{2}', val)
            if m:
                y = int(m.group())
                if 2000 <= y <= THIS_YEAR:
                    doc.close()
                    return y

        # 2. First-page content patterns
        if len(doc) > 0:
            text = doc[0].get_text()[:3000]
            patterns = [
                r'(?:FY|Fiscal Year|Annual Report|Report)\s*(20\d{2})',
                r'(20\d{2})\s*(?:Annual|Report|Sustainability|ESG|Environmental|Climate)',
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+(20\d{2})',
            ]
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    y = int(m.group(1))
                    if 2000 <= y <= THIS_YEAR:
                        doc.close()
                        return y

            # Fallback: most-frequent plausible year in first page
            counts: dict[int, int] = {}
            for m in re.finditer(r'20\d{2}', text):
                y = int(m.group())
                if 2000 <= y <= THIS_YEAR:
                    counts[y] = counts.get(y, 0) + 1
            if counts:
                doc.close()
                return max(counts, key=counts.get)

        doc.close()
    except Exception as exc:
        print(f"    ⚠️  PDF parse error for {filepath}: {exc}")
    return None


def locate_file(download_dir: Path, db_year: int, filename: str) -> Optional[Path]:
    """
    Try to find the PDF on disk.  Checks the DB year folder first, then
    scans all year sub-folders in case the file was already partially moved.
    """
    candidate = download_dir / str(db_year) / filename
    if candidate.exists():
        return candidate
    # Scan other year folders
    for year_dir in sorted(download_dir.iterdir()):
        if year_dir.is_dir() and re.fullmatch(r'20\d{2}', year_dir.name):
            p = year_dir / filename
            if p.exists():
                return p
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fix t_data_source year values")
    parser.add_argument('--dry-run', action='store_true',
                        help="Print changes without writing to DB or disk")
    parser.add_argument('--limit', type=int, default=0,
                        help="Max rows to process (0 = all)")
    parser.add_argument('--download-dir', type=Path,
                        default=DEFAULT_DOWNLOAD_DIR,
                        help="Base directory where PDF year-folders live")
    args = parser.parse_args()

    download_dir: Path = args.download_dir
    dry_run: bool = args.dry_run

    print(f"{'[DRY RUN] ' if dry_run else ''}Connecting to DB...")
    conn_str = DB_Connection().DB_CONNECTION_STRING
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ── Fetch rows where original_source_url has >=2 distinct plausible years ─
    # We do the heavy filtering in Python because regex across 65k rows in
    # Postgres is fine, but pulling unique_id + url + year + filename is cheap.
    print("Fetching rows from t_data_source...")
    limit_sql = f"LIMIT {args.limit}" if args.limit > 0 else ""
    cur.execute(f"""
        SELECT unique_id, company_name, year, source_url, original_source_url
        FROM   t_data_source
        WHERE  original_source_url IS NOT NULL
          AND  original_source_url <> ''
          AND  source_type = 'file'
        ORDER BY unique_id
        {limit_sql}
    """)
    rows = cur.fetchall()
    total_rows = len(rows)
    print(f"  {total_rows:,} rows fetched.")

    # Filter to only those with >=2 distinct years in the URL, with progress
    print("Scanning for ambiguous URLs...", flush=True)
    ambiguous = []
    for i, r in enumerate(rows, 1):
        if len(plausible_years(r['original_source_url'])) >= 2:
            ambiguous.append(r)
        if i % 5000 == 0 or i == total_rows:
            pct = i / total_rows * 100
            print(f"  Scanned {i:,}/{total_rows:,} ({pct:.1f}%) — {len(ambiguous)} ambiguous so far",
                  flush=True)

    total_ambiguous = len(ambiguous)
    print(
        f"\n  {total_ambiguous} rows have >=2 distinct years in original_source_url.\n")

    updated = skipped_no_file = skipped_same_year = skipped_no_pdf_year = 0
    errors = 0
    _t_start = time.monotonic()

    for _idx, row in enumerate(ambiguous, 1):
        uid = row['unique_id']
        db_year = int(row['year'])
        filename = row['source_url']          # source_url stores the filename
        url = row['original_source_url']
        company = row['company_name']

        # ── Progress header ───────────────────────────────────────────────
        elapsed = time.monotonic() - _t_start
        avg_sec = elapsed / _idx
        remaining = avg_sec * (total_ambiguous - _idx)
        eta_str = time.strftime('%H:%M:%S', time.gmtime(
            remaining)) if _idx > 1 else '??:??:??'
        print(f"\n[{_idx}/{total_ambiguous}] uid={uid} | {company} "
              f"| DB year={db_year} | ETA {eta_str}", flush=True)

        url_years = plausible_years(url)
        print(f"  URL years={url_years} | {filename}")

        # Locate the file on disk
        filepath = locate_file(download_dir, db_year, filename)
        if filepath is None:
            print(f"    ⏭  File not found on disk — skipping")
            skipped_no_file += 1
            continue

        # Extract year from PDF (only for actual PDF files)
        is_pdf = filepath.suffix.lower() == '.pdf'
        if is_pdf:
            pdf_year = extract_year_from_pdf(filepath)
        else:
            # For HTM/TXT/other files PyMuPDF gives unreliable results;
            # rely solely on the filename date.
            pdf_year = None
            print(
                f"    ℹ️  Non-PDF file ({filepath.suffix}) — skipping content extraction")

        if pdf_year is None:
            # Fall back: first year in filename stem
            fname_stem = Path(filename).stem
            m = re.search(r'20\d{2}', fname_stem)
            if m:
                pdf_year = int(m.group())
                print(
                    f"    📄 {'PDF inconclusive' if is_pdf else 'Filename'} — using filename year: {pdf_year}")
            else:
                print(
                    f"    ❓ Could not determine year from {'PDF or ' if is_pdf else ''}filename — skipping")
                skipped_no_pdf_year += 1
                continue
        else:
            print(f"    📄 PDF year: {pdf_year}")

        if pdf_year == db_year:
            print(f"    ✅ Year already correct ({db_year}) — no change needed")
            skipped_same_year += 1
            continue

        print(f"    🔧 Updating year: {db_year} → {pdf_year}")

        if not dry_run:
            # 1. Update DB (always)
            try:
                update_cur = conn.cursor()
                update_cur.execute(
                    "UPDATE t_data_source SET year = %s WHERE unique_id = %s",
                    (pdf_year, uid)
                )
                update_cur.close()
                conn.commit()
                updated += 1
                print(f"    ✔  DB updated year={pdf_year}")
            except Exception as exc:
                conn.rollback()
                print(f"    ❌ DB update error: {exc}")
                errors += 1
                continue

            # 2. Move file to correct year folder (best-effort — GCS-fuse may deny)
            try:
                new_dir = download_dir / str(pdf_year)
                new_dir.mkdir(parents=True, exist_ok=True)
                new_path = new_dir / filepath.name
                if not new_path.exists():
                    shutil.move(str(filepath), str(new_path))
                    print(f"    📁 Moved: {filepath} → {new_path}")
                else:
                    print(
                        f"    📁 Target already exists, leaving file in place: {filepath}")
            except PermissionError as pe:
                print(
                    f"    ⚠️  File move skipped (permission denied on GCS mount): {pe}")
            except Exception as exc:
                print(f"    ⚠️  File move failed (DB already updated): {exc}")
        else:
            print(
                f"    [DRY RUN] Would update DB year={pdf_year} and move file.")
            updated += 1

    _total_elapsed = time.monotonic() - _t_start
    print(f"\n{'='*60}")
    print(f"Done in {time.strftime('%H:%M:%S', time.gmtime(_total_elapsed))}.")
    print(
        f"  Processed      : {total_ambiguous:,} ambiguous rows (of {total_rows:,} total)")
    print(f"  Updated        : {updated}")
    print(f"  Same year (OK) : {skipped_same_year}")
    print(f"  File not found : {skipped_no_file}")
    print(f"  No PDF year    : {skipped_no_pdf_year}")
    print(f"  Errors         : {errors}")
    if dry_run:
        print("  (DRY RUN — no changes written)")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
