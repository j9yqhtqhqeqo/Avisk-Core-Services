"""Quick verify: scrape 3 companies and check opex is populated for previously-zero years."""
from Services.FinancialDataScraper import FinancialDataScraper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

scraper = FinancialDataScraper(years_needed=list(range(2012, 2026)))

TESTS = [
    ('AMD',  'Advanced Micro Devices Inc',        list(range(2012, 2016))),
    ('COST', 'Costco Wholesale Corp',             list(range(2012, 2016))),
    ('JNJ',  'Johnson & Johnson',                 list(range(2012, 2017))),
    ('MRK',  'Merck & Company Inc',               list(range(2012, 2016))),
    ('PG',   'Procter & Gamble Company',          list(range(2012, 2017))),
    ('KO',   'The Coca-Cola Company',             list(range(2012, 2016))),
    ('PM',   'Philip Morris International Inc',   list(range(2012, 2016))),
    ('LIN',  'Linde plc Ordinary Shares',         list(range(2016, 2025))),
]

all_ok = True
for sym, name, check_years in TESTS:
    rows = scraper.scrape_company(sym, name)
    by_year = {r['reporting_year']: r for r in rows}
    fails = []
    for yr in check_years:
        r = by_year.get(yr)
        if r is None:
            fails.append(f"{yr}:missing")
        elif not r.get('operating_expenses'):
            fails.append(f"{yr}:zero/null")
    if fails:
        print(f"  STILL BAD  {sym}: {fails}")
        all_ok = False
    else:
        vals = {
            yr: f"${by_year[yr]['operating_expenses']/1e9:.1f}B" for yr in check_years if yr in by_year}
        print(f"  OK  {sym}: opex {vals}")

if all_ok:
    print("\n✅ All previously-zero operating_expenses gaps are now filled.")
else:
    print("\n❌ Some gaps remain.")
