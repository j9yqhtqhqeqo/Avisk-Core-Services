"""
_investigate_suspicious_changes.py
-----------------------------------
Among the 65 "high-churn" tickers, identify BACK-AND-FORTH patterns
(same CEO name reappearing after a different name) which are almost
always data errors, and flag specific rows that are clearly wrong based
on known CEO history.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2, psycopg2.extras
from Utilities.Lookups import DB_Connection
from collections import defaultdict

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT ticker, year, ceo_name, source
    FROM t_ceo
    WHERE ceo_name IS NOT NULL
    ORDER BY ticker, year
""")
all_rows = cur.fetchall()
conn.close()

by_ticker: dict[str, list] = defaultdict(list)
for r in all_rows:
    by_ticker[r['ticker']].append((r['year'], r['ceo_name'], r['source']))

# ── 1. Back-and-forth detector ────────────────────────────────────────────────
# A→B→A pattern in consecutive years = almost certainly wrong
print("=" * 72)
print("  BACK-AND-FORTH CEO PATTERNS (A→B→A in adjacent years)")
print("  (same CEO reappears after a different one — near-certain data error)")
print("=" * 72)

zigzag: list[tuple] = []
for ticker, pairs in by_ticker.items():
    pairs.sort()
    for i in range(2, len(pairs)):
        y0, n0, s0 = pairs[i-2]
        y1, n1, s1 = pairs[i-1]
        y2, n2, s2 = pairs[i]
        if (n0 == n2 and n0 != n1 and
                y1 - y0 == 1 and y2 - y1 == 1):
            zigzag.append((ticker, y0, n0, y1, n1, y2, n2, s1))

for t in sorted(zigzag, key=lambda x: (x[0], x[1])):
    ticker, y0, n0, y1, n1, y2, n2, s1 = t
    print(f"  {ticker:<6} {y0}='{n0}'  ← {y1}='{n1}' [{s1}] →  {y2}='{n2}'")

# ── 2. Known-wrong spot checks based on public CEO history ────────────────────
# These are confirmed wrong from the high-churn flag review
KNOWN_WRONG = {
    # Ticker: [(year, current_db_name, correct_name, reason)]
    'VZ':   [(2013, 'Daniel Schulman', 'Lowell McAdam',
              'Schulman was PayPal/Sprint CEO; McAdam was Verizon CEO 2011-2018')],
    'TRV':  [(2013, 'Jay Baker',       'Jay Fishman',
              'Fishman was TRV CEO 2004-2015; Baker not TRV CEO')],
    'XEL':  [(2012, 'Teresa Madden',   'Ben Fowke',
              'Madden was XEL CFO; Fowke was CEO 2011-2021'),
             (2013, 'Teresa Madden',   'Ben Fowke', 'Fowke was CEO'),
             (2014, 'Teresa Madden',   'Ben Fowke', 'Fowke was CEO'),
             (2015, 'Teresa Madden',   'Ben Fowke', 'Fowke was CEO')],
    'PG':   [(2013, 'Shailesh Jejurikar', 'Alan Lafley',
              'Jejurikar is a division president; Lafley was P&G CEO Jun 2013-Oct 2015')],
    'WYNN': [(2013, 'Matt Maddox',     'Steve Wynn',
              'Maddox became CEO Feb 2018; Wynn was CEO 2002-2018')],
    'PCAR': [(2013, 'Mark Pigott',     'Mark Pigott', ''),   # Pigott is correct for 2013
             (2014, 'Mark Smith',      'Mark Pigott',
              'Pigott was PACCAR CEO 2009-2014; Smith is not correct here')],
    'KMX':  [(2013, 'William Nash',    'Tom Folliard',
              'Nash became CEO in 2016; Folliard was CEO 2006-2016'),
             (2014, 'Tom Folliard',    'Tom Folliard', '')],  # 2014 is correct
    'CPRT': [(2012, 'Willie Johnson',  'Jay Adair',
              'Jay Adair has been Copart CEO since 2010; Willie Johnson is not CEO'),
             (2013, 'Willie Johnson',  'Jay Adair', 'Adair is CEO')],
    'CEG':  [(2012, 'Michael McMahon', None,
              'CEG (Constellation Energy) spun from Exelon Jan 2022; pre-2022 CEOs may be Exelon data'),
             (2013, 'Michael Kearney', None, 'pre-spinoff — verify'),
             (2014, 'Michael Kagan',   None, 'pre-spinoff — verify')],
    'CF':   [(2013, 'Stephen Furbacher', 'Tony Will',
              'CF Industries CEOs: Wilson until 2014, then Tony Will; Furbacher is wrong')],
    'DVN':  [(2012, 'John McNabb III', 'John Richels',
              'Devon Energy: Richels was CEO 2010-2016; McNabb III is wrong')],
    'RTX':  [(2012, 'Alain Bellemare', None,
              'RTX is post-merger UTC+Raytheon (2020); pre-merger data may be mixed'),
             (2014, 'Geraud Darnis',   None, 'Darnis was UTC division president, not CEO')],
}

print()
print("=" * 72)
print("  KNOWN WRONG — Confirmed erroneous CEO names from high-churn review")
print("=" * 72)

confirmed_fixes: list[tuple] = []
for ticker, cases in sorted(KNOWN_WRONG.items()):
    for year, old_name, correct_name, reason in cases:
        # Check what's actually in DB right now
        row = next(
            ((y, n, s) for t, pairs in by_ticker.items()
             if t == ticker
             for y, n, s in pairs if y == year),
            None
        )
        if row is None:
            print(f"  {ticker:<6} {year}  NOT IN DB")
            continue
        db_year, db_name, db_src = row
        if not reason:  # skip rows marked as correct
            continue
        match = '✅' if db_name == old_name else '⚠️ '
        print(f"  {match} {ticker:<6} {year}  DB='{db_name}' [{db_src}]")
        if correct_name:
            print(f"       → Should be '{correct_name}'  ({reason[:70]})")
        else:
            print(f"       ⚠️  UNCERTAIN  ({reason[:70]})")
        if correct_name and db_name == old_name:
            confirmed_fixes.append((ticker, year, old_name, correct_name, reason))

print()
print(f"  Rows needing fix: {len(confirmed_fixes)}")
for f in confirmed_fixes:
    print(f"    {f[0]:<6} {f[1]}  '{f[2]}'  →  '{f[3]}'")
