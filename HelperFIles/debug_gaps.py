"""
Deep-dive: Visa EPS and data-gap validation for GOOGL/LIN/DIS/JNJ/MA/PLTR.
"""
from Services.FinancialDataScraper import _get_headers, EDGAR_10K_FORMS, cik_for_symbol
import requests
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


HEADERS_DATA = {**_get_headers(), 'Host': 'data.sec.gov'}


def get_facts(sym):
    cik = int(cik_for_symbol(sym))
    print(f"  {sym} → CIK {cik}")
    return requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        headers=HEADERS_DATA, timeout=30
    ).json()['facts'].get('us-gaap', {})


# ── 1. Visa EPS: dump ALL 10-K entries for every EPS-like concept ─────────────
print("\n=== VISA: All EPS-like concepts in 10-K filings ===")
usgaap = get_facts('V')
for c in sorted(usgaap.keys()):
    if 'earningspershare' not in c.lower() and 'pershare' not in c.lower():
        continue
    cd = usgaap[c]
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        if tenk:
            fps = {e.get('fp', '?') for e in tenk}
            years = sorted({int(e['end'][:4]) for e in tenk if e.get('end')})
            print(f"  {c}")
            print(f"    fp values: {fps}  |  years: {years}")
            for e in sorted(tenk, key=lambda e: e.get('end', ''), reverse=True)[:3]:
                print(
                    f"    end={e.get('end')}  fp={e.get('fp')}  frame={e.get('frame','')}  val={e.get('val')}")
            break

# ── 2. GOOGL: show what earliest years exist under any concept ────────────────
print("\n\n=== GOOGL: earliest available years across key concepts ===")
usgaap = get_facts('GOOGL')
for c in ['Assets', 'Liabilities', 'Revenues', 'NetIncomeLoss', 'EarningsPerShareDiluted',
          'RevenueFromContractWithCustomerExcludingAssessedTax', 'NetCashProvidedByUsedInOperatingActivities']:
    cd = usgaap.get(c)
    if not cd:
        print(f"  MISSING  {c}")
        continue
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        years = sorted({int(e['end'][:4]) for e in tenk if e.get('end')})
        print(f"  {c}: years={years}")
        break

# ── 3. JNJ 2015: what end-date are their 2015 10-K entries under? ────────────
print("\n\n=== JNJ: 10-K entry dates for Assets and CF around 2015 ===")
usgaap = get_facts('JNJ')
for c in ['Assets', 'NetCashProvidedByUsedInOperatingActivities']:
    cd = usgaap.get(c)
    if not cd:
        print(f"  MISSING {c}")
        continue
    for unit_entries in cd.get('units', {}).values():
        tenk = sorted([e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS],
                      key=lambda e: e.get('end', ''))
        print(f"  {c}:")
        for e in tenk:
            yr = int(e['end'][:4]) if e.get('end') else '?'
            print(
                f"    end={e.get('end')}  fp={e.get('fp')}  frame={e.get('frame','')}  val={e.get('val')}")
        break

# ── 4. Check DIS/MA/LIN/PLTR earliest 10-K filings ──────────────────────────
print("\n\n=== DIS / MA / LIN / PLTR: CIK and earliest 10-K data year ===")
for sym in ['DIS', 'MA', 'LIN', 'PLTR']:
    usgaap = get_facts(sym)
    cd = usgaap.get('Assets') or usgaap.get('Revenues')
    if not cd:
        print(f"  {sym}: no Assets/Revenues concept at all")
        continue
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        years = sorted({int(e['end'][:4]) for e in tenk if e.get('end')})
        print(
            f"  {sym}: earliest={years[:3] if years else 'NONE'} latest={years[-3:] if years else 'NONE'}")
        break
