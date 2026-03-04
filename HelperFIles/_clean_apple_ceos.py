import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '.')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()

# Show all Apple rows first
cur.execute("""
    SELECT ceo_id, year, ceo_name, source
    FROM t_ceo WHERE ticker = 'AAPL' ORDER BY year
""")
print("Before:")
for r in cur.fetchall():
    print(f"  {r}")

# Delete only the clearly bad ones — "Special Advisor", "Pay Ratio", "Tim Cook\nMessage"
cur.execute("""
    DELETE FROM t_ceo
    WHERE ticker = 'AAPL'
      AND (
          ceo_name ILIKE '%Special Advisor%'
       OR ceo_name ILIKE '%Pay Ratio%'
       OR ceo_name ~ E'\\n'
       OR ceo_name ILIKE '%Message%'
      )
""")
print(f"\nDeleted {cur.rowcount} bad rows")
conn.commit()

cur.execute("""
    SELECT ceo_id, year, ceo_name, source
    FROM t_ceo WHERE ticker = 'AAPL' ORDER BY year
""")
print("\nAfter:")
for r in cur.fetchall():
    print(f"  {r}")

cur.close()
conn.close()
