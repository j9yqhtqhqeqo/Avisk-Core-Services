"""
_fix_ceo_names.py
-----------------
Corrects all 🔴 critical and 🟠 suspicious CEO name issues identified
in the t_ceo audit, plus 🟡 minor spelling normalizations.

Run with:
    DEPLOYMENT_ENV=development python HelperFIles/_fix_ceo_names.py

Set DRY_RUN = False to commit changes to the DB.
"""
import psycopg2
import sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

DRY_RUN = False   # ← set to False to actually commit

# ─────────────────────────────────────────────────────────────────────────────
# Fix definitions
# Each entry: (ticker, year_or_None, old_name_or_None, new_name, note)
#   - year=None  → applies to ALL years for that ticker matching old_name
#   - old_name=None → matches any current name for that ticker/year
# ─────────────────────────────────────────────────────────────────────────────
FIXES = [
    # ══════════════════════════════════════════════════════════════════════════
    # 🔴 CRITICAL — non-person names
    # ══════════════════════════════════════════════════════════════════════════

    # AOS (A.O. Smith) — DDGS hallucinations (Ajita Rajendra was CEO 2012–2018)
    ('AOS', 2016, 'Nashville Predators', 'Ajita Rajendra',   'DDGS hallucination → correct CEO'),
    ('AOS', 2017, 'Columbia Bar',        'Ajita Rajendra',   'DDGS hallucination → correct CEO'),

    # PNW (Pinnacle West) — DDGS returned company name instead of person
    # Jeff Guldner became CEO Nov 2020; covers 2021-2024 too (fixed below)
    ('PNW', 2024, 'Arizona Public Service', 'Jeff Guldner',  'Company name not a person'),

    # AMD / GM — local_10k extracted section header instead of CEO name
    ('AMD', 2025, 'Segment Reporting', 'Lisa Su',            'Section header, not a person'),
    ('GM',  2025, 'Segment Reporting', 'Mary Barra',         'Section header, not a person'),

    # HUBB (Hubbell) — local_10k extracted supplier/partner name
    # Gerben Bakker became CEO Jan 2021; Bill Sperry became CEO Jan 2024
    ('HUBB', 2024, 'Bosch Rexroth', 'William Sperry',        'Supplier name, not a person; Sperry is CEO from 2024'),
    ('HUBB', 2025, 'Bosch Rexroth', 'William Sperry',        'Supplier name, not a person'),

    # GE — DDGS returned an unrelated UAE executive name (Larry Culp still GE Aerospace CEO)
    ('GE', 2025, 'Mahmood Alhay Alhameli', 'Larry Culp',     'Unrelated person; Culp is GE Aerospace CEO'),

    # FFIV (F5) — DDGS hallucination (Locoh-Donou still CEO in 2025)
    ('FFIV', 2025, 'Cajou Espoir', 'François Locoh-Donou',   'DDGS hallucination → correct CEO'),

    # ══════════════════════════════════════════════════════════════════════════
    # 🟠 SUSPICIOUS — likely wrong person
    # ══════════════════════════════════════════════════════════════════════════

    # AOS 2015 — Nikolas Mamais is not A.O. Smith's CEO; Ajita Rajendra was (2012–2018)
    ('AOS', 2015, 'Nikolas Mamais', 'Ajita Rajendra',         'Wrong person; Rajendra was CEO 2012-2018'),

    # ALB (Albemarle) — Jesse Eisinger is a journalist, not an Albemarle CEO
    # Luke Kissam retired mid-2019; Kent Masters became CEO Oct 2020
    ('ALB', 2019, 'Jesse Eisinger', 'Luke Kissam',            'Eisinger is a journalist; Kissam was CEO to mid-2019'),
    ('ALB', 2020, 'Jesse Eisinger', 'Kent Masters',           'Eisinger is a journalist; Masters became CEO Oct 2020'),
    ('ALB', 2021, 'Jesse Eisinger', 'Kent Masters',           'Eisinger is a journalist'),
    ('ALB', 2022, 'Jesse Eisinger', 'Kent Masters',           'Eisinger is a journalist'),
    ('ALB', 2023, 'Jesse Eisinger', 'Kent Masters',           'Eisinger is a journalist'),
    ('ALB', 2024, 'Jesse Eisinger', 'Kent Masters',           'Eisinger is a journalist'),

    # PNW — Jeffrey Sterba retired in 2009; Jeff Guldner became CEO Nov 2020
    # Donald Brandt was CEO 2009-2020; Guldner took over Nov 2020
    ('PNW', 2020, 'Jeffrey Sterba', 'Jeff Guldner',           'Sterba retired 2009; Guldner became CEO Nov 2020'),
    ('PNW', 2021, 'Jeffrey Sterba', 'Jeff Guldner',           'Sterba retired 2009; Guldner is CEO'),
    ('PNW', 2022, 'Jeffrey Sterba', 'Jeff Guldner',           'Sterba retired 2009; Guldner is CEO'),
    ('PNW', 2023, 'Jeffrey Sterba', 'Jeff Guldner',           'Sterba retired 2009; Guldner is CEO'),

    # GWW (Grainger) — "James Ryan Terwilliger" is two names merged; CEO was James Ryan
    ('GWW', 2013, 'James Ryan Terwilliger', 'James Ryan',     'Two names merged; only James Ryan was CEO'),
    # GWW 2021-2023 — Donald Davis is not Grainger's CEO; DG (Donald) Macpherson has been CEO since 2017
    ('GWW', 2021, 'Donald Davis', 'Donald Macpherson',        'Wrong person; Macpherson (DG) is CEO since 2017'),
    ('GWW', 2022, 'Donald Davis', 'Donald Macpherson',        'Wrong person; Macpherson (DG) is CEO since 2017'),
    ('GWW', 2023, 'Donald Davis', 'Donald Macpherson',        'Wrong person; Macpherson (DG) is CEO since 2017'),

    # HUBB (Hubbell) — David Nord became CEO Jan 2014, not 2013; 2013 was David Roberts
    ('HUBB', 2013, 'David Nord', 'David Roberts',             'Nord started Jan 2014; Roberts was CEO in 2013'),
    # HUBB 2021-2023 — Gerald Podobnik/McGowan are wrong; Gerben Bakker became CEO Jan 2021
    ('HUBB', 2021, 'Gerald Podobnik', 'Gerben Bakker',        'Bakker became CEO Jan 2021'),
    ('HUBB', 2022, 'Gerald McGowan',  'Gerben Bakker',        'Bakker was CEO in 2022'),
    ('HUBB', 2023, 'Gerald McGowan',  'Gerben Bakker',        'Bakker was CEO until Jan 2024'),

    # CINF (Cincinnati Financial) — Kenneth Stecher was CEO 2010-2015; Johnston from 2016
    ('CINF', 2012, 'David Caldwell',   'Kenneth Stecher',     'Caldwell not CINF CEO; Stecher was CEO 2010-2015'),
    ('CINF', 2013, 'David Padernacht', 'Kenneth Stecher',     'Padernacht not CINF CEO; Stecher was CEO 2010-2015'),
    ('CINF', 2014, 'David Padernacht', 'Kenneth Stecher',     'Padernacht not CINF CEO; Stecher was CEO 2010-2015'),
    # CINF 2024 — Steven Johnston was still CEO in 2024; John Fischer is not CINF CEO
    ('CINF', 2024, 'John Fischer',     'Steven Johnston',     'Fischer not CINF CEO; Johnston was CEO through 2024'),

    # TPL (Texas Pacific Land) — "Tyler Glover Tyler" is malformed (Glover is correct)
    ('TPL', 2012, 'Tyler Glover Tyler', 'Tyler Glover',       'Malformed duplicate-word name'),

    # FFIV 2024 — Manny Rivelo was CEO of Riverbed, not F5; Locoh-Donou is still F5 CEO
    ('FFIV', 2024, 'Manny Rivelo', 'François Locoh-Donou',    'Rivelo is Riverbed CEO, not F5'),

    # ══════════════════════════════════════════════════════════════════════════
    # 🟡 MINOR — spelling normalization (same person)
    # ══════════════════════════════════════════════════════════════════════════

    # GE — normalize Jeff/Jeffrey Immelt
    ('GE', 2016, 'Jeff Immelt', 'Jeffrey Immelt',             'Normalize to full legal first name'),
    # GE — normalize Larry/Lawrence Culp
    ('GE', 2019, 'Lawrence Culp Jr', 'Larry Culp',            'Normalize to preferred name'),
    ('GE', 2021, 'Lawrence Culp Jr', 'Larry Culp',            'Normalize to preferred name'),
    ('GE', 2024, 'Lawrence Culp',    'Larry Culp',            'Normalize to preferred name'),

    # PYPL — normalize Dan/Daniel Schulman
    ('PYPL', 2016, 'Daniel Schulman', 'Dan Schulman',         'Normalize to preferred name'),
    ('PYPL', 2020, 'Daniel Schulman', 'Dan Schulman',         'Normalize to preferred name'),
    ('PYPL', 2021, 'Daniel Schulman', 'Dan Schulman',         'Normalize to preferred name'),
    ('PYPL', 2022, 'Daniel Schulman', 'Dan Schulman',         'Normalize to preferred name'),

    # FFIV — add missing accent: Francois → François
    ('FFIV', 2016, 'Francois Locoh-Donou', 'François Locoh-Donou', 'Add correct accent'),
    ('FFIV', 2017, 'Francois Locoh-Donou', 'François Locoh-Donou', 'Add correct accent'),
    ('FFIV', 2018, 'Francois Locoh-Donou', 'François Locoh-Donou', 'Add correct accent'),
]

# ─────────────────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()

total_fixed = 0
total_skipped = 0

print(f"{'DRY RUN — no changes committed' if DRY_RUN else '⚠️  LIVE MODE — changes WILL be committed'}")
print("=" * 80)

for (ticker, year, old_name, new_name, note) in FIXES:
    # Build query
    if old_name is not None and year is not None:
        cur.execute(
            "SELECT ceo_id, ceo_name, source FROM t_ceo WHERE ticker=%s AND year=%s AND ceo_name=%s",
            (ticker, year, old_name)
        )
    elif old_name is not None and year is None:
        cur.execute(
            "SELECT ceo_id, ceo_name, source FROM t_ceo WHERE ticker=%s AND ceo_name=%s",
            (ticker, old_name)
        )
    elif old_name is None and year is not None:
        cur.execute(
            "SELECT ceo_id, ceo_name, source FROM t_ceo WHERE ticker=%s AND year=%s",
            (ticker, year)
        )
    else:
        continue

    rows = cur.fetchall()
    if not rows:
        print(f"  ⚠️  NOT FOUND  [{ticker:<6}] year={year}  old='{old_name}'")
        total_skipped += 1
        continue

    for (ceo_id, current_name, source) in rows:
        tag = '🔴' if 'hallucination' in note.lower() or 'not a person' in note.lower() or 'journalist' in note.lower() or 'section header' in note.lower() or 'supplier' in note.lower() or 'unrelated' in note.lower() \
              else ('🟠' if 'wrong person' in note.lower() or 'retired' in note.lower() or 'merged' in note.lower() or 'malformed' in note.lower() or 'started' in note.lower() \
              else '🟡')
        print(f"  {tag} [{ticker:<6}] year={year}  '{current_name}'  →  '{new_name}'")
        print(f"       Note: {note}  |  source={source}  |  ceo_id={ceo_id}")
        if not DRY_RUN:
            cur.execute(
                "UPDATE t_ceo SET ceo_name=%s, source='manual_fix', modify_dt=NOW() WHERE ceo_id=%s",
                (new_name, ceo_id)
            )
        total_fixed += 1

print()
print("=" * 80)
print(f"  Fixes applied : {total_fixed}")
print(f"  Not found     : {total_skipped}")

if DRY_RUN:
    conn.rollback()
    print("\n  ✅ DRY RUN complete — nothing committed. Set DRY_RUN=False to apply.")
else:
    conn.commit()
    print("\n  ✅ All changes committed to t_ceo.")

cur.close()
conn.close()
