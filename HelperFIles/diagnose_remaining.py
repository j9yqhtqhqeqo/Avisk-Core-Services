#!/usr/bin/env python3
"""
diagnose_remaining.py
Investigate all remaining missing-field companies to determine:
 - Current EDGAR CIK
 - Whether legacy CIK exists (reincorporations/mergers)
 - What years of 10-K data are available
 - Which specific XBRL concepts cover the missing fields
"""
import requests
import sys
import os
import time
import json
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')


HEADERS = {
    'User-Agent': 'Avisk Research contact@avisk.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'data.sec.gov',
}
FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'

# Known old/legacy CIKs to check
LEGACY_CIKS = {
    # Broadcom Corp (pre-Avago merger 2016)
    'BRCM_OLD': 1054374,
    # Praxair (merged with Linde AG → Linde plc 2018)
    'PX':       884905,
    # Medtronic Inc (reincorporated as Medtronic PLC 2015)
    'MDT_OLD':  310764,
    # General Electric (GE Vernova parent)
    'GE':       40533,
}


def get_facts(cik: int) -> dict:
    url = FACTS_URL.format(cik=cik)
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        return r.json().get('facts', {})
    return {}


def get_10k_years(facts: dict, concept: str, namespace: str = 'us-gaap') -> list:
    """Return sorted list of fiscal years that have 10-K data for a concept."""
    ns = facts.get(namespace, {})
    cd = ns.get(concept, {})
    years = set()
    for entry in cd.get('units', {}).get('USD', []):
        if entry.get('form', '') in ('10-K', '10-K405', '10-KSB', '10-KT'):
            fp = entry.get('fp', '')
            frame = entry.get('frame', '')
            if fp == 'FY' or frame.startswith('CY'):
                end = entry.get('end', '')
                if end:
                    years.add(int(end[:4]))
    return sorted(years)


def check_eps_concepts(facts: dict, years: list, symbol: str):
    """Check what EPS concepts are available."""
    eps_concepts = [
        'EarningsPerShareDiluted', 'EarningsPerShareBasic',
        'EarningsPerShareBasicAndDiluted',
    ]
    us_gaap = facts.get('us-gaap', {})
    for c in eps_concepts:
        yrs = get_10k_years(facts, c)
        if yrs:
            print(f"  EPS concept {c}: {yrs}")


# ─── 1. Look up current CIKs ─────────────────────────────────────────────────
print("=" * 70)
print("STEP 1: Current EDGAR CIK lookup")
print("=" * 70)
r = requests.get(TICKERS_URL, headers={
                 **HEADERS, 'Host': 'www.sec.gov'}, timeout=30)
ticker_map = {v['ticker'].upper(): (v['cik_str'], v['title'])
              for v in r.json().values()}

targets = ['AVGO', 'BLK', 'GEV', 'LIN', 'MDT', 'GOOG', 'GOOGL',
           'PANW', 'ANET', 'V', 'UBER', 'CRWD', 'PLTR', 'PLD']
current_ciks = {}
for t in targets:
    if t in ticker_map:
        cik, title = ticker_map[t]
        current_ciks[t] = int(cik)
        print(f"  {t:8s}  CIK={int(cik):10d}  {title}")
    else:
        print(f"  {t:8s}  NOT FOUND in EDGAR tickers")

# ─── 2. Check legacy CIK 10-K year ranges ────────────────────────────────────
print()
print("=" * 70)
print("STEP 2: Legacy CIK 10-K year coverage (Revenues concept)")
print("=" * 70)
revenue_concepts = [
    'Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']
for name, cik in LEGACY_CIKS.items():
    facts = get_facts(cik)
    years = []
    for c in revenue_concepts:
        y = get_10k_years(facts, c)
        if y:
            years = y
            print(f"  {name} (CIK {cik}): {c} → {y}")
            break
    if not years:
        print(f"  {name} (CIK {cik}): no revenue data found")
    time.sleep(0.5)

# ─── 3. Specific problem diagnostics ─────────────────────────────────────────
print()
print("=" * 70)
print("STEP 3: Problem-specific diagnostics")
print("=" * 70)

# 3a. BlackRock 2021 — all fields missing
print()
print("--- BlackRock (BLK) ---")
blk_cik = current_ciks.get('BLK', 1364742)
blk_facts = get_facts(blk_cik)
time.sleep(0.5)
for c in ['InvestmentAdvisoryFees', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'RevenueFromContractWithCustomerIncludingAssessedTax']:
    yrs = get_10k_years(blk_facts, c)
    if yrs:
        print(f"  {c}: {yrs}")
# Check assets
asset_yrs = get_10k_years(blk_facts, 'Assets')
print(f"  Assets: {asset_yrs}")
net_inc = get_10k_years(blk_facts, 'NetIncomeLoss')
print(f"  NetIncomeLoss: {net_inc}")

# 3b. Broadcom AVGO — check new CIK 10-K years and old Broadcom Corp
print()
print("--- Broadcom (AVGO) current CIK ---")
avgo_cik = current_ciks.get('AVGO', 1730168)
avgo_facts = get_facts(avgo_cik)
time.sleep(0.5)
rev_yrs = []
for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']:
    y = get_10k_years(avgo_facts, c)
    if y:
        print(f"  {c}: {y}")
        if not rev_yrs:
            rev_yrs = y
asset_yrs = get_10k_years(avgo_facts, 'Assets')
print(f"  Assets: {asset_yrs}")
print(f"  → Broadcom Corp (CIK {LEGACY_CIKS['BRCM_OLD']}):")
brcm_facts = get_facts(LEGACY_CIKS['BRCM_OLD'])
time.sleep(0.5)
for c in ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
    y = get_10k_years(brcm_facts, c)
    if y:
        print(f"    {c}: {y}")
print(f"    Assets: {get_10k_years(brcm_facts, 'Assets')}")

# 3c. GE Vernova
print()
print("--- GE Vernova (GEV) ---")
gev_cik = current_ciks.get('GEV')
if gev_cik:
    gev_facts = get_facts(gev_cik)
    time.sleep(0.5)
    for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
        y = get_10k_years(gev_facts, c)
        if y:
            print(f"  GEV CIK {gev_cik} - {c}: {y}")
    print(f"  GEV Assets: {get_10k_years(gev_facts, 'Assets')}")

    # Check GE parent
    print(f"  → GE (CIK {LEGACY_CIKS['GE']}) revenue years:")
    ge_facts = get_facts(LEGACY_CIKS['GE'])
    time.sleep(0.5)
    for c in ['Revenues', 'SalesRevenueNet']:
        y = get_10k_years(ge_facts, c)
        if y:
            print(f"    GE {c}: {y}")

# 3d. Linde plc
print()
print("--- Linde plc (LIN) ---")
lin_cik = current_ciks.get('LIN', 1707092)
lin_facts = get_facts(lin_cik)
time.sleep(0.5)
for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']:
    y = get_10k_years(lin_facts, c)
    if y:
        print(f"  Linde plc CIK {lin_cik} - {c}: {y}")
print(f"  Linde plc Assets: {get_10k_years(lin_facts, 'Assets')}")
print(f"  → Praxair (CIK {LEGACY_CIKS['PX']}):")
px_facts = get_facts(LEGACY_CIKS['PX'])
time.sleep(0.5)
for c in ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
    y = get_10k_years(px_facts, c)
    if y:
        print(f"    Praxair {c}: {y}")
print(f"    Praxair Assets: {get_10k_years(px_facts, 'Assets')}")

# 3e. Medtronic PLC
print()
print("--- Medtronic PLC (MDT) ---")
mdt_cik = current_ciks.get('MDT', 1613103)
mdt_facts = get_facts(mdt_cik)
time.sleep(0.5)
for c in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'NetRevenues']:
    y = get_10k_years(mdt_facts, c)
    if y:
        print(f"  Medtronic PLC CIK {mdt_cik} - {c}: {y}")
print(f"  Medtronic PLC Assets: {get_10k_years(mdt_facts, 'Assets')}")
print(f"  → Medtronic Inc (CIK {LEGACY_CIKS['MDT_OLD']}):")
mdt_old_facts = get_facts(LEGACY_CIKS['MDT_OLD'])
time.sleep(0.5)
for c in ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'NetRevenues']:
    y = get_10k_years(mdt_old_facts, c)
    if y:
        print(f"    MDT old {c}: {y}")
print(f"    MDT old Assets: {get_10k_years(mdt_old_facts, 'Assets')}")

# 3f. Alphabet Class C 2015 EPS
print()
print("--- Alphabet Class C (GOOG) 2015 EPS ---")
goog_cik = current_ciks.get('GOOG', 1652044)
goog_facts = get_facts(goog_cik)
time.sleep(0.5)
check_eps_concepts(goog_facts, [2015], 'GOOG')
# Also check Google original CIK
google_facts = get_facts(1288776)
time.sleep(0.5)
print("  Google original CIK 1288776:")
check_eps_concepts(google_facts, [2015], 'GOOGL_old')

# 3g. Palo Alto Networks 2012 EPS
print()
print("--- Palo Alto Networks (PANW) 2012 EPS ---")
panw_cik = current_ciks.get('PANW', 1327567)
panw_facts = get_facts(panw_cik)
time.sleep(0.5)
check_eps_concepts(panw_facts, [2012], 'PANW')
asset_yrs = get_10k_years(panw_facts, 'Assets')
print(f"  PANW Assets years: {asset_yrs}")
net_inc_yrs = get_10k_years(panw_facts, 'NetIncomeLoss')
print(f"  PANW NetIncomeLoss years: {net_inc_yrs}")
# Check shares
for sc in ['CommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic', 'WeightedAverageNumberOfDilutedSharesOutstanding']:
    yrs = get_10k_years(panw_facts, sc, 'us-gaap')
    if yrs:
        print(f"  PANW shares {sc}: {yrs}")

# 3h. Prologis operating_expenses 2019-2021
print()
print("--- Prologis (PLD) operating_expenses 2019-2021 ---")
pld_cik = current_ciks.get('PLD', 1045609)
pld_facts = get_facts(pld_cik)
time.sleep(0.5)
opex_concepts = ['OperatingExpenses', 'CostsAndExpenses', 'OperatingCostsAndExpenses',
                 'RealEstateExpense', 'GeneralAndAdministrativeExpense']
for c in opex_concepts:
    us_gaap = pld_facts.get('us-gaap', {})
    cd = us_gaap.get(c, {})
    entries_by_year = {}
    for entry in cd.get('units', {}).get('USD', []):
        if entry.get('form', '') in ('10-K', '10-K405') and entry.get('fp') == 'FY':
            yr = int(entry.get('end', '0000')[:4])
            if yr in [2019, 2020, 2021, 2022]:
                entries_by_year[yr] = entry.get('val')
    if entries_by_year:
        print(f"  PLD {c}: {entries_by_year}")

# 3i. Visa 2012-2014 EPS — check shares availability
print()
print("--- Visa (V) 2012-2014 EPS / Shares ---")
v_cik = current_ciks.get('V', 1403161)
v_facts = get_facts(v_cik)
time.sleep(0.5)
check_eps_concepts(v_facts, [2012, 2013, 2014], 'V')
for sc in ['CommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic',
           'WeightedAverageNumberOfDilutedSharesOutstanding']:
    us_gaap = v_facts.get('us-gaap', {})
    cd = us_gaap.get(sc, {})
    entries = []
    for entry in cd.get('units', {}).get('shares', []):
        if entry.get('form', '') in ('10-K', '10-K405') and entry.get('fp') == 'FY':
            yr = int(entry.get('end', '0000')[:4])
            if yr <= 2015:
                entries.append((yr, entry.get('val')))
    if entries:
        print(f"  Visa {sc} (early years): {sorted(entries)}")
# Check DEI shares for early years
dei = v_facts.get('dei', {})
dei_cd = dei.get('EntityCommonStockSharesOutstanding', {})
dei_early = []
for entry in dei_cd.get('units', {}).get('shares', []):
    if entry.get('form', '') in ('10-K', '10-K405'):
        date = entry.get('instant') or entry.get('end', '')
        yr = int(date[:4]) if date else 0
        if yr <= 2016:
            dei_early.append((date, entry.get('val')))
print(f"  Visa DEI shares (early): {sorted(dei_early)}")

# 3j. Uber 2018 EPS
print()
print("--- Uber (UBER) 2018 EPS ---")
uber_cik = current_ciks.get('UBER', 1543151)
uber_facts = get_facts(uber_cik)
time.sleep(0.5)
asset_yrs = get_10k_years(uber_facts, 'Assets')
print(f"  UBER Assets years: {asset_yrs}")
check_eps_concepts(uber_facts, [2018], 'UBER')
ni_yrs = get_10k_years(uber_facts, 'NetIncomeLoss')
print(f"  UBER NetIncomeLoss: {ni_yrs}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
