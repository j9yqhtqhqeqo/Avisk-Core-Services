"""
Diagnostic: step through every CEO source for AAPL year-by-year.
Run with:
  conda run -n data-company-gcc python3 HelperFIles/_diag_aapl_ceo.py 2>&1
"""
from pathlib import Path
import fitz
from Services.CEODataService import (
    _fmp_get, _is_valid_name,
    _extract_ceo_from_sec_text, _extract_ceo_from_web_text,
    _SEC_CEO_PATTERNS, _WEB_CEO_PATTERNS,
    fetch_ceo_from_fmp, fetch_ceo_from_ddgs,
)
from Utilities.Lookups import DB_Connection
import psycopg2
import sys
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')


# ── 1. FMP raw response ──────────────────────────────────────────────────────

YEARS = list(range(2012, 2027))
TICKER = 'AAPL'
COMPANY = 'Apple Inc'

print("=" * 70)
print("1. FMP /historical-key-executives raw dump for AAPL")
print("=" * 70)
data = _fmp_get('/historical-key-executives', {'symbol': TICKER})
if not data:
    print("  ❌  No data returned from FMP!")
else:
    print(f"  {len(data)} records")
    for ex in data:
        title = ex.get('title', '')
        if 'chief executive' in title.lower() or title.strip().lower() == 'ceo':
            print(f"  CEO: name={ex.get('name')!r}  title={title!r}")
            print(
                f"       yearActive={ex.get('yearActive')}  startDate={ex.get('startDate')}  endDate={ex.get('endDate')}")

print()
print("=" * 70)
print("2. FMP fetch_ceo_from_fmp per year")
print("=" * 70)
for yr in YEARS:
    name, src = fetch_ceo_from_fmp(TICKER, yr)
    print(f"  {yr}: name={name!r:20}  src={src!r}")

print()
print("=" * 70)
print("3. _is_valid_name checks for likely FMP names")
print("=" * 70)
candidates = ['Tim Cook', 'Timothy Cook', 'Timothy D. Cook',
              'Steve Jobs', 'Stephen Jobs']
for c in candidates:
    print(f"  {c!r:30} → valid={_is_valid_name(c)}")

print()
print("=" * 70)
print("4. Local 10-K PDF text analysis  (first CEO pattern match per year)")
print("=" * 70)
try:
    from Utilities.PathConfiguration import PathConfiguration
    base_path = PathConfiguration().get_stage0_input_path()
    print(f"  base_path = {base_path}")
except Exception as e:
    print(f"  PathConfiguration error: {e}")
    base_path = None

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)

for yr in YEARS:
    # Find what PDF files exist for this year
    with conn.cursor() as cur:
        cur.execute("""
            SELECT source_url FROM t_data_source
            WHERE content_type=2 AND year=%s
              AND (ticker ILIKE %s OR company_name ILIKE %s)
            ORDER BY source_confidence_score DESC NULLS LAST, unique_id DESC
            LIMIT 3
        """, (yr, TICKER, COMPANY))
        rows = cur.fetchall()

    if not rows:
        print(f"  {yr}: no PDF in t_data_source")
        continue

    for (filename,) in rows:
        if not filename:
            continue
        if base_path:
            pdf_path = Path(base_path) / str(yr) / filename
        else:
            print(f"  {yr}: base_path unavailable, skipping")
            break

        if not pdf_path.exists():
            print(f"  {yr}: PDF not found: {pdf_path.name}")
            continue

        doc = fitz.open(str(pdf_path))
        total = len(doc)
        pages = sorted(set(
            list(range(min(30, total))) +
            list(range(max(0, total - 15), total))
        ))
        text = '\n'.join(doc[pg].get_text() for pg in pages)
        doc.close()

        # Normalize like _extract_ceo_from_sec_text does
        norm = re.sub(r'[ \t]{2,}', ' ', text)

        # Show all "Chief Executive" contexts
        ceo_indices = [m.start()
                       for m in re.finditer(r'Chief Executive', norm)]
        print(
            f"\n  {yr}: {pdf_path.name} | {len(ceo_indices)} 'Chief Executive' hits")
        for idx in ceo_indices[:8]:
            snippet = norm[max(0, idx-80):idx+120].replace('\n', '↵')
            print(f"    …{snippet}…")

        # Show which pattern matches and what it captures
        print(f"  {yr}: Pattern matches →")
        for i, pat in enumerate(_SEC_CEO_PATTERNS):
            for m in pat.finditer(norm):
                candidate = re.sub(r'\s+', ' ', m.group(1)).strip()
                valid = _is_valid_name(candidate)
                ctx = norm[max(0, m.start()-40):m.end()+40].replace('\n', '↵')
                print(
                    f"    Pat[{i}] candidate={candidate!r:25} valid={valid}  ctx=…{ctx}…")

        name = _extract_ceo_from_sec_text(text)
        print(f"  {yr}: → FINAL: {name!r}")
        break  # only first PDF per year

conn.close()

print()
print("=" * 70)
print("5. DDGS test for a few years")
print("=" * 70)
for yr in [2013, 2019, 2023]:
    name, src = fetch_ceo_from_ddgs(COMPANY, yr)
    print(f"  {yr}: name={name!r}  src={src!r}")
