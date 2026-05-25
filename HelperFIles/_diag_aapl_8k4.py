"""Inspect EDGAR index using the .htm format to see what Apple files."""
import requests
import time

HDRS = {
    'User-Agent': 'Avisk research@avisk.ai',
    'Accept-Encoding': 'gzip, deflate',
}

r = requests.get(
    'https://data.sec.gov/submissions/CIK0000320193.json',
    headers={**HDRS, 'Host': 'data.sec.gov'},
    timeout=30,
)
data = r.json()
filings = data['filings']['recent']
forms = filings['form']
dates = filings['filingDate']
accessions = filings['accessionNumber']
primary_docs = filings.get('primaryDocument', [])
primary_doc_desc = filings.get('primaryDocDescription', [])

eightks = [
    (dates[i], accessions[i],
     primary_docs[i] if i < len(primary_docs) else '',
     primary_doc_desc[i] if i < len(primary_doc_desc) else '')
    for i, f in enumerate(forms) if f == '8-K'
]
print(f"Total AAPL 8-Ks: {len(eightks)}")

# Show what fields are available in the submissions data
print("\nFields in filings:", list(filings.keys()))

# Print first 10 8-K entries with all available metadata
print("\nFirst 10 8-Ks from submissions API:")
for date, accn, pdoc, pdoc_desc in eightks[:10]:
    print(f"  {date}  {accn}  primaryDoc={pdoc}  desc={pdoc_desc}")

# Try fetching one known filing -- Apple Q1 FY2025 earnings (Jan 30, 2025)
# Get accession for that date
for date, accn, pdoc, _ in eightks:
    if date == '2025-01-30':
        accn_clean = accn.replace('-', '')
        print(f"\nApple Q1 FY2025 8-K: accn={accn}")
        # Try the EDGAR viewer API
        url = f'https://efts.sec.gov/LATEST/search-index?q=%22earnings+call%22&dateRange=custom&startdt=2025-01-28&enddt=2025-02-01&entity=Apple+Inc'
        ri = requests.get(url, headers=HDRS, timeout=20)
        print(f"EFTS status: {ri.status_code}")
        # Try direct filing page
        for suffix in [f'{accn}-index.htm', f'{accn_clean}-index.json']:
            url2 = f'https://www.sec.gov/Archives/edgar/data/320193/{accn_clean}/{suffix}'
            ri2 = requests.get(
                url2, headers={**HDRS, 'Host': 'www.sec.gov'}, timeout=20)
            print(f"  {suffix}: HTTP {ri2.status_code}")
            if ri2.status_code == 200 and 'json' not in suffix:
                # Parse simple HTML to find exhibits
                text = ri2.text
                for line in text.split('\n'):
                    if 'EX-99' in line or 'transcript' in line.lower():
                        print(f"    {line.strip()[:120]}")
        break
