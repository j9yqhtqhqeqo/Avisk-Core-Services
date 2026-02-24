"""
diagnose_missing_fields.py
Investigate why specific fields are missing for specific companies/years.
"""
import requests
import sys
import json
import re

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept': 'application/json'}
EDGAR_10K_FORMS = {'10-K', '10-K405', '10-KSB', '10-KT'}


def get_cik(ticker):
    resp = requests.get(
        'https://www.sec.gov/files/company_tickers.json', headers=HEADERS, timeout=20)
    data = resp.json()
    for v in data.values():
        if v.get('ticker', '').upper() == ticker.upper():
            return str(v['cik_str']).zfill(10)
    return None


def get_facts(cik):
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def check_concept(facts, concept, years=None):
    us_gaap = facts.get('us-gaap', {})
    data = us_gaap.get(concept)
    if not data:
        return None
    results = {}
    for unit_entries in data.get('units', {}).values():
        for entry in unit_entries:
            if entry.get('form') not in EDGAR_10K_FORMS:
                continue
            fp = entry.get('fp', '')
            if fp and fp not in ('FY', 'Q4'):
                continue
            end = entry.get('end', '')
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
            results[yr] = entry.get('val')
    return results


def list_eps_concepts(facts, years=None):
    """List ALL EPS-related concepts in the facts"""
    us_gaap = facts.get('us-gaap', {})
    eps_concepts = {k: v for k, v in us_gaap.items()
                    if 'EarningsPerShare' in k or 'PerShare' in k or 'PerDiluted' in k or 'PerBasic' in k}
    for concept, data in sorted(eps_concepts.items()):
        yr_data = {}
        for unit_entries in data.get('units', {}).values():
            for entry in unit_entries:
                if entry.get('form') not in EDGAR_10K_FORMS:
                    continue
                fp = entry.get('fp', '')
                if fp and fp not in ('FY', 'Q4'):
                    continue
                end = entry.get('end', '')
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
                yr_data[yr] = entry.get('val')
        if yr_data:
            print(f"  {concept}: {dict(sorted(yr_data.items()))}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. VISA EPS - all years missing
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("1. VISA EPS investigation")
print("=" * 60)
cik = get_cik('V')
print(f"Visa CIK: {cik}")
facts = get_facts(cik)
print("All EPS-related concepts in Visa XBRL:")
list_eps_concepts(facts, years=list(range(2012, 2026)))
print()

# Check standard EPS concepts
for concept in ['EarningsPerShareDiluted', 'EarningsPerShareBasic', 'EarningsPerShareBasicAndDiluted']:
    result = check_concept(facts, concept, years=list(range(2012, 2026)))
    print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 2. EATON revenue 2012-2015
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("2. EATON revenue 2012-2015")
print("=" * 60)
cik = get_cik('ETN')
print(f"Eaton CIK: {cik}")
facts = get_facts(cik)
years = [2012, 2013, 2014, 2015, 2016]
for concept in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                'SalesRevenueNet', 'SalesRevenueGoodsNet', 'SalesRevenueNetOfInterestExpense',
                'RevenueFromContractWithCustomerIncludingAssessedTax',
                'NetSales']:
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 3. NEXTERA revenue 2013-2017
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("3. NEXTERA revenue 2013-2017")
print("=" * 60)
cik = get_cik('NEE')
print(f"Nextera CIK: {cik}")
facts = get_facts(cik)
years = [2013, 2014, 2015, 2016, 2017, 2018]
for concept in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                'ElectricUtilityRevenue', 'RegulatedAndUnregulatedOperatingRevenue',
                'OperatingRevenue', 'SalesRevenueNet', 'RevenuesNetOfInterestExpense',
                'UtilityRevenue']:
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 4. PROLOGIS revenue 2012-2015 and opex 2019-2021
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("4. PROLOGIS revenue 2012-2015 and opex 2019-2021")
print("=" * 60)
cik = get_cik('PLD')
print(f"Prologis CIK: {cik}")
facts = get_facts(cik)
years = [2012, 2013, 2014, 2015, 2016, 2019, 2020, 2021, 2022]
for concept in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                'RealEstateRevenueNet', 'OperatingLeasesIncomeStatementLeaseRevenue',
                'SalesRevenueNet', 'LeaseIncome', 'RentalIncome', 'RentalRevenue',
                'OperatingExpenses', 'CostsAndExpenses', 'RealEstateExpenses',
                'OperatingCostsAndExpenses']:
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 5. CONOCOPHILLIPS EBITDA 2012-2014
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("5. CONOCOPHILLIPS EBITDA 2012-2014")
print("=" * 60)
cik = get_cik('COP')
print(f"ConocoPhillips CIK: {cik}")
facts = get_facts(cik)
years = [2012, 2013, 2014, 2015]
us_gaap = facts.get('us-gaap', {})
# Search for income/operating concepts
income_concepts = {k: v for k, v in us_gaap.items()
                   if any(x in k for x in ['OperatingIncome', 'IncomeLoss', 'EBITDA', 'IncomeBeforeTax'])}
for concept in sorted(income_concepts.keys()):
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 6. CHUBB EBITDA 2012-2013
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("6. CHUBB EBITDA 2012-2013")
print("=" * 60)
cik = get_cik('CB')
print(f"Chubb CIK: {cik}")
facts = get_facts(cik)
years = [2012, 2013, 2014]
us_gaap = facts.get('us-gaap', {})
income_concepts = {k: v for k, v in us_gaap.items()
                   if any(x in k for x in ['OperatingIncome', 'IncomeLoss', 'Income', 'Underwriting'])}
for concept in sorted(income_concepts.keys()):
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 7. WALT DISNEY assets/liabilities/equity 2017
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("7. WALT DISNEY assets/liabilities/equity 2017")
print("=" * 60)
cik = get_cik('DIS')
print(f"Disney CIK: {cik}")
facts = get_facts(cik)
years = [2016, 2017, 2018]
for concept in ['Assets', 'Liabilities', 'StockholdersEquity',
                'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']:
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# 8. WELLTOWER EBITDA 2025
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("8. WELLTOWER EBITDA 2025")
print("=" * 60)
cik = get_cik('WELL')
print(f"Welltower CIK: {cik}")
facts = get_facts(cik)
years = [2023, 2024, 2025]
us_gaap = facts.get('us-gaap', {})
income_concepts = {k: v for k, v in us_gaap.items()
                   if any(x in k for x in ['OperatingIncome', 'IncomeLoss', 'Income'])}
for concept in sorted(income_concepts.keys()):
    result = check_concept(facts, concept, years=years)
    if result:
        print(f"  {concept}: {result}")
