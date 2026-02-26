#!/usr/bin/env python3
"""diagnose_remaining4.py — find Avago/Broadcom Limited CIK"""
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


def rev_yrs(facts):
    for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']:
        cd = facts.get('us-gaap', {}).get(c, {})
        yrs = set()
        for e in cd.get('units', {}).get('USD', []):
            if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
                yrs.add(int(e.get('end', '0')[:4]))
        if yrs:
            return c, sorted(yrs)
    return None, []


def asset_yrs(facts):
    cd = facts.get('us-gaap', {}).get('Assets', {})
    yrs = set()
    for e in cd.get('units', {}).get('USD', []):
        if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
            yrs.add(int(e.get('end', '0')[:4]))
    return sorted(yrs)


# Search for Avago Technologies / Broadcom Limited via EDGAR full-text search
# Known possible CIKs from public records
print("Searching for Avago/Broadcom Limited CIK...")
candidates = [
    1365135,  # common guess for Avago
    1566090,  # another candidate
    1728205,  # another candidate
    1657853,  # another candidate
    1679788,  # another candidate
    1054374,  # old Broadcom Corp (already known)
]
for cik in candidates:
    sub = get_sub(cik)
    name = sub.get('name', '')
    if name:
        tickers = sub.get('tickers', [])
        facts = get_facts(cik)
        c, ry = rev_yrs(facts)
        ay = asset_yrs(facts)
        if ry:
            print(
                f"  CIK {cik}: {name}  tickers={tickers}  Rev={ry}  Assets={ay}")
        elif name:
            print(f"  CIK {cik}: {name}  tickers={tickers}  (no revenue)")
    time.sleep(0.4)

# Try EDGAR company search API for "avago"
print()
print("EDGAR search for 'avago':")
search_r = requests.get(
    'https://efts.sec.gov/LATEST/search-index?q=%22avago%22&forms=10-K&dateRange=custom&startdt=2010-01-01&enddt=2016-12-31',
    headers={**HEADERS, 'Host': 'efts.sec.gov'}, timeout=30)
# Use the company search instead
r2 = requests.get(
    'https://www.sec.gov/cgi-bin/browse-edgar?company=avago&CIK=&type=10-K&dateb=&owner=include&count=20&search_text=&action=getcompany&output=atom',
    headers={**HEADERS, 'Host': 'www.sec.gov'}, timeout=30)
print(f"  Status: {r2.status_code}")
if r2.status_code == 200:
    # Parse just CIK numbers from the response
    import re
    cik_matches = re.findall(r'CIK=(\d+)', r2.text)
    name_matches = re.findall(r'<company-name>([^<]+)</company-name>', r2.text)
    for cik_str, name in zip(cik_matches[:5], name_matches[:5]):
        print(f"  CIK {cik_str}: {name}")
        cik_int = int(cik_str)
        facts = get_facts(cik_int)
        c, ry = rev_yrs(facts)
        ay = asset_yrs(facts)
        if ry:
            print(f"    Revenue({c})={ry}  Assets={ay}")
        time.sleep(0.4)

# Check BlackRock InvestmentAdvisoryFees as revenue proxy
print()
print("BlackRock old CIK 1364742 - InvestmentAdvisoryFees detail:")
blk_facts = get_facts(1364742)
time.sleep(0.5)
cd = blk_facts.get('us-gaap', {}).get('InvestmentAdvisoryFees', {})
vals = {}
for e in cd.get('units', {}).get('USD', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        vals[yr] = e.get('val')
print(f"  InvestmentAdvisoryFees: {vals}")
# Also check RevenueFromContractWithCustomerExcludingAssessedTax
cd2 = blk_facts.get(
    'us-gaap', {}).get('RevenueFromContractWithCustomerExcludingAssessedTax', {})
vals2 = {}
for e in cd2.get('units', {}).get('USD', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        vals2[yr] = e.get('val')
print(f"  RevenueFromContract: {vals2}")
