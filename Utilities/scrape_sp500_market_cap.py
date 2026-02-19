"""
Scrape S&P 500 companies ranked by market cap from marketcap.company

This script fetches all pages of S&P 500 companies and saves them to a CSV file
with their market cap ranking for use in the Sustainability Report Downloader.

Usage:
    python Utilities/scrape_sp500_market_cap.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from pathlib import Path


def extract_symbol_from_text(text: str) -> str:
    """Extract stock symbol from text like 'NASDAQ:NVDA' or 'NYSE:JPM'."""
    match = re.search(r'(?:NASDAQ|NYSE):([A-Z.]+)', text)
    if match:
        return match.group(1)
    return ""


def scrape_sp500_market_cap(num_pages: int = 11) -> pd.DataFrame:
    """
    Scrape S&P 500 companies ranked by market cap.

    Args:
        num_pages: Number of pages to scrape (default 11 for ~500 companies)

    Returns:
        DataFrame with columns: rank, symbol, company, market_cap
    """
    base_url = "https://marketcap.company/stock-indices/s-p-500-index-market-cap/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    all_companies = []

    for page in range(1, num_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}?page={page}"

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
                            'symbol': symbol,
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
