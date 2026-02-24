"""
Read actual file content (PDF or HTM) for content_type=3 form_type='OTHER' records
and classify them based on what's inside the document.

Run on the VM:
  PYTHONPATH=/opt/avisk/app python3 /tmp/classify_ct3_by_content.py
"""
from collections import Counter
from pathlib import Path
import psycopg2
from Utilities.PathConfiguration import PathConfiguration
from Utilities.Lookups import DB_Connection
import sys
import re
sys.path.insert(0, '/opt/avisk/app')


# ── Form-type keyword rules (checked in order, first match wins) ─────────────
# Each entry: (regex_pattern, form_type_label)
CONTENT_RULES = [
    # Proxy / DEF 14A
    (r'proxy statement|notice of annual meeting|definitive proxy', 'DEF 14A'),
    # Quarterly report
    (r'quarterly report|form 10-q|10-q\b', '10-Q'),
    # 8-K current report
    (r'current report|form 8-k|pursuant to section 13 or 15', '8-K'),
    # 20-F foreign private issuer
    (r'annual report.*form 20-f|form 20-f', '20-F'),
    # 6-K
    (r'report of foreign private issuer|form 6-k', '6-K'),
    # Annual report to shareholders (not 10-K)
    (r'annual report to (shareholders|stockholders)', 'ARS'),
    # Earnings / press release
    (r'earnings per share|net income|revenue.*quarter|reports (first|second|third|fourth) quarter', 'PRESS-RELEASE'),
    # Investor presentation / slides
    (r'investor (day|presentation|conference)|roadshow', 'PRESENTATION'),
    # Supplemental / factsheet
    (r'supplemental (data|financial|information)|fact sheet', 'SUPPLEMENT'),
    # ESG / Sustainability
    (r'sustainability report|environmental.{0,20}social.{0,20}governance|esg report|corporate responsibility report|corporate social responsibility', 'ESG'),
    # Transcripts
    (r'operator:|good (morning|afternoon|evening).{0,60}(welcome|thank you for joining)|question.and.answer session', 'TRANSCRIPT'),
]


def classify_from_text(text: str) -> str:
    t = text.lower()
    for pattern, form in CONTENT_RULES:
        if re.search(pattern, t):
            return form
    return None


def read_pdf_text(filepath: Path, max_pages: int = 5) -> str:
    try:
        import fitz
        doc = fitz.open(str(filepath))
        parts = []
        for i in range(min(max_pages, doc.page_count)):
            parts.append(doc[i].get_text())
        doc.close()
        return ' '.join(parts)
    except Exception as e:
        return ''


def read_htm_text(filepath: Path, max_chars: int = 8000) -> str:
    try:
        raw = filepath.read_bytes()
        text = raw.decode('utf-8', errors='replace')
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text[:max_chars]
    except Exception as e:
        return ''


# ── Connect ───────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

base = Path(PathConfiguration().get_stage0_input_path())
print(f"Stage0 base: {base}")

cur.execute("""
    SELECT unique_id, year, source_url
    FROM t_data_source
    WHERE content_type = 3 AND form_type = 'OTHER'
    ORDER BY unique_id
""")
rows = cur.fetchall()
print(f"Rows to classify: {len(rows)}\n")

results = Counter()
updated = 0
not_found = 0
unclassified = 0

for uid, year, source_url in rows:
    if not source_url:
        unclassified += 1
        continue

    filepath = base / str(year) / source_url
    if not filepath.exists():
        not_found += 1
        continue

    ext = filepath.suffix.lower()
    if ext == '.pdf':
        text = read_pdf_text(filepath)
    elif ext in ('.htm', '.html', '.txt'):
        text = read_htm_text(filepath)
    else:
        unclassified += 1
        continue

    if not text.strip():
        unclassified += 1
        continue

    form = classify_from_text(text)
    if form:
        cur.execute(
            "UPDATE t_data_source SET form_type = %s WHERE unique_id = %s",
            (form, uid)
        )
        results[form] += 1
        updated += 1
    else:
        unclassified += 1

conn.commit()

print(f"Updated:      {updated}")
print(f"Not on disk:  {not_found}")
print(f"Unclassified: {unclassified}")
print(f"\nNew form_type assignments:")
for form, cnt in results.most_common():
    print(f"  {form!r:20s}  {cnt}")

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
