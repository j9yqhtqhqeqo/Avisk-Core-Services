"""Diagnose FMP transcript endpoints for AAPL."""
import requests
import sys
import os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')


FMP_API_KEY = 'j1sUHyVT1lU3gsc2l6zF2jkuleFJEA2o'
SYMBOL = 'AAPL'

endpoints = [
    # current stable endpoint used by the code
    ('stable/earning-call-transcript (per-quarter)',
     'https://financialmodelingprep.com/stable/earning-call-transcript',
     {'symbol': SYMBOL, 'year': 2024, 'quarter': 1, 'apikey': FMP_API_KEY}),
    # v3 per-quarter
    ('v3/earning_call_transcript (per-quarter)',
     f'https://financialmodelingprep.com/api/v3/earning_call_transcript/{SYMBOL}',
     {'year': 2024, 'quarter': 1, 'apikey': FMP_API_KEY}),
    # v4 batch (returns all quarters for a year)
    ('v4/batch_earning_call_transcript',
     f'https://financialmodelingprep.com/api/v4/batch_earning_call_transcript/{SYMBOL}',
     {'year': 2024, 'apikey': FMP_API_KEY}),
    # stable list endpoint (no year/quarter — returns index)
    ('stable/earning-call-transcript (list/no-quarter)',
     'https://financialmodelingprep.com/stable/earning-call-transcript',
     {'symbol': SYMBOL, 'apikey': FMP_API_KEY}),
    # older 2016 data
    ('stable/earning-call-transcript 2016 Q1',
     'https://financialmodelingprep.com/stable/earning-call-transcript',
     {'symbol': SYMBOL, 'year': 2016, 'quarter': 1, 'apikey': FMP_API_KEY}),
]

for label, url, params in endpoints:
    try:
        r = requests.get(url, params=params, timeout=20)
        print(f"\n--- {label} ---")
        print(f"  HTTP {r.status_code}  url={r.url[:120]}")
        if r.status_code == 200:
            d = r.json()
            print(
                f"  type={type(d).__name__}  len={len(d) if isinstance(d, list) else 'n/a'}")
            if isinstance(d, list) and d:
                print(f"  keys={list(d[0].keys())}")
                content = d[0].get('content') or d[0].get('transcript') or ''
                print(f"  content_length={len(content)}")
                if content:
                    print(f"  content_preview={content[:100]!r}")
            elif isinstance(d, dict):
                print(f"  keys={list(d.keys())}")
        else:
            print(f"  body={r.text[:200]}")
    except Exception as e:
        print(f"\n--- {label} ---")
        print(f"  ERROR: {e}")
