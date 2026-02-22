"""Verify all batch-2 companies for zero values after fixes."""
from Services.FinancialDataScraper import FinancialDataScraper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


COMPANIES = [
    ('AMD',  'Advanced Micro Devices Inc'),
    ('AXP',  'American Express Company'),
    ('CVX',  'Chevron Corp'),
    ('C',    'Citigroup Inc'),
    ('COST', 'Costco Wholesale Corp'),
    ('IBM',  'International Business Machines'),
    ('JNJ',  'Johnson & Johnson'),
    ('KLAC', 'KLA-Tencor Corporation'),
    ('LIN',  'Linde plc Ordinary Shares'),
    ('MA',   'Mastercard Inc'),
    ('MRK',  'Merck & Company Inc'),
    ('NFLX', 'Netflix Inc'),
    ('PM',   'Philip Morris International Inc'),
    ('PG',   'Procter & Gamble Company'),
    ('KO',   'The Coca-Cola Company'),
    ('V',    'Visa Inc. Class A'),
    ('DIS',  'Walt Disney Company'),
    ('WFC',  'Wells Fargo & Company'),
    ('PLTR', 'Palantir Technologies'),
    ('GOOGL', 'Alphabet Inc Class C'),
]

COLS = ['revenue', 'net_income', 'assets', 'liabilities', 'equity',
        'operating_expenses', 'operating_income_ebitda', 'eps',
        'cash_flow_operations', 'cash_flow_investing',
        'cash_flow_financing', 'free_cash_flow']

scraper = FinancialDataScraper(years_needed=list(range(2012, 2026)))

for sym, name in COMPANIES:
    rows = scraper.scrape_company(sym, name)
    rows_by_year = {r['reporting_year']: r for r in rows}
    zeros = []
    for r in sorted(rows, key=lambda x: x['reporting_year']):
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
        years = sorted(rows_by_year.keys())
        print(f"  ✅ {sym}: no zeros  (years: {years})")
