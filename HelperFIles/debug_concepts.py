"""Diagnose CapEx and balance sheet concept availability for NVDA and GOOGL."""
from Services.FinancialDataScraper import _get_headers, EDGAR_10K_FORMS, cik_for_symbol
import requests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


HEADERS_DATA = {**_get_headers(), 'Host': 'data.sec.gov'}

CAPEX_CONCEPTS = [
    'PaymentsToAcquirePropertyPlantAndEquipment',
    'PaymentsForCapitalImprovements',
    'CapitalExpendituresIncurredButNotYetPaid',
    'PurchaseOfPropertyPlantAndEquipment',
    'PaymentsToAcquireProductiveAssets',
]
ASSET_CONCEPTS = ['Assets', 'AssetsCurrent']
LIAB_CONCEPTS = ['Liabilities', 'LiabilitiesAndStockholdersEquity']
EQUITY_CONCEPTS = ['StockholdersEquity',
                   'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']


def probe(symbol, concepts, label):
    cik = int(cik_for_symbol(symbol))
    facts = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        headers=HEADERS_DATA, timeout=30
    ).json()['facts'].get('us-gaap', {})

    print(f"\n--- {symbol} | {label} ---")
    for c in concepts:
        cd = facts.get(c)
        if not cd:
            print(f"  MISSING  {c}")
            continue
        for unit_entries in cd.get('units', {}).values():
            annual = [e for e in unit_entries
                      if e.get('form') in EDGAR_10K_FORMS
                      and e.get('fp', '') in ('FY', '')]
            annual.sort(key=lambda e: e.get('end', ''), reverse=True)
            years = sorted({int(e['end'][:4])
                           for e in annual if e.get('end')}, reverse=True)
            print(f"  EXISTS   {c}")
            print(f"           years with 10-K data: {years[:10]}")
            for e in annual[:5]:
                print(f"           end={e.get('end')}  fp={e.get('fp')}  "
                      f"frame={e.get('frame','')}  val={e.get('val')}")
            break


for sym in ('NVDA', 'GOOGL'):
    probe(sym, CAPEX_CONCEPTS,  'CapEx concepts')
    probe(sym, ASSET_CONCEPTS,  'Assets concepts')
    probe(sym, LIAB_CONCEPTS,   'Liabilities concepts')
    probe(sym, EQUITY_CONCEPTS, 'Equity concepts')
