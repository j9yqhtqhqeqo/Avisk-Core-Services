"""
Diagnose genuine vs fixable gaps for the reported zero-value companies.
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


def fy_years(entries):
    """Return sorted set of FY 10-K end-date years."""
    out = set()
    for e in entries:
        if e.get('form') not in EDGAR_10K_FORMS:
            continue
        if e.get('fp') and e.get('fp') != 'FY':
            continue
        end = e.get('end', '')
        if end and len(end) >= 4:
            out.add(int(end[:4]))
    return sorted(out)


def check_concepts(usgaap, candidates, gap_years):
    hits = {}
    for c in candidates:
        cd = usgaap.get(c)
        if not cd:
            continue
        for unit_entries in cd.get('units', {}).values():
            yrs = fy_years(unit_entries)
            found = [y for y in yrs if y in gap_years]
            if found:
                hits[c] = found
            break
    return hits


# ── 1. Operating-expenses gaps ─────────────────────────────────────────────────
OPEX_CANDS = [
    'OperatingExpenses', 'CostsAndExpenses', 'CostOfGoodsAndServicesSold',
    'CostOfRevenue', 'CostOfGoodsSold', 'OperatingCostsAndExpenses',
    'SellingGeneralAndAdministrativeExpense', 'BenefitsLossesAndExpenses',
    'NoninterestExpense', 'CostsAndExpensesApplicableToRevenues',
]
OPEX_TARGETS = {
    'AMD':  list(range(2012, 2016)),
    'COST': list(range(2012, 2016)),
    'LLY':  [2012],
    'JNJ':  list(range(2012, 2017)),
    'LIN':  list(range(2015, 2025)),
    'MRK':  list(range(2012, 2016)),
    'PM':   list(range(2012, 2016)),
    'PG':   list(range(2012, 2017)),
    'KO':   list(range(2012, 2016)),
}

print("\n" + "="*65)
print("OPERATING EXPENSES GAPS")
print("="*65)
for sym, gap_years in OPEX_TARGETS.items():
    usgaap = get_usgaap(sym)
    hits = check_concepts(usgaap, OPEX_CANDS, gap_years)
    if hits:
        for c, yrs in hits.items():
            print(f"  FIXABLE  {sym:6s}  {c}  covers {yrs}")
    else:
        print(f"  GENUINE  {sym:6s}  no concept covers gap years {gap_years}")

# ── 2. GOOGL special checks ────────────────────────────────────────────────────
print("\n" + "="*65)
print("ALPHABET (GOOGL) GAPS")
print("="*65)
usgaap = get_usgaap('GOOGL')
for concept, gap_years, label in [
    ('Assets',       [2012, 2013], 'assets 2012-2013'),
    ('Liabilities',  [2012, 2013], 'liabilities 2012-2013'),
    ('EarningsPerShareDiluted', [2015], 'eps 2015'),
    ('EarningsPerShareBasic',   [2015], 'eps 2015'),
]:
    cd = usgaap.get(concept)
    if not cd:
        print(f"  GENUINE  GOOGL  {label} — concept not tagged at all")
        continue
    for unit_entries in cd.get('units', {}).values():
        yrs = fy_years(unit_entries)
        found = [y for y in yrs if y in gap_years]
        if found:
            print(f"  FIXABLE  GOOGL  {label} — {concept} has years {found}")
        else:
            print(
                f"  GENUINE  GOOGL  {label} — earliest year in EDGAR: {min(yrs) if yrs else 'N/A'}")
        break

# ── 3. Other asset/liability gaps ──────────────────────────────────────────────
print("\n" + "="*65)
print("ASSETS / LIABILITIES / EQUITY GAPS")
print("="*65)
for sym, gap_years, label in [
    ('MA',   [2017], 'Mastercard assets/liabilities 2017'),
    ('DIS',  [2017], 'Disney assets/liabilities/equity 2017'),
    ('PLTR', [2017, 2018], 'Palantir all columns 2017-2018'),
    ('LIN',  [2015, 2016], 'Linde assets/liabilities 2015-2016'),
]:
    usgaap = get_usgaap(sym)
    for concept in ['Assets', 'Liabilities', 'StockholdersEquity']:
        cd = usgaap.get(concept)
        if not cd:
            continue
        for unit_entries in cd.get('units', {}).values():
            yrs = fy_years(unit_entries)
            found = [y for y in yrs if y in gap_years]
            earliest = min(yrs) if yrs else 'N/A'
            if found:
                print(
                    f"  FIXABLE  {sym:6s}  {label} — {concept} has years {found}")
            else:
                print(
                    f"  GENUINE  {sym:6s}  {label} — {concept} earliest={earliest}")
            break

# ── 4. Visa EPS (known genuine) ────────────────────────────────────────────────
print("\n" + "="*65)
print("VISA EPS (SPOT CHECK)")
print("="*65)
usgaap = get_usgaap('V')
eps_concepts = [c for c in usgaap.keys(
) if 'earningspershare' in c.lower() or 'pershare' in c.lower()]
for c in eps_concepts[:5]:
    cd = usgaap[c]
    for unit_entries in cd.get('units', {}).values():
        tenk = [e for e in unit_entries if e.get('form') in EDGAR_10K_FORMS]
        if tenk:
            fps = {e.get('fp') for e in tenk}
            yrs = sorted({int(e['end'][:4]) for e in tenk if e.get('end')})
            print(f"  {c}")
            print(f"    fp={fps}  years={yrs}")
        break
if not eps_concepts:
    print("  GENUINE  V — no EPS concept tagged in EDGAR at all")
