"""
_check_unusual_ceo_names.py
---------------------------
Diagnostic script to surface unusual / suspect CEO names in t_ceo
that need manual verification.
"""
import psycopg2
import psycopg2.extras
import sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

SEP = "=" * 80

# ── 1. Special / non-alpha characters ─────────────────────────────────────────
print(SEP)
print("1. NAMES WITH SPECIAL / NON-ALPHA CHARS  (excl. spaces, hyphens, apostrophes, dots, commas)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND ceo_name ~ '[^a-zA-Z\s\-''\.\,]'
    ORDER BY company_name, year
    LIMIT 80
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name'])[:70]:<70}  [{r['source']}]")

# ── 2. Names containing title / corporate words ────────────────────────────────
print()
print(SEP)
print("2. NAMES CONTAINING TITLE/CORPORATE WORDS  (Chief, Officer, Director, President…)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND ceo_name ~* '(Chief|Officer|Director|President|Executive|Chairman|Vice|Board|Inc\.|Corp\.|LLC|Ltd|Co\.)'
    ORDER BY company_name, year
    LIMIT 80
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name'])[:70]:<70}  [{r['source']}]")

# ── 3. Very short names ────────────────────────────────────────────────────────
print()
print(SEP)
print("3. VERY SHORT NAMES  (< 5 characters after trimming)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND LENGTH(TRIM(ceo_name)) < 5
    ORDER BY LENGTH(TRIM(ceo_name)), company_name, year
    LIMIT 60
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name']):<30}  [{r['source']}]")

# ── 4. Very long names ─────────────────────────────────────────────────────────
print()
print(SEP)
print("4. VERY LONG NAMES  (> 40 characters)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND LENGTH(TRIM(ceo_name)) > 40
    ORDER BY LENGTH(ceo_name) DESC
    LIMIT 50
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name'])[:80]:<80}  [{r['source']}]")

# ── 5. Names containing newlines / tabs ───────────────────────────────────────
print()
print(SEP)
print("5. NAMES WITH EMBEDDED NEWLINES OR TABS")
print(SEP)
cur.execute("""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND (ceo_name LIKE E'%\\n%' OR ceo_name LIKE E'%\\t%' OR ceo_name LIKE E'%\\r%')
    LIMIT 40
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name'])[:80]}")

# ── 6. Sentence-like / non-name phrases ───────────────────────────────────────
print()
print(SEP)
print("6. SENTENCE-LIKE / NON-NAME PHRASES  (common English words, separators, etc.)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND (
          ceo_name ~* '\m(the|and|of|for|with|pursuant|agreement|per|ratio|pay|compensation|role|serves|since)\M'
          OR ceo_name LIKE '% - %'
          OR ceo_name LIKE '%,%,%,%'
          OR ceo_name ILIKE '%message%'
          OR ceo_name ILIKE '%advisor%'
          OR ceo_name ILIKE '%report%'
      )
    ORDER BY company_name, year
    LIMIT 60
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name'])[:80]:<80}  [{r['source']}]")

# ── 7. Names that start with lowercase ────────────────────────────────────────
print()
print(SEP)
print("7. NAMES STARTING WITH LOWERCASE  (likely malformed)")
print(SEP)
cur.execute(r"""
    SELECT ceo_id, ticker, company_name, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
      AND ceo_name ~ '^[a-z]'
    ORDER BY company_name, year
    LIMIT 40
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    print(f"  [{r['ticker']:<6}] {r['year']}  {repr(r['ceo_name']):<40}  [{r['source']}]")

# ── 8. Tickers with suspiciously many distinct CEO names ──────────────────────
print()
print(SEP)
print("8. TICKERS WITH > 3 DISTINCT CEO NAMES  (possible data inconsistency)")
print(SEP)
cur.execute(r"""
    SELECT ticker, company_name,
           COUNT(DISTINCT ceo_name) AS distinct_names,
           STRING_AGG(year::text || ':' || ceo_name, ' | ' ORDER BY year) AS years_names
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
    GROUP BY ticker, company_name
    HAVING COUNT(DISTINCT ceo_name) > 3
    ORDER BY COUNT(DISTINCT ceo_name) DESC
    LIMIT 30
""")
rows = cur.fetchall()
print(f"  Count: {len(rows)}")
for r in rows:
    yn = r['years_names'][:130]
    print(f"  [{r['ticker']:<6}] distinct={r['distinct_names']}  {yn}")

# ── 9. Summary ─────────────────────────────────────────────────────────────────
print()
print(SEP)
print("9. OVERALL SUMMARY")
print(SEP)
cur.execute("SELECT COUNT(*) FROM t_ceo")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NOT NULL AND TRIM(ceo_name) <> ''")
populated = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NULL OR TRIM(ceo_name) = ''")
empty = cur.fetchone()[0]
cur.execute("SELECT source, COUNT(*) AS n FROM t_ceo GROUP BY source ORDER BY n DESC")
by_source = cur.fetchall()

print(f"  Total rows        : {total:,}")
print(f"  With ceo_name     : {populated:,}")
print(f"  NULL / blank      : {empty:,}")
print(f"  Coverage          : {populated/total*100:.1f}%" if total else "  N/A")
print()
print("  By source:")
for r in by_source:
    print(f"    {str(r['source']):<25}  {r['n']:,}")

cur.close()
conn.close()
print()
print("Done.")
