import psycopg2
from Utilities.Lookups import DB_Connection
import sys
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

# content_type=1 (Sustainability/ESG) → 'ESG'
cur.execute("""
    UPDATE t_data_source
    SET form_type = 'ESG'
    WHERE form_type IS NULL AND content_type = 1
""")
print(f"ESG (ct=1): {cur.rowcount}")

# content_type=4 (Transcripts) → 'TRANSCRIPT'
cur.execute("""
    UPDATE t_data_source
    SET form_type = 'TRANSCRIPT'
    WHERE form_type IS NULL AND content_type = 4
""")
print(f"TRANSCRIPT (ct=4): {cur.rowcount}")

# content_type=2 with SEC EDGAR URL containing '10k' or '10-k' → '10-K'
cur.execute("""
    UPDATE t_data_source
    SET form_type = '10-K'
    WHERE form_type IS NULL
      AND content_type = 2
      AND (
          LOWER(source_url) LIKE '%10k%'
          OR LOWER(source_url) LIKE '%10-k%'
          OR LOWER(source_url) LIKE '%annual%'
      )
""")
print(f"10-K from URL pattern (ct=2): {cur.rowcount}")

# Remaining ct=2 → '10-K' (it's the annual report content type by definition)
cur.execute("""
    UPDATE t_data_source
    SET form_type = '10-K'
    WHERE form_type IS NULL AND content_type = 2
""")
print(f"10-K remaining (ct=2): {cur.rowcount}")

# content_type=3 with no EDGAR form → 'OTHER'
cur.execute("""
    UPDATE t_data_source
    SET form_type = 'OTHER'
    WHERE form_type IS NULL AND content_type = 3
""")
print(f"OTHER (ct=3): {cur.rowcount}")

conn.commit()

cur.execute("SELECT COUNT(*) FROM t_data_source WHERE form_type IS NULL")
print(f"\nStill null: {cur.fetchone()[0]}")

# Summary
cur.execute("""
    SELECT form_type, COUNT(*) FROM t_data_source
    GROUP BY form_type ORDER BY COUNT(*) DESC
""")
print("\nform_type distribution:")
for r in cur.fetchall():
    print(f"  {r[0]!r:20s}  {r[1]}")

cur.close()
conn.close()
