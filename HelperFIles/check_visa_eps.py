#!/usr/bin/env python3
"""check_visa_eps.py — check Visa EPS in DB"""
from Utilities.Lookups import DB_Connection
import psycopg2
import sys
import os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()
cur.execute("""
    SELECT reporting_year, eps, net_income, shares_outstanding
    FROM   t_financial_metrics
    WHERE  company_name = 'Visa Inc. Class A'
    ORDER  BY reporting_year
""")
rows = cur.fetchall()
cur.close()
conn.close()

print(f"{'Year':<6} {'EPS':>10} {'Net Income':>18} {'Shares':>18}")
print('-' * 56)
bad_eps = []
for yr, eps, ni, sh in rows:
    eps_str = f"{eps:.4f}" if eps is not None else "NULL"
    ni_str = f"{ni:,}" if ni is not None else "NULL"
    sh_str = f"{sh:,}" if sh is not None else "NULL"
    flag = " ❌" if (eps is None or eps == 0) else " ✅"
    print(f"{yr:<6} {eps_str:>10} {ni_str:>18} {sh_str:>18}{flag}")
    if eps is None or eps == 0:
        bad_eps.append(yr)

print()
if bad_eps:
    print(f"❌ {len(bad_eps)} years have NULL or zero EPS: {bad_eps}")
else:
    print(f"✅ All {len(rows)} years have real EPS populated")
