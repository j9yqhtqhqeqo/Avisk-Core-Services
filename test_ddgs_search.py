#!/usr/bin/env python3
"""Test script for DuckDuckGo search functionality."""

from ddgs import DDGS

company_name = 'NVIDIA'
year = 2017
year_str = str(year)
pdf_urls = []

search_terms = [
    f'"{company_name}" sustainability report {year_str} filetype:pdf',
    f'"{company_name}" ESG report {year_str} filetype:pdf',
    f'"{company_name}" corporate responsibility report {year_str} filetype:pdf',
]

for query in search_terms:
    print(f'Searching: {query}')
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=15))
        for result in results:
            url = result.get('href', '')
            if not url:
                continue

            # Check if URL is a PDF
            is_pdf = url.lower().endswith('.pdf')
            if not is_pdf and '/pdf/' in url.lower():
                is_pdf = True

            if is_pdf and year_str in url:
                if url not in pdf_urls:
                    pdf_urls.append(url)
                    print(f'  Found: {url}')

print(f'\nTotal unique PDFs for {year}: {len(pdf_urls)}')
for url in pdf_urls:
    print(f'  - {url}')
