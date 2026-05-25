"""
Debug: check what EX-99.1 descriptions EDGAR returns for AAPL 8-K filings.
Run: python3 HelperFIles/_diag_pr_filter.py
"""
from bs4 import BeautifulSoup
from Services.AviskDataScraper import AviskDataScraper
import sys
import requests
import time
sys.path.insert(0, '.')


dl = AviskDataScraper(use_storage=True, content_types=[4])
hdrs = dl._get_edgar_session_headers()
www_hdrs = {**hdrs, 'Host': 'www.sec.gov'}
sub_hdrs = {**hdrs, 'Host': 'data.sec.gov'}

# Fetch AAPL submissions
resp = requests.get(dl.EDGAR_SUBMISSIONS_URL.format(
    cik=320193), headers=sub_hdrs, timeout=30)
sub = resp.json()
recent = sub['filings']['recent']

# Get the 5 most recent 8-K accessions
ex99_found = 0
for i, form in enumerate(recent['form']):
    if form != '8-K':
        continue
    accession = recent['accessionNumber'][i]
    date = recent['filingDate'][i]
    accession_nodash = accession.replace('-', '')

    index_url = f"https://www.sec.gov/Archives/edgar/data/320193/{accession_nodash}/{accession}-index.htm"
    try:
        time.sleep(0.2)
        r = requests.get(index_url, headers=www_hdrs, timeout=15)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} for {accession}")
            continue
        soup = BeautifulSoup(r.content, 'lxml')
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 4:
                continue
            dtype = cells[1].get_text(strip=True)
            desc = cells[2].get_text(strip=True)
            link = cells[3].find('a')
            fname = link['href'].split('/')[-1] if link else ''
            if dtype == 'EX-99.1':
                print(
                    f"DATE={date} | TYPE={dtype} | DESC={desc!r} | FILE={fname!r}")
                ex99_found += 1
    except Exception as e:
        print(f"  Error: {e}")

    if ex99_found >= 10:
        break

print(f"\nTotal EX-99.1 exhibits shown: {ex99_found}")
