from pathlib import Path
import psycopg2
from Utilities.PathConfiguration import PathConfiguration
from Utilities.Lookups import DB_Connection
import sys
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("""
    SELECT unique_id, year, source_url, original_source_url
    FROM t_data_source
    WHERE content_type = 3 AND form_type = 'OTHER'
    ORDER BY unique_id
""")
rows = cur.fetchall()
print(f"Total 'OTHER' content_type=3 rows: {len(rows)}")

base = Path(PathConfiguration().get_stage0_input_path())
print(f"Stage0 base: {base}")

found = 0
missing = 0
sample_missing = []
for uid, year, source_url, orig_url in rows:
    if not source_url:
        missing += 1
        continue
    filepath = base / str(year) / source_url
    if filepath.exists():
        found += 1
    else:
        missing += 1
        if len(sample_missing) < 10:
            sample_missing.append((year, source_url))

print(f"Files found on disk: {found}")
print(f"Files missing locally: {missing}")
print(f"\nSample missing:")
for y, f in sample_missing:
    print(f"  {y}/{f}")

cur.close()
conn.close()
