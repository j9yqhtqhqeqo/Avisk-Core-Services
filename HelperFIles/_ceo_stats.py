from Utilities.Lookups import DB_Connection
import psycopg2
import sys
sys.path.insert(0, '.')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM t_ceo")
print("Total CEO records:", cur.fetchone()[0])

cur.execute(
    "SELECT source, COUNT(*) FROM t_ceo GROUP BY source ORDER BY COUNT(*) DESC")
print("By source:")
for r in cur.fetchall():
    print(" ", r)

cur.execute("SELECT year, COUNT(*) FROM t_ceo GROUP BY year ORDER BY year")
print("By year:")
for r in cur.fetchall():
    print(" ", r)

cur.execute("SELECT COUNT(DISTINCT ticker) FROM t_ceo")
print("Distinct tickers with CEO:", cur.fetchone()[0])

cur.execute("SELECT MIN(year), MAX(year) FROM t_ceo")
print("Year range in DB:", cur.fetchone())

# Check the upsert conflict key — (company_name, year)
# If two companies share the same name for different years, rows get overwritten
cur.execute("""
    SELECT company_name, year, COUNT(*) as cnt
    FROM t_ceo
    GROUP BY company_name, year
    HAVING COUNT(*) > 1
    LIMIT 10
""")
dupes = cur.fetchall()
print("Duplicate (company_name, year) pairs (should be 0):", len(dupes))
for r in dupes:
    print(" ", r)

# Check if ticker is being used in conflict key at all
cur.execute("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 't_ceo'
""")
print("Indexes on t_ceo:")
for r in cur.fetchall():
    print(" ", r)

# How many tasks were skipped (already_has_ceo returns True)?
# Proxy: companies where year appears multiple times across runs
cur.execute("""
    SELECT ticker, COUNT(DISTINCT year) as years_covered
    FROM t_ceo
    GROUP BY ticker
    ORDER BY years_covered DESC
    LIMIT 20
""")
print("Top 20 tickers by year coverage:")
for r in cur.fetchall():
    print(" ", r)

cur.close()
conn.close()
