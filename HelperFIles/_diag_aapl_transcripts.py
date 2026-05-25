"""
Diagnostic: test all transcript download paths for AAPL on the VM.
Run with: python3 HelperFIles/_diag_aapl_transcripts.py
"""
from Services.AviskDataScraper import AviskDataScraper
import sys
import logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


dl = AviskDataScraper(
    use_storage=True,
    year_filter=[2023, 2024],
    content_types=[4],
    force_reload=True,
    delay_seconds=0.5,
)

print('\n=== 1. get_company_website ===')
website = dl.get_company_website('AAPL', 'Apple Inc.')
print(f'website: {website!r}')

print('\n=== 2. download_edgar_transcripts (2023, 2024) ===')
try:
    paths = dl.download_edgar_transcripts(
        'AAPL', 'Apple Inc.', years_needed=[2023, 2024])
    print(f'EDGAR transcript paths ({len(paths)}): {paths}')
except Exception as e:
    print(f'ERROR: {e}')

print('\n=== 3. download_ir_website_transcripts ===')
if website:
    try:
        paths2 = dl.download_ir_website_transcripts(
            'AAPL', 'Apple Inc.', website, years_needed=[2023, 2024])
        print(f'IR transcript paths ({len(paths2)}): {paths2}')
    except Exception as e:
        print(f'ERROR: {e}')
else:
    print('No website found — IR scraper would be skipped')

print('\n=== 4. download_fmp_transcripts (2023) ===')
try:
    paths3 = dl.download_fmp_transcripts(
        'AAPL', 'Apple Inc.', years_needed=[2023])
    print(f'FMP paths ({len(paths3)}): {paths3}')
except Exception as e:
    print(f'ERROR: {e}')

print('\n=== 5. download_edgar_press_releases (2023, 2024) ===')
try:
    paths4 = dl.download_edgar_press_releases(
        'AAPL', 'Apple Inc.', years_needed=[2023, 2024])
    print(f'Press release paths ({len(paths4)}): {paths4}')
except Exception as e:
    print(f'ERROR: {e}')

print('\nDone.')
