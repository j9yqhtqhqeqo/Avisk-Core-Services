"""
fix_acn_liabilities.py
----------------------
Accenture plc's `liabilities` column was stored as the same value as
`assets` (because XBRL has no standalone Liabilities tag for ACN and we
were using LiabilitiesAndStockholdersEquity as a fallback, which equals
Assets).

This script corrects it using:  liabilities = assets - equity
Then recomputes tobins_q for every Accenture row that has all the
required inputs.

Run locally (Cloud SQL Auth Proxy must be running on port 5434):
    conda run -n data-company-gcc python3 HelperFIles/fix_acn_liabilities.py
"""
from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Fetch all ACN rows
cur.execute("""
    SELECT reporting_year, assets, equity, liabilities,
           stock_price_calender_year_end AS price,
           shares_outstanding
    FROM   t_financial_metrics
    WHERE  company_name = 'Accenture plc'
    ORDER  BY reporting_year
""")
rows = cur.fetchall()

print(f"Found {len(rows)} Accenture row(s)\n")
print(f"{'Year':<6} {'Old Liab':>15} {'New Liab':>15} {'Assets':>15} {'Equity':>15} {'Old TQ':>8} {'New TQ':>8}")
print("-" * 88)

update_cur = conn.cursor()
fixed = 0

for r in rows:
    yr = r['reporting_year']
    assets = r['assets']
    equity = r['equity']
    old_l = r['liabilities']
    price = r['price']
    shares = r['shares_outstanding']

    if assets is None or equity is None:
        print(f"{yr:<6} {'N/A (missing assets or equity)':>50}")
        continue

    new_liab = assets - equity

    # Recompute Tobin's Q with corrected liabilities
    new_tq = None
    if price and shares and shares > 0 and assets > 0:
        market_cap = price * shares
        new_tq = round((market_cap + new_liab) / assets, 4)

    # Old Tobin's Q (for display)
    old_tq = None
    if price and shares and shares > 0 and assets > 0:
        market_cap = price * shares
        old_tq = round((market_cap + (old_l or 0)) / assets, 4)

    print(f"{yr:<6} {(old_l or 0):>15,.0f} {new_liab:>15,.0f} "
          f"{assets:>15,.0f} {equity:>15,.0f} "
          f"{(old_tq or 0):>8.3f} {(new_tq or 0):>8.3f}")

    update_cur.execute("""
        UPDATE t_financial_metrics
        SET    liabilities = %s,
               tobins_q   = %s,
               modify_dt  = NOW(),
               modify_by  = 'fix_acn_liabilities'
        WHERE  company_name   = 'Accenture plc'
          AND  reporting_year = %s
    """, (int(new_liab), new_tq, yr))
    fixed += 1

conn.commit()
print(f"\nUpdated {fixed} rows.")
conn.close()
