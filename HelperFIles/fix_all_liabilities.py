"""
fix_all_liabilities.py
----------------------
Fixes all t_financial_metrics rows where liabilities was incorrectly stored
as the same value as assets (caused by using LiabilitiesAndStockholdersEquity
as a fallback, which equals Total Assets).

Corrects using:  liabilities = assets - equity
Then recomputes tobins_q for every affected row.

Run locally (Cloud SQL Auth Proxy must be running on port 5434):
    conda run -n data-company-gcc python3 HelperFIles/fix_all_liabilities.py
"""
from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Find all rows where liabilities ~= assets (within 1%) and equity is available
cur.execute("""
    SELECT company_name, reporting_year,
           assets, equity, liabilities,
           stock_price_calender_year_end AS price,
           shares_outstanding
    FROM   t_financial_metrics
    WHERE  assets      IS NOT NULL
      AND  equity      IS NOT NULL
      AND  liabilities IS NOT NULL
      AND  ABS(liabilities - assets) < assets * 0.01
    ORDER  BY company_name, reporting_year
""")
rows = cur.fetchall()
print(
    f"Found {len(rows)} row(s) to fix across {len(set(r['company_name'] for r in rows))} companies\n")

update_cur = conn.cursor()
fixed = 0
companies_fixed = set()

for r in rows:
    co = r['company_name']
    yr = r['reporting_year']
    assets = r['assets']
    equity = r['equity']
    price = r['price']
    shares = r['shares_outstanding']

    new_liab = assets - equity

    new_tq = None
    if price and shares and shares > 0 and assets > 0:
        market_cap = price * shares
        new_tq = round((market_cap + new_liab) / assets, 4)

    update_cur.execute("""
        UPDATE t_financial_metrics
        SET    liabilities = %s,
               tobins_q   = %s,
               modify_dt  = NOW(),
               modify_by  = 'fix_all_liabilities'
        WHERE  company_name   = %s
          AND  reporting_year = %s
    """, (int(new_liab), new_tq, co, yr))

    companies_fixed.add(co)
    fixed += 1

conn.commit()
print(f"Fixed {fixed} rows across {len(companies_fixed)} companies:")
for co in sorted(companies_fixed):
    print(f"  {co}")
conn.close()
