"""
Deep-dive on remaining gaps to confirm genuine vs edge-case fixable.
Focus: Mastercard 2017 assets/liabilities, GOOGL 2015 EPS.
"""
from Services.FinancialDataScraper import _get_headers, EDGAR_10K_FORMS, cik_for_symbol
import sys
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

H = {**_get_headers(), 'Host': 'data.sec.gov'}


def get_usgaap(sym):
    cik = int(cik_for_symbol(sym))
    r = requests.get(
        f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
        headers=H, timeout=30)
    return r.json()['facts'].get('us-gaap', {})


# ─── Mastercard 2017: dump every 10-K Assets entry to see what years exist ────
print("\n" + "="*65)
print("MASTERCARD — All 10-K Assets entries around 2016-2019")
print("="*65)
usgaap = get_usgaap('MA')
cd = usgaap.get('Assets')
if cd:
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        tenk_sorted = sorted(tenk, key=lambda e: e.get('end', ''))
        for e in tenk_sorted:
            end = e.get('end', '')
            if '2015' <= end[:4] <= '2020':
                print(f"  end={end}  fp={e.get('fp','')}  frame={e.get('frame','')}  "
                      f"accn={e.get('accn','')}  val={e.get('val')}")
        break

# Also check Liabilities
print("\nMASTERCARD — All 10-K Liabilities entries around 2016-2019")
cd = usgaap.get('Liabilities')
if cd:
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        tenk_sorted = sorted(tenk, key=lambda e: e.get('end', ''))
        for e in tenk_sorted:
            end = e.get('end', '')
            if '2015' <= end[:4] <= '2020':
                print(f"  end={end}  fp={e.get('fp','')}  frame={e.get('frame','')}  "
                      f"accn={e.get('accn','')}  val={e.get('val')}")
        break

# ─── GOOGL 2015 EPS: dump all EPS-like 10-K entries ──────────────────────────
print("\n" + "="*65)
print("ALPHABET (GOOGL) — All EPS 10-K entries 2013-2017")
print("="*65)
usgaap = get_usgaap('GOOGL')
for concept in ['EarningsPerShareDiluted', 'EarningsPerShareBasic',
                'EarningsPerShareBasicAndDiluted',
                'IncomeLossFromContinuingOperationsPerDilutedShare']:
    cd = usgaap.get(concept)
    if not cd:
        print(f"  {concept}: NOT TAGGED")
        continue
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        tenk_sorted = sorted(tenk, key=lambda e: e.get('end', ''))
        relevant = [e for e in tenk_sorted if '2013' <= e.get('end', '')[
            :4] <= '2017']
        if relevant:
            print(f"\n  {concept}:")
            for e in relevant:
                print(f"    end={e.get('end')}  fp={e.get('fp','')}  "
                      f"frame={e.get('frame','')}  val={e.get('val')}")
        break

# ─── Disney 2017: double-check CIK and what years are in EDGAR ───────────────
print("\n" + "="*65)
print("DISNEY — CIK and earliest 10-K Assets entry")
print("="*65)
cik = cik_for_symbol('DIS')
print(f"  DIS CIK: {cik}")
usgaap = get_usgaap('DIS')
cd = usgaap.get('Assets')
if cd:
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        tenk_sorted = sorted(tenk, key=lambda e: e.get('end', ''))
        print(f"  First 5 10-K Assets entries:")
        for e in tenk_sorted[:5]:
            print(
                f"    end={e.get('end')}  fp={e.get('fp','')}  frame={e.get('frame','')}  val={e.get('val')}")
        break

# ─── Palantir 2017-2018 ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("PALANTIR — CIK and earliest 10-K data")
print("="*65)
cik = cik_for_symbol('PLTR')
print(f"  PLTR CIK: {cik}")
usgaap = get_usgaap('PLTR')
cd = usgaap.get('Assets') or usgaap.get('Revenues')
if cd:
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        tenk_sorted = sorted(tenk, key=lambda e: e.get('end', ''))
        print(f"  First 3 10-K entries:")
        for e in tenk_sorted[:3]:
            print(
                f"    end={e.get('end')}  fp={e.get('fp','')}  val={e.get('val')}")
        break
