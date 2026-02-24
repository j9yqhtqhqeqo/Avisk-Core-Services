import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

# Breakdown by content_type
cur.execute("""
    SELECT content_type, COUNT(*) as cnt
    FROM t_data_source
    WHERE form_type IS NULL
    GROUP BY content_type
    ORDER BY content_type
""")
print("Null form_type breakdown by content_type:")
for r in cur.fetchall():
    print(f"  content_type={r[0]}  count={r[1]}")

# Sample filenames per content_type
for ct in (1, 2, 3, 4):
    cur.execute("""
        SELECT source_url
        FROM t_data_source
        WHERE form_type IS NULL AND content_type = %s
        LIMIT 5
    """, (ct,))
    rows = cur.fetchall()
    if rows:
        print(f"\nSamples content_type={ct}:")
        for r in rows:
            print(f"  {r[0]}")

cur.close()
conn.close()
