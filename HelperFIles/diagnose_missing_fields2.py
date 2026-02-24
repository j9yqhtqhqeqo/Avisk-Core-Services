"""
diagnose_missing_fields2.py - more verbose debugging
"""
import requests
import sys

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept': 'application/json'}
EDGAR_10K_FORMS = {'10-K', '10-K405', '10-KSB', '10-KT'}


def get_cik(ticker):
    resp = requests.get(
        'https://www.sec.gov/files/company_tickers.json', headers=HEADERS, timeout=20)
    data = resp.json()
    for v in data.values():
        if v.get('ticker', '').upper() == ticker.upper():
            return str(v['cik_str']).zfill(10), v.get('title', '')
    return None, None


def get_facts(cik):
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code} fetching {url}")
        return {}
    return resp.json()


def find_annual_values(facts, concept, years=None):
    """Extract annual values - verbose version showing what filters are hitting"""
    us_gaap = facts.get('us-gaap', {})
    data = us_gaap.get(concept)
    if not data:
        return None, "concept not in us-gaap"

    all_entries = []
    for unit_key, unit_entries in data.get('units', {}).items():
        for entry in unit_entries:
            form = entry.get('form', '')
            fp = entry.get('fp', '')
            end = entry.get('end', '')
            val = entry.get('val')
            all_entries.append(
                {'form': form, 'fp': fp, 'end': end, 'val': val, 'unit': unit_key})

    # Filter to 10-K
    k10 = [e for e in all_entries if e['form'] in EDGAR_10K_FORMS]
    if not k10:
        return None, f"no 10-K entries (total {len(all_entries)} entries across all forms)"

    # Filter to annual (FY or Q4)
    annual = [e for e in k10 if e['fp'] in ('FY', 'Q4', '')]

    results = {}
    for e in annual:
        end = e['end']
        if end and len(end) >= 10:
            yr = int(end[:4])
            m = int(end[5:7])
            d = int(end[8:10])
            if m == 1 and d <= 10:
                yr -= 1
        else:
            continue
        if years and yr not in years:
            continue
        results[yr] = e['val']

    if not results and k10:
        # Show some sample entries to understand why
        samples = [(e['form'], e['fp'], e['end'], e['val']) for e in k10[:5]]
        return None, f"{len(k10)} 10-K entries but none matched years filter. Samples: {samples}"

    return results, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Check each ticker
# ─────────────────────────────────────────────────────────────────────────────
checks = [
    ('V',    'Visa',          ['EarningsPerShareDiluted',
     'EarningsPerShareBasic'], [2020, 2021, 2022, 2023]),
    ('ETN',  'Eaton',         ['Revenues', 'SalesRevenueNet',
     'SalesRevenueGoodsNet'], [2012, 2013, 2014, 2015]),
    ('NEE',  'Nextera',       ['Revenues', 'ElectricUtilityRevenue',
     'RegulatedAndUnregulatedOperatingRevenue'], [2013, 2014, 2015]),
    ('PLD',  'Prologis',      ['Revenues', 'RealEstateRevenueNet',
     'OperatingLeasesIncomeStatementLeaseRevenue', 'LeaseIncome'], [2012, 2013, 2014]),
    ('COP',  'ConocoPhillips', ['OperatingIncomeLoss'], [2012, 2013, 2014]),
    ('CB',   'Chubb',         ['OperatingIncomeLoss'], [2012, 2013, 2014]),
    ('DIS',  'Disney',        ['Assets', 'Liabilities',
     'StockholdersEquity'], [2016, 2017, 2018]),
    ('WELL', 'Welltower',     ['OperatingIncomeLoss'], [2024, 2025]),
]

for ticker, name, concepts, years in checks:
    cik, title = get_cik(ticker)
    print(f"\n{'='*60}")
    print(f"{name} ({ticker}) — CIK: {cik} — {title}")
    print(f"{'='*60}")
    if not cik:
        print("  NOT FOUND in EDGAR ticker map!")
        continue
    facts = get_facts(cik)
    if not facts:
        continue

    us_gaap_keys = list(facts.get('us-gaap', {}).keys())
    print(f"  Total us-gaap concepts: {len(us_gaap_keys)}")
    print(f"  DEI concepts: {list(facts.get('dei', {}).keys())[:5]}")

    for concept in concepts:
        result, status = find_annual_values(facts, concept, years)
        if result:
            print(f"  ✅ {concept}: {dict(sorted(result.items()))}")
        else:
            print(f"  ❌ {concept}: {status}")

    # For Visa - also show what EPS concepts exist at all
    if ticker == 'V':
        eps_concepts = [
            k for k in us_gaap_keys if 'EarningsPerShare' in k or 'PerShare' in k]
        print(f"  EPS-like concepts available: {eps_concepts[:10]}")

    # For Eaton revenue - show ALL revenue-like concepts
    if ticker == 'ETN':
        rev_concepts = [
            k for k in us_gaap_keys if 'Revenue' in k or 'Sales' in k or 'NetSales' in k]
        print(f"  Revenue-like concepts available: {rev_concepts[:15]}")
        # Also check fiscal year structure
        assets_result, _ = find_annual_values(
            facts, 'Assets', [2010, 2011, 2012, 2013, 2014, 2015, 2016])
        print(f"  Assets (to verify CIK/FY structure): {assets_result}")

    if ticker == 'NEE':
        rev_concepts = [
            k for k in us_gaap_keys if 'Revenue' in k or 'Sales' in k or 'Operating' in k]
        print(f"  Revenue-like concepts available: {rev_concepts[:15]}")

    if ticker == 'PLD':
        rev_concepts = [
            k for k in us_gaap_keys if 'Revenue' in k or 'Sales' in k or 'Lease' in k or 'Rental' in k]
        print(f"  Revenue-like concepts available: {rev_concepts[:15]}")
        opex_concepts = [
            k for k in us_gaap_keys if 'Expense' in k or 'Cost' in k]
        print(f"  Opex-like concepts: {opex_concepts[:10]}")

    if ticker == 'COP':
        inc_concepts = [
            k for k in us_gaap_keys if 'IncomeLoss' in k or 'OperatingIncome' in k]
        print(f"  Income-like concepts: {inc_concepts[:10]}")

    if ticker == 'CB':
        inc_concepts = [k for k in us_gaap_keys if 'Income' in k]
        print(f"  Income-like concepts: {inc_concepts[:15]}")

    if ticker == 'WELL':
        inc_concepts = [
            k for k in us_gaap_keys if 'Income' in k or 'Operating' in k]
        print(f"  Income/operating concepts: {inc_concepts[:15]}")
