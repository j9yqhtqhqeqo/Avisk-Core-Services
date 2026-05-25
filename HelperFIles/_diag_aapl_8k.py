"""Check what Apple files in 8-Ks — do they attach transcripts?"""
import os
import requests
import sys
import json
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

HDRS = {'User-Agent': 'Avisk research@avisk.ai',
        'Accept-Encoding': 'gzip, deflate'}

r = requests.get('https://data.sec.gov/submissions/CIK0000320193.json',
                 headers={**HDRS, 'Host': 'data.sec.gov'}, timeout=30)
data = r.json()
filings = data['filings']['recent']
forms = filings['form']
dates = filings['filingDate']
accessions = filings['accessionNumber']

eightks = [(d, a) for f, d, a in zip(forms, dates, accessions) if f == '8-K']
print(f"Total AAPL 8-Ks in recent history: {len(eightks)}")
print(f"Years: {sorted(set(d[:4] for d,_ in eightks))}")

# Inspect the 4 most recent 8-Ks
for date, accn in eightks[:4]:
    accn_clean = accn.replace('-', '')
    idx_url = f'https://www.sec.gov/Archives/edgar/data/320193/{accn_clean}/{accn}-index.json'
    ri = requests.get(idx_url, headers={
                      **HDRS, 'Host': 'www.sec.gov'}, timeout=20)
    print(f"\n--- 8-K {date} (HTTP {ri.status_code}) ---")
    if ri.status_code == 200:
        idx = ri.json()
        for doc in idx.get('documents', []):
            print(
                f"  type={doc.get('type','?'):15}  desc={doc.get('description','?')[:60]:60}  file={doc.get('filename','?')}")
