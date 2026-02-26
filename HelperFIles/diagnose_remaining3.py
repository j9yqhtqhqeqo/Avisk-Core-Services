#!/usr/bin/env python3
"""diagnose_remaining3.py — identify mystery CIKs and Broadcom history"""
import requests
import sys
import os
import time
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept-Encoding': 'gzip, deflate', 'Host': 'data.sec.gov'}


def get_submission(cik):
    r = requests.get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                     headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else {}


def get_facts(cik):
    r = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
                     headers=HEADERS, timeout=30)
    return r.json().get('facts', {}) if r.status_code == 200 else {}


def yrs(facts, concept, ns='us-gaap'):
    cd = facts.get(ns, {}).get(concept, {})
    years = set()
    for e in cd.get('units', {}).get('USD', []):
        if e.get('form', '') in ('10-K', '10-K405', '10-KSB') and (
                e.get('fp') == 'FY' or (e.get('frame', '') or '').startswith('CY')):
            years.add(int(e.get('end', '0')[:4]))
    return sorted(years)


# 1. Identify mystery CIKs
print("Mystery CIKs:")
for cik in [1116132, 1341439]:
    sub = get_submission(cik)
    print(f"  CIK {cik}: {sub.get('name')}  tickers={sub.get('tickers')}  "
          f"formerNames={sub.get('formerNames',[])}")
    time.sleep(0.4)

# 2. Broadcom Inc CIK 1730168 - former names and earliest 10-K
print()
sub_avgo = get_submission(1730168)
print(
    f"AVGO CIK 1730168: {sub_avgo.get('name')}  tickers={sub_avgo.get('tickers')}")
print(f"  formerNames: {sub_avgo.get('formerNames', [])}")
filings = sub_avgo.get('filings', {}).get('recent', {})
forms = filings.get('form', [])
dates = filings.get('filingDate', [])
accns = filings.get('accessionNumber', [])
tenks = [(d, a) for f, d, a in zip(forms, dates, accns) if '10-K' in f]
print(f"  10-K filings: {tenks[:8]}")
time.sleep(0.4)

# 3. Check Avago Technologies - try CIK from EDGAR submissions search
# Avago was ticker AVGO before the Broadcom merger, different CIK
for cik in [1444175, 1569987]:
    sub = get_submission(cik)
    if sub.get('name'):
        print(f"CIK {cik}: {sub.get('name')}  tickers={sub.get('tickers')}")
        facts = get_facts(cik)
        rev = yrs(facts, 'Revenues') or yrs(facts, 'SalesRevenueNet') or yrs(
            facts, 'RevenueFromContractWithCustomerExcludingAssessedTax')
        assets = yrs(facts, 'Assets')
        print(f"  Revenue={rev}  Assets={assets}")
    time.sleep(0.4)

# 4. Check CIK 1730168 XBRL for 2016 Assets - what concept is used
print()
print("AVGO 1730168 — checking Assets concept for 2016:")
avgo_facts = get_facts(1730168)
time.sleep(0.5)
assets_cd = avgo_facts.get('us-gaap', {}).get('Assets', {})
for e in assets_cd.get('units', {}).get('USD', []):
    if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
        yr = int(e.get('end', '0')[:4])
        if yr in [2016, 2017]:
            print(
                f"  Assets yr={yr} val={e.get('val')} accn={e.get('accn')} end={e.get('end')}")

# 5. BlackRock old CIK 1364742 - check company name and revenue details
print()
sub_blk = get_submission(1364742)
print(
    f"BLK CIK 1364742: {sub_blk.get('name')}  tickers={sub_blk.get('tickers')}")
print(f"  formerNames: {sub_blk.get('formerNames', [])}")
blk_facts = get_facts(1364742)
time.sleep(0.5)
for c in ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'InvestmentAdvisoryFees', 'BaseManagementFees']:
    r = yrs(blk_facts, c)
    if r:
        print(f"  {c}: {r}")
print(f"  Assets: {yrs(blk_facts, 'Assets')}")
print(f"  NI: {yrs(blk_facts, 'NetIncomeLoss')}")

# 6. BlackRock new CIK 2012383
sub_blk_new = get_submission(2012383)
print(
    f"BLK new CIK 2012383: {sub_blk_new.get('name')}  tickers={sub_blk_new.get('tickers')}")
print(f"  formerNames: {sub_blk_new.get('formerNames', [])}")
