"""
_fix_ceo_verification_mismatches.py
-------------------------------------
Applies the 34 confirmed DB corrections identified by the FMP cross-reference audit.

Categories fixed:
  - GENUINE_ERROR : wrong person entirely (different human)
  - PARTIAL_YEAR  : CEO changed mid-year; DB has prior CEO, correct = year-end CEO

All updates set source='manual_fix'.

DRY_RUN = True  → print plan only, no DB writes
DRY_RUN = False → commit all changes
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2
import psycopg2.extras
from Utilities.Lookups import DB_Connection

DRY_RUN = False   # ← set False to commit

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

total_fixed = 0


def _fix(ticker: str, year: int, new_name: str, note: str,
         old_name: str = None) -> None:
    """Update t_ceo for the given ticker+year. If old_name given, verify match first."""
    global total_fixed

    clause = "ticker = %s AND year = %s"
    params: list = [ticker, year]
    if old_name:
        clause += " AND ceo_name = %s"
        params.append(old_name)

    cur.execute(
        f"SELECT ceo_id, ceo_name, source FROM t_ceo WHERE {clause}",
        params
    )
    rows = cur.fetchall()

    if not rows:
        if old_name:
            # Row may have already been fixed or old_name mismatch — check without old_name
            cur.execute(
                "SELECT ceo_id, ceo_name, source FROM t_ceo "
                "WHERE ticker = %s AND year = %s",
                [ticker, year]
            )
            existing = cur.fetchone()
            if existing:
                print(f"  SKIP  {ticker} {year}  current='{existing['ceo_name']}'  "
                      f"expected old='{old_name}' — already fixed or different")
            else:
                print(f"  MISS  {ticker} {year}  row not found")
        else:
            print(f"  MISS  {ticker} {year}  row not found")
        return

    for row in rows:
        if not DRY_RUN:
            cur.execute(
                "UPDATE t_ceo SET ceo_name = %s, source = 'manual_fix', modify_dt = NOW() "
                "WHERE ceo_id = %s",
                [new_name, row['ceo_id']]
            )
        total_fixed += 1
        print(
            f"  {'DRY ' if DRY_RUN else 'FIX '}"
            f"{ticker} {year}  "
            f"'{row['ceo_name']}'  →  '{new_name}'  ({note[:55]})"
        )


print("=" * 72)
print("  CEO MISMATCH FIXES — FMP cross-reference audit results")
print(f"  DRY_RUN = {DRY_RUN}")
print("=" * 72)

# ─── ADP ─────────────────────────────────────────────────────────────────────
# Maria Black became CEO July 2023; Rodriguez had retired
_fix('ADP', 2023, 'Maria Black',     'Black became CEO Jul 2023; Rodriguez retired', 'Carlos Rodriguez')
_fix('ADP', 2024, 'Maria Black',     'Black has been CEO since Jul 2023',            'Carlos Rodriguez')
_fix('ADP', 2025, 'Maria Black',     'Black is CEO',                                 'Carlos Rodriguez')

# ─── AEE ─────────────────────────────────────────────────────────────────────
# Martin Lyons Jr became CEO Feb 2023; Baxter retired
_fix('AEE', 2023, 'Martin Lyons',    'Lyons became CEO Feb 2023; Baxter retired',    'Warner Baxter')
_fix('AEE', 2024, 'Martin Lyons',    'Lyons has been CEO since Feb 2023',            'Warner Baxter')
# AEE 2025 already has Martin Lyons (ddgs source) — skip

# ─── AEP ─────────────────────────────────────────────────────────────────────
# William Fehrman became CEO May 2023; Akins stepped down
_fix('AEP', 2023, 'William Fehrman', 'Fehrman became CEO May 2023; Akins stepped down', 'Nicholas Akins')

# ─── AIG ─────────────────────────────────────────────────────────────────────
# local_10k extracted "Guy Carpenter" (a reinsurance subsidiary) as the CEO name
_fix('AIG', 2025, 'Peter Zaffino',   'Guy Carpenter is a subsidiary; CEO=Zaffino',   'Guy Carpenter')

# ─── AIZ (Assurant) ───────────────────────────────────────────────────────────
# Keith Demmings became CEO Jan 2021; Catherine McHugh was never CEO of Assurant
_fix('AIZ', 2023, 'Keith Demmings',  'Demmings has been CEO since 2021; McHugh wrong', 'Catherine McHugh')

# ─── AJG (Arthur J. Gallagher) ───────────────────────────────────────────────
# local_10k returned CFO Douglas Howell instead of CEO Patrick Gallagher Jr
_fix('AJG', 2025, 'Patrick Gallagher Jr', 'Howell is CFO; Gallagher Jr is CEO',      'Douglas Howell')

# ─── ALLE (Allegion) ─────────────────────────────────────────────────────────
# John Stone became CEO Aug 2023; Petratis retired
_fix('ALLE', 2023, 'John Stone',     'Stone became CEO Aug 2023; Petratis retired',  'David Petratis')

# ─── AMCR (Amcor) ────────────────────────────────────────────────────────────
# Michele Buck is Hershey CEO — completely wrong company
_fix('AMCR', 2023, 'Peter Konieczny', "Michele Buck is Hershey's CEO; Amcor=Konieczny", 'Michele Buck')

# ─── AMT (American Tower) ────────────────────────────────────────────────────
# Steven Vondran became CEO April 2023; Bartlett retired
_fix('AMT', 2023, 'Steven Vondran',  'Vondran became CEO Apr 2023; Bartlett retired', 'Tom Bartlett')
_fix('AMT', 2024, 'Steven Vondran',  'Vondran has been CEO since Apr 2023',           'Tom Bartlett')

# ─── AOS (A.O. Smith) ────────────────────────────────────────────────────────
# Shafer became CEO in 2024; Wheeler retired
_fix('AOS', 2024, 'Stephen Shafer',  'Shafer became CEO 2024; Wheeler retired',       'Kevin Wheeler')

# ─── APD (Air Products) ──────────────────────────────────────────────────────
# Eduardo Menezes became CEO Oct 2024; Ghasemi is Chairman
_fix('APD', 2024, 'Eduardo Menezes', 'Menezes became CEO Oct 2024; Ghasemi retired',  'Seifi Ghasemi')
_fix('APD', 2025, 'Eduardo Menezes', 'Menezes has been CEO since Oct 2024',           'Seifi Ghasemi')

# ─── APTV (Aptiv) ────────────────────────────────────────────────────────────
# Kevin Clark is Aptiv CEO; Kevin Frazier is wrong
_fix('APTV', 2023, 'Kevin Clark',    'Clark is Aptiv CEO; Frazier is wrong person',   'Kevin Frazier')

# ─── ARE (Alexandria Real Estate) ────────────────────────────────────────────
# Peter Moglia is CEO; Joel Marcus is Executive Chairman, not CEO
_fix('ARE', 2023, 'Peter Moglia',    'Moglia is CEO; Marcus is Exec Chairman',        'Joel Marcus')

# ─── AVB (AvalonBay) ─────────────────────────────────────────────────────────
# Benjamin Schall has been CEO since 2018; Neithercut left 2018
_fix('AVB', 2023, 'Benjamin Schall', 'Schall has been CEO since 2018; Neithercut wrong', 'David Neithercut')

# ─── AVY (Avery Dennison) ────────────────────────────────────────────────────
# Mitchell Butier was CEO all of 2023; Stander from Jan 2024 — DB is correct, skip
# (already classified FALSE_POSITIVE)

# ─── AWK (American Water Works) ──────────────────────────────────────────────
# John Griffith became CEO Oct 2021; Story left Oct 2021
_fix('AWK', 2023, 'John Griffith',   'Griffith has been CEO since Oct 2021; Story wrong', 'Susan Story')
_fix('AWK', 2024, 'John Griffith',   'Griffith was CEO 2021-2024; Story wrong',            'Susan Story')

# ─── AZO (AutoZone) ──────────────────────────────────────────────────────────
# Philip Daniele became CEO Jan 2023; Rhodes had retired
_fix('AZO', 2023, 'Philip Daniele',  'Daniele became CEO Jan 2023; Rhodes retired',    'William Rhodes III')
_fix('AZO', 2024, 'Philip Daniele',  'Daniele is CEO',                                 'William Rhodes III')

# ─── BALL ────────────────────────────────────────────────────────────────────
# Daniel Fisher became CEO in early 2024; Ronald Lewis was CEO from March 2023
# Lewis became CEO March 2023; Hayes retired
_fix('BALL', 2023, 'Ronald Lewis',   'Lewis became CEO Mar 2023; Hayes retired',       'John Hayes')
_fix('BALL', 2024, 'Ronald Lewis',   'Lewis was CEO all of 2024; Hayes wrong',         'John Hayes')

# ─── BAX (Baxter International) ──────────────────────────────────────────────
# Andrew Hider became CEO July 2023; Almeida stepped down
_fix('BAX', 2023, 'Andrew Hider',    'Hider became CEO Jul 2023; Almeida stepped down', 'José Almeida')
# BAX 2024: Brent Shafer (Cerner) is completely wrong; Hider is CEO
_fix('BAX', 2024, 'Andrew Hider',    'Hider is Baxter CEO; Shafer was Cerner CEO',      'Brent Shafer')

# ─── BMY (Bristol-Myers Squibb) ──────────────────────────────────────────────
# Christopher Boerner became CEO Nov 2023; Caforio stepped down
_fix('BMY', 2023, 'Christopher Boerner', 'Boerner became CEO Nov 2023; Caforio stepped down', 'Giovanni Caforio')

# ─── BSX (Boston Scientific) ─────────────────────────────────────────────────
# Michael Mahoney is BSX CEO; Jonathan Monson is wrong
_fix('BSX', 2025, 'Michael Mahoney', 'Mahoney is BSX CEO; Monson is wrong',            'Jonathan Monson')

# ─── BXP ─────────────────────────────────────────────────────────────────────
# Owen Thomas has been CEO since 2010; Douglas Linde is President
_fix('BXP', 2024, 'Owen Thomas',     'Thomas is CEO; Linde is President/CFO',          'Douglas Linde')
_fix('BXP', 2025, 'Owen Thomas',     'Thomas is CEO; Linde is President',              'Douglas Linde')

# ─── CAG (Conagra Brands) ────────────────────────────────────────────────────
# Sean Connolly is CEO; David Marberger is CFO
_fix('CAG', 2025, 'Sean Connolly',   'Connolly is CEO; Marberger is CFO',              'David Marberger')

# ─── CAH (Cardinal Health) ───────────────────────────────────────────────────
# Jason Hollar became CEO August 2022; Kaufmann retired
_fix('CAH', 2023, 'Jason Hollar',    'Hollar became CEO Aug 2022; Kaufmann wrong for 2023', 'Mike Kaufmann')
_fix('CAH', 2024, 'Jason Hollar',    'Hollar is CEO; Kaufmann wrong for 2024',              'Mike Kaufmann')

# ─── Commit ───────────────────────────────────────────────────────────────────
print()
print("=" * 72)
print(f"  Total rows {'would be ' if DRY_RUN else ''}fixed: {total_fixed}")

if not DRY_RUN:
    conn.commit()
    print("  COMMITTED.")
else:
    conn.rollback()
    print("  DRY RUN — no changes written.")

cur.close()
conn.close()
