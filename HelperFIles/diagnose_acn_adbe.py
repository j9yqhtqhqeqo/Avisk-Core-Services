"""Diagnose why ACN / ADBE have null Sharpe and Tobin's Q."""
import psycopg2.extras
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')


conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT company_name, reporting_year, fiscal_year_end_date,
           shares_outstanding, assets, liabilities,
           stock_price_calender_year_end AS price,
           beta_calender_year_end        AS beta,
           sharpe_ratio, tobins_q, eps
    FROM   t_financial_metrics
    WHERE  company_name IN ('Accenture plc', 'Adobe Systems Incorporated')
    ORDER  BY company_name, reporting_year DESC
""")
rows = cur.fetchall()
conn.close()

for r in rows:
    print()
    print(f"  {r['company_name']}  FY{r['reporting_year']}")
    print(f"    fiscal_year_end_date : {r['fiscal_year_end_date']}")
    print(f"    price                : {r['price']}")
    print(f"    beta                 : {r['beta']}")
    print(f"    sharpe_ratio         : {r['sharpe_ratio']}")
    print(f"    tobins_q             : {r['tobins_q']}")
    print(f"    shares_outstanding   : {r['shares_outstanding']}")
    print(f"    assets               : {r['assets']}")
    print(f"    liabilities          : {r['liabilities']}")
    print(f"    eps                  : {r['eps']}")
