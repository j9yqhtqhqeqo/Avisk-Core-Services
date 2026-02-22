"""Verify all fixed companies now return correct values."""
from Services.FinancialDataScraper import FinancialDataScraper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


COMPANIES = [
    ('GOOGL', 'Alphabet Inc Class C'),
    ('AAPL',  'Apple Inc'),
    ('LLY',   'Eli Lilly and Company'),
    ('XOM',   'Exxon Mobil Corp'),
    ('JPM',   'JPMorgan Chase & Co'),
    ('MSFT',  'Microsoft Corporation'),
    ('TSLA',  'Tesla Inc'),
]

COLS = ['revenue', 'net_income', 'assets', 'liabilities', 'equity',
        'operating_expenses', 'operating_income_ebitda', 'eps',
        'cash_flow_operations', 'cash_flow_investing',
        'cash_flow_financing', 'free_cash_flow']

scraper = FinancialDataScraper(years_needed=list(range(2012, 2026)))

for sym, name in COMPANIES:
    rows = scraper.scrape_company(sym, name)
    rows_by_year = {r['reporting_year']: r for r in rows}
    years = sorted(rows_by_year.keys())
    zeros = []
    for r in rows:
        yr = r['reporting_year']
        bad = [c for c in COLS if r.get(c) is not None and r.get(c) == 0]
        if bad:
            zeros.append(f"  {yr}: {' '.join(bad)}")
    if zeros:
        print(f"\n{'='*60}")
        print(f"  {sym} — {name}  STILL HAS ZEROS:")
        for z in zeros:
            print(z)
    else:
        print(f"\n  ✅ {sym} — {name}: no zeros  (years: {years})")
