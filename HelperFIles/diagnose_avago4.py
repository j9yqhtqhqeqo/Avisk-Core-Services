#!/usr/bin/env python3
"""diagnose_avago4.py — verify Avago CIK 1441634"""
import requests
import sys
import os
import time
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept-Encoding': 'gzip, deflate', 'Host': 'data.sec.gov'}


def get_sub(cik):
    r = requests.get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                     headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else {}


def get_facts(cik):
    r = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
                     headers=HEADERS, timeout=30)
    return r.json().get('facts', {}) if r.status_code == 200 else {}


AVAGO_CIK = 1441634
sub = get_sub(AVAGO_CIK)
print(f"CIK {AVAGO_CIK}: {sub.get('name')}")
print(f"  tickers: {sub.get('tickers')}")
print(f"  formerNames: {sub.get('formerNames', [])}")

filings = sub.get('filings', {}).get('recent', {})
forms = filings.get('form', [])
dates = filings.get('filingDate', [])
form_counts = {}
for f in forms:
    form_counts[f] = form_counts.get(f, 0) + 1
print(f"  form types: {form_counts}")
tenks = [(d, f) for f, d in zip(forms, dates) if '10-K' in f]
print(f"  10-K filings: {tenks[:8]}")

time.sleep(0.5)
facts = get_facts(AVAGO_CIK)
print()

# Check all revenue/asset concepts
for concept in ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                'NetRevenues']:
    cd = facts.get('us-gaap', {}).get(concept, {})
    yrs = {}
    for e in cd.get('units', {}).get('USD', []):
        if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
            yr = int(e.get('end', '0')[:4])
            yrs[yr] = e.get('val')
    if yrs:
        print(f"  {concept}: {yrs}")

assets_cd = facts.get('us-gaap', {}).get('Assets', {})
asset_yrs = {}
for e in assets_cd.get('units', {}).get('USD', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        asset_yrs[yr] = e.get('val')
print(f"  Assets: {asset_yrs}")

ni_cd = facts.get('us-gaap', {}).get('NetIncomeLoss', {})
ni_yrs = {}
for e in ni_cd.get('units', {}).get('USD', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        ni_yrs[yr] = e.get('val')
print(f"  NetIncomeLoss: {ni_yrs}")

eps_cd = facts.get('us-gaap', {}).get('EarningsPerShareDiluted', {})
eps_yrs = {}
for e in eps_cd.get('units', {}).get('USD/shares', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        eps_yrs[yr] = e.get('val')
print(f"  EPS Diluted: {eps_yrs}")
