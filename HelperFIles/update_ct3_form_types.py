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

# Rules checked in order — first match wins.
# S-1 excluded: s1.q4cdn.com is a CDN host, not an SEC S-1 filing.
FORM_RULES = [
    # Must check transcript / press-release before ESG to avoid false ESG hits
    (r'transcript|earnings.call|earnings-call|investor.day',              'TRANSCRIPT'),
    (r'press.release|financial.results|quarterly.results|earnings.release', 'PRESS-RELEASE'),
    (r'investor.present|investor-present|presenta|roadshow',              'PRESENTATION'),
    (r'supplement|factsheet|fact.sheet|data.book',                        'SUPPLEMENT'),
    # SEC form types — match on filename/URL path only, not CDN host
    (r'[\-_/]def\s?14a[\-_/.]|[\-_/]proxy[\-_/.]',                       'DEF 14A'),
    (r'[\-_/]10[\-_]?q[\-_/.]',                                           '10-Q'),
    (r'[\-_/]8[\-_]?k[\-_/.]|earnings.release.8.k|-8-k-',                '8-K'),
    (r'[\-_/]6[\-_]?k[\-_/.]',                                            '6-K'),
    (r'[\-_/]20[\-_]?f[\-_/.]',                                           '20-F'),
    # Annual report shareholder (ARS)
    (r'\bars[\-_.]|\-ars[\-_.]|annual.report.shareholder',                'ARS'),
    # Sustainability/ESG — only after more specific checks
    (r'sustainab|esg|csr|responsibility|environment|citizenship|impact.report|social.report', 'ESG'),
]


def detect_form(url_str: str) -> str:
    if not url_str:
        return None
    s = url_str.lower()
    for pattern, form in FORM_RULES:
        if re.search(pattern, s):
            return form
    return None


updates = []
for uid, source_url, orig_url in rows:
    combined = (source_url or '') + ' ' + (orig_url or '')
    form = detect_form(combined)
    if form:
        updates.append((form, uid))

print(f"Updating {len(updates)} rows...")
dist = Counter(f for f, _ in updates)
for form, cnt in dist.most_common():
    print(f"  {form!r:20s}  {cnt}")

for form, uid in updates:
    cur.execute(
        "UPDATE t_data_source SET form_type = %s WHERE unique_id = %s",
        (form, uid)
    )

conn.commit()

cur.execute(
    "SELECT COUNT(*) FROM t_data_source WHERE content_type = 3 AND form_type = 'OTHER'")
remaining_other = cur.fetchone()[0]
print(f"\nStill 'OTHER' after update: {remaining_other}")

cur.execute("""
    SELECT form_type, COUNT(*) FROM t_data_source
    WHERE content_type = 3
    GROUP BY form_type ORDER BY COUNT(*) DESC
""")
print("\nFinal content_type=3 distribution:")
for r in cur.fetchall():
    print(f"  {r[0]!r:20s}  {r[1]}")

cur.close()
conn.close()
