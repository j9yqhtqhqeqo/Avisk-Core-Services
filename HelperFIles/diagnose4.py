#!/usr/bin/env python3
"""diagnose4.py - curl-pipe based approach to avoid hanging"""
import subprocess
import json
import sys


def fetch(cik):
    r = subprocess.run(
        ['curl', '-s', '-m', '15', '-H', 'User-Agent: Avisk Research contact@avisk.com',
         f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'],
        capture_output=True)
    return json.loads(r.stdout).get('facts', {})


def k10_annual(facts, concept):
    usg = facts.get('us-gaap', {})
    d = usg.get(concept, {})
    K10 = {'10-K', '10-K405', '10-KSB', '10-KT'}
    out = {}
    for unit_entries in d.get('units', {}).values():
        for e in unit_entries:
            if e.get('form') not in K10:
                continue
            if e.get('fp') and e.get('fp') not in ('FY', 'Q4'):
                continue
            end = e.get('end', '')
            if len(end) < 10:
                continue
            yr = int(end[:4])
            m = int(end[5:7])
            dy = int(end[8:10])
            if m == 1 and dy <= 10:
                yr -= 1
            out[yr] = e.get('val')
    return out


# ── 1. Visa EPS ────────────────────────────────────────────────────────────────
print('='*60)
print('VISA EPS')
facts = fetch('0001403161')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
print(f'  Namespaces: {list(facts.keys())}')

# All USD/shares concepts
per_share = []
for cname, cdata in usg.items():
    if 'USD/shares' in cdata.get('units', {}):
        ents = [e for v in cdata['units']['USD/shares'] if True
                for e in [v] if e.get('form') in ('10-K', '10-K405') and e.get('fp') in ('FY', '')]
        if ents:
            per_share.append(cname)
print(f'  USD/shares concepts with 10-K FY data: {per_share}')

# Standard EPS check
for c in ['EarningsPerShareDiluted', 'EarningsPerShareBasic']:
    d = usg.get(c, {})
    units_keys = list(d.get('units', {}).keys())
    all_entries = [e for v in d.get('units', {}).values() for e in v]
    print(f'  {c}: units={units_keys}, total_entries={len(all_entries)}')

# Visa fiscal year
ni = k10_annual(facts, 'NetIncomeLoss')
print(f'  NetIncomeLoss by year: {dict(sorted(ni.items()))}')

# ── 2. Eaton revenue ──────────────────────────────────────────────────────────
print('\n' + '='*60)
print('EATON revenue')
facts = fetch('0001551182')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
rev = sorted(
    [k for k in usg if 'Revenue' in k or 'Sales' in k or 'NetSales' in k])
print(f'  Revenue-like: {rev[:15]}')
for c in ['Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet',
          'RevenueFromContractWithCustomerExcludingAssessedTax']:
    r = k10_annual(facts, c)
    if r:
        print(f'  ✅ {c}: {dict(sorted(r.items()))}')
    else:
        print(f'  ❌ {c}')
assets = k10_annual(facts, 'Assets')
print(f'  Assets years: {sorted(assets.keys())}')

# ── 3. Nextera revenue ────────────────────────────────────────────────────────
print('\n' + '='*60)
print('NEXTERA revenue')
facts = fetch('0000753308')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
rev = sorted([k for k in usg if 'Revenue' in k or 'Sales' in k])
print(f'  Revenue-like: {rev[:10]}')
for c in ['Revenues', 'ElectricUtilityRevenue', 'RegulatedAndUnregulatedOperatingRevenue',
          'OperatingRevenues', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
    r = k10_annual(facts, c)
    if r:
        years_shown = {k: v for k, v in r.items() if 2012 <= k <= 2018}
        print(f'  ✅ {c}: {dict(sorted(years_shown.items()))}')
    else:
        print(f'  ❌ {c}')

# ── 4. Prologis revenue + opex ────────────────────────────────────────────────
print('\n' + '='*60)
print('PROLOGIS revenue + opex')
facts = fetch('0001045609')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
rev = sorted(
    [k for k in usg if 'Revenue' in k or 'Lease' in k or 'Rental' in k])
print(f'  Revenue-like: {rev[:15]}')
for c in ['Revenues', 'RealEstateRevenueNet', 'LeaseIncome',
          'OperatingLeasesIncomeStatementLeaseRevenue',
          'OperatingExpenses', 'CostsAndExpenses']:
    r = k10_annual(facts, c)
    tgt = {k: v for k, v in r.items() if k in [
        2012, 2013, 2014, 2015, 2019, 2020, 2021, 2022]}
    if tgt:
        print(f'  ✅ {c}: {dict(sorted(tgt.items()))}')
    elif r:
        print(f'  ✅ {c} (other yrs): {dict(sorted(r.items()))}')
    else:
        print(f'  ❌ {c}')

# ── 5. ConocoPhillips EBITDA ──────────────────────────────────────────────────
print('\n' + '='*60)
print('CONOCOPHILLIPS EBITDA')
facts = fetch('0001163165')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
inc = sorted([k for k in usg if 'IncomeLoss' in k or 'OperatingIncome' in k])
print(f'  Income concepts: {inc[:10]}')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments']:
    r = k10_annual(facts, c)
    tgt = {k: v for k, v in r.items() if 2012 <= k <= 2015}
    if tgt:
        print(f'  ✅ {c}: {tgt}')
    elif r:
        print(f'  ❌ {c}: not in 2012-15, available years: {sorted(r.keys())}')
    else:
        print(f'  ❌ {c}: no data')

# ── 6. Chubb EBITDA ───────────────────────────────────────────────────────────
print('\n' + '='*60)
print('CHUBB EBITDA')
facts = fetch('0000896159')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
inc = sorted([k for k in usg if 'Income' in k and 'Loss' in k])
print(f'  IncomeLoss concepts: {inc[:10]}')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
    r = k10_annual(facts, c)
    tgt = {k: v for k, v in r.items() if 2012 <= k <= 2015}
    if tgt:
        print(f'  ✅ {c}: {tgt}')
    elif r:
        print(f'  ❌ {c}: available years: {sorted(r.keys())}')
    else:
        print(f'  ❌ {c}: no data')

# ── 7. Disney 2017 balance sheet ──────────────────────────────────────────────
print('\n' + '='*60)
print('DISNEY assets 2016-2018')
facts = fetch('0001744489')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
for c in ['Assets', 'Liabilities', 'StockholdersEquity',
          'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']:
    r = k10_annual(facts, c)
    tgt = {k: v for k, v in r.items() if 2015 <= k <= 2019}
    print(f'  {c}: {tgt}')

# ── 8. Welltower EBITDA 2025 ──────────────────────────────────────────────────
print('\n' + '='*60)
print('WELLTOWER EBITDA 2025')
facts = fetch('0000766704')
usg = facts.get('us-gaap', {})
print(f'  us-gaap: {len(usg)} concepts')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
    r = k10_annual(facts, c)
    tgt = {k: v for k, v in r.items() if 2023 <= k <= 2025}
    print(f'  {c}: {tgt}')
