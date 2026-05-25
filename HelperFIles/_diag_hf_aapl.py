#!/usr/bin/env python3
"""
Diagnostic: Test HuggingFace transcript download for AAPL directly.
Run on VM:
  sudo -u avisk bash -c 'export PYTHONPATH=/opt/avisk/app; \
    /opt/avisk/venv/bin/python3 /opt/avisk/app/HelperFIles/_diag_hf_aapl.py'
"""
import logging
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, '/opt/avisk/app')

# Load env
load_dotenv('/opt/avisk/config/.env')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("AAPL HuggingFace Transcript Diagnostic")
print("=" * 60)

# Step 1: Can we instantiate AviskDataScraper with content_types=[4]?
try:
    from Services.AviskDataScraper import AviskDataScraper
    dl = AviskDataScraper(
        download_dir='/tmp/diag_transcripts',
        delay_seconds=1.0,
        use_storage=False,
        content_types=[4],
        year_filter=[2024, 2023],
    )
    print(f"✅ AviskDataScraper instantiated OK")
    print(f"   content_types = {dl.content_types}")
    print(f"   download_dir  = {dl.base_download_dir}")
except Exception as e:
    print(f"❌ Failed to instantiate AviskDataScraper: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test the HF cache
print("\n--- Step 2: HF Cache ---")
try:
    cache_path = dl._ensure_hf_cache()
    if cache_path:
        print(f"✅ HF cache ready: {cache_path}")
        print(f"   Size: {cache_path.stat().st_size / 1_000_000:.1f} MB")
    else:
        print("❌ HF cache download failed")
        sys.exit(1)
except Exception as e:
    print(f"❌ HF cache error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Check if AAPL is in the dataset
print("\n--- Step 3: AAPL in HF dataset ---")
try:
    import pandas as pd
    df = pd.read_parquet(str(cache_path))
    print(f"   Dataset rows: {len(df)}")
    print(f"   Columns: {list(df.columns)}")

    aapl_df = df[df['ticker'].str.upper() == 'AAPL']
    print(f"   AAPL rows: {len(aapl_df)}")

    if not aapl_df.empty:
        print(f"   Years available: {sorted(aapl_df['year'].unique())}")
        print(f"   Sample:")
        for _, row in aapl_df.head(3).iterrows():
            text = str(row.get('transcript', ''))[:100]
            print(
                f"     Q{row.get('quarter')} {row.get('year')}: {text[:80]}...")
    else:
        print("   ❌ AAPL not found in HF dataset!")
        # Show what tickers ARE there
        sample_tickers = sorted(df['ticker'].unique())[:30]
        print(f"   Sample tickers in dataset: {sample_tickers}")
except Exception as e:
    print(f"❌ Dataset read error: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Actually run the HF download for AAPL
print("\n--- Step 4: download_huggingface_transcripts(AAPL) ---")
try:
    paths = dl.download_huggingface_transcripts(
        'AAPL', 'Apple Inc.', years_needed=[2024, 2023, 2022])
    print(f"✅ Downloaded {len(paths)} transcript(s)")
    for p in paths:
        print(f"   {p}")
except Exception as e:
    print(f"❌ download_huggingface_transcripts failed: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Run full process_company for AAPL
print("\n--- Step 5: process_company(AAPL) with content_types=[4] ---")
try:
    result = dl.process_company(
        'AAPL', 'Apple Inc.', 'https://investor.apple.com')
    print(f"   status:                {result.get('status')}")
    print(f"   reports_downloaded:    {result.get('reports_downloaded', 0)}")
    print(
        f"   hf_transcripts:        {result.get('hf_transcripts_downloaded', 'n/a')}")
    print(
        f"   edgar_transcripts:     {result.get('edgar_transcripts_downloaded', 'n/a')}")
    print(
        f"   ir_transcripts:        {result.get('ir_transcripts_downloaded', 'n/a')}")
    print(
        f"   fmp_transcripts:       {result.get('fmp_transcripts_downloaded', 'n/a')}")
    print(
        f"   pr_fallback:           {result.get('pr_fallback_downloaded', 'n/a')}")
    print(f"   Full result: {result}")
except Exception as e:
    print(f"❌ process_company failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete.")
