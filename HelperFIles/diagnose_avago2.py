#!/usr/bin/env python3
"""diagnose_avago2.py — find Avago through 20-F and targeted CIK search"""
import requests
import sys
import os
import time
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

SEC_HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
               'Accept-Encoding': 'gzip, deflate'}
DATA_HEADERS = {**SEC_HEADERS, 'Host': 'data.sec.gov'}


def get_sub(cik):
    r = requests.get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                     headers=DATA_HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else {}


def get_facts(cik):
    r = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
                     headers=DATA_HEADERS, timeout=30)
    return r.json().get('facts', {}) if r.status_code == 200 else {}


def rev_asset_yrs(facts):
    rev = set()
    assets = set()
    for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']:
        for e in facts.get('us-gaap', {}).get(c, {}).get('units', {}).get('USD', []):
            if e.get('fp') == 'FY':  # ANY form type for this check
                rev.add(int(e.get('end', '0')[:4]))
    for e in facts.get('us-gaap', {}).get('Assets', {}).get('units', {}).get('USD', []):
        if e.get('fp') == 'FY':
            assets.add(int(e.get('end', '0')[:4]))
    return sorted(rev), sorted(assets)


# Broad scan around Avago's likely CIK range (IPO 2009, CIK ~1400k-1500k range)
print("Scanning CIK range for Avago Technologies:")
candidates = [1441816, 1456502, 1388601, 1475922, 1441799, 1441820,
              1388601, 1505512, 1456288, 1441816, 1370946, 1378449]
for cik in candidates:
    sub = get_sub(cik)
    name = sub.get('name', '')
    if 'avago' in name.lower() or 'broadcom' in name.lower():
        tickers = sub.get('tickers', [])
        former = sub.get('formerNames', [])
        facts = get_facts(cik)
        rv, ay = rev_asset_yrs(facts)
        print(f"  *** CIK {cik}: {name}  tickers={tickers}  former={former}")
        print(f"      Rev={rv}  Assets={ay}")
        time.sleep(0.5)
    elif name:
        print(f"  CIK {cik}: {name}")
    time.sleep(0.2)

# Try EDGAR EFTS search API (machine-readable)
print()
print("EFTS search for Avago 10-K/20-F:")
for form in ['10-K', '20-F']:
    r = requests.get(
        f'https://efts.sec.gov/LATEST/search-index?q=%22avago+technologies%22&forms={form}&dateRange=custom&startdt=2014-01-01&enddt=2017-01-01',
        headers={**SEC_HEADERS, 'Host': 'efts.sec.gov'}, timeout=30)
    if r.status_code == 200:
        try:
            data = r.json()
            hits = data.get('hits', {}).get('hits', [])
            for h in hits[:3]:
                src = h.get('_source', {})
                print(
                    f"  Form={form}: entity={src.get('entity_name')} CIK={src.get('entity_id')} date={src.get('file_date')}")
        except Exception as e:
            print(f"  Error parsing {form} results: {e}")
    time.sleep(0.3)

# Check if CIK 1730168 has 20-F forms pre-2018
print()
print("AVGO CIK 1730168 - all form types:")
sub_avgo = get_sub(1730168)
filings = sub_avgo.get('filings', {}).get('recent', {})
forms = filings.get('form', [])
dates = filings.get('filingDate', [])
form_counts = {}
for f in forms:
    form_counts[f] = form_counts.get(f, 0) + 1
print(f"  Form types: {form_counts}")

# Check what forms are in the XBRL for AVGO
avgo_facts = get_facts(1730168)
rev_cd = avgo_facts.get('us-gaap', {}).get('Revenues', {})
all_forms = set()
for e in rev_cd.get('units', {}).get('USD', []):
    all_forms.add(e.get('form', ''))
print(f"  Forms in XBRL Revenue concept: {all_forms}")
