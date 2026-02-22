"""
Diagnose zero-value columns across problematic companies.
For each company/year/column combo that's zero, find what concept EDGAR
actually has data under.
"""
from Services.FinancialDataScraper import _get_headers, EDGAR_10K_FORMS, cik_for_symbol
import requests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


HEADERS_DATA = {**_get_headers(), 'Host': 'data.sec.gov'}

# ── Companies to probe ────────────────────────────────────────────────────────
TARGETS = {
    'GOOGL': ('Alphabet Inc Class C', {
        'operating_expenses': [2012, 2013],
        'eps':                [2015],
        'assets':             [2012, 2013],
        'liabilities':        [2012, 2013],
        'cash_flow_operations':  [2012],
        'cash_flow_investing':   [2012],
        'cash_flow_financing':   [2012],
        'free_cash_flow':        [2012],
        'revenue':               [2012],
        'net_income':            [2012],
    }),
    'AAPL': ('Apple Inc', {
        'cash_flow_operations':  [2014],
        'cash_flow_investing':   [2014],
        'cash_flow_financing':   [2014],
        'free_cash_flow':        [2014],
    }),
    'LLY': ('Eli Lilly and Company', {
        'operating_expenses': list(range(2012, 2026)),
    }),
    'XOM': ('Exxon Mobil Corp', {
        'cash_flow_operations':  [2013, 2014],
        'cash_flow_investing':   [2013, 2014],
        'cash_flow_financing':   [2013, 2014],
    }),
    'JPM': ('JPMorgan Chase & Co', {
        'operating_expenses': list(range(2012, 2026)),
    }),
    'MSFT': ('Microsoft Corporation', {
        'cash_flow_operations':  [2014, 2015],
        'cash_flow_investing':   [2014, 2015],
        'cash_flow_financing':   [2014, 2015],
        'operating_expenses':    list(range(2016, 2023)),
    }),
    'TSLA': ('Tesla Inc', {
        'eps':                   [2012, 2013, 2014],
        'cash_flow_operations':  [2014, 2015],
        'cash_flow_investing':   [2014, 2015],
        'cash_flow_financing':   [2014, 2015],
    }),
}

# ── Candidate concepts by column ─────────────────────────────────────────────
CANDIDATES = {
    'operating_expenses': [
        'OperatingExpenses',
        'CostsAndExpenses',
        'NoninterestExpense',                        # banks
        'BenefitsLossesAndExpenses',                 # insurance
        'OperatingCostsAndExpenses',
        'CostOfGoodsAndServicesSold',
        'CostsAndExpensesApplicableToRevenues',
        'OtherExpenses',
        'GeneralAndAdministrativeExpense',
        'SellingGeneralAndAdministrativeExpense',
        'ResearchAndDevelopmentExpense',
    ],
    'cash_flow_operations': [
        'NetCashProvidedByUsedInOperatingActivities',
        'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
        'NetCashUsedInOperatingActivities',
        'NetCashProvidedByOperatingActivities',
    ],
    'cash_flow_investing': [
        'NetCashProvidedByUsedInInvestingActivities',
        'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
        'NetCashUsedInInvestingActivities',
    ],
    'cash_flow_financing': [
        'NetCashProvidedByUsedInFinancingActivities',
        'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
        'NetCashUsedInFinancingActivities',
    ],
    'free_cash_flow': [
        # computed — same as cash_flow_operations candidates
        'NetCashProvidedByUsedInOperatingActivities',
    ],
    'eps': [
        'EarningsPerShareDiluted',
        'EarningsPerShareBasic',
        'EarningsPerShareBasicAndDiluted',
        'EarningsPerShareBasicAndDiluted2013',
        'IncomeLossFromContinuingOperationsPerDilutedShare',
        'IncomeLossFromContinuingOperationsPerBasicShare',
    ],
    'assets': [
        'Assets',
        'AssetsCurrent',
    ],
    'liabilities': [
        'Liabilities',
        'LiabilitiesAndStockholdersEquity',
    ],
    'revenue': [
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'Revenues',
        'SalesRevenueNet',
        'SalesRevenueGoodsNet',
        'RevenueFromContractWithCustomerIncludingAssessedTax',
    ],
    'net_income': [
        'NetIncomeLoss',
        'ProfitLoss',
        'NetIncomeLossAvailableToCommonStockholdersBasic',
    ],
}


def get_annual_values(usgaap, concept, target_years):
    """Return {year: val} for 10-K annual entries of a concept."""
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
            import re
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
    print(f"Fetching {sym} (CIK {cik})...")
    facts = requests.get(url, headers=HEADERS_DATA, timeout=30).json()['facts']
    _facts_cache[sym] = facts
    return facts


# ── Run probes ────────────────────────────────────────────────────────────────
for sym, (name, col_years) in TARGETS.items():
    facts = get_facts(sym)
    usgaap = facts.get('us-gaap', {})
    print(f"\n{'='*70}")
    print(f"  {sym} — {name}")
    print(f"{'='*70}")

    for col, years in col_years.items():
        candidates = CANDIDATES.get(col, [])
        found = {}
        for concept in candidates:
            vals = get_annual_values(usgaap, concept, set(years))
            if vals:
                for yr, v in vals.items():
                    if yr not in found:
                        found[yr] = (concept, v)

        hit_years = sorted(found.keys())
        miss_years = sorted(y for y in years if y not in found)
        if not found:
            print(f"\n  {col}: NO concept found for years {years}")
        else:
            print(f"\n  {col}: hits={hit_years}  misses={miss_years}")
            by_concept = {}
            for yr, (concept, v) in found.items():
                by_concept.setdefault(concept, []).append(yr)
            for concept, yrs in by_concept.items():
                print(f"    → {concept}  years={sorted(yrs)}")
