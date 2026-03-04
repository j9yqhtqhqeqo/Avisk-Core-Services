import psycopg2
from Utilities.Lookups import DB_Connection
from Services.CEODataService import (
    _is_valid_name, _extract_ceo_from_sec_text, _extract_ceo_from_web_text
)
import sys
sys.path.insert(0, '.')

print('=== SEC/10-K patterns (strict) ===')
cases_sec = [
    # (description, text, expected)
    ('officer table',
     "Name                Age  Position\nTim Cook             63  Chief Executive Officer\nArt Levinson         68  Lead Independent Director\n",
     'Tim Cook'),
    ('signature block',
     "/s/ Tim Cook\nApple Inc.\nChief Executive Officer",
     'Tim Cook'),
    ('CEO immediately after title',
     "Chief Executive Officer  Tim Cook announced quarterly results.",
     'Tim Cook'),
    ('Northrop Grumman trap',
     "...served as Chief Executive Officer of Northrop Grumman Corporation before joining our board...",
     None),
    ('Art Levinson compensation trap',
     "The Compensation Committee, chaired by Art Levinson, reviewed the Chief Executive Officer compensation.",
     None),
    ('reverse with "of" gap (should fail)',
     "Chief Executive Officer of Apple Inc. since 2011, Tim Cook has led the company.",
     None),  # "since 2011, Tim Cook" is >50 chars from CEO... let's see
]

all_ok = True
for desc, text, expected in cases_sec:
    name = _extract_ceo_from_sec_text(text)
    ok = (name == expected)
    if not ok:
        all_ok = False
    print(
        f'  {"✅" if ok else "❌"} {desc:45} → {repr(name):20}  (want {repr(expected)})')

print()
print('=== Web/DDGS patterns (loose) ===')
cases_web = [
    ('forward: "Tim Cook CEO"',
     'Tim Cook is Apple Chief Executive Officer.',
     'Tim Cook'),
    ('forward: name then title',
     'Apple CEO Tim Cook unveiled the new iPhone today.',
     'Tim Cook'),
    ('reverse: title then name',
     "Apple's Chief Executive Officer Tim Cook said the company...",
     'Tim Cook'),
    ('reverse: title of company then name (50-char gap)',
     "Chief Executive Officer of Apple Inc., Tim Cook announced...",
     'Tim Cook'),
    ('Northrop Grumman should NOT match in web text too',
     "served as Chief Executive Officer of Northrop Grumman before joining Apple's board.",
     None),  # "Northrop" not in blacklist but "Grumman" not either...
             # "Northrop Grumman" passes _is_valid_name unless we block it
    ('Bloomberg snippet style',
     'Tim Cook, Chief Executive Officer of Apple Inc., spoke at the event.',
     'Tim Cook'),
]

for desc, text, expected in cases_web:
    name = _extract_ceo_from_web_text(text)
    ok = (name == expected)
    if not ok:
        all_ok = False
    print(
        f'  {"✅" if ok else "❌"} {desc:45} → {repr(name):20}  (want {repr(expected)})')

print()
print('All OK:', all_ok)

# ── Delete bad rows ──
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()
cur.execute("""
    DELETE FROM t_ceo
    WHERE ticker = 'AAPL'
      AND (ceo_name ILIKE '%Northrop%' OR ceo_name ILIKE '%Grumman%')
""")
print(f'\nDeleted {cur.rowcount} bad Apple rows (Northrop Grumman)')
conn.commit()
cur.execute(
    "SELECT year, ceo_name, source FROM t_ceo WHERE ticker='AAPL' ORDER BY year")
print('Remaining Apple rows:')
for r in cur.fetchall():
    print(f'  {r}')
cur.close()
conn.close()
