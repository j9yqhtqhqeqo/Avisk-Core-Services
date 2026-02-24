#!/usr/bin/env python3
"""diagnose5.py - targeted follow-up checks"""
import subprocess
import json

H = ['curl', '-s', '-m', '15', '-H',
     'User-Agent: Avisk Research contact@avisk.com']
K10 = {'10-K', '10-K405', '10-KSB', '10-KT'}


def fetch(cik):
    r = subprocess.run(H + [f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'],
                       capture_output=True)
    return json.loads(r.stdout).get('facts', {})


def k10_annual(ns_data, concept):
    d = ns_data.get(concept, {})
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
            if e.get('val') is not None:
                out[yr] = e.get('val')
    return out


# ── 1. Visa - check ALL namespaces for EPS ───────────────────────────────────
print('='*60)
print('VISA - check invest/srt namespaces for EPS')
facts = fetch('0001403161')
for ns in ['dei', 'invest', 'us-gaap', 'srt']:
    ns_data = facts.get(ns, {})
    eps = [k for k in ns_data if 'PerShare' in k or 'EarningsPer' in k or 'EPS' in k]
    if eps:
        print(f'  {ns} EPS concepts: {eps}')
        for c in eps:
            r = k10_annual(ns_data, c)
            if r:
                print(f'    {c}: {dict(sorted(r.items()))}')

# Also check: maybe Visa uses a completely different FY attribution
# Their FY ends Sep 30, so "FY2025" end date is 2025-09-30
# Check if EPS data exists with fp != 'FY'
usg = facts.get('us-gaap', {})
for concept in ['EarningsPerShareDiluted', 'EarningsPerShareBasic']:
    d = usg.get(concept, {})
    all_e = [e for v in d.get('units', {}).values() for e in v]
    if all_e:
        print(f'  {concept} ALL entries: {all_e[:5]}')
    else:
        print(f'  {concept}: ZERO entries in EDGAR (concept not filed in XBRL)')

# ── 2. Prologis opex 2019-2021 ───────────────────────────────────────────────
print('\n' + '='*60)
print('PROLOGIS - opex 2019-2021')
facts = fetch('0001045609')
usg = facts.get('us-gaap', {})
# Find all expense/cost concepts that have 2019-2021 data
for cname, cdata in sorted(usg.items()):
    if not any(x in cname for x in ['Expense', 'Cost', 'Operating']):
        continue
    r = k10_annual(usg, cname)
    tgt = {k: v for k, v in r.items() if k in [2019, 2020, 2021]}
    if tgt:
        print(f'  {cname}: {tgt}')

# ── 3. Disney original CIK ───────────────────────────────────────────────────
print('\n' + '='*60)
print('DISNEY - original CIK check')
# CIK 1001039 is the original Walt Disney Company
for cik, label in [('0001744489', 'New CIK'), ('0001001039', 'Original CIK')]:
    facts = fetch(cik)
    usg = facts.get('us-gaap', {})
    r = k10_annual(usg, 'Assets')
    print(f'  {label} ({cik}): Assets years={sorted(r.keys())}')
    tgt = {k: v for k, v in r.items() if 2015 <= k <= 2019}
    print(f'    2015-2019: {tgt}')

# ── 4. ConocoPhillips - extended income concepts ─────────────────────────────
print('\n' + '='*60)
print('CONOCOPHILLIPS - income concepts for 2012-2014')
facts = fetch('0001163165')
usg = facts.get('us-gaap', {})
# Check ALL income/operating concepts for 2012-2014
for cname, cdata in sorted(usg.items()):
    r = k10_annual(usg, cname)
    tgt = {k: v for k, v in r.items() if k in [2012, 2013, 2014]}
    if tgt and any(x in cname for x in ['Income', 'Operating', 'Profit', 'Earning']):
        print(f'  {cname}: {tgt}')

# ── 5. Chubb - extended income concepts 2012-2013 ────────────────────────────
print('\n' + '='*60)
print('CHUBB - income concepts for 2012-2013')
facts = fetch('0000896159')
usg = facts.get('us-gaap', {})
for cname in sorted(usg.keys()):
    r = k10_annual(usg, cname)
    tgt = {k: v for k, v in r.items() if k in [2012, 2013]}
    if tgt and any(x in cname for x in ['Income', 'Operating', 'Profit']):
        print(f'  {cname}: {tgt}')

# ── 6. Welltower - what concepts have 2025 data? ─────────────────────────────
print('\n' + '='*60)
print('WELLTOWER - available 2025 data')
facts = fetch('0000766704')
usg = facts.get('us-gaap', {})
yrs_available = set()
for cdata in usg.values():
    for unit_entries in cdata.get('units', {}).values():
        for e in unit_entries:
            if e.get('form') in K10:
                end = e.get('end', '')
                if end and len(end) >= 4:
                    yr = int(end[:4])
                    yrs_available.add(yr)
print(f'  Years with 10-K data: {sorted(yrs_available)}')
# Check if 2025 10-K was even filed
dei = facts.get('dei', {})
doctype = dei.get('DocumentType', {})
types = k10_annual(dei, 'DocumentType') if False else {}
filings_2025 = [e for v in doctype.get('units', {}).values() for e in v
                if e.get('end', '').startswith('2025') and e.get('form') in K10]
print(f'  2025 10-K filings: {filings_2025[:3]}')

# ── 7. Alphabet Class C - why 2012 is missing ────────────────────────────────
print('\n' + '='*60)
print('ALPHABET - Google old CIK for 2012')
# GOOGL CIK is 1652044, original Google CIK was 1288776
for cik, label in [('0001652044', 'Alphabet (GOOGL)'), ('0001288776', 'Original Google')]:
    facts = fetch(cik)
    usg = facts.get('us-gaap', {})
    r = k10_annual(usg, 'Revenues')
    tgt = {k: v for k, v in r.items() if 2010 <= k <= 2015}
    print(f'  {label} ({cik}): Revenues 2010-2015={tgt}')
