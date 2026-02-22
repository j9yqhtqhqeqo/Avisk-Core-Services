"""Full column diagnostic for NVDA and GOOGL across 2020-2025."""
from Services.FinancialDataScraper import FinancialDataScraper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


COMPANIES = [
    ('NVDA',  'NVIDIA Corporation'),
    ('GOOGL', 'Alphabet Inc.'),
]

COLS = [
    'reporting_year', 'revenue', 'net_income', 'assets', 'liabilities',
    'equity', 'operating_expenses', 'operating_income_ebitda', 'eps',
    'cash_flow_operations', 'cash_flow_investing', 'cash_flow_financing',
    'free_cash_flow',
]

scraper = FinancialDataScraper(years_needed=list(range(2020, 2026)))

for sym, name in COMPANIES:
    rows = scraper.scrape_company(sym, name)
    rows_by_year = {r['reporting_year']: r for r in rows}
    print(f"\n{'='*80}")
    print(
        f"  {sym} — {name}  ({len(rows)} years returned: {sorted(rows_by_year.keys())})")
    print(f"{'='*80}")
    print(f"  {'Col':<32} " + "  ".join(f"{yr}" for yr in range(2020, 2026)))
    print(f"  {'-'*32} " + "  ".join("------" for _ in range(6)))
    for col in COLS[1:]:  # skip reporting_year
        vals = []
        for yr in range(2020, 2026):
            r = rows_by_year.get(yr)
            v = r.get(col) if r else None
            if v is None:
                vals.append("  None")
            elif v == 0:
                vals.append(" *** 0")
            elif abs(v) >= 1e9:
                vals.append(f"{v/1e9:>6.1f}B")
            elif abs(v) >= 1e6:
                vals.append(f"{v/1e6:>6.1f}M")
            else:
                vals.append(f"{v:>6.2f}")
        has_zero = any("*** 0" in x for x in vals)
        flag = " ⚠️ ZEROS" if has_zero else ""
        print(f"  {col:<32} {'  '.join(vals)}{flag}")
