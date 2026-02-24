"""
Backfill null tickers in t_data_source.

Pass 1: extract from source_url filename prefix (already done for pure alpha symbols).
Pass 2: wider regex — allow digits/dots (e.g. BRK.B) and longer prefixes up to 5 chars.
Pass 3: company-name → ticker lookup via sp500 CSV + a hardcoded mapping for known companies.
"""
from pathlib import Path
import csv
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

# ── Pass 2: extract ticker from filename even when it contains digits ─────────
# e.g.  "PM_..." → "PM",  "BRK.B_..." won't appear but covers numeric tickers
cur.execute("""
    UPDATE t_data_source
    SET ticker = UPPER(
        CASE
            WHEN source_url ~ '^[A-Z0-9]{1,5}[_-]' THEN
                REGEXP_REPLACE(source_url, '^([A-Z0-9]{1,5})[_-].*$', '\\1')
            ELSE NULL
        END
    )
    WHERE ticker IS NULL
      AND source_url IS NOT NULL
      AND source_url ~ '^[A-Z0-9]{1,5}[_-]'
""")
print(f"Pass 2 updated: {cur.rowcount}")
conn.commit()

# ── Pass 3: company-name → ticker lookup ──────────────────────────────────────

# Load SP500 CSV
sp500_path = Path(
    '/Users/mohanganadal/Avisk/Avisk-Core-Services/Clients/sp500_market_cap_ranked.csv')
name_to_ticker = {}
if sp500_path.exists():
    with open(sp500_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get('Symbol') or row.get('symbol')
                      or row.get('ticker') or '').strip().upper()
            name = (row.get('Name') or row.get('name')
                    or row.get('company') or '').strip()
            if ticker and name:
                name_to_ticker[name.lower()] = ticker

# Hardcoded fallbacks for known mismatches from the inspect output
HARDCODED = {
    'philip morris international': 'PM',
    'unitedhealth group': 'UNH',
    'jpmorgan chase': 'JPM',
    'tesla, inc.': 'TSLA',
    'costco': 'COST',
    'mastercard': 'MA',
    'pepsico': 'PEP',
    'linde plc': 'LIN',
    "mcdonald's": 'MCD',
    'citigroup': 'C',
    'abbvie': 'ABBV',
    'ge aerospace': 'GE',
    'ibm': 'IBM',
    'visa inc.': 'V',
    'alphabet inc. (class c)': 'GOOG',
    'meta platforms': 'META',
    'caterpillar inc.': 'CAT',
    'at&t': 'T',
    'applied materials': 'AMAT',
}
name_to_ticker.update(HARDCODED)

# Fetch remaining nulls
cur.execute(
    "SELECT unique_id, company_name FROM t_data_source WHERE ticker IS NULL")
rows = cur.fetchall()
print(f"Pass 3: {len(rows)} rows still null")

updated = 0
unresolved_companies = set()
for uid, company in rows:
    if not company:
        continue
    key = company.strip().lower()
    ticker = name_to_ticker.get(key)
    if not ticker:
        # Partial match — try first word
        first_word = key.split()[0] if key else ''
        for n, t in name_to_ticker.items():
            if n.startswith(first_word) and len(first_word) >= 4:
                ticker = t
                break
    if ticker:
        cur.execute(
            "UPDATE t_data_source SET ticker = %s WHERE unique_id = %s", (ticker, uid))
        updated += 1
    else:
        unresolved_companies.add(company)

conn.commit()
print(f"Pass 3 updated: {updated}")

cur.execute("SELECT COUNT(*) FROM t_data_source WHERE ticker IS NULL")
remaining = cur.fetchone()[0]
print(f"Still null after all passes: {remaining}")

if unresolved_companies:
    print("\nUnresolved companies (no ticker found):")
    for c in sorted(unresolved_companies):
        print(f"  {c!r}")

cur.close()
conn.close()
