"""CEO gap analysis — understand why only 2056 records were saved."""
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '.')


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

print("=" * 60)
print("t_ceo table summary")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM t_ceo")
print("Total rows in t_ceo:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NOT NULL")
print("Rows WITH ceo_name:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NULL")
print("Rows WITHOUT ceo_name (no_ceo):", cur.fetchone()[0])

print()
cur.execute("SELECT source, COUNT(*) FROM t_ceo GROUP BY source ORDER BY 2 DESC")
print("By source:")
for r in cur.fetchall():
    print(f"  {r[0]:<20} {r[1]}")

print()
cur.execute(
    "SELECT year, COUNT(*) FROM t_ceo WHERE ceo_name IS NOT NULL GROUP BY year ORDER BY year")
print("Named CEOs per year:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print()
cur.execute("SELECT COUNT(DISTINCT ticker) FROM t_ceo WHERE ceo_name IS NOT NULL")
print("Distinct tickers with at least one CEO:", cur.fetchone()[0])

cur.execute("SELECT COUNT(DISTINCT ticker) FROM t_ceo")
print("Distinct tickers total in t_ceo:", cur.fetchone()[0])

print()
print("=" * 60)
print("t_data_source (10-K) coverage")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM t_data_source WHERE content_type=2")
print("Total 10-K rows:", cur.fetchone()[0])

cur.execute(
    "SELECT COUNT(DISTINCT ticker) FROM t_data_source WHERE content_type=2")
print("Distinct tickers:", cur.fetchone()[0])

cur.execute("SELECT COUNT(DISTINCT year) FROM t_data_source WHERE content_type=2")
print("Distinct years:", cur.fetchone()[0])

cur.execute("SELECT MIN(year), MAX(year) FROM t_data_source WHERE content_type=2")
print("Year range:", cur.fetchone())

cur.execute(
    "SELECT COUNT(DISTINCT (ticker, year)) FROM t_data_source WHERE content_type=2")
print("Distinct ticker/year combos in 10-K:", cur.fetchone()[0])

print()
print("=" * 60)
print("Gap: 10-K rows with no CEO saved")
print("=" * 60)

cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT DISTINCT ticker, year FROM t_data_source WHERE content_type=2
    ) ds
    LEFT JOIN t_ceo c USING(ticker, year)
    WHERE c.ceo_name IS NULL
""")
print("ticker/year combos in 10-K with NO CEO saved:", cur.fetchone()[0])

# Sample of tickers/years with 10-K but no CEO
print()
print("Sample of tickers with 10-K but no CEO (first 20):")
cur.execute("""
    SELECT ds.ticker, ds.year, ds.source_url
    FROM (
        SELECT DISTINCT ON (ticker, year) ticker, year, source_url
        FROM t_data_source
        WHERE content_type=2
        ORDER BY ticker, year, source_confidence_score DESC NULLS LAST
    ) ds
    LEFT JOIN t_ceo c USING(ticker, year)
    WHERE c.ceo_name IS NULL
    ORDER BY ds.ticker, ds.year
    LIMIT 20
""")
for r in cur.fetchall():
    print(
        f"  ticker={r[0]:<6} year={r[1]}  file={r[2][:70] if r[2] else 'NULL'}")

# Check if skip_existing is the cause — how many were already in DB before this run
print()
print("=" * 60)
print("Most recent 10 CEO records saved (modify_dt desc)")
print("=" * 60)
cur.execute("""
    SELECT ticker, company_name, year, ceo_name, source, modify_dt
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
    ORDER BY modify_dt DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[0]:<6} {r[2]}  {r[3]:<25} [{r[4]}]  {str(r[5])[:19]}")

conn.close()
