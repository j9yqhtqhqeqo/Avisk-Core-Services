"""One-time migration: add ticker column to t_data_source and backfill from source_url."""
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


conn_str = DB_Connection().DB_CONNECTION_STRING
if not conn_str:
    print("ERROR: No DB connection string found")
    sys.exit(1)

print(f"Connecting: {conn_str[:70]}")
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute(
    "ALTER TABLE t_data_source ADD COLUMN IF NOT EXISTS ticker VARCHAR(20)")
print("✅ Column added (or already exists)")

cur.execute("""
    UPDATE t_data_source
    SET    ticker = UPPER(SPLIT_PART(source_url, '_', 1))
    WHERE  ticker IS NULL
      AND  source_url IS NOT NULL
      AND  source_url <> ''
      AND  LENGTH(SPLIT_PART(source_url, '_', 1)) BETWEEN 1 AND 10
      AND  SPLIT_PART(source_url, '_', 1) ~ '^[A-Za-z0-9]+$'
""")
print(f"✅ Backfilled {cur.rowcount} rows")

cur.execute(
    "CREATE INDEX IF NOT EXISTS idx_t_data_source_ticker ON t_data_source (ticker)")
print("✅ Index created")

conn.commit()
cur.close()
conn.close()

# Verify
conn2 = psycopg2.connect(conn_str)
cur2 = conn2.cursor()
cur2.execute(
    "SELECT ticker, COUNT(*) FROM t_data_source GROUP BY ticker ORDER BY ticker")
rows = cur2.fetchall()
print(f"\n{'Ticker':<15} {'Count':>6}")
print("-" * 22)
for r in rows:
    print(f"{str(r[0]):<15} {r[1]:>6}")
cur2.close()
conn2.close()
