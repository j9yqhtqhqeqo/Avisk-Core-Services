"""
Backfill SHA-256 hashes for existing t_data_source records that have no hash.

For each record in t_data_source where file_hash_sha256 IS NULL:
  1. Locate the PDF in GCS under Stage0SourcePDFFiles/{year}/{filename}
     (falls back to local disk if GCS is unavailable)
  2. Compute SHA-256 of the file content
  3. Update file_hash_sha256 and file_size_bytes in t_data_source
  4. Detect and report any cross-record content duplicates discovered during backfill

Usage:
    python Services/BackfillFileHashes.py [--dry-run] [--year YEAR]

Options:
    --dry-run      Report what would be updated without writing to the database.
    --year YEAR    Only process records for a specific year (e.g. --year 2024).
"""

from Utilities.GCSFileManager import GCSFileManager
from Utilities.PathConfiguration import PathConfiguration
from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
import sys
import os
import hashlib
import argparse
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def calculate_hash_from_bytes(content: bytes) -> str:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(content).hexdigest()


def extract_filename(source_url: str) -> str | None:
    """
    Extract a clean PDF filename from source_url.
    source_url may be a plain filename or a full URL.
    Returns None if no valid PDF filename can be derived.
    """
    parsed = urlparse(source_url)
    if parsed.scheme in ('http', 'https'):
        filename = os.path.basename(parsed.path)
    else:
        filename = os.path.basename(source_url)

    if not filename or not filename.lower().endswith('.pdf'):
        return None
    if len(filename) > 255:   # URL-encoded blob stored as filename
        return None
    return filename


def fetch_file_bytes(gcs: GCSFileManager, year: int, filename: str,
                     local_base: Path) -> bytes | None:
    """
    Try to fetch file content:
      1. From GCS  (Stage0SourcePDFFiles/{year}/{filename})
      2. Fallback: local disk  (local_base / year / filename)
    Returns raw bytes or None if not found anywhere.
    """
    gcs_relative = f"Stage0SourcePDFFiles/{year}/{filename}"

    # ── GCS ──────────────────────────────────────────────────────────────────
    if gcs.is_available():
        content = gcs.download_as_bytes(gcs_relative)
        if content is not None:
            return content

    # ── Local fallback ───────────────────────────────────────────────────────
    for candidate in [local_base / str(year) / filename, local_base / filename]:
        try:
            if candidate.exists():
                return candidate.read_bytes()
        except OSError:
            pass

    return None


def backfill_hashes(dry_run: bool = False, year_filter: int | None = None):
    path_config = PathConfiguration()
    gcs = GCSFileManager(path_config)
    local_base = Path(path_config.get_stage0_input_path())

    print(f"GCS available      : {gcs.is_available()}")
    if gcs.is_available():
        print(f"GCS bucket         : {gcs.bucket_name}")
        print(f"GCS prefix         : {gcs.gcs_prefix}")
    print(f"Local fallback dir : {local_base}")
    print(f"Dry-run mode       : {dry_run}")
    if year_filter:
        print(f"Year filter        : {year_filter}")
    print("=" * 70)

    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Fetch records without a hash
    if year_filter:
        cur.execute("""
            SELECT unique_id, company_name, year, source_url, file_size_bytes
            FROM t_data_source
            WHERE file_hash_sha256 IS NULL AND year = %s
            ORDER BY company_name
        """, (year_filter,))
    else:
        cur.execute("""
            SELECT unique_id, company_name, year, source_url, file_size_bytes
            FROM t_data_source
            WHERE file_hash_sha256 IS NULL
            ORDER BY year, company_name
        """)
    records = cur.fetchall()
    print(f"Records without hash: {len(records)}\n")

    updated = 0
    not_found = 0
    errors = 0
    duplicates_found = []

    # In-memory hash map to detect duplicates within this run
    seen_hashes: dict[str, dict] = {}

    for rec in records:
        uid = rec['unique_id']
        company = rec['company_name']
        year = rec['year']
        source_url = rec['source_url']

        filename = extract_filename(source_url)
        if not filename:
            print(
                f"  [SKIP      ] id={uid:6d}  {company} ({year})  no valid filename")
            not_found += 1
            continue

        content = fetch_file_bytes(gcs, year, filename, local_base)

        if content is None:
            print(
                f"  [NOT FOUND ] id={uid:6d}  {company} ({year})  {filename}")
            not_found += 1
            continue

        try:
            file_hash = calculate_hash_from_bytes(content)
            file_size = len(content)

            # ── Duplicate check within this backfill run ──────────────────
            if file_hash in seen_hashes:
                original = seen_hashes[file_hash]
                duplicates_found.append({
                    'hash': file_hash,
                    'original_id': original['unique_id'],
                    'original_file': original['source_url'],
                    'duplicate_id': uid,
                    'duplicate_file': source_url,
                    'company': company,
                    'year': year,
                })
                print(f"  [DUPLICATE ] id={uid:6d}  {company} ({year})")
                print(f"               {filename}")
                print(
                    f"               same content as id={original['unique_id']}  {original['source_url']}")
            else:
                seen_hashes[file_hash] = rec
                print(
                    f"  [OK        ] id={uid:6d}  {company} ({year})  hash={file_hash[:16]}...")

            if not dry_run:
                # Check for existing DB record with same hash (different unique_id)
                cur.execute("""
                    SELECT unique_id, source_url FROM t_data_source
                    WHERE file_hash_sha256 = %s AND unique_id != %s
                    LIMIT 1
                """, (file_hash, uid))
                db_dup = cur.fetchone()
                if db_dup and not any(d['duplicate_id'] == uid for d in duplicates_found):
                    duplicates_found.append({
                        'hash': file_hash,
                        'original_id': db_dup['unique_id'],
                        'original_file': db_dup['source_url'],
                        'duplicate_id': uid,
                        'duplicate_file': source_url,
                        'company': company,
                        'year': year,
                    })

                cur.execute("""
                    UPDATE t_data_source
                    SET file_hash_sha256 = %s,
                        file_size_bytes  = %s,
                        modify_dt        = CURRENT_TIMESTAMP,
                        modify_by        = 'BackfillFileHashes'
                    WHERE unique_id = %s
                """, (file_hash, file_size, uid))
                updated += 1

        except Exception as e:
            print(f"  [ERROR     ] id={uid:6d}  {source_url}: {e}")
            errors += 1

    if not dry_run:
        conn.commit()

    cur.close()
    conn.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    found_count = len(seen_hashes)
    print("\n" + "=" * 70)
    print("BACKFILL SUMMARY")
    print("=" * 70)
    print(f"  Total records without hash    : {len(records)}")
    print(
        f"  Files found & {'would update' if dry_run else 'updated'}        : {found_count if dry_run else updated}")
    print(f"  Files not found in GCS/disk   : {not_found}")
    print(f"  Errors reading files          : {errors}")
    print(f"  Duplicates detected           : {len(duplicates_found)}")

    if duplicates_found:
        print("\n" + "=" * 70)
        print("DUPLICATES FOUND (same content, different records)")
        print("=" * 70)
        for d in duplicates_found:
            print(f"  Company  : {d['company']} ({d['year']})")
            print(f"  Hash     : {d['hash'][:20]}...")
            print(f"  Keep     : id={d['original_id']}  {d['original_file']}")
            print(
                f"  Duplicate: id={d['duplicate_id']}  {d['duplicate_file']}")
            print()

        if not dry_run:
            print("To remove duplicates from the database, run:")
            dup_ids = [str(d['duplicate_id']) for d in duplicates_found]
            print(
                f"  DELETE FROM t_data_source WHERE unique_id IN ({', '.join(dup_ids)});")
    else:
        print("\n  No duplicate content detected.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Backfill SHA-256 hashes in t_data_source from GCS')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report without writing to the database')
    parser.add_argument('--year', type=int, default=None,
                        help='Only process records for this year (e.g. --year 2024)')
    args = parser.parse_args()
    backfill_hashes(dry_run=args.dry_run, year_filter=args.year)
