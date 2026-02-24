"""
diagnose_visa_eps.py - Check Visa EPS and then key others one at a time
"""
import requests
import time
import sys

HEADERS = {'User-Agent': 'Avisk Research contact@avisk.com',
           'Accept': 'application/json'}
EDGAR_10K_FORMS = {'10-K', '10-K405', '10-KSB', '10-KT'}


def get(url, retries=3, delay=2):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code} for {url}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(delay * (i + 1))
    return None


def cik_for(ticker):
    data = get('https://www.sec.gov/files/company_tickers.json')
    if not data:
        return None, None
    for v in data.values():
        if v.get('ticker', '').upper() == ticker.upper():
            return str(v['cik_str']).zfill(10), v.get('title', '')
    return None, None


def check(ticker, concepts, years=None):
    cik, title = cik_for(ticker)
    if not cik:
        print(f"  {ticker}: NOT FOUND")
        return
    print(f"\n{ticker} ({title}) CIK={cik}")
    time.sleep(0.5)
    facts = get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json')
    if not facts:
        print(f"  ERROR loading facts")
        return

    us_gaap = facts.get('us-gaap', {})
    print(f"  us-gaap concepts: {len(us_gaap)}")

    for concept in concepts:
        data = us_gaap.get(concept)
        if not data:
            print(f"  ❌ {concept}: NOT IN us-gaap")
            continue
        # Show ALL annual 10-K entries regardless of fp/frame
        results = {}
        for unit_key, unit_entries in data.get('units', {}).items():
            for e in unit_entries:
                if e.get('form') not in EDGAR_10K_FORMS:
                    continue
                end = e.get('end', '')
                fp = e.get('fp', '')
                val = e.get('val')
                if end and len(end) >= 4:
                    yr = int(end[:4])
                    if len(end) >= 10:
                        m = int(end[5:7])
                        d = int(end[8:10])
                        if m == 1 and d <= 10:
                            yr -= 1
                    if not years or yr in years:
                        results[f"{yr}({fp})"] = val
        if results:
            print(f"  ✅ {concept}: {dict(sorted(results.items()))}")
        else:
            print(
                f"  ❌ {concept}: concept EXISTS but no 10-K annual entries for years={years}")

# ── Run targeted checks ────────────────────────────────────────────────────────


# 1. Visa - why is EPS always None?
check('V', ['EarningsPerShareDiluted', 'EarningsPerShareBasic',
            'EarningsPerShareBasicAndDiluted',
            'IncomeLossFromContinuingOperationsPerDilutedShare'],
      years=list(range(2012, 2026)))

# What EPS concepts does Visa actually have?
cik, _ = cik_for('V')
time.sleep(0.5)
facts = get(
    f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json') if cik else None
if facts:
    us_gaap = facts.get('us-gaap', {})
    eps = [k for k in us_gaap if 'PerShare' in k or 'EarningsPer' in k]
    print(f"\nVisa EPS-like concepts: {eps}")

time.sleep(1)

# 2. Eaton - revenue 2012-2015
check('ETN', ['Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet',
              'RevenueFromContractWithCustomerExcludingAssessedTax',
              'SalesRevenueNetOfInterestExpense', 'NetSales'],
      years=[2011, 2012, 2013, 2014, 2015, 2016])
cik, _ = cik_for('ETN')
time.sleep(0.5)
facts2 = get(
    f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json') if cik else None
if facts2:
    us_gaap2 = facts2.get('us-gaap', {})
    rev = [k for k in us_gaap2 if 'Revenue' in k or 'Sales' in k]
    print(f"\nEaton Revenue-like concepts: {rev}")
    # Also check what years Assets shows - to verify the CIK is right
    assets = {k for k in us_gaap2 if k == 'Assets'}
    print(f"Assets in ETN us-gaap: {assets}")

time.sleep(1)

# 3. Nextera revenue 2013-2017
check('NEE', ['Revenues', 'ElectricUtilityRevenue',
              'RegulatedAndUnregulatedOperatingRevenue', 'OperatingRevenues',
              'RevenueFromContractWithCustomerExcludingAssessedTax'],
      years=[2012, 2013, 2014, 2015, 2016, 2017, 2018])

time.sleep(1)

# 4. Prologis revenue 2012-2015
check('PLD', ['Revenues', 'RealEstateRevenueNet',
              'OperatingLeasesIncomeStatementLeaseRevenue', 'LeaseIncome',
              'RevenueFromContractWithCustomerExcludingAssessedTax',
              'RentalPropertiesRevenues', 'RentalRevenue'],
      years=[2011, 2012, 2013, 2014, 2015, 2016, 2019, 2020, 2021])

time.sleep(1)

# 5. ConocoPhillips EBITDA 2012-2014
check('COP', ['OperatingIncomeLoss',
              'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'],
      years=[2012, 2013, 2014, 2015])

time.sleep(1)

# 6. Chubb EBITDA 2012-2013
check('CB', ['OperatingIncomeLoss',
             'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'],
      years=[2012, 2013, 2014])

time.sleep(1)

# 7. Disney assets/liabilities 2017
check('DIS', ['Assets', 'Liabilities', 'StockholdersEquity',
              'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
      years=[2016, 2017, 2018])

time.sleep(1)

# 8. Welltower EBITDA 2025
check('WELL', ['OperatingIncomeLoss'], years=[2023, 2024, 2025])
