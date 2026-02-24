#!/usr/bin/env python3
"""diagnose_avago.py — find Avago/Broadcom Limited CIK via EDGAR search"""
import sys, os, time, re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')
import requests

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
    rev = set(); assets = set()
    for c in ['Revenues','RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet']:
        for e in facts.get('us-gaap',{}).get(c,{}).get('units',{}).get('USD',[]):
            if e.get('form','') in ('10-K','10-K405') and e.get('fp') == 'FY':
                rev.add(int(e.get('end','0')[:4]))
    for e in facts.get('us-gaap',{}).get('Assets',{}).get('units',{}).get('USD',[]):
        if e.get('form','') in ('10-K','10-K405') and e.get('fp') == 'FY':
            assets.add(int(e.get('end','0')[:4]))
    return sorted(rev), sorted(assets)

# EDGAR company search (HTML atom feed)
print("EDGAR company search for 'avago':")
r = requests.get(
    'https://www.sec.gov/cgi-bin/browse-edgar?company=avago&CIK=&type=10-K&dateb=&owner=include&count=20&search_text=&action=getcompany',
    headers={**SEC_HEADERS, 'Host': 'www.sec.gov'}, timeout=30)
# Extract CIK/name pairs from HTML
cik_names = re.findall(r'/cgi-bin/browse-edgar\?action=getcompany&CIK=(\d+)[^"]*"[^>]*>([^<]+)</a>', r.text)
seen = set()
for cik_str, name in cik_names[:20]:
    if cik_str not in seen and ('avago' in name.lower() or 'broadcom' in name.lower()):
        seen.add(cik_str)
        print(f"  CIK {cik_str}: {name.strip()}")

print()
print("EDGAR company search for 'broadcom limited':")
r2 = requests.get(
    'https://www.sec.gov/cgi-bin/browse-edgar?company=broadcom+limited&CIK=&type=10-K&dateb=&owner=include&count=20&search_text=&action=getcompany',
    headers={**SEC_HEADERS, 'Host': 'www.sec.gov'}, timeout=30)
cik_names2 = re.findall(r'/cgi-bin/browse-edgar\?action=getcompany&CIK=(\d+)[^"]*"[^>]*>([^<]+)</a>', r2.text)
seen2 = set()
for cik_str, name in cik_names2[:20]:
    if cik_str not in seen2:
        seen2.add(cik_str)
        print(f"  CIK {cik_str}: {name.strip()}")

# Check a few specific candidate CIKs from public records
print()
print("Targeted CIK checks:")
for cik in [1444171, 1393053, 1388072, 1409970, 1540160, 1607982]:
    sub = get_sub(cik)
    name = sub.get('name', '')
    if not name:
        continue
    tickers = sub.get('tickers', [])
    facts = get_facts(cik)
    rv, ay = rev_asset_yrs(facts)
    if rv or ay:
        print(f"  CIK {cik}: {name}  tickers={tickers}  Rev={rv}  Assets={ay}")
    time.sleep(0.3)
