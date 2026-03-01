"""
full_year_scan.py
-----------------
Full scan of ALL t_data_source file rows to verify the stored year matches
the document's actual reporting year.

Strategy by file type:
  PDF  → PyMuPDF metadata + first-page high-confidence patterns
  HTM  → BeautifulSoup text + high-confidence patterns
  TXT  → regex directly on text content

HIGH-CONFIDENCE patterns required (to avoid false positives):
  "Annual Report 2022", "FY 2022", "Fiscal Year 2022",
  "2022 Sustainability Report", "For the year ended ... 2022",
  "Dated: January 2022", cover-page date lines, etc.
  Low-confidence: lone year with no context → SKIPPED (no update)

Safeguards:
  --dry-run    : print changes without writing
  --min-uid N  : resume from uid > N (for crash recovery)
  --limit N    : process at most N rows
  --audit-csv  : path to write CSV log of every change (default /tmp/year_fixes.csv)

Usage:
  python3 full_year_scan.py [--dry-run] [--min-uid 0] [--limit 0] [--audit-csv /tmp/year_fixes.csv]
"""

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️  PyMuPDF not available — PDF content extraction disabled")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️  BeautifulSoup not available — HTM text extraction disabled")

from Utilities.Lookups import DB_Connection

THIS_YEAR = 2026
DOWNLOAD_DIR_DEFAULT = Path("/opt/avisk/gcs-data/Development/data/Stage0SourcePDFFiles")

# ── High-confidence year patterns ─────────────────────────────────────────────
# Each must have a contextual keyword near the year.
HC_PATTERNS = [
    # "Annual Report 2022" / "2022 Annual Report"
    r'(?:Annual\s+Report|Sustainability\s+Report|ESG\s+Report|Climate\s+Report|'
    r'Corporate\s+Responsibility|Proxy\s+Statement|10-K|10K)\s*[\-–—]?\s*(20\d{2})',
    r'(20\d{2})\s*[\-–—]?\s*(?:Annual\s+Report|Sustainability\s+Report|ESG\s+Report|'
    r'Climate\s+Report|Corporate\s+Responsibility|Proxy\s+Statement|10-K|10K)',
    # "FY 2022" / "Fiscal Year 2022" / "FY2022"
    r'(?:FY|Fiscal\s+Year)\s*[\-–]?\s*(20\d{2})',
    # "For the year ended December 31, 2022"
    r'[Ff]or\s+the\s+year\s+ended\s+[A-Za-z]+\s+\d{1,2},?\s+(20\d{2})',
    # "Year Ended December 31, 2022"
    r'[Yy]ear\s+[Ee]nded\s+[A-Za-z]+\s+\d{1,2},?\s+(20\d{2})',
    # Month Day, Year at start of doc (cover page date)
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2},\s+(20\d{2})',
    # "Dated January 2022" / "Published: March 2022"
    r'(?:Dated|Published|Issued|Released):?\s+[A-Za-z]+\s+(20\d{2})',
    # "Report Year: 2022" / "Reporting Year: 2022"
    r'[Rr]eport(?:ing)?\s+[Yy]ear\s*:?\s*(20\d{2})',
    # "Data as of 2022" / "as of December 31, 2022"
    r'[Aa]s\s+of\s+(?:[A-Za-z]+\s+\d{1,2},?\s+)?(20\d{2})',
]
HC_RE = [re.compile(p, re.IGNORECASE) for p in HC_PATTERNS]


def extract_year_high_confidence(text: str) -> Optional[int]:
    """Return year only if a high-confidence pattern matches. None otherwise."""
    for pattern in HC_RE:
        m = pattern.search(text)
        if m:
            try:
                y = int(m.group(1))
                if 2000 <= y <= THIS_YEAR:
                    return y
            except (IndexError, ValueError):
                pass
    return None


def year_from_pdf(filepath: Path) -> tuple[Optional[int], str]:
    """
    Extract high-confidence year from PDF.
    Returns (year, source) where source describes how year was found.
    """
    if not PYMUPDF_AVAILABLE:
        return None, "pymupdf_unavailable"
    try:
        doc = fitz.open(str(filepath))
        meta = doc.metadata or {}

        # 1. PDF creation/mod date metadata (most reliable for EDGAR docs)
        for key in ('creationDate', 'modDate'):
            val = meta.get(key, '')
            m = re.search(r'(20\d{2})', val)
            if m:
                y = int(m.group(1))
                if 2000 <= y <= THIS_YEAR:
                    doc.close()
                    return y, f"pdf_metadata_{key}"

        # 2. PDF title metadata
        title = meta.get('title', '')
        if title:
            y = extract_year_high_confidence(title)
            if y:
                doc.close()
                return y, "pdf_metadata_title"

        # 3. First 3 pages — high-confidence patterns only
        pages_text = ""
        for i in range(min(3, len(doc))):
            pages_text += doc[i].get_text()[:3000]

        doc.close()

        y = extract_year_high_confidence(pages_text)
        if y:
            return y, "pdf_content_hc"

        return None, "pdf_no_hc_match"

    except Exception as exc:
        return None, f"pdf_error:{exc}"


def year_from_htm(filepath: Path) -> tuple[Optional[int], str]:
    """Extract high-confidence year from HTM/HTML file."""
    if not BS4_AVAILABLE:
        return None, "bs4_unavailable"
    try:
        raw = filepath.read_bytes()
        soup = BeautifulSoup(raw, 'lxml')
        text = soup.get_text(separator=' ', strip=True)[:6000]
        y = extract_year_high_confidence(text)
        if y:
            return y, "htm_content_hc"
        return None, "htm_no_hc_match"
    except Exception as exc:
        return None, f"htm_error:{exc}"


def year_from_txt(filepath: Path) -> tuple[Optional[int], str]:
    """Extract high-confidence year from plain text file."""
    try:
        text = filepath.read_text(errors='replace')[:6000]
        y = extract_year_high_confidence(text)
        if y:
            return y, "txt_content_hc"
        return None, "txt_no_hc_match"
    except Exception as exc:
        return None, f"txt_error:{exc}"


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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--min-uid', type=int, default=0,
                        help="Resume: process only uid > this value")
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--download-dir', type=Path, default=DOWNLOAD_DIR_DEFAULT)
    parser.add_argument('--audit-csv', type=Path, default=Path('/tmp/year_fixes.csv'))
    args = parser.parse_args()

    download_dir: Path = args.download_dir
    dry_run: bool = args.dry_run

    print(f"{'[DRY RUN] ' if dry_run else ''}Full year scan starting...")
    print(f"  Download dir : {download_dir}")
    print(f"  Min UID      : {args.min_uid}")
    print(f"  Audit CSV    : {args.audit_csv}")

    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    limit_sql = f"LIMIT {args.limit}" if args.limit > 0 else ""
    min_uid_sql = f"AND unique_id > {args.min_uid}" if args.min_uid > 0 else ""

    print("Fetching rows...", flush=True)
    cur.execute(f"""
        SELECT unique_id, company_name, year, source_url, original_source_url
        FROM   t_data_source
        WHERE  source_type = 'file'
          AND  source_url IS NOT NULL
          {min_uid_sql}
        ORDER BY unique_id
        {limit_sql}
    """)
    rows = cur.fetchall()
    total = len(rows)
    print(f"  {total:,} rows to process.\n", flush=True)

    # ── Audit CSV setup ───────────────────────────────────────────────────────
    csv_file = open(args.audit_csv, 'w', newline='')
    writer = csv.writer(csv_file)
    writer.writerow(['uid', 'company', 'old_year', 'new_year', 'source', 'filename'])

    # ── Counters ──────────────────────────────────────────────────────────────
    updated = correct = no_file = no_hc = errors = 0
    _t_start = time.monotonic()
    BATCH_COMMIT = 100
    pending_updates: list[tuple[int, int]] = []  # (new_year, uid)

    for idx, row in enumerate(rows, 1):
        uid = row['unique_id']
        db_year = int(row['year'])
        filename = row['source_url']
        company = row['company_name']

        # ── Progress every 200 rows ───────────────────────────────────────────
        if idx % 200 == 0 or idx == total:
            elapsed = time.monotonic() - _t_start
            avg = elapsed / idx
            eta = time.strftime('%H:%M:%S', time.gmtime(avg * (total - idx)))
            print(f"[{idx:,}/{total:,}] elapsed={time.strftime('%H:%M:%S', time.gmtime(elapsed))} "
                  f"ETA={eta} | updated={updated} correct={correct} no_file={no_file} "
                  f"no_hc={no_hc} errors={errors}", flush=True)

        # Locate file
        filepath = locate_file(download_dir, db_year, filename)
        if filepath is None:
            no_file += 1
            continue

        # Extract year by file type
        suffix = filepath.suffix.lower()
        if suffix == '.pdf':
            doc_year, source = year_from_pdf(filepath)
        elif suffix in ('.htm', '.html'):
            doc_year, source = year_from_htm(filepath)
        elif suffix == '.txt':
            doc_year, source = year_from_txt(filepath)
        else:
            no_hc += 1
            continue

        if doc_year is None:
            no_hc += 1
            continue

        if doc_year == db_year:
            correct += 1
            continue

        # Year mismatch — log and queue update
        print(f"  UID {uid} | {company} | {filename[:60]}", flush=True)
        print(f"    DB year={db_year}  →  doc year={doc_year}  [{source}]", flush=True)

        writer.writerow([uid, company, db_year, doc_year, source, filename])
        csv_file.flush()

        if not dry_run:
            pending_updates.append((doc_year, uid))
            updated += 1

            # Batch commit every BATCH_COMMIT updates
            if len(pending_updates) >= BATCH_COMMIT:
                try:
                    update_cur = conn.cursor()
                    update_cur.executemany(
                        "UPDATE t_data_source SET year = %s WHERE unique_id = %s",
                        pending_updates
                    )
                    update_cur.close()
                    conn.commit()
                    print(f"  ✔  Committed batch of {len(pending_updates)} updates", flush=True)
                    pending_updates.clear()
                except Exception as exc:
                    conn.rollback()
                    print(f"  ❌ Batch commit error: {exc}", flush=True)
                    errors += len(pending_updates)
                    pending_updates.clear()
        else:
            updated += 1

    # Commit any remaining
    if pending_updates and not dry_run:
        try:
            update_cur = conn.cursor()
            update_cur.executemany(
                "UPDATE t_data_source SET year = %s WHERE unique_id = %s",
                pending_updates
            )
            update_cur.close()
            conn.commit()
            print(f"  ✔  Final commit: {len(pending_updates)} updates", flush=True)
        except Exception as exc:
            conn.rollback()
            print(f"  ❌ Final commit error: {exc}", flush=True)
            errors += len(pending_updates)

    csv_file.close()
    elapsed_total = time.monotonic() - _t_start

    print(f"\n{'='*60}")
    print(f"Done in {time.strftime('%H:%M:%S', time.gmtime(elapsed_total))}.")
    print(f"  Total processed : {total:,}")
    print(f"  Year corrected  : {updated}")
    print(f"  Already correct : {correct}")
    print(f"  File not found  : {no_file}")
    print(f"  No HC match     : {no_hc}")
    print(f"  Errors          : {errors}")
    print(f"  Audit CSV       : {args.audit_csv}")
    if dry_run:
        print("  (DRY RUN — no changes written)")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
