"""Parse and display _ceo_verification_report.csv."""
import csv
from collections import defaultdict, Counter

path = '/Users/mohanganadal/Avisk/Avisk-Core-Services/HelperFIles/_ceo_verification_report.csv'

with open(path, newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

status_count = Counter(r['status'] for r in rows)
print("=" * 72)
print("  CEO VERIFICATION SUMMARY")
print("=" * 72)
print(f"  Total rows : {len(rows)}")
for s, c in status_count.most_common():
    icon = {'MATCH': 'OK', 'LIKELY_SAME': '~~', 'MISMATCH': '!!', 'NO_FMP_REF': '--'}.get(s, '  ')
    print(f"  [{icon}] {s:<15}: {c}")

mismatches = [r for r in rows if r['status'] == 'MISMATCH']
likely     = [r for r in rows if r['status'] == 'LIKELY_SAME']

# ── LIKELY_SAME (nickname / preferred-name variants) ─────────────────────────
if likely:
    print()
    print(f"  ~~ LIKELY_SAME  ({len(likely)} rows — first-name prefix/nickname variants)")
    likely_by_ticker = defaultdict(list)
    for r in likely:
        likely_by_ticker[r['ticker']].append(r)
    for tkr in sorted(likely_by_ticker.keys()):
        for r in sorted(likely_by_ticker[tkr], key=lambda x: int(x['year'])):
            print(f"    {r['ticker']:<6} {r['year']}  DB='{r['db_ceo']}'  FMP='{r['fmp_ceo']}'")

# ── MISMATCH (genuine wrong-person candidates) ────────────────────────────────
mism_by_ticker = defaultdict(list)
for r in mismatches:
    mism_by_ticker[r['ticker']].append(r)

print()
print("=" * 72)
print(f"  !! MISMATCHES  ({len(mismatches)} rows across {len(mism_by_ticker)} tickers)")
print("=" * 72)
if mismatches:
    for tkr in sorted(mism_by_ticker.keys()):
        for r in sorted(mism_by_ticker[tkr], key=lambda x: int(x['year'])):
            print(
                f"  {r['ticker']:<6} {r['year']}  "
                f"DB='{r['db_ceo']}'  "
                f"FMP='{r['fmp_ceo']}'  "
                f"[fmp={r['fmp_source']}  db={r['db_source']}]"
            )
else:
    print("  None found!")

print()
print("Done.")
