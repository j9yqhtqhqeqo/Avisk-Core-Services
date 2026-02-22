"""
Comprehensive diagnostic for all new zero-value companies.
"""
from Services.FinancialDataScraper import _get_headers, EDGAR_10K_FORMS, cik_for_symbol
import requests
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


HEADERS_DATA = {**_get_headers(), 'Host': 'data.sec.gov'}

TARGETS = {
    'AMD':   ('Advanced Micro Devices Inc',    {'operating_expenses': list(range(2012, 2016))}),
    'GOOGL': ('Alphabet Inc Class C',          {'assets': [2012, 2013], 'liabilities': [2012, 2013],
                                                'eps': [2015], 'revenue': [2012], 'net_income': [2012],
                                                'cash_flow_operations': [2012], 'cash_flow_investing': [2012],
                                                'cash_flow_financing': [2012], 'operating_expenses': [2012],
                                                'operating_income_ebitda': [2012]}),
    'AXP':   ('American Express Company',      {'revenue': [2012, 2013, 2014],
                                                'operating_income_ebitda': list(range(2012, 2019))}),
    'CVX':   ('Chevron Corp',                  {'operating_income_ebitda': list(range(2012, 2025))}),
    'C':     ('Citigroup Inc',                 {'operating_income_ebitda': [2012, 2013]}),
    'COST':  ('Costco Wholesale Corp',         {'operating_expenses': list(range(2012, 2016))}),
    'LLY':   ('Eli Lilly and Company',         {'operating_expenses': [2012]}),
    'IBM':   ('International Business Machines', {'operating_expenses': list(range(2012, 2025))}),
    'JNJ':   ('Johnson & Johnson',             {'operating_expenses': list(range(2012, 2017)),
                                                'operating_income_ebitda': list(range(2015, 2019)),
                                                'assets': [2015], 'liabilities': [2015], 'equity': [2015],
                                                'cash_flow_operations': [2015], 'cash_flow_investing': [2015],
                                                'cash_flow_financing': [2015]}),
    'KLAC':  ('KLA-Tencor Corporation',        {'operating_expenses': list(range(2015, 2026)),
                                                'operating_income_ebitda': list(range(2015, 2020))}),
    'LIN':   ('Linde plc Ordinary Shares',     {'operating_expenses': list(range(2015, 2025)),
                                                'operating_income_ebitda': [2015],
                                                'assets': [2015, 2016], 'liabilities': [2015, 2016],
                                                'revenue': [2015], 'net_income': [2015], 'eps': [2015],
                                                'cash_flow_operations': [2015], 'cash_flow_investing': [2015],
                                                'cash_flow_financing': [2015]}),
    'MA':    ('Mastercard Inc',                {'assets': [2017], 'liabilities': [2017]}),
    'MRK':   ('Merck & Company Inc',           {'operating_expenses': list(range(2012, 2016))}),
    'NFLX':  ('Netflix Inc',                   {'operating_expenses': list(range(2012, 2026))}),
    'PLTR':  ('Palantir Technologies',         {'revenue': [2017, 2018], 'assets': [2017, 2018],
                                                'liabilities': [2017, 2018], 'net_income': [2017],
                                                'operating_expenses': [2017], 'operating_income_ebitda': [2017],
                                                'eps': [2017], 'cash_flow_operations': [2017],
                                                'cash_flow_investing': [2017], 'cash_flow_financing': [2017]}),
    'PM':    ('Philip Morris International',   {'operating_expenses': list(range(2012, 2016))}),
    'PG':    ('Procter & Gamble Company',      {'operating_expenses': list(range(2012, 2017))}),
    'KO':    ('The Coca-Cola Company',         {'operating_expenses': list(range(2012, 2016))}),
    'V':     ('Visa Inc.',                     {'eps': list(range(2012, 2026))}),
    'DIS':   ('Walt Disney Company',           {'assets': [2017], 'liabilities': [2017], 'equity': [2017]}),
    'WFC':   ('Wells Fargo & Company',         {'revenue': list(range(2012, 2016))}),
}

CANDIDATES = {
    'operating_expenses': [
        'OperatingExpenses', 'CostsAndExpenses', 'NoninterestExpense',
        'CostOfGoodsAndServicesSold', 'OperatingCostsAndExpenses',
        'BenefitsLossesAndExpenses', 'CostOfRevenue',
        'SellingGeneralAndAdministrativeExpense',
        'CostsAndExpensesApplicableToRevenues',
        'OtherExpenses', 'GeneralAndAdministrativeExpense',
        'CostOfGoodsSold',
    ],
    'operating_income_ebitda': [
        'OperatingIncomeLoss',
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic',
        'GrossProfit',
        'IncomeLossBeforeIncomeTaxes',
        'PretaxIncomeLoss',
        'IncomeLossFromContinuingOperations',
    ],
    'revenue': [
        'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues',
        'SalesRevenueNet', 'SalesRevenueGoodsNet',
        'RevenueFromContractWithCustomerIncludingAssessedTax',
        'RevenuesNetOfInterestExpense',
        'InterestAndDividendIncomeOperating',
        'InterestIncomeOperating',
        'NoninterestIncome',
        'RevenueFromContractWithCustomerExcludingAssessedTaxAndOtherRevenue',
    ],
    'eps': [
        'EarningsPerShareDiluted', 'EarningsPerShareBasic',
        'EarningsPerShareBasicAndDiluted',
        'IncomeLossFromContinuingOperationsPerDilutedShare',
        'IncomeLossFromContinuingOperationsPerBasicShare',
        'EarningsPerShareDilutedIncludingDiscontinuedOperations',
        'EarningsPerShareBasicIncludingDiscontinuedOperations',
    ],
    'assets': ['Assets', 'AssetsCurrent'],
    'liabilities': ['Liabilities', 'LiabilitiesAndStockholdersEquity'],
    'equity': ['StockholdersEquity',
               'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
    'cash_flow_operations': [
        'NetCashProvidedByUsedInOperatingActivities',
        'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
    ],
    'cash_flow_investing': [
        'NetCashProvidedByUsedInInvestingActivities',
        'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
    ],
    'cash_flow_financing': [
        'NetCashProvidedByUsedInFinancingActivities',
        'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
    ],
    'net_income': [
        'NetIncomeLoss', 'ProfitLoss',
        'NetIncomeLossAvailableToCommonStockholdersBasic',
    ],
}


def get_annual_values(usgaap, concept, target_years):
    cd = usgaap.get(concept)
    if not cd:
        return {}
    results = {}
    for unit_entries in cd.get('units', {}).values():
        for e in unit_entries:
            if e.get('form') not in EDGAR_10K_FORMS:
                continue
            fp = e.get('fp', '')
            if fp and fp != 'FY':
                continue
            frame = e.get('frame', '')
            if not fp and frame and not re.match(r'^CY\d{4}($|Q\d+I$)', frame):
                continue
            end = e.get('end', '')
            if not end:
                continue
            yr = int(end[:4])
            if yr not in target_years:
                continue
            val = e.get('val')
            if val is not None:
                accn = e.get('accn', '')
                if yr not in results or accn >= results[yr][0]:
                    results[yr] = (accn, float(val))
    return {yr: v for yr, (_, v) in results.items()}


_facts_cache = {}


def get_facts(sym):
    if sym in _facts_cache:
        return _facts_cache[sym]
    cik = int(cik_for_symbol(sym))
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    print(f"  Fetching {sym} (CIK {cik})...", flush=True)
    facts = requests.get(url, headers=HEADERS_DATA, timeout=30).json()['facts']
    _facts_cache[sym] = facts
    return facts


for sym, (name, col_years) in TARGETS.items():
    facts = get_facts(sym)
    usgaap = facts.get('us-gaap', {})
    print(f"\n{'='*65}")
    print(f"  {sym} — {name}")
    print(f"{'='*65}")

    for col, years in col_years.items():
        candidates = CANDIDATES.get(col, [])
        found = {}
        for concept in candidates:
            vals = get_annual_values(usgaap, concept, set(years))
            for yr, v in vals.items():
                if yr not in found:
                    found[yr] = (concept, v)

        miss = sorted(y for y in years if y not in found)
        by_concept = {}
        for yr, (c, v) in found.items():
            by_concept.setdefault(c, []).append(yr)

        if not found:
            print(f"  {col}: ❌ NO concept found — years {years}")
        else:
            print(f"  {col}: misses={miss}")
            for concept, yrs in by_concept.items():
                print(f"    → {concept}  {sorted(yrs)}")
