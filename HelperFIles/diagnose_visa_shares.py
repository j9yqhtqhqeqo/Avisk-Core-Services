#!/usr/bin/env python3
"""diagnose_visa_shares.py — trace why derived EPS is null for Visa"""
import sys
import os
from Services.FinancialDataScraper import FinancialDataScraper
import logging
import subprocess
import json
import sys

H = ['curl', '-s', '-m', '20', '-H',
     'User-Agent: Avisk Research contact@avisk.com']
K10 = {'10-K', '10-K405', '10-KSB', '10-KT'}


def fetch(cik):
    r = subprocess.run(H + [f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'],
                       capture_output=True)
    return json.loads(r.stdout).get('facts', {})


# Visa CIK = 0001403161, FY ends Sep 30
VISA_CIK = '0001403161'
facts = fetch(VISA_CIK)
usg = facts.get('us-gaap', {})
dei = facts.get('dei', {})

print('='*60)
print('VISA shares investigation')
print('='*60)

# ── 1. DEI shares ─────────────────────────────────────────────────────────────
print('\n--- DEI EntityCommonStockSharesOutstanding ---')
dei_shares = dei.get('EntityCommonStockSharesOutstanding', {})
dei_entries = [e for v in dei_shares.get('units', {}).values() for e in v
               if e.get('form') in K10]
print(f'Total 10-K DEI share entries: {len(dei_entries)}')
for e in sorted(dei_entries, key=lambda x: x.get('instant', ''))[-10:]:
    print(
        f'  instant={e.get("instant","?")} val={e.get("val")} form={e.get("form")}')

# ── 2. us-gaap shares ─────────────────────────────────────────────────────────
print('\n--- us-gaap share concepts ---')
for concept in ['CommonStockSharesOutstanding',
                'WeightedAverageNumberOfSharesOutstandingBasic',
                'WeightedAverageNumberOfDilutedSharesOutstanding']:
    d = usg.get(concept, {})
    entries = [e for v in d.get('units', {}).values() for e in v
               if e.get('form') in K10 and e.get('fp') in ('FY', 'Q4', '')]
    if entries:
        yrs = {}
        for e in entries:
            end = e.get('end', '')
            if len(end) >= 10:
                yr = int(end[:4])
                m = int(end[5:7])
                dy = int(end[8:10])
                if m == 1 and dy <= 10:
                    yr -= 1
                yrs[yr] = e.get('val')
        print(f'  {concept}: {dict(sorted(yrs.items()))}')
    else:
        all_e = [e for v in d.get('units', {}).values() for e in v]
        combos = sorted(set((e.get('form', '?'), e.get('fp', '?'))
                        for e in all_e))
        print(
            f'  {concept}: 0 annual entries (total={len(all_e)}, combos={combos[:5]})')

# ── 3. Visa FY end dates ─────────────────────────────────────────────────────
print('\n--- Visa fiscal year end dates ---')
# Extract from NetIncomeLoss
ni = usg.get('NetIncomeLoss', {})
ni_k10 = [e for v in ni.get('units', {}).values() for e in v
          if e.get('form') in K10 and e.get('fp') == 'FY']
fye_by_yr = {}
for e in ni_k10:
    end = e.get('end', '')
    if len(end) >= 10:
        yr = int(end[:4])
        m = int(end[5:7])
        dy = int(end[8:10])
        if m == 1 and dy <= 10:
            yr -= 1
        fye_by_yr[yr] = end
print(f'FY end dates: {dict(sorted(fye_by_yr.items()))}')

# ── 4. Actually run the scraper on Visa ───────────────────────────────────────
print('\n--- Running scraper on Visa ---')
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s')

scraper = FinancialDataScraper(db_connection=None)
rows = scraper.get_company_financial_data('Visa Inc. Class A', 'V')

print(f'\nExtracted {len(rows)} rows')
for r in sorted(rows, key=lambda x: x['reporting_year']):
    eps = r.get('eps')
    ni = r.get('net_income')
    sh = r.get('shares_outstanding')
    print(f'  FY{r["reporting_year"]}: eps={eps}, net_income={ni}, shares={sh}')
