"""
CleanupDuplicates.py
====================
Scans t_data_source for records sharing the same file_hash_sha256, then
uses PDF content analysis (via PyMuPDF + GCS) to determine which copy is
canonical and deletes the others.

Decision rules
--------------
  Same-company prefix (TICK_... vs TICK_...)
      → delete the duplicate ID (keep is canonical)

  Cross-company, content clearly belongs to "keep" company
      → delete the duplicate ID

  Cross-company, content clearly belongs to "dup" company (keep is wrong)
      → delete the KEEP ID (the mislabelled one)

  Cross-company, neither company name appears (shared third-party doc)
      → keep BOTH — legit multi-company document, delete neither

  Cross-company, file missing / unreadable
      → skip — never delete without certainty

  No-prefix filename (no recognisable ticker)
      → delete the duplicate ID (keep lower unique_id)

Usage
-----
  # dry run — prints what would be deleted, touches nothing
  python CleanupDuplicates.py --dry-run

  # write mode — executes the DELETE
  python CleanupDuplicates.py

  # use a specific backfill log instead of querying the DB fresh
  python CleanupDuplicates.py --log /tmp/backfill_live.txt

  # combine
  python CleanupDuplicates.py --dry-run --log /tmp/backfill_live.txt
"""

from Utilities.Lookups import DB_Connection
from Utilities.PathConfiguration import PathConfiguration
from Utilities.GCSFileManager import GCSFileManager
import argparse
import re
import sys

import fitz       # PyMuPDF  (pip install pymupdf)
import psycopg2

sys.path.insert(0, "/Users/mohanganadal/Avisk/Avisk-Core-Services")


# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Remove duplicate records from t_data_source")
parser.add_argument("--dry-run", action="store_true",
                    help="Print what would be deleted without touching the DB")
parser.add_argument("--log", metavar="PATH",
                    help="Path to a BackfillFileHashes output log to read duplicate "
                         "pairs from. If omitted, duplicates are queried fresh from DB.")
args = parser.parse_args()


# ── GCS setup ─────────────────────────────────────────────────────────────────
pc = PathConfiguration()
gcs = GCSFileManager(pc)


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_db_conn():
    return psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)


def build_ticker_map():
    """Derive ticker → company_name from filenames stored in the DB."""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT source_url, company_name FROM t_data_source WHERE source_url IS NOT NULL")
    mapping = {}
    for url, cname in cur.fetchall():
        fname = url.split("/")[-1] if "/" in url else url
        parts = fname.split("_", 1)
        if len(parts) > 1 and parts[0].isupper() and 1 < len(parts[0]) <= 5:
            ticker = parts[0]
            if ticker not in mapping and cname:
                mapping[ticker] = cname
    cur.close()
    conn.close()
    return mapping


def fetch_duplicate_pairs_from_db():
    """
    Query t_data_source for all records that share a file_hash_sha256,
    returning a list of (keep_rec, dup_rec) tuples where keep_rec is the
    lowest unique_id for that hash.
    rec = (unique_id, filename_stem)
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT unique_id, source_url, file_hash_sha256
        FROM   t_data_source
        WHERE  file_hash_sha256 IS NOT NULL
        ORDER  BY file_hash_sha256, unique_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Group by hash
    from collections import defaultdict
    by_hash = defaultdict(list)
    for uid, url, h in rows:
        fname = url.split("/")[-1] if url and "/" in url else (url or "")
        by_hash[h].append((uid, fname))

    pairs = []
    for recs in by_hash.values():
        if len(recs) < 2:
            continue
        keep = recs[0]
        for dup in recs[1:]:
            pairs.append((keep, dup))
    return pairs


def fetch_duplicate_pairs_from_log(log_path):
    """Parse (keep, dup) pairs from a BackfillFileHashes log file."""
    pairs = []
    keep = None
    with open(log_path) as f:
        for line in f:
            km = re.match(r"\s+Keep\s+:\s+id=\s*(\d+)\s+(\S+)", line)
            dm = re.match(r"\s+Duplicate:\s+id=\s*(\d+)\s+(\S+)", line)
            if km:
                keep = (int(km.group(1)), km.group(2))
            elif dm and keep:
                pairs.append((keep, (int(dm.group(1)), dm.group(2))))
    return pairs


# ── PDF helpers ───────────────────────────────────────────────────────────────
def fetch_pdf_bytes(year, filename):
    try:
        return gcs.download_as_bytes(f"Stage0SourcePDFFiles/{year}/{filename}")
    except Exception:
        return None


def extract_text(pdf_bytes, max_pages=3):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(doc[i].get_text()
                       for i in range(min(max_pages, len(doc))))
        doc.close()
        return text.lower()
    except Exception:
        return ""


def score_company(text, ticker, company_name):
    """Count weighted occurrences of the ticker and company name in text."""
    score = 0
    if ticker:
        score += text.count(ticker.lower()) * 2
    if company_name:
        name_lower = company_name.lower()
        score += text.count(name_lower) * 3
        first_word = name_lower.split()[0]
        if len(first_word) > 3:
            score += text.count(first_word)
    return score


# ── filename helpers ──────────────────────────────────────────────────────────
def ticker_from_filename(fname):
    parts = fname.split("_", 1)
    return parts[0] if (len(parts) > 1 and parts[0].isupper() and 1 < len(parts[0]) <= 5) else None


def year_from_filename(fname):
    m = re.search(r"-(\d{4})\.pdf$", fname, re.I)
    return m.group(1) if m else None


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Dry-run mode : {args.dry_run}")

    print("Building ticker → company name map from DB...")
    TICKER_TO_NAME = build_ticker_map()

    if args.log:
        print(f"Reading duplicate pairs from log: {args.log}")
        all_dups = fetch_duplicate_pairs_from_log(args.log)
    else:
        print("Querying duplicate pairs fresh from DB...")
        all_dups = fetch_duplicate_pairs_from_db()

    print(f"Total duplicate pairs to evaluate: {len(all_dups)}")
    print()

    to_delete = set()
    stats = {
        "same":       0,
        "cross_keep": 0,
        "cross_dup":  0,
        "shared":     0,
        "unreadable": 0,
        "no_prefix":  0,
    }

    for keep_rec, dup_rec in all_dups:
        keep_id, keep_fname = keep_rec
        dup_id,  dup_fname = dup_rec

        kp = ticker_from_filename(keep_fname)
        dp = ticker_from_filename(dup_fname)

        # Case 1: same-company prefix — straightforward duplicate
        if kp and dp and kp == dp:
            to_delete.add(dup_id)
            stats["same"] += 1
            continue

        # Case 2: no ticker prefix — keep the lower ID
        if kp is None or dp is None:
            to_delete.add(dup_id)
            stats["no_prefix"] += 1
            continue

        # Case 3: different ticker — need PDF content to decide
        year = year_from_filename(
            keep_fname) or year_from_filename(dup_fname) or "2024"
        pdf_bytes = fetch_pdf_bytes(
            year, keep_fname) or fetch_pdf_bytes(year, dup_fname)

        if not pdf_bytes:
            stats["unreadable"] += 1
            continue   # never delete without reading the content

        text = extract_text(pdf_bytes)
        if not text.strip():
            stats["unreadable"] += 1
            continue

        keep_score = score_company(text, kp, TICKER_TO_NAME.get(kp, ""))
        dup_score = score_company(text, dp, TICKER_TO_NAME.get(dp, ""))
        diff = abs(keep_score - dup_score)
        total = keep_score + dup_score

        if total == 0 or diff < 2:
            # Shared third-party doc — keep both records
            stats["shared"] += 1
        elif keep_score > dup_score:
            to_delete.add(dup_id)
            stats["cross_keep"] += 1
        else:
            # Keep is mislabelled — delete it, the dup is the real one
            to_delete.add(keep_id)
            stats["cross_dup"] += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"{'='*70}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'='*70}")
    print(f"  Same-company dups (delete dup)          : {stats['same']}")
    print(f"  Cross-company, keep is correct (del dup): {stats['cross_keep']}")
    print(f"  Cross-company, dup is correct (del keep): {stats['cross_dup']}")
    print(f"  Shared third-party doc (keep both)      : {stats['shared']}")
    print(f"  Unreadable / missing file (skip)        : {stats['unreadable']}")
    print(f"  No-prefix filename (del dup)            : {stats['no_prefix']}")
    print(f"{'='*70}")
    print(f"  Total IDs to DELETE                     : {len(to_delete)}")

    if not to_delete:
        print("\nNothing to delete.")
        return

    ids_sorted = sorted(to_delete)
    print(
        f"\nDELETE FROM t_data_source WHERE unique_id IN ({', '.join(str(i) for i in ids_sorted)});")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return

    # ── Execute ───────────────────────────────────────────────────────────────
    print(f"\nExecuting DELETE of {len(to_delete)} records...")
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM t_data_source WHERE unique_id = ANY(%s)", (ids_sorted,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅  Deleted {deleted} records from t_data_source.")


if __name__ == "__main__":
    main()
