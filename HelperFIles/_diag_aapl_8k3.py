"""Check Apple 8-K exhibits on EDGAR using correct URL format."""
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
print(f"Total AAPL 8-Ks: {len(eightks)}")

found_any_transcript = False
# Try multiple URL styles to find which one works
for date, accn in eightks[3:12]:
    accn_clean = accn.replace('-', '')
    time.sleep(0.3)
    # Try both nodash and dashed variants via www.sec.gov AND data.sec.gov
    success = False
    for base_domain, host, fname_accn in [
        ('https://www.sec.gov/Archives/edgar/data/320193', 'www.sec.gov', accn_clean),
        ('https://www.sec.gov/Archives/edgar/data/320193', 'www.sec.gov', accn),
        ('https://data.sec.gov/Archives/edgar/data/320193', 'data.sec.gov', accn_clean),
    ]:
        url = f'{base_domain}/{accn_clean}/{fname_accn}-index.json'
        ri = requests.get(url, headers={**HDRS, 'Host': host}, timeout=20)
        if ri.status_code == 200:
            idx = ri.json()
            docs = idx.get('documents', [])
            print(f"\n8-K {date} [OK via {host} fname={fname_accn[:10]}]:")
            for doc in docs:
                t = doc.get('type', '?')
                desc = doc.get('description', '?')
                fname = doc.get('filename', '?')
                print(f"  {t:15}  {desc[:55]:55}  {fname}")
                if 'transcript' in desc.lower() or 'transcript' in fname.lower():
                    found_any_transcript = True
            success = True
            break
    if not success:
        print(f"8-K {date}: all URLs 404")

print(f"\n==> Any transcript exhibit found: {found_any_transcript}")
