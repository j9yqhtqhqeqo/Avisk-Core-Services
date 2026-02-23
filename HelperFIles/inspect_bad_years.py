"""Investigate bad year values in t_data_source."""
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("""
    SELECT year, COUNT(*) as cnt
    FROM t_data_source
    WHERE year > 2026
    GROUP BY year ORDER BY year
""")
print("=== Bad future years ===")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} rows")

cur.execute("""
    SELECT year, company_name, source_url
    FROM t_data_source
    WHERE year > 2026
    ORDER BY year
    LIMIT 20
""")
print("\n=== Sample bad rows ===")
for r in cur.fetchall():
    print(f"  year={r[0]}  company={r[1]}  url={str(r[2])[:80]}")

cur.close()
conn.close()
