"""
_final_quality_audit.py
-----------------------
Comprehensive quality audit of the current t_ceo table state.
Checks:
  1. Basic stats (row count, source breakdown, year coverage)
  2. NULL / empty names
  3. Name pattern issues (special chars, title words, short/long, lowercase, sentences)
  4. Duplicate CEOs per ticker-year
  5. Suspicious consecutive-year changes (same ticker, adjacent years, different names)
  6. Names still containing known-bad patterns from prior audit rounds
"""
from __future__ import annotations
import sys, os, re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2, psycopg2.extras
from Utilities.Lookups import DB_Connection
from collections import defaultdict

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. Basic stats ────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) AS n FROM t_ceo")
total = cur.fetchone()['n']

cur.execute("SELECT source, COUNT(*) AS n FROM t_ceo GROUP BY source ORDER BY n DESC")
sources = cur.fetchall()

cur.execute("SELECT year, COUNT(*) AS n FROM t_ceo GROUP BY year ORDER BY year")
by_year = cur.fetchall()

cur.execute("SELECT COUNT(DISTINCT ticker) AS n FROM t_ceo WHERE ceo_name IS NOT NULL")
tickers_with_ceo = cur.fetchone()['n']

print("=" * 70)
print("  FINAL CEO DATA QUALITY AUDIT")
print("=" * 70)
print(f"\n  Total rows   : {total}")
print(f"  Tickers with CEO : {tickers_with_ceo}")
print(f"\n  By source:")
for r in sources:
    print(f"    {r['source']:<25} {r['n']:>5}")
print(f"\n  By year (spot check):")
for r in by_year:
    print(f"    {r['year']}  {r['n']:>4} rows")

# ── 2. NULL / blank names ─────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) AS n FROM t_ceo WHERE ceo_name IS NULL OR TRIM(ceo_name)=''")
nulls = cur.fetchone()['n']
print(f"\n  NULL/blank names : {nulls}")

# ── 3. Name pattern issues ────────────────────────────────────────────────────
issues: dict[str, list] = defaultdict(list)

cur.execute("SELECT ceo_id, ticker, year, ceo_name, source FROM t_ceo WHERE ceo_name IS NOT NULL ORDER BY ticker, year")
all_rows = cur.fetchall()

# Known-bad patterns
_TITLE_WORDS = re.compile(
    r'\b(chief|executive|officer|president|chairman|director|vice|senior|'
    r'segment|reporting|operations|filed|herewith|pursuant|building|automation|'
    r'announces|transition|attacks|arizona|public|service|revenue)\b', re.I)
_SENTENCE_LIKE  = re.compile(r'\b(and|the|of|for|in|to|at|by|from|with|is|was|are|were)\b', re.I)
_ALL_UPPER_2    = re.compile(r'^[A-Z\s\.\-\']{6,}$')
_NEWLINE        = re.compile(r'[\n\r]')
_GARBAGE_CHARS  = re.compile(r'[<>{}|\[\]\\@#$%^&*=+`~]')

for r in all_rows:
    name = r['ceo_name'].strip()
    key  = f"{r['ticker']} {r['year']}"

    if len(name) < 4:
        issues['too_short'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    if len(name) > 60:
        issues['too_long'].append(f"  {key:<12} '{name[:70]}'  [{r['source']}]")
    if _TITLE_WORDS.search(name):
        issues['title_word'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    if _SENTENCE_LIKE.search(name) and len(name.split()) > 4:
        issues['sentence_like'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    if _NEWLINE.search(name):
        issues['has_newline'].append(f"  {key:<12} '{repr(name)}'  [{r['source']}]")
    if _GARBAGE_CHARS.search(name):
        issues['garbage_chars'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    if _ALL_UPPER_2.match(name) and len(name.split()) >= 2:
        issues['all_caps'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    words = name.split()
    if len(words) >= 2 and words[0][0].islower():
        issues['lowercase_start'].append(f"  {key:<12} '{name}'  [{r['source']}]")
    if len(words) > 5:
        issues['too_many_words'].append(f"  {key:<12} '{name}'  [{r['source']}]")

print()
print("  Name pattern issues:")
clean = True
for cat, rows_list in sorted(issues.items()):
    if rows_list:
        clean = False
        print(f"\n  [{cat}]  ({len(rows_list)} rows)")
        for line in rows_list[:30]:
            print(line)
        if len(rows_list) > 30:
            print(f"    … and {len(rows_list)-30} more")

if clean:
    print("  ✅  None found — all names pass pattern checks")

# ── 4. Duplicate (ticker, year) rows ─────────────────────────────────────────
cur.execute("""
    SELECT ticker, year, COUNT(*) AS n, array_agg(ceo_name) AS names
    FROM t_ceo
    GROUP BY ticker, year
    HAVING COUNT(*) > 1
    ORDER BY ticker, year
""")
dups = cur.fetchall()
print(f"\n  Duplicate (ticker, year) pairs : {len(dups)}")
for d in dups[:20]:
    print(f"    {d['ticker']} {d['year']}  n={d['n']}  names={d['names']}")

# ── 5. Suspicious year-over-year changes ─────────────────────────────────────
# Flag tickers where CEO changes MORE than twice in a 5-year window (may indicate noise)
by_ticker_year: dict[str, list] = defaultdict(list)
for r in all_rows:
    if r['ceo_name']:
        by_ticker_year[r['ticker']].append((r['year'], r['ceo_name']))

noisy: list[str] = []
for ticker, pairs in by_ticker_year.items():
    pairs.sort()
    changes = sum(
        1 for i in range(1, len(pairs))
        if pairs[i][1] != pairs[i-1][1] and pairs[i][0] - pairs[i-1][0] == 1
    )
    if changes >= 4:  # 4+ CEO changes in consecutive years = suspicious
        noisy.append(f"  {ticker:<6}  {changes} consecutive-year changes  "
                     f"{[(y,n) for y,n in pairs]}")

print(f"\n  Tickers with 4+ consecutive-year CEO changes (suspicious): {len(noisy)}")
for line in noisy:
    print(line[:120])

# ── 6. Summary ───────────────────────────────────────────────────────────────
total_issues = sum(len(v) for v in issues.values()) + len(dups) + len(noisy)
print()
print("=" * 70)
if total_issues == 0 and nulls == 0:
    print("  ✅  TABLE IS CLEAN — no issues found")
else:
    print(f"  Issues remaining: {total_issues} rows across all checks + {nulls} NULLs")
print("=" * 70)

conn.close()
