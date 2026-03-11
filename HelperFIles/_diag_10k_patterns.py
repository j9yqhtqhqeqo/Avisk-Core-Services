"""
Fetch 5 sample 10-K files from EDGAR using their stored filenames
and show the snippets around "Chief Executive Officer" to diagnose
why _extract_ceo_from_sec_text() fails to find a name.
"""
from Services.CEODataService import _extract_ceo_from_sec_text
from bs4 import BeautifulSoup
import sys
import re
import requests
sys.path.insert(0, '.')

EDGAR_HEADERS = {
    'User-Agent': 'Avisk-AI-Platform contact@avisk.ai',
    'Accept-Encoding': 'gzip, deflate',
}

# Fetch the SEC ticker→CIK map once
print("Loading SEC ticker map...")
r2 = requests.get('https://www.sec.gov/files/company_tickers.json',
                  headers=EDGAR_HEADERS, timeout=15)
tmap = {v['ticker'].upper(): str(v['cik_str']).zfill(10)
        for v in r2.json().values()}
print(f"Loaded {len(tmap)} tickers\n")

samples = [
    ('AKAM', 'AKAM_10K_2024-12-31_000108622225000028.htm', 2024),
    ('CME',  'CME_10K_2024-12-31_000115637525000021.htm',  2024),
    ('CVS',  'CVS_10K_2024-12-31_000006480325000007.htm',  2024),
    ('CF',   'CF_10K_2020-12-31_000132440421000008.htm',   2020),
    ('GEN',  'GEN_10K_2023-03-31_000084939923000014.htm',  2023),
]


def get_primary_doc_url(cik: str, acc_raw: str) -> str | None:
    """Use EDGAR submissions JSON to find the 10-K primary document for this accession."""
    # acc_raw e.g. '000108622225000028' -> '0001086222-25-000028'
    acc_fmt = f'{acc_raw[:10]}-{acc_raw[10:12]}-{acc_raw[12:]}'
    subs_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    try:
        r = requests.get(subs_url, headers=EDGAR_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        recent = data.get('filings', {}).get('recent', {})
        accns = recent.get('accessionNumber', [])
        docs = recent.get('primaryDocument', [])
        for accn, doc in zip(accns, docs):
            if accn == acc_fmt:
                return (f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/'
                        f'{acc_raw}/{doc}')
    except Exception as e:
        print(f'  submissions lookup error: {e}')
    return None


for ticker, fname, year in samples:
    cik = tmap.get(ticker)
    if not cik:
        print(f'{ticker}: no CIK')
        continue

    acc_raw = fname.rsplit('_', 1)[-1].replace('.htm', '')

    print(f'=== {ticker}/{year}  CIK={cik} ===')

    url = get_primary_doc_url(cik, acc_raw)
    if not url:
        print(f'  Could not find primary doc in index, acc={acc_raw}')
        print()
        continue
    print(f'URL: {url}')

    try:
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=20)
        print(f'HTTP {resp.status_code}  bytes={len(resp.content):,}')
    except Exception as e:
        print(f'FETCH ERROR: {e}')
        continue

    if resp.status_code != 200:
        print()
        continue

    soup = BeautifulSoup(resp.content, 'html.parser')
    for t in soup(['script', 'style']):
        t.decompose()
    text = soup.get_text(separator='\n', strip=True)

    # Show ALL occurrences of "chief executive officer" with context
    occurrences = [m.start() for m in re.finditer(
        r'chief executive officer', text, re.I)]
    print(f'Found "Chief Executive Officer" at {len(occurrences)} position(s)')

    for idx in occurrences[:3]:   # first 3 hits
        snippet = text[max(0, idx-200):idx+200]
        print(f'  --- snippet ---')
        print(snippet)
        print()

    # Try the actual extraction
    result = _extract_ceo_from_sec_text(text)
    print(f'>>> _extract_ceo_from_sec_text → {result!r}')
    print()
