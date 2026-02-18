#!/usr/bin/env python
"""Test script for sustainability report download with DB integration"""

from Services.SustainabilityReportDownloader import SustainabilityReportDownloader
import os

# Use context manager for automatic cleanup
with SustainabilityReportDownloader() as downloader:
    print('Testing download for Apple Inc...')
    result = downloader.process_company(
        'AAPL', 'Apple Inc.', 'https://www.apple.com')

    print()
    print(f'Reports found: {result["reports_found"]}')
    print(f'Reports downloaded: {result["reports_downloaded"]}')

    # Count actual files
    files = os.listdir('sustainability_reports/AAPL')
    print(f'Actual files on disk: {len(files)}')

    # Check DB entries
    db_entries = [r.get('db_id')
                  for r in downloader.downloaded_reports if r.get('db_id')]
    print(f'Database entries created: {len(db_entries)}')

    print()
    print('Sample filenames:')
    for f in sorted(files)[:5]:
        print(f'  {f}')
