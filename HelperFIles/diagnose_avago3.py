#!/usr/bin/env python3
"""diagnose_avago3.py — find Avago CIK via EDGAR filing search"""
import sys, os, time
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')
import requests

SEC_HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
               'Accept-Encoding': 'gzip, deflate'}
DATA_HEADERS = {**SEC_HEADERS, 'Host': 'data.sec.gov'}

def get_facts(cik):
    r = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
                     headers=DATA_HEADERS, timeout=30)
    return r.json().get('facts', {}) if r.status_code == 200 else {}

def get_sub(cik):
    r = requests.get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                     headers=DATA_HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else {}

# Use EDGAR full-text search with entity search
print("EFTS full search for Avago 10-K filings:")
r = requests.get(
    'https://efts.sec.gov/LATEST/search-index?q=%22avago+technologies%22&forms=10-K',
    headers={**SEC_HEADERS, 'Host': 'efts.sec.gov'}, timeout=30)
if r.status_code == 200:
    data = r.json()
    hits = data.get('hits', {}).get('hits', [])
    for h in hits[:5]:
        src = h.get('_source', {})
        print(f"  id={h.get('_id')} entity={src.get('entity_name')} ciks={src.get('entity_ids')} date={src.get('file_date')} form={src.get('form_type')}")

# Try the EDGAR company search returning JSON
print()
print("EDGAR company search API for Avago:")
r2 = requests.get(
    'https://efts.sec.gov/LATEST/search-index?q=%22Avago+Technologies%22&category=form-type&forms=10-K&dateRange=custom&startdt=2009-01-01&enddt=2017-01-01',
    headers={**SEC_HEADERS, 'Host': 'efts.sec.gov'}, timeout=30)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    try:
        data2 = r2.json()
        hits2 = data2.get('hits', {}).get('hits', [])
        for h in hits2[:5]:
            src = h.get('_source', {})
            print(f"  entity_ids={src.get('entity_ids')} entity_names={src.get('entity_names')} form={src.get('form_type')} date={src.get('file_date')}")
    except: pass

# Direct accession number approach - the 2015-12-17 10-K for Avago
# Accession numbers are sortable. Try to find it via EDGAR search
print()
print("Try finding via SEC full-text search:")
r3 = requests.get(
    'https://efts.sec.gov/LATEST/search-index?q=%22avago%22&forms=10-K&dateRange=custom&startdt=2015-12-01&enddt=2015-12-31',
    headers={**SEC_HEADERS, 'Host': 'efts.sec.gov'}, timeout=30)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    try:
        data3 = r3.json()
        print(f"Total hits: {data3.get('hits',{}).get('total',{})}")
        for h in data3.get('hits',{}).get('hits',[])[:5]:
            src = h.get('_source', {})
            print(f"  entity_ids={src.get('entity_ids')} entity_names={src.get('entity_names')} accn={h.get('_id')} date={src.get('file_date')}")
    except Exception as e:
        print(f"Error: {e}")
        print(r3.text[:500])

# Search for CIKs starting with 1444 through 1450 that have Avago-related data
print()
print("Brute force CIK scan for Avago (1440000-1445000 range):")
found = []
for cik in range(1440000, 1445000, 100):
    sub = get_sub(cik)
    name = sub.get('name', '')
    if 'avago' in name.lower() or ('broadcom' in name.lower() and cik != 1730168 and cik != 1054374):
        tickers = sub.get('tickers', [])
        former = sub.get('formerNames', [])
        facts = get_facts(cik)
        rev_yrs = set()
        for c in ['Revenues','SalesRevenueNet','RevenueFromContractWithCustomerExcludingAssessedTax']:
            for e in facts.get('us-gaap',{}).get(c,{}).get('units',{}).get('USD',[]):
                if e.get('fp') == 'FY':
                    rev_yrs.add(int(e.get('end','0')[:4]))
        asset_yrs = set()
        for e in facts.get('us-gaap',{}).get('Assets',{}).get('units',{}).get('USD',[]):
            if e.get('fp') == 'FY':
                asset_yrs.add(int(e.get('end','0')[:4]))
        found.append(cik)
        print(f"  *** CIK {cik}: {name}  tickers={tickers}")
        print(f"      former={former}")
        print(f"      Rev={sorted(rev_yrs)}  Assets={sorted(asset_yrs)}")
        time.sleep(0.3)
if not found:
    print("  Not found in this range")
