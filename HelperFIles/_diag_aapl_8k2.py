"""Check what Apple files in 8-Ks -- exhibits with transcript?"""
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
eightks = [(d, a) for f, d, a in zip(forms, dates, accessions) if f == '8-K']
print(f"Total AAPL 8-Ks in recent history: {len(eightks)}")

# Try 10 filings, skipping the most recent ones (may not be indexed yet)
found_any_transcript = False
for date, accn in eightks[3:15]:
    accn_clean = accn.replace('-', '')
    url = f'https://www.sec.gov/Archives/edgar/data/320193/{accn_clean}/{accn}-index.json'
    time.sleep(0.2)
    ri = requests.get(url, headers={**HDRS, 'Host': 'www.sec.gov'}, timeout=20)
    if ri.status_code != 200:
        print(f"8-K {date}: HTTP {ri.status_code}")
        continue
    idx = ri.json()
    docs = idx.get('documents', [])
    print(f"\n8-K {date}:")
    for doc in docs:
        t = doc.get('type', '?')
        desc = doc.get('description', '?')
        fname = doc.get('filename', '?')
        print(f"  {t:15}  {desc[:55]:55}  {fname}")
        if 'transcript' in desc.lower() or 'transcript' in fname.lower():
            found_any_transcript = True

print(f"\n==> Any transcript exhibit found: {found_any_transcript}")
