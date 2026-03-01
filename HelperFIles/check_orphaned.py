"""
check_orphaned.py — quick sanity check after fix_datasource_years.py run.
Looks for:
  1. NULL year rows
  2. Rows with 2+ URL years that were updated to a year NOT in the URL
     (would indicate a bad DB update without a matching rollback)
"""
import psycopg2.extras
import psycopg2
from Utilities.Lookups import DB_Connection
import os
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(str(Path(__file__).resolve().parent.parent))


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. NULL years
cur.execute("SELECT COUNT(*) AS n FROM t_data_source WHERE year IS NULL")
print("NULL year rows:", cur.fetchone()['n'])

# 2. Total ambiguous rows (2+ distinct years in URL)
cur.execute("""
    SELECT COUNT(*) AS n FROM t_data_source
    WHERE original_source_url IS NOT NULL
      AND original_source_url <> ''
      AND source_type = 'file'
      AND (SELECT COUNT(DISTINCT m[1]::int)
           FROM regexp_matches(original_source_url, '20[0-9]{2}', 'g') AS t(m)
           WHERE m[1]::int BETWEEN 2000 AND 2026) >= 2
""")
print("Ambiguous rows (2+ years in URL):", cur.fetchone()['n'])

# 3. Rows where the stored year is NOT present in the URL at all
cur.execute("""
    SELECT unique_id, company_name, year, source_url, original_source_url
    FROM t_data_source
    WHERE original_source_url IS NOT NULL
      AND original_source_url <> ''
      AND source_type = 'file'
      AND (SELECT COUNT(DISTINCT m[1]::int)
           FROM regexp_matches(original_source_url, '20[0-9]{2}', 'g') AS t(m)
           WHERE m[1]::int BETWEEN 2000 AND 2026) >= 2
      AND year::text NOT IN (
           SELECT m[1] FROM regexp_matches(original_source_url, '20[0-9]{2}', 'g') AS t(m)
      )
    ORDER BY unique_id
    LIMIT 20
""")
rows = cur.fetchall()
print(
    f"\nRows where stored year is NOT in URL (orphaned candidates): {len(rows)}")
for r in rows:
    print(
        f"  uid={r['unique_id']} | {r['company_name']} | year={r['year']} | {r['original_source_url'][:80]}")

cur.close()
conn.close()
print("\nDone.")
