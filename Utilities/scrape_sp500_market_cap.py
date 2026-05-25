"""
Build a current S&P 500 market-cap ranking CSV.

The primary ranking feed comes from marketcap.company. That source can lag the
live S&P 500 constituent list, so this script reconciles the scraped ranking
against the current Wikipedia constituent table and fills any missing current
symbols with live market caps from Yahoo Finance.

Usage:
    python Utilities/scrape_sp500_market_cap.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from pathlib import Path
import yfinance as yf


WIKIPEDIA_SP500_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
MARKETCAP_URL = 'https://marketcap.company/stock-indices/s-p-500-index-market-cap/'


def extract_symbol_from_text(text: str) -> str:
    """Extract stock symbol from text like 'NASDAQ:NVDA' or 'NYSE:JPM'."""
    match = re.search(r'(?:NASDAQ|NYSE):([A-Z.]+)', text)
    if match:
        return match.group(1)
    return ""


def normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper().replace('.', '-')


def fetch_current_sp500_constituents() -> pd.DataFrame:
    """Fetch the current S&P 500 constituent list from Wikipedia."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(WIKIPEDIA_SP500_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'}) or soup.find('table', {'class': 'wikitable'})
    if table is None:
        raise ValueError('Could not find S&P 500 constituents table on Wikipedia')

    rows: list[dict[str, str]] = []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
        rows.append({
            'symbol': normalize_symbol(cols[0].get_text(' ', strip=True)),
            'company': cols[1].get_text(' ', strip=True),
            'sector': cols[3].get_text(' ', strip=True),
        })

    dataframe = pd.DataFrame(rows)
    return dataframe.drop_duplicates(subset=['symbol']).reset_index(drop=True)


def parse_market_cap_value(market_cap_text: str) -> float:
    """Convert strings like '$4.32 Trillion' into numeric dollars."""
    text = str(market_cap_text or '').strip().replace('$', '').replace(',', '')
    match = re.match(r'([0-9.]+)\s*(Trillion|Billion|Million)?', text, re.IGNORECASE)
    if not match:
        return 0.0

    value = float(match.group(1))
    suffix = (match.group(2) or '').lower()
    if suffix == 'trillion':
        return value * 1_000_000_000_000
    if suffix == 'billion':
        return value * 1_000_000_000
    if suffix == 'million':
        return value * 1_000_000
    return value


def format_market_cap_value(market_cap_value: float) -> str:
    if market_cap_value >= 1_000_000_000_000:
        return f"${market_cap_value / 1_000_000_000_000:.2f} Trillion"
    if market_cap_value >= 1_000_000_000:
        return f"${market_cap_value / 1_000_000_000:.2f} Billion"
    if market_cap_value >= 1_000_000:
        return f"${market_cap_value / 1_000_000:.2f} Million"
    return f"${market_cap_value:,.0f}"


def scrape_sp500_market_cap(num_pages: int = 11) -> pd.DataFrame:
    """
    Scrape S&P 500 companies ranked by market cap.

    Args:
        num_pages: Number of pages to scrape (default 11 for ~500 companies)

    Returns:
        DataFrame with columns: rank, symbol, company, market_cap
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    all_companies = []

    for page in range(1, num_pages + 1):
        if page == 1:
            url = MARKETCAP_URL
        else:
            url = f"{MARKETCAP_URL}?page={page}"

        print(f"Fetching page {page}/{num_pages}: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the table with company data
            table = soup.find('table')
            if not table:
                print(f"  No table found on page {page}")
                continue

            rows = table.find_all('tr')[1:]  # Skip header row

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    # Column 0: Rank number
                    rank_text = cols[0].text.strip()
                    try:
                        rank = int(rank_text)
                    except ValueError:
                        continue

                    # Column 1: Company name with exchange (e.g., "NVIDIA Corporation NASDAQ:NVDA")
                    company_cell_text = cols[1].text.strip()
                    # Clean up whitespace
                    company_cell_text = ' '.join(company_cell_text.split())

                    # Extract symbol from exchange:symbol format
                    symbol = extract_symbol_from_text(company_cell_text)

                    # Extract company name (everything before the exchange)
                    company_name = re.sub(
                        r'\s*(NASDAQ|NYSE):[A-Z.]+.*', '', company_cell_text).strip()

                    # Column 3: Market cap (e.g., "$4.32 Trillion")
                    market_cap = cols[3].text.strip() if len(cols) > 3 else ""

                    # Column 4: Sector
                    sector = cols[4].text.strip() if len(cols) > 4 else ""

                    if symbol:
                        all_companies.append({
                            'rank': rank,
                            'symbol': normalize_symbol(symbol),
                            'company': company_name,
                            'market_cap': market_cap,
                            'sector': sector
                        })

            print(
                f"  Found {len(rows)} rows, total companies: {len(all_companies)}")

            # Be respectful - wait between requests
            time.sleep(1)

        except Exception as e:
            print(f"  Error fetching page {page}: {e}")
            continue

    return pd.DataFrame(all_companies)


def fetch_market_cap_from_yahoo(symbol: str) -> float | None:
    """Fetch a live market cap from Yahoo Finance for a single ticker."""
    try:
        info = yf.Ticker(symbol).info
    except Exception as exc:
        print(f"  Yahoo lookup failed for {symbol}: {exc}")
        return None

    market_cap = info.get('marketCap')
    if market_cap is None:
        print(f"  Yahoo lookup returned no market cap for {symbol}")
        return None
    return float(market_cap)


def reconcile_with_current_constituents(scraped_df: pd.DataFrame) -> pd.DataFrame:
    """Keep only current S&P 500 constituents and backfill missing current symbols."""
    current_df = fetch_current_sp500_constituents()
    scraped_df = scraped_df.copy()
    scraped_df['symbol'] = scraped_df['symbol'].astype(str).map(normalize_symbol)
    scraped_df['market_cap_value'] = scraped_df['market_cap'].map(parse_market_cap_value)

    current_symbols = set(current_df['symbol'])
    scraped_df = scraped_df[scraped_df['symbol'].isin(current_symbols)].copy()

    wiki_by_symbol = current_df.set_index('symbol').to_dict('index')
    scraped_df['company'] = scraped_df['symbol'].map(lambda symbol: wiki_by_symbol[symbol]['company'])
    scraped_df['sector'] = scraped_df['symbol'].map(lambda symbol: wiki_by_symbol[symbol]['sector'])

    scraped_symbols = set(scraped_df['symbol'])
    missing_symbols = current_df[~current_df['symbol'].isin(scraped_symbols)].copy()
    print(f"Reconciling against live S&P 500 list: {len(missing_symbols)} current symbols missing from scrape")

    enriched_rows: list[dict[str, object]] = []
    for row in missing_symbols.itertuples(index=False):
        print(f"  Fetching live market cap for missing symbol {row.symbol} ({row.company})")
        market_cap_value = fetch_market_cap_from_yahoo(row.symbol)
        if market_cap_value is None:
            continue
        enriched_rows.append({
            'symbol': row.symbol,
            'company': row.company,
            'market_cap': format_market_cap_value(market_cap_value),
            'market_cap_value': market_cap_value,
            'sector': row.sector,
        })
        time.sleep(0.2)

    if enriched_rows:
        scraped_df = pd.concat([scraped_df, pd.DataFrame(enriched_rows)], ignore_index=True)

    scraped_df = scraped_df.sort_values('market_cap_value', ascending=False).reset_index(drop=True)
    scraped_df['rank'] = scraped_df.index + 1
    return scraped_df[['rank', 'symbol', 'company', 'market_cap', 'sector']]


def save_to_csv(df: pd.DataFrame, output_path: str):
    """Save DataFrame to CSV file."""
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(df)} companies to {output_path}")


def generate_python_list(df: pd.DataFrame, top_n: int = 150) -> str:
    """Generate Python list code for embedding in the app."""
    symbols = df.head(top_n)['symbol'].tolist()

    # Format as Python list with 10 items per line
    lines = []
    for i in range(0, len(symbols), 10):
        batch = symbols[i:i+10]
        line = "    " + ", ".join([f"'{s}'" for s in batch]) + ","
        lines.append(line)

    code = "TOP_SP500_BY_MARKET_CAP = [\n"
    code += "\n".join(lines)
    code += "\n]"

    return code


def main():
    # Scrape all pages
    print("=" * 60)
    print("Scraping S&P 500 companies by market cap")
    print("=" * 60)

    df = scrape_sp500_market_cap(num_pages=11)

    if df.empty:
        print("No data scraped!")
        return

    df = reconcile_with_current_constituents(df)

    # Save to CSV
    output_dir = Path(__file__).parent.parent / 'Clients'
    output_path = output_dir / 'sp500_market_cap_ranked.csv'
    save_to_csv(df, str(output_path))

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total companies: {len(df)}")
    print(f"\nTop 10 by market cap:")
    print(df[['rank', 'symbol', 'company', 'market_cap']].head(
        10).to_string(index=False))

    # Generate Python code for embedding
    print("\n" + "=" * 60)
    print("Python list for embedding (top 150):")
    print("=" * 60)
    print(generate_python_list(df, top_n=150))


if __name__ == "__main__":
    main()
