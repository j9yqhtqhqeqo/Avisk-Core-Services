"""Check Apple 8-K exhibits properly using HTM index."""
import requests
import re
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

found_transcript = False
# Check 12 8-Ks using the correct .htm index URL
for date, accn in eightks[3:15]:
    accn_clean = accn.replace('-', '')
    url = f'https://www.sec.gov/Archives/edgar/data/320193/{accn_clean}/{accn}-index.htm'
    time.sleep(0.3)
    ri = requests.get(url, headers={**HDRS, 'Host': 'www.sec.gov'}, timeout=20)
    if ri.status_code != 200:
        print(f"8-K {date}: HTTP {ri.status_code}")
        continue
    html = ri.text
    # Extract exhibit rows from the table
    # Find all rows with EX-99
    rows = re.findall(
        r'<tr[^>]*>.*?</tr>', html, re.DOTALL | re.IGNORECASE)
    ex99_rows = [r for r in rows if 'EX-99' in r]
    if not ex99_rows:
        print(f"8-K {date}: no EX-99 exhibits")
        continue
    print(f"\n8-K {date}:")
    for row in ex99_rows:
        # Extract text from cells
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row,
                           re.DOTALL | re.IGNORECASE)
        cells_clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        print(f"  {cells_clean}")
        for c in cells_clean:
            if 'transcript' in c.lower():
                found_transcript = True

print(f"\n==> Any transcript exhibit found: {found_transcript}")
print("NOTE: EX-99.1 = usually press release, EX-99.2 = sometimes transcript")
