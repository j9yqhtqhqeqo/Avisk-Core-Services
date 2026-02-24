"""
diagnose3.py - investigate missing XBRL tags for each company
"""
import requests
import time

H = {'User-Agent': 'Avisk Research contact@avisk.com', 'Accept': 'application/json'}
K10 = {'10-K', '10-K405', '10-KSB', '10-KT'}


def gf(cik):
    r = requests.get(
        f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', headers=H, timeout=30)
    return r.json().get('facts', {})


def all_entries(facts, concept):
    usg = facts.get('us-gaap', {})
    d = usg.get(concept, {})
    return [e for entries in d.get('units', {}).values() for e in entries]


def k10_fy(facts, concept):
    """Annual 10-K entries only"""
    return [e for e in all_entries(facts, concept)
            if e.get('form') in K10 and e.get('fp') in ('FY', 'Q4', '')]


def show(facts, concept, years=None):
    es = k10_fy(facts, concept)
    if not es:
        all_e = all_entries(facts, concept)
        combos = sorted(set((e.get('form', '?'), e.get('fp', '?'))
                        for e in all_e))
        print(
            f'  ❌ {concept}: 0 annual 10-K entries (total={len(all_e)}, form/fp combos={combos[:5]})')
        return
    results = {}
    for e in es:
        end = e.get('end', '')
        if len(end) >= 10:
            yr = int(end[:4])
            m = int(end[5:7])
            d2 = int(end[8:10])
            if m == 1 and d2 <= 10:
                yr -= 1
        else:
            continue
        if years and yr not in years:
            continue
        results[yr] = e.get('val')
    filtered = {k: v for k, v in results.items() if v is not None}
    if filtered:
        print(f'  ✅ {concept}: {dict(sorted(filtered.items()))}')
    else:
        print(f'  ❌ {concept}: entries exist but years {years} not found')


# ─────────────────────────────────────────────────────────────────────────────
# VISA - EPS
# ─────────────────────────────────────────────────────────────────────────────
print('='*60, '\nVISA EPS')
facts = gf('0001403161')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')

# All EPS-like concepts
eps = [k for k in usg if 'PerShare' in k or 'EarningsPer' in k]
print(f'  EPS-like concepts: {eps}')

for c in ['EarningsPerShareDiluted', 'EarningsPerShareBasic']:
    all_e = all_entries(facts, c)
    combos = sorted(set((e.get('form', '?'), e.get('fp', '?')) for e in all_e))
    print(f'  {c}: total={len(all_e)}, form/fp={combos[:8]}')
    if all_e:
        print(f'    sample: {all_e[:3]}')

# Check Visa FY end dates
ni_es = k10_fy(facts, 'NetIncomeLoss')
fye = sorted(set(e.get('end', '') for e in ni_es))
print(f'  Visa FY end dates (from NetIncomeLoss 10-K): {fye}')

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# EATON - revenue 2012-2015
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nEATON revenue 2012-2015')
facts = gf('0001551182')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
rev_concepts = sorted([k for k in usg if 'Revenue' in k or 'Sales' in k])
print(f'  Revenue/Sales concepts: {rev_concepts[:15]}')
years_e = [2012, 2013, 2014, 2015, 2016]
for c in ['Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet',
          'RevenueFromContractWithCustomerExcludingAssessedTax', 'NetSales']:
    show(facts, c, years_e)

# Verify CIK is right by checking what years Assets has data
assets_es = k10_fy(facts, 'Assets')
assets_yrs = sorted(set(int(e['end'][:4])
                    for e in assets_es if e.get('end') and len(e['end']) >= 4))
print(f'  Assets years available: {assets_yrs}')

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# NEXTERA - revenue 2013-2017
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nNEXTERA revenue 2013-2017')
facts = gf('0000753308')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
rev_concepts = sorted([k for k in usg if 'Revenue' in k or 'Operating' in k])
print(f'  Revenue-like concepts: {rev_concepts[:15]}')
years_n = [2013, 2014, 2015, 2016, 2017, 2018]
for c in ['Revenues', 'ElectricUtilityRevenue', 'RegulatedAndUnregulatedOperatingRevenue',
          'OperatingRevenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
          'RevenuesNetOfInterestExpense']:
    show(facts, c, years_n)

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# PROLOGIS - revenue 2012-2015 and opex 2019-2021
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nPROLOGIS')
facts = gf('0001045609')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
rev_concepts = sorted(
    [k for k in usg if 'Revenue' in k or 'Lease' in k or 'Rental' in k])
print(f'  Revenue/Lease concepts: {rev_concepts[:15]}')
opex_concepts = sorted([k for k in usg if 'Expense' in k or 'Cost' in k])
print(f'  Expense/Cost concepts: {opex_concepts[:10]}')
yrs_p = [2012, 2013, 2014, 2015, 2016, 2019, 2020, 2021, 2022]
for c in ['Revenues', 'RealEstateRevenueNet', 'LeaseIncome',
          'OperatingLeasesIncomeStatementLeaseRevenue', 'RentalRevenue',
          'OperatingExpenses', 'CostsAndExpenses', 'OperatingCostsAndExpenses']:
    show(facts, c, yrs_p)

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# CONOCOPHILLIPS EBITDA 2012-2014
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nCONOCOPHILLIPS EBITDA 2012-2014')
facts = gf('0001163165')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
inc_concepts = sorted(
    [k for k in usg if 'IncomeLoss' in k or 'OperatingIncome' in k])
print(f'  Income concepts: {inc_concepts[:10]}')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments']:
    show(facts, c, [2012, 2013, 2014, 2015])

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# CHUBB EBITDA 2012-2013
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nCHUBB EBITDA 2012-2013')
facts = gf('0000896159')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
inc_concepts = sorted(
    [k for k in usg if 'Income' in k and ('Loss' in k or 'Operating' in k)])
print(f'  Income concepts: {inc_concepts[:15]}')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
    show(facts, c, [2012, 2013, 2014, 2015])

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# DISNEY assets 2017
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nDISNEY assets/liabilities/equity 2017')
facts = gf('0001744489')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
assets_yrs = sorted(set(int(e['end'][:4]) for e in k10_fy(
    facts, 'Assets') if e.get('end') and len(e['end']) >= 4))
print(f'  Assets years: {assets_yrs}')
for c in ['Assets', 'Liabilities', 'StockholdersEquity',
          'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']:
    show(facts, c, [2016, 2017, 2018, 2019])

time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# WELLTOWER EBITDA 2025
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60, '\nWELLTOWER EBITDA 2025')
facts = gf('0000766704')
usg = facts.get('us-gaap', {})
print(f'  us-gaap concepts: {len(usg)}')
inc = sorted([k for k in usg if 'IncomeLoss' in k or 'OperatingIncome' in k])
print(f'  Income concepts: {inc[:10]}')
for c in ['OperatingIncomeLoss',
          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
    show(facts, c, [2023, 2024, 2025])
