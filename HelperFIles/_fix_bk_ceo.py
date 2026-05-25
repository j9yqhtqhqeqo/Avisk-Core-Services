"""
_fix_bk_ceo.py
--------------
Fix Bank of New York Mellon (BK) CEO history:
  Gerald Hassell    : CEO 2011 – Jun 2017
  Charlie Scharf    : CEO Jul 2017 – Oct 2019
  Thomas Gibbons    : CEO Nov 2019 – Jul 2022
  Robin Vince       : CEO Aug 2022 – present
"""
import psycopg2, sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()

print("=== BK before fix ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='BK' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  '{r[1]}'  [{r[2]}]")

FIXES = [
    # Hassell was CEO all of 2015 and 2016; Scharf arrived mid-2017
    (2015, 'Gerald Hassell'),
    (2016, 'Gerald Hassell'),
    # Scharf left Oct 2019; Gibbons covered the rest — for annual purposes use Gibbons
    (2019, 'Thomas Gibbons'),
    # Gibbons was CEO through Jul 2022; Robin Vince took over Aug 2022
    (2020, 'Thomas Gibbons'),
    (2021, 'Thomas Gibbons'),
    # 2022: Vince became CEO in Aug so the annual year is typically attributed to Vince
    (2022, 'Robin Vince'),
]

print("\n=== Applying fixes ===")
for (year, new_name) in FIXES:
    cur.execute(
        "UPDATE t_ceo SET ceo_name=%s, source='manual_fix', modify_dt=NOW() "
        "WHERE ticker='BK' AND year=%s",
        (new_name, year)
    )
    print(f"  BK {year}  →  '{new_name}'  ({cur.rowcount} row{'s' if cur.rowcount!=1 else ''})")

conn.commit()

print("\n=== BK after fix ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='BK' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  '{r[1]}'  [{r[2]}]")

cur.close()
conn.close()
print("\nDone.")
