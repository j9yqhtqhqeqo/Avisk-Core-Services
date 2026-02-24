"""
check_duplicates.py
-------------------
Audit t_data_source for duplicate records in three categories:

  1. Same file_hash_sha256 per company  (identical content, multiple rows)
  2. Same original_source_url per company (same URL downloaded multiple times)
  3. Same company_name + year + source_url (same filename stored multiple times)

Prints a summary and, per category, lists the duplicate groups with their
unique_ids so we can decide how to clean up.

Run locally (Cloud SQL Auth Proxy must be running on port 5434):
    conda run -n data-company-gcc python3 HelperFIles/check_duplicates.py
"""

from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def connect():
    return psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)


def check_hash_duplicates(conn):
    """Same SHA-256 hash for the same company → identical file downloaded twice."""
    sql = """
        SELECT
            company_name,
            file_hash_sha256,
            COUNT(*)           AS cnt,
            array_agg(unique_id ORDER BY unique_id)     AS ids,
            array_agg(year     ORDER BY unique_id)      AS years,
            array_agg(content_type ORDER BY unique_id)  AS ctypes,
            array_agg(form_type    ORDER BY unique_id)  AS ftypes,
            array_agg(source_url   ORDER BY unique_id)  AS filenames
        FROM t_data_source
        WHERE file_hash_sha256 IS NOT NULL
        GROUP BY company_name, file_hash_sha256
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, company_name
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def check_url_duplicates(conn):
    """Same original_source_url for the same company → URL downloaded multiple times."""
    sql = """
        SELECT
            company_name,
            original_source_url,
            COUNT(*)           AS cnt,
            array_agg(unique_id ORDER BY unique_id)     AS ids,
            array_agg(year     ORDER BY unique_id)      AS years,
            array_agg(content_type ORDER BY unique_id)  AS ctypes,
            array_agg(form_type    ORDER BY unique_id)  AS ftypes,
            array_agg(source_url   ORDER BY unique_id)  AS filenames
        FROM t_data_source
        WHERE original_source_url IS NOT NULL
          AND original_source_url <> ''
        GROUP BY company_name, original_source_url
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, company_name
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def check_filename_duplicates(conn):
    """Same company + year + source_url (filename) → identical DB key."""
    sql = """
        SELECT
            company_name,
            year,
            source_url,
            COUNT(*)           AS cnt,
            array_agg(unique_id ORDER BY unique_id)     AS ids,
            array_agg(content_type ORDER BY unique_id)  AS ctypes,
            array_agg(form_type    ORDER BY unique_id)  AS ftypes
        FROM t_data_source
        GROUP BY company_name, year, source_url
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, company_name
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def total_rows(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM t_data_source")
        return cur.fetchone()[0]


def print_section(title, rows, key_field, max_show=20):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"  Groups: {len(rows)}   (showing up to {max_show})")
    print(f"{'='*70}")
    if not rows:
        print("  ✅  No duplicates found.")
        return
    # Total extra rows = sum(cnt - 1)
    extra = sum(r['cnt'] - 1 for r in rows)
    print(
        f"  ⚠️   {extra} extra rows could be deleted across {len(rows)} groups\n")
    for r in rows[:max_show]:
        key_val = r[key_field]
        if key_val and len(str(key_val)) > 80:
            key_val = str(key_val)[:77] + "..."
        print(f"  [{r['cnt']} rows] {r['company_name']}  |  {key_field}: {key_val}")
        print(f"           IDs={r['ids']}  years={r.get('years','?')}  "
              f"ctypes={r.get('ctypes','?')}  ftypes={r.get('ftypes','?')}")
        if 'filenames' in r:
            fnames = r['filenames']
            for fn in fnames:
                short = fn if fn and len(fn) <= 70 else (
                    fn[:67] + "..." if fn else "")
                print(f"           filename: {short}")
        print()
    if len(rows) > max_show:
        print(f"  ... and {len(rows) - max_show} more groups not shown.")


def main():
    print("Connecting to database...")
    conn = connect()
    print(f"Total rows in t_data_source: {total_rows(conn):,}")

    hash_dups = check_hash_duplicates(conn)
    url_dups = check_url_duplicates(conn)
    fname_dups = check_filename_duplicates(conn)

    print_section("1. SAME HASH (identical content, multiple rows)",
                  hash_dups, key_field='file_hash_sha256')
    print_section("2. SAME original_source_url (URL downloaded multiple times)",
                  url_dups, key_field='original_source_url')
    print_section("3. SAME company + year + filename (duplicate DB key)",
                  fname_dups, key_field='source_url')

    # Summary
    h_extra = sum(r['cnt'] - 1 for r in hash_dups)
    u_extra = sum(r['cnt'] - 1 for r in url_dups)
    f_extra = sum(r['cnt'] - 1 for r in fname_dups)

    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    print(
        f"  Hash duplicates   : {len(hash_dups):>4} groups  →  {h_extra:>4} deletable rows")
    print(
        f"  URL duplicates    : {len(url_dups):>4} groups  →  {u_extra:>4} deletable rows")
    print(
        f"  Filename dupes    : {len(fname_dups):>4} groups  →  {f_extra:>4} deletable rows")

    # Overlap note: rows counted in multiple categories are not double-deletable
    all_dup_ids = set()
    for r in hash_dups:
        all_dup_ids.update(r['ids'][1:])  # keep lowest id, delete rest
    for r in url_dups:
        all_dup_ids.update(r['ids'][1:])
    for r in fname_dups:
        all_dup_ids.update(r['ids'][1:])
    print(f"\n  Unique rows that could be deleted (union): {len(all_dup_ids)}")
    if all_dup_ids:
        print(f"\n  IDs to delete: {sorted(all_dup_ids)}")
    print()

    conn.close()


if __name__ == "__main__":
    main()
