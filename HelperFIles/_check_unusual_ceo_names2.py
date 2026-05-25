"""
_check_unusual_ceo_names2.py
Targeted follow-up on specific suspects found in check #1.
"""
import psycopg2
import sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

print("=== SUMMARY ===")
cur.execute("SELECT COUNT(*) FROM t_ceo")
print("Total rows:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NOT NULL AND TRIM(ceo_name)<>''")
print("With ceo_name:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM t_ceo WHERE ceo_name IS NULL OR TRIM(ceo_name)=''")
print("NULL/blank:", cur.fetchone()[0])
cur.execute("SELECT source, COUNT(*) FROM t_ceo GROUP BY source ORDER BY 2 DESC")
print("\nBy source:")
for r in cur.fetchall():
    print(f"  {str(r[0]):<25} {r[1]}")

print("\n=== AOS (A.O. Smith) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='AOS' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== GWW (Grainger) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='GWW' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== TPL (Texas Pacific Land) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='TPL' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<45}  [{r[2]}]")

print("\n=== PNW (Pinnacle West) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='PNW' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<45}  [{r[2]}]")

print("\n=== AMD ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='AMD' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== GM ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='GM' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== FFIV (F5 Networks) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='FFIV' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<45}  [{r[2]}]")

print("\n=== HUBB (Hubbell) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='HUBB' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== CINF (Cincinnati Financial) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='CINF' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== GE ALL YEARS (Jeff/Jeffrey inconsistency) ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='GE' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== PYPL ALL YEARS (Dan/Daniel inconsistency) ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='PYPL' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

print("\n=== ALB (Albemarle) ALL YEARS ===")
cur.execute("SELECT year, ceo_name, source FROM t_ceo WHERE ticker='ALB' ORDER BY year")
for r in cur.fetchall():
    print(f"  {r[0]}  {repr(r[1]):<40}  [{r[2]}]")

cur.close()
conn.close()
print("\nDone.")
