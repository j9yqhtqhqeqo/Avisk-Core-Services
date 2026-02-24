from collections import Counter
import psycopg2
from Utilities.Lookups import DB_Connection
import sys
import re
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("""
    SELECT unique_id, source_url, original_source_url
    FROM t_data_source
    WHERE content_type = 3
    ORDER BY unique_id
""")
rows = cur.fetchall()
print(f"Total content_type=3 rows: {len(rows)}\n")

# Rules: check URL/filename for known form type signals
FORM_RULES = [
    # SEC EDGAR form types from URL patterns
    (r'\bdef\s?14a\b|proxy',                   'DEF 14A'),
    (r'\b10[\-_]?q\b',                          '10-Q'),
    (r'\b10[\-_]?k\b',                          '10-K'),
    (r'\b20[\-_]?f\b',                          '20-F'),
    (r'\b8[\-_]?k\b',                           '8-K'),
    (r'\b6[\-_]?k\b',                           '6-K'),
    (r'\bs[\-_]?1\b',                           'S-1'),
    (r'\bsc\s?13[dg]\b',                        'SC 13G'),
    (r'\bform[\-_]?4\b',                        'Form 4'),
    (r'\bars\b|annual.report|annual-report',    'ARS'),
    # Sustainability/ESG
    (r'sustainab|esg|csr|responsibility|environment|citizenship|impact.report|social', 'ESG'),
    # Transcripts
    (r'transcript|earnings.call|earnings-call|investor.day', 'TRANSCRIPT'),
    # Press releases / financial results
    (r'press.release|financial.results|quarterly.results|earnings.release', 'PRESS-RELEASE'),
    # Investor presentations
    (r'investor.present|investor-present|presenta|roadshow',  'PRESENTATION'),
    # Factsheets / supplemental data
    (r'supplement|factsheet|fact.sheet|data.book', 'SUPPLEMENT'),
]


def detect_form(url_str: str) -> str:
    if not url_str:
        return None
    s = url_str.lower()
    for pattern, form in FORM_RULES:
        if re.search(pattern, s):
            return form
    return None


detected = Counter()
updates = []  # (form_type, unique_id)

for uid, source_url, orig_url in rows:
    combined = (source_url or '') + ' ' + (orig_url or '')
    form = detect_form(combined)
    detected[form or 'OTHER'] += 1
    if form and form != 'OTHER':
        updates.append((form, uid))

print("Detected form_type distribution for content_type=3:")
for form, cnt in detected.most_common():
    print(f"  {form!r:20s}  {cnt}")

print(f"\nWould update {len(updates)} rows to more specific form types")
print("\nSample of what would change:")
shown = Counter()
for form, uid in updates:
    if shown[form] < 3:
        shown[form] += 1
        # find the URL for display
        for r in rows:
            if r[0] == uid:
                print(f"  → {form:15s}  {(r[1] or '')[:80]}")
                break

cur.close()
conn.close()
