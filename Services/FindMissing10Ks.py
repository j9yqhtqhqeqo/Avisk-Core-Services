"""
Find companies with missing 10-K filings between 2012 and 2025.

Checks two sources and cross-references them:
  1. t_data_source (content_type=2) — what we have downloaded in the DB
  2. Local disk    (sustainability_reports/<year>/<symbol>/) — what exists on disk

Outputs:
  - Console table of missing years per company
  - CSV report saved to sustainability_cache/missing_10ks_report.csv

Usage:
    python Services/FindMissing10Ks.py [--start YEAR] [--end YEAR] [--symbol TICKER] [--csv-only]

Options:
    --start YEAR    First year to check (default: 2012)
    --end   YEAR    Last  year to check (default: 2025)
    --symbol TICKER Check a single ticker only
    --csv-only      Skip console table, only write the CSV
"""

import pandas as pd
import sys
import os
import argparse
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


try:
    import psycopg2
    import psycopg2.extras
    from Utilities.Lookups import DB_Connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Constants ────────────────────────────────────────────────────────────────
SP500_CSV = Path(__file__).resolve().parent.parent / \
    "Clients" / "sp500_market_cap_ranked.csv"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "sustainability_reports"
CACHE_DIR = Path(__file__).resolve().parent.parent / "sustainability_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONTENT_TYPE_10K = 2       # t_data_source content_type for 10-K / Annual Report

# ── Helpers ──────────────────────────────────────────────────────────────────


def load_sp500() -> pd.DataFrame:
    """Load S&P 500 company list from local CSV."""
    df = pd.read_csv(SP500_CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    # Normalise column names — handle 'symbol'/'Symbol', 'company'/'Company'
    rename = {}
    for col in df.columns:
        if col in ('symbol', 'ticker'):
            rename[col] = 'symbol'
        elif col in ('company', 'name', 'company name'):
            rename[col] = 'company'
        elif col == 'sector':
            rename[col] = 'sector'
    df = df.rename(columns=rename)
    return df[['symbol', 'company', 'sector'] if 'sector' in df.columns else ['symbol', 'company']]


def get_db_10k_years(conn, symbol: str, company_name: str) -> Set[int]:
    """
    Return set of years that have a 10-K record in t_data_source.

    Mirrors:  SELECT * FROM t_data_source
              WHERE  content_type = 2
                AND  company_name ILIKE '<company_name>'
              ORDER BY year

    Falls back to symbol match when company_name yields nothing
    (handles cases where the name was stored slightly differently).
    """
    if conn is None:
        return set()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Primary: exact company_name match (case-insensitive)
            cur.execute(
                """
                SELECT DISTINCT year
                FROM   t_data_source
                WHERE  content_type = %s
                  AND  year IS NOT NULL
                  AND  company_name ILIKE %s
                ORDER BY year
                """,
                (CONTENT_TYPE_10K, company_name)
            )
            rows = cur.fetchall()
            years = {int(r['year']) for r in rows if r['year']}

            # Fallback: partial symbol match on source_url / company_name
            if not years:
                cur.execute(
                    """
                    SELECT DISTINCT year
                    FROM   t_data_source
                    WHERE  content_type = %s
                      AND  year IS NOT NULL
                      AND  (
                               company_name ILIKE %s
                            OR source_url   ILIKE %s
                           )
                    ORDER BY year
                    """,
                    (CONTENT_TYPE_10K, f"%{symbol}%", f"%{symbol}%")
                )
                rows = cur.fetchall()
                years = {int(r['year']) for r in rows if r['year']}

            return years
    except Exception as e:
        print(f"  [WARN] DB query failed for {symbol}: {e}", file=sys.stderr)
        return set()


def get_disk_10k_years(symbol: str) -> Set[int]:
    """
    Scan the local sustainability_reports folder for 10-K files belonging to this symbol.
    Expected folder layout:  sustainability_reports/<year>/<symbol>/  or
                             sustainability_reports/<year>/  (flat, filename contains symbol)
    """
    years_found: Set[int] = set()

    if not REPORTS_DIR.exists():
        return years_found

    for year_dir in REPORTS_DIR.iterdir():
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue

        # Check symbol sub-folder first
        symbol_dir = year_dir / symbol.upper()
        if symbol_dir.is_dir():
            for f in symbol_dir.iterdir():
                if f.suffix.lower() == '.pdf':
                    years_found.add(year)
                    break
            continue

        # Fallback: filename contains the symbol
        for f in year_dir.rglob('*.pdf'):
            if symbol.upper() in f.stem.upper():
                years_found.add(year)
                break

    return years_found


def build_report(companies: pd.DataFrame, start: int, end: int,
                 conn, target_symbol: Optional[str]) -> list[dict]:
    """Build the missing-10K report rows."""
    all_years = list(range(start, end + 1))
    rows = []

    total = len(companies)
    for i, (_, row) in enumerate(companies.iterrows(), 1):
        symbol = str(row['symbol']).strip().upper()
        company = str(row['company']).strip()
        sector = str(row.get('sector', '')).strip()

        if target_symbol and symbol != target_symbol.upper():
            continue

        print(f"  [{i:3}/{total}] {symbol:<6}  {company[:45]}",
              end="  ", flush=True)

        db_years = get_db_10k_years(conn, symbol, company)
        disk_years = get_disk_10k_years(symbol)
        have_years = db_years | disk_years

        missing = sorted(y for y in all_years if y not in have_years)
        present = sorted(have_years & set(all_years))

        status = "✅ complete" if not missing else f"❌ missing {len(missing)} year(s)"
        print(status)

        rows.append({
            'symbol':        symbol,
            'company':       company,
            'sector':        sector,
            'years_present': ','.join(map(str, present)),
            'years_missing': ','.join(map(str, missing)),
            'missing_count': len(missing),
            'present_count': len(present),
            'in_db':         ','.join(map(str, sorted(db_years & set(all_years)))),
            'on_disk':       ','.join(map(str, sorted(disk_years & set(all_years)))),
            'checked_at':    datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        })

    return rows


def print_summary(rows: list[dict], start: int, end: int):
    """Print a readable summary table to console."""
    missing_rows = [r for r in rows if r['missing_count'] > 0]

    print()
    print("=" * 90)
    print(
        f"  10-K Coverage Gap Report  |  {start}–{end}  |  {len(rows)} companies checked")
    print("=" * 90)

    if not missing_rows:
        print("  🎉  All companies have complete 10-K coverage for the requested range!")
        return

    # Sort: most missing first, then alpha
    missing_rows.sort(key=lambda r: (-r['missing_count'], r['symbol']))

    print(f"  {'SYMBOL':<8}  {'COMPANY':<40}  {'SECTOR':<25}  MISSING YEARS")
    print("  " + "-" * 86)
    for r in missing_rows:
        print(
            f"  {r['symbol']:<8}  {r['company'][:40]:<40}  {r['sector'][:25]:<25}  {r['years_missing']}")

    print()
    print(f"  Summary: {len(missing_rows)} / {len(rows)} companies have gaps")

    # Gap-size histogram
    buckets = {
        "1-3 yrs":   [r for r in missing_rows if 1 <= r['missing_count'] <= 3],
        "4-7 yrs":   [r for r in missing_rows if 4 <= r['missing_count'] <= 7],
        "8-13 yrs":  [r for r in missing_rows if 8 <= r['missing_count'] <= 13],
        "14+ yrs":   [r for r in missing_rows if r['missing_count'] >= 14],
    }
    print()
    print("  Gap size breakdown:")
    for label, group in buckets.items():
        if group:
            print(f"    {label:10s}: {len(group):4d} companies")
    print("=" * 90)


def save_csv(rows: list[dict], output_path: Path):
    """Write the full report to CSV."""
    fieldnames = [
        'symbol', 'company', 'sector',
        'missing_count', 'present_count',
        'years_missing', 'years_present',
        'in_db', 'on_disk', 'checked_at',
    ]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # Sort: most missing first
        for r in sorted(rows, key=lambda x: (-x['missing_count'], x['symbol'])):
            writer.writerow(r)
    print(f"\n  📄  Full report saved → {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Find S&P 500 companies with missing 10-K filings')
    parser.add_argument('--start',   type=int, default=2012,
                        help='Start year (default 2012)')
    parser.add_argument('--end',     type=int, default=2025,
                        help='End year   (default 2025)')
    parser.add_argument('--symbol',  type=str, default=None,
                        help='Check a single ticker only')
    parser.add_argument('--limit',   type=int, default=None,
                        help='Only check the top N companies by market-cap rank (e.g. --limit 50)')
    parser.add_argument('--csv-only', action='store_true',
                        help='Skip console table')
    args = parser.parse_args()

    start, end = args.start, args.end
    if start > end:
        parser.error("--start must be <= --end")

    print(f"\n{'='*60}")
    print(f"  Finding missing 10-Ks  |  {start}–{end}")
    print(f"{'='*60}")

    # Load company list
    print("\n  Loading S&P 500 company list …")
    companies = load_sp500()
    if args.symbol:
        companies = companies[companies['symbol'].str.upper()
                              == args.symbol.upper()]
        if companies.empty:
            print(f"  Symbol '{args.symbol}' not found in {SP500_CSV.name}")
            sys.exit(1)
    if args.limit:
        companies = companies.head(args.limit)
    print(f"  {len(companies)} companies loaded")

    # Connect to DB (optional — disk scan always runs)
    conn = None
    if DB_AVAILABLE:
        try:
            conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
            print("  ✅  Database connected — checking t_data_source")
        except Exception as e:
            print(f"  ⚠️   DB unavailable ({e}) — disk-only scan")
    else:
        print("  ⚠️   DB modules not installed — disk-only scan")

    # Run the scan
    print(
        f"\n  Scanning {len(companies)} companies for years {start}–{end} …\n")
    rows = build_report(companies, start, end, conn, args.symbol)

    if conn:
        conn.close()

    # Output
    if not args.csv_only:
        print_summary(rows, start, end)

    output_path = CACHE_DIR / f"missing_10ks_{start}_{end}.csv"
    save_csv(rows, output_path)


if __name__ == '__main__':
    main()
