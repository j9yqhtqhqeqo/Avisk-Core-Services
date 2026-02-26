#!/usr/bin/env python3
"""diagnose_remaining2.py — targeted follow-up diagnostics"""
import requests
import sys
import os
import time
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept-Encoding': 'gzip, deflate', 'Host': 'data.sec.gov'}
WEB_HEADERS = {**HEADERS, 'Host': 'efts.sec.gov'}
FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'


def get_facts(cik):
    r = requests.get(FACTS_URL.format(cik=cik), headers=HEADERS, timeout=30)
    return r.json().get('facts', {}) if r.status_code == 200 else {}


def yrs_for_concept(facts, concept, ns='us-gaap'):
    cd = facts.get(ns, {}).get(concept, {})
    years = set()
    for e in cd.get('units', {}).get('USD', []):
        if e.get('form', '') in ('10-K', '10-K405', '10-KSB') and (
                e.get('fp') == 'FY' or (e.get('frame', '') or '').startswith('CY')):
            years.add(int(e.get('end', '0')[:4]))
    return sorted(years)


def first_filing_year(facts, concept, ns='us-gaap'):
    """Return min year of ANY filing (not just 10-K)."""
    cd = facts.get(ns, {}).get(concept, {})
    years = set()
    for e in cd.get('units', {}).get('USD', []):
        end = e.get('end', '')
        if end:
            years.add(int(end[:4]))
    return min(years) if years else None


# ─── 1. Find old BlackRock CIK ───────────────────────────────────────────────
print("=" * 65)
print("1. BlackRock — searching EDGAR full-text for old CIK")
print("=" * 65)
# Search EDGAR for BlackRock company entries
search_url = 'https://efts.sec.gov/LATEST/search-index?q=%22BlackRock%22&dateRange=custom&startdt=2000-01-01&enddt=2010-12-31&forms=10-K'
# Use company search instead
company_search = 'https://www.sec.gov/cgi-bin/browse-edgar?company=blackrock&CIK=&type=10-K&dateb=&owner=include&count=40&search_text=&action=getcompany'

# Try known likely CIKs
for cik in [1364742, 1310067, 1359841, 1280776]:
    facts = get_facts(cik)
    rev = yrs_for_concept(
        facts, 'RevenueFromContractWithCustomerExcludingAssessedTax')
    assets = yrs_for_concept(facts, 'Assets')
    ni = yrs_for_concept(facts, 'NetIncomeLoss')
    if rev or assets or ni:
        entity = facts.get('entity', {}) if 'entity' in facts else {}
        print(f"  CIK {cik}: Revenue={rev} Assets={assets} NI={ni}")
    time.sleep(0.3)

# ─── 2. Find Avago Technologies CIK ─────────────────────────────────────────
print()
print("=" * 65)
print("2. Avago Technologies — find CIK for FY2015 Broadcom pre-merger")
print("=" * 65)
# Avago Technologies CIK — try known candidates
for cik in [1444175, 1569987, 1116132, 1341439, 1336920]:
    facts = get_facts(cik)
    rev = yrs_for_concept(facts, 'Revenues')
    rev2 = yrs_for_concept(
        facts, 'RevenueFromContractWithCustomerExcludingAssessedTax')
    rev3 = yrs_for_concept(facts, 'SalesRevenueNet')
    assets = yrs_for_concept(facts, 'Assets')
    if rev or rev2 or rev3 or assets:
        print(f"  CIK {cik}: Revenues={rev or rev2 or rev3} Assets={assets}")
    time.sleep(0.3)

# EDGAR company search for Avago
tickers_url = 'https://www.sec.gov/files/company_tickers.json'
r = requests.get(tickers_url, headers={
                 **HEADERS, 'Host': 'www.sec.gov'}, timeout=30)
ticker_map = {v['ticker'].upper(): (int(v['cik_str']), v['title'])
              for v in r.json().values()}
# Try AVGO as historical ticker — may still map
print(f"  Current AVGO CIK: {ticker_map.get('AVGO', 'not found')}")
# Also search by name prefix
matches = [(cik, title) for t, (cik, title) in ticker_map.items()
           if 'avago' in title.lower() or 'broadcom' in title.lower()]
for cik, title in sorted(matches):
    print(f"  Match: CIK {cik}  {title}")

# ─── 3. Alphabet 2015 EPS ───────────────────────────────────────────────────
print()
print("=" * 65)
print("3. Alphabet 2015 EPS — detailed check")
print("=" * 65)
# Alphabet CIK 1652044 (incorporated Aug 2015)
alph_facts = get_facts(1652044)
time.sleep(0.5)
eps_concepts = ['EarningsPerShareDiluted',
                'EarningsPerShareBasic', 'EarningsPerShareBasicAndDiluted']
for c in eps_concepts:
    cd = alph_facts.get('us-gaap', {}).get(c, {})
    entries_by_year = {}
    for e in cd.get('units', {}).get('USD/shares', []):
        if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
            yr = int(e.get('end', '0')[:4])
            entries_by_year[yr] = e.get('val')
    if entries_by_year:
        print(f"  Alphabet (1652044) {c}: {entries_by_year}")

# Check Google old CIK for 2015
google_facts = get_facts(1288776)
time.sleep(0.5)
for c in eps_concepts:
    cd = google_facts.get('us-gaap', {}).get(c, {})
    entries_by_year = {}
    for e in cd.get('units', {}).get('USD/shares', []):
        if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') == 'FY':
            yr = int(e.get('end', '0')[:4])
            entries_by_year[yr] = e.get('val')
    if entries_by_year:
        print(f"  Google old (1288776) {c}: {entries_by_year}")

# ─── 4. GE Vernova 2021 in XBRL ─────────────────────────────────────────────
print()
print("=" * 65)
print("4. GE Vernova 2021 — check all concepts and filing types")
print("=" * 65)
gev_facts = get_facts(1996810)
time.sleep(0.5)
gev_usgaap = gev_facts.get('us-gaap', {})
# Check assets with ALL form types
assets_cd = gev_usgaap.get('Assets', {})
all_asset_entries = []
for e in assets_cd.get('units', {}).get('USD', []):
    yr = int(e.get('end', '0')[:4])
    form = e.get('form', '')
    fp = e.get('fp', '')
    all_asset_entries.append((yr, form, fp, e.get('val')))
print(f"  GEV Assets all forms: {sorted(all_asset_entries)}")

rev_cd = gev_usgaap.get(
    'RevenueFromContractWithCustomerExcludingAssessedTax', {})
all_rev = []
for e in rev_cd.get('units', {}).get('USD', []):
    yr = int(e.get('end', '0')[:4])
    form = e.get('form', '')
    fp = e.get('fp', '')
    all_rev.append((yr, form, fp, e.get('val')))
print(f"  GEV Revenue all forms: {sorted(all_rev)}")

# ─── 5. Palo Alto EPS — check shares 2012 ──────────────────────────────────
print()
print("=" * 65)
print("5. Palo Alto Networks 2012 — EPS and shares check")
print("=" * 65)
panw_facts = get_facts(1327567)
time.sleep(0.5)
share_concepts = ['CommonStockSharesOutstanding',
                  'WeightedAverageNumberOfSharesOutstandingBasic',
                  'WeightedAverageNumberOfDilutedSharesOutstanding',
                  'WeightedAverageNumberOfShareOutstandingBasic']
for c in share_concepts:
    cd = panw_facts.get('us-gaap', {}).get(c, {})
    entries = {}
    for e in cd.get('units', {}).get('shares', []):
        if e.get('form', '') in ('10-K', '10-K405') and e.get('fp') in ('FY', None, ''):
            yr = int(e.get('end', '0')[:4])
            entries[yr] = e.get('val')
    if entries:
        print(f"  PANW {c}: {entries}")
ni_cd = panw_facts.get('us-gaap', {}).get('NetIncomeLoss', {})
ni_2012 = next((e.get('val') for e in ni_cd.get('units', {}).get('USD', [])
                if e.get('form', '') in ('10-K', '10-K405') and int(e.get('end', '0')[:4]) == 2012
                and e.get('fp') == 'FY'), None)
print(f"  PANW NetIncomeLoss 2012: {ni_2012}")

# Check EPS concepts with USD/shares unit
for c in eps_concepts:
    cd = panw_facts.get('us-gaap', {}).get(c, {})
    for unit_key in cd.get('units', {}).keys():
        entries = [(int(e.get('end', '0')[:4]), e.get('val'))
                   for e in cd['units'][unit_key]
                   if e.get('form', '') in ('10-K', '10-K405') and int(e.get('end', '0')[:4]) == 2012]
        if entries:
            print(f"  PANW {c} ({unit_key}): {entries}")

print()
print("DONE")
