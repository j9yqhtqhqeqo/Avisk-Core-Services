"""
Diagnose why fetch_ceo_from_local_10k misses PDFs that exist in t_data_source.
"""
from Utilities.PathConfiguration import PathConfiguration
from Utilities.Lookups import DB_Connection
from pathlib import Path
import psycopg2
import sys
sys.path.insert(0, '.')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

base_path = PathConfiguration().get_stage0_input_path()
print("base_path:", base_path)
print()

# 1. What content_types exist in t_data_source?
cur.execute(
    "SELECT content_type, COUNT(*) FROM t_data_source GROUP BY content_type ORDER BY content_type")
print("content_type distribution in t_data_source:")
for r in cur.fetchall():
    print(" ", r)
print()

# 2. Sample rows with content_type=2 to see structure
cur.execute("""
    SELECT ticker, company_name, year, content_type, source_url
    FROM t_data_source
    WHERE content_type = 2
    ORDER BY ticker, year
    LIMIT 20
""")
rows = cur.fetchall()
print("Sample content_type=2 rows:")
for r in rows:
    print(" ", r)
print()

# 3. Check a broader content_type range — maybe 10Ks are stored with a different type
cur.execute("""
    SELECT ticker, company_name, year, content_type, source_url
    FROM t_data_source
    WHERE ticker = 'AMZN'
    ORDER BY year, content_type
    LIMIT 30
""")
print("AMZN rows in t_data_source (all content types):")
for r in cur.fetchall():
    print(" ", r)
print()

# 4. For content_type=2, check how many files actually exist on disk
cur.execute("""
    SELECT ticker, year, source_url
    FROM t_data_source
    WHERE content_type = 2
    ORDER BY ticker, year
    LIMIT 100
""")
rows2 = cur.fetchall()
found = 0
missing = 0
missing_examples = []
for (ticker, year, fname) in rows2:
    if not fname:
        continue
    p = Path(base_path) / str(year) / fname.strip()
    if p.exists():
        found += 1
    else:
        missing += 1
        if len(missing_examples) < 10:
            missing_examples.append((ticker, year, str(p)))

print(
    f"content_type=2: {found} found on disk, {missing} missing (sample of 100)")
print("Missing examples:")
for e in missing_examples:
    print(" ", e)
print()

# 5. Check if files are stored WITHOUT a year subdirectory (flat layout)
cur.execute("""
    SELECT ticker, year, source_url
    FROM t_data_source
    WHERE content_type = 2
    LIMIT 20
""")
print("Checking flat layout (base_path/filename, no year subdir):")
for (ticker, year, fname) in cur.fetchall():
    if not fname:
        continue
    flat = Path(base_path) / fname.strip()
    if flat.exists():
        print(f"  FLAT EXISTS: {ticker} {year} {flat}")
    # Also try base_path/ticker/year/filename
    nested = Path(base_path) / ticker / str(year) / fname.strip()
    if nested.exists():
        print(f"  NESTED EXISTS: {ticker} {year} {nested}")

# 6. What does the actual directory look like?
print()
print("base_path directory listing (top level):")
bp = Path(base_path)
if bp.exists():
    for item in sorted(bp.iterdir())[:30]:
        print(f"  {'DIR' if item.is_dir() else 'FILE':4}  {item.name}")
else:
    print("  base_path does not exist!")

cur.close()
conn.close()
