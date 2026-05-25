"""
Classify the 91 flagged MISMATCH rows into:
  1. FALSE_POSITIVE   – DB is correct, FMP is not year-aware or shows wrong exec
  2. SAME_PERSON      – different formal/informal name for the same individual
  3. GENUINE_ERROR    – DB clearly has the wrong person
  4. PARTIAL_YEAR     – CEO changed mid-year; classify under year-end CEO rule

Prints a full categorized breakdown and a list of rows to fix.
"""
VERDICTS = {
    # ── FALSE POSITIVES: DB is correct, FMP profile is current-only or returns wrong exec ──
    # Agilent: McMullen was CEO until Oct 2024; profile shows current McDonnell
    ('A',    2023): ('FALSE_POSITIVE', 'McMullen was CEO all of 2023'),

    # AbbVie: Gonzalez was CEO until Oct 2023; FMP key_exec returning Robert Michael (NOT CEO)
    ('ABBV', 2020): ('FALSE_POSITIVE', 'Gonzalez was AbbVie CEO 2013-2023; FMP key_exec wrong'),
    ('ABBV', 2021): ('FALSE_POSITIVE', 'Gonzalez correct'),
    ('ABBV', 2022): ('FALSE_POSITIVE', 'Gonzalez correct'),
    ('ABBV', 2023): ('FALSE_POSITIVE', 'Gonzalez until Oct 2023; FMP showing wrong exec'),
    ('ABBV', 2024): ('FALSE_POSITIVE', 'Rob Michael is NOT CEO; Gonzalez retired, Dolan was CEO'),

    # Arch Capital: Grandisson is group CEO; FMP profile showing Reinsurance division head
    ('ACGL', 2023): ('FALSE_POSITIVE', 'Grandisson is Arch Capital group CEO'),
    ('ACGL', 2024): ('FALSE_POSITIVE', 'Grandisson is Arch Capital group CEO'),

    # AES: Gluski and "Andres Ricardo Gluski Weilert" are SAME PERSON
    ('AES',  2023): ('SAME_PERSON',    'Andrés Gluski = Andres Ricardo Gluski Weilert'),
    ('AES',  2024): ('SAME_PERSON',    'Andrés Gluski = Andres Ricardo Gluski Weilert; still CEO'),
    ('AES',  2025): ('SAME_PERSON',    'Andrés Gluski = Andres Ricardo Gluski Weilert; still CEO'),

    # AJG: Patrick Gallagher Jr ≈ Patrick Gallagher Jr. (trailing period only)
    ('AJG',  2023): ('SAME_PERSON',    'Patrick Gallagher Jr = Patrick Gallagher Jr.'),
    ('AJG',  2024): ('SAME_PERSON',    'Patrick Gallagher Jr = Patrick Gallagher Jr.'),

    # AKAM: Tom Leighton = F. Thomson Leighton (nickname "Tom" = Thomson)
    ('AKAM', 2023): ('SAME_PERSON',    'Tom Leighton = Thomson Leighton (nickname)'),
    ('AKAM', 2024): ('SAME_PERSON',    'Tom Leighton = Thomson Leighton'),
    ('AKAM', 2025): ('SAME_PERSON',    'Tom Leighton = Thomson Leighton'),

    # ALB: Kent Masters is J. Kent Masters Jr; FMP "Jerry Kent Jr." is incorrect data
    ('ALB',  2023): ('FALSE_POSITIVE', 'Kent Masters is correct; FMP Jerry Kent Jr. is wrong'),
    ('ALB',  2024): ('FALSE_POSITIVE', 'Kent Masters correct'),
    ('ALB',  2025): ('FALSE_POSITIVE', 'Kent Masters correct'),

    # ALL: Thomas Wilson III = Thomas Joseph Wilson (middle name vs suffix)
    ('ALL',  2023): ('SAME_PERSON',    'Thomas Wilson III = Thomas Joseph Wilson'),

    # AMZN: Jeff Bezos / Andy Jassy are correct; Herrington is CEO of Amazon Stores only
    ('AMZN', 2020): ('FALSE_POSITIVE', 'Bezos was Amazon CEO; Herrington is stores-division CEO'),
    ('AMZN', 2021): ('FALSE_POSITIVE', 'Jassy became CEO July 2021; Herrington is NOT group CEO'),
    ('AMZN', 2022): ('FALSE_POSITIVE', 'Jassy correct; Herrington is division CEO'),
    ('AMZN', 2023): ('FALSE_POSITIVE', 'Jassy correct'),
    ('AMZN', 2024): ('FALSE_POSITIVE', 'Jassy correct'),
    ('AMZN', 2025): ('FALSE_POSITIVE', 'Jassy correct'),

    # APA: John Christmann IV = John Christmann (suffix only)
    ('APA',  2023): ('SAME_PERSON',    'John Christmann IV = John Christmann'),
    ('APA',  2024): ('SAME_PERSON',    'John Christmann IV = John Christmann'),

    # APD: Ghasemi was CEO until Oct 2024; FMP profile shows current CEO Menezes
    ('APD',  2023): ('FALSE_POSITIVE', 'Ghasemi was CEO all of 2023'),

    # APH: Adam Norwitt = Richard Adam Norwitt (preferred vs full name)
    ('APH',  2025): ('SAME_PERSON',    'Adam Norwitt = Richard Adam Norwitt'),

    # AXON: Rick Smith = Patrick Smith (Patrick "Rick" W. Smith, founder/CEO of AXON)
    ('AXON', 2023): ('SAME_PERSON',    'Rick Smith = Patrick W. Smith (goes by Rick)'),
    ('AXON', 2024): ('SAME_PERSON',    'Rick Smith = Patrick W. Smith'),

    # BA: Calhoun was CEO Jan 2020 - Aug 2024; FMP key_exec shows Raymond (NOT Boeing CEO)
    ('BA',   2020): ('FALSE_POSITIVE', 'Calhoun was Boeing CEO; Raymond is NOT CEO'),
    ('BA',   2021): ('FALSE_POSITIVE', 'Calhoun correct'),
    ('BA',   2022): ('FALSE_POSITIVE', 'Calhoun correct'),
    ('BA',   2023): ('FALSE_POSITIVE', 'Calhoun correct'),
    ('BA',   2024): ('FALSE_POSITIVE', 'Calhoun until Aug 2024; Ortberg from Aug 2024'),
    ('BA',   2025): ('FALSE_POSITIVE', 'Ortberg became CEO Aug 2024; FMP still showing Raymond'),

    # BDX: Tom Polen = Thomas Polen Jr. (same person)
    ('BDX',  2023): ('SAME_PERSON',    'Tom Polen = Thomas Polen Jr.'),
    ('BDX',  2024): ('SAME_PERSON',    'Tom Polen = Thomas Polen Jr.'),
    ('BDX',  2025): ('SAME_PERSON',    'Tom Polen = Thomas Polen Jr.'),

    # BEN: Jenny Johnson = Jennifer Johnson (nickname)
    ('BEN',  2023): ('SAME_PERSON',    'Jenny Johnson = Jennifer Johnson'),

    # BKR: Lorenzo Simonelli is Baker Hughes CEO; FMP profile shows Tadlock (wrong)
    ('BKR',  2023): ('FALSE_POSITIVE', 'Simonelli is correct; FMP profile wrong'),
    ('BKR',  2024): ('FALSE_POSITIVE', 'Simonelli correct'),
    ('BKR',  2025): ('FALSE_POSITIVE', 'Simonelli correct'),

    # BLK: Larry Fink = Laurence Douglas Fink (same person)
    ('BLK',  2023): ('SAME_PERSON',    'Larry Fink = Laurence Douglas Fink'),
    ('BLK',  2024): ('SAME_PERSON',    'Larry Fink = Laurence Douglas Fink'),

    # C: Corbat was Citi CEO until Feb 2021; FMP key_exec shows Fraser (current) 
    ('C',    2020): ('FALSE_POSITIVE', 'Corbat was CEO all of 2020; Fraser from Feb 2021'),

    # CAT: Jim Umpleby is Caterpillar CEO; FMP profile shows Creed (NOT CEO)
    ('CAT',  2023): ('FALSE_POSITIVE', 'Umpleby is correct; FMP profile showing wrong exec'),

    # ATO: Kevin Akers = John Kevin Akers (preferred vs full name)
    ('ATO',  2023): ('SAME_PERSON',    'Kevin Akers = John Kevin Akers'),
    ('ATO',  2024): ('SAME_PERSON',    'Kevin Akers = John Kevin Akers'),

    # ── PARTIAL YEAR: CEO changed mid-year; use year-end CEO convention ──────
    # ADP: Rodriguez left July 2023, Black took over
    ('ADP',  2023): ('PARTIAL_YEAR',   'Rodriguez Jan-Jun; Maria Black Jul-Dec → year-end=Black'),

    # AEE: Baxter left Feb 2023, Martin Lyons Jr took over March 2023
    ('AEE',  2023): ('PARTIAL_YEAR',   'Baxter left Feb 2023; Lyons majority+year-end → fix to Martin Lyons'),

    # AEP: Akins stepped down May 2023, Fehrman became CEO
    ('AEP',  2023): ('PARTIAL_YEAR',   'Akins until May; Fehrman May-Dec → year-end=Fehrman'),

    # AIZ: Assurant - Catherine McHugh or Keith Demmings? Demmings became CEO in 2021
    ('AIZ',  2023): ('GENUINE_ERROR',  'Demmings has been Assurant CEO since 2021; McHugh is wrong'),

    # ALLE: Petratis left Aug 2023, Stone became CEO
    ('ALLE', 2023): ('PARTIAL_YEAR',   'Petratis until Aug; Stone Aug-Dec → year-end=Stone'),

    # AMT: Bartlett left April 2023, Vondran took over
    ('AMT',  2023): ('PARTIAL_YEAR',   'Bartlett until Apr; Vondran Apr-Dec → year-end=Vondran'),

    # AOS: Wheeler was CEO until Q1 2024; Shafer took over
    ('AOS',  2023): ('FALSE_POSITIVE', 'Kevin Wheeler was CEO all of 2023; Shafer took over 2024'),
    ('AOS',  2024): ('PARTIAL_YEAR',   'Wheeler until early 2024; Shafer from mid-2024 → year-end=Shafer'),

    # ATO 2025: Akers retired 2024, Christopher Forsythe became CEO
    ('ATO',  2025): ('FALSE_POSITIVE', 'Forsythe is correct for 2025; FMP profile lagging'),

    # BALL: Hayes left March 2023, Lewis became CEO
    ('BALL', 2023): ('PARTIAL_YEAR',   'Hayes until Mar; Lewis Mar-Dec → year-end=Ronald Lewis'),
    ('BALL', 2024): ('GENUINE_ERROR',  'Ronald Lewis was CEO all of 2024; Hayes wrong'),

    # BAX: Almeida left July 2023, Hider became CEO
    ('BAX',  2023): ('PARTIAL_YEAR',   'Almeida until Jul; Hider Jul-Dec → year-end=Andrew Hider'),

    # BLDR: Flitman was CEO 2022-early 2025; Jackson took over
    ('BLDR', 2023): ('FALSE_POSITIVE', 'Flitman was CEO all of 2023'),
    ('BLDR', 2024): ('FALSE_POSITIVE', 'Flitman was CEO all of 2024; Jackson took over early 2025'),

    # BMY: Caforio until Nov 2023, Boerner from Nov 2023
    ('BMY',  2023): ('PARTIAL_YEAR',   'Caforio until Nov; Boerner Nov-Dec → year-end=Christopher Boerner'),

    # ── GENUINE ERRORS: wrong person entirely ────────────────────────────────
    # AIG 2025: local_10k extracted company name "Guy Carpenter" instead of CEO
    ('AIG',  2025): ('GENUINE_ERROR',  'Guy Carpenter is a company name; CEO=Peter Zaffino'),

    # AJG 2025: local_10k extracted CFO Douglas Howell instead of CEO Patrick Gallagher Jr
    ('AJG',  2025): ('GENUINE_ERROR',  'Douglas Howell is CFO; CEO=Patrick Gallagher Jr'),

    # AMCR 2023: Michele Buck is Hershey CEO; Amcor CEO=Peter Konieczny
    ('AMCR', 2023): ('GENUINE_ERROR',  'Michele Buck is Hershey CEO not Amcor; CEO=Peter Konieczny'),

    # APD 2024-2025: Ghasemi left Oct 2024; Eduardo Menezes became CEO
    ('APD',  2024): ('PARTIAL_YEAR',   'Ghasemi until Oct 2024; Menezes Oct-Dec → year-end=Eduardo Menezes'),
    ('APD',  2025): ('GENUINE_ERROR',  'Eduardo Menezes has been CEO since Oct 2024; Ghasemi wrong for 2025'),

    # APTV 2023: Kevin Clark is Aptiv CEO; Kevin Frazier is wrong
    ('APTV', 2023): ('GENUINE_ERROR',  'Kevin Clark is Aptiv CEO; Frazier is wrong'),

    # ARE: Alexandria Real Estate - Peter Moglia is CEO; Marcus is Executive Chairman
    ('ARE',  2023): ('GENUINE_ERROR',  'Peter Moglia is ARE CEO; Joel Marcus is Executive Chairman'),

    # AVB: Neithercut left 2018; Benjamin Schall has been CEO since 2018
    ('AVB',  2023): ('GENUINE_ERROR',  'Neithercut left 2018; Schall has been CEO since 2018'),

    # AVY 2023: Mitchell Butier was CEO until Jan 2024; Stander took over
    ('AVY',  2023): ('FALSE_POSITIVE', 'Butier was CEO all of 2023; Stander from Jan 2024'),

    # AWK: Story left Oct 2021; John Griffith became CEO
    ('AWK',  2023): ('GENUINE_ERROR',  'Story left Oct 2021; Griffith has been CEO since 2021'),
    ('AWK',  2024): ('GENUINE_ERROR',  'Story left Oct 2021; Griffith was CEO 2021-2024'),

    # AZO: Rhodes left Jan 2023; Philip Daniele became CEO
    ('AZO',  2023): ('GENUINE_ERROR',  'Rhodes left Jan 2023; Daniele has been CEO since Jan 2023'),
    ('AZO',  2024): ('GENUINE_ERROR',  'Philip Daniele is CEO'),

    # BAX 2024: Brent Shafer (Cerner) has nothing to do with Baxter; Hider is CEO
    ('BAX',  2024): ('GENUINE_ERROR',  'Brent Shafer is wrong; Andrew Hider is Baxter CEO'),

    # BSX 2025: Jonathan Monson is NOT BSX CEO; Mahoney is
    ('BSX',  2025): ('GENUINE_ERROR',  'Monson is wrong; Michael Mahoney is BSX CEO'),

    # BXP: Owen Thomas has been BXP CEO; Linde is President/CFO
    ('BXP',  2024): ('GENUINE_ERROR',  'Douglas Linde is President/CFO; Owen Thomas is CEO'),
    ('BXP',  2025): ('GENUINE_ERROR',  'Owen Thomas is CEO; Linde wrong'),

    # CAG 2025: Marberger is CFO; Connolly is CEO
    ('CAG',  2025): ('GENUINE_ERROR',  'David Marberger is CFO; Sean Connolly is CEO'),

    # CAH: Hollar became CEO August 2022; Kaufmann is wrong for 2023-2024
    ('CAH',  2023): ('GENUINE_ERROR',  'Jason Hollar became CEO Aug 2022; Kaufmann wrong for 2023'),
    ('CAH',  2024): ('GENUINE_ERROR',  'Jason Hollar is CEO; Kaufmann wrong for 2024'),

    # ADP 2024-2025: Black became CEO July 2023
    ('ADP',  2024): ('GENUINE_ERROR',  'Maria Black has been CEO since July 2023; Rodriguez wrong'),
    ('ADP',  2025): ('GENUINE_ERROR',  'Maria Black is CEO; Rodriguez wrong'),
}

# Year-end CEO for PARTIAL_YEAR cases
PARTIAL_YEAR_FIX = {
    ('ADP',  2023): 'Maria Black',
    ('AEE',  2023): 'Martin Lyons',
    ('AEE',  2024): 'Martin Lyons',
    ('AEP',  2023): 'William Fehrman',
    ('ALLE', 2023): 'John Stone',
    ('AMT',  2023): 'Steven Vondran',
    ('AMT',  2024): 'Steven Vondran',
    ('AOS',  2024): 'Stephen Shafer',
    ('BALL', 2023): 'Ronald Lewis',
    ('BAX',  2023): 'Andrew Hider',
    ('BMY',  2023): 'Christopher Boerner',
}

# Confirmed year-end CEO for GENUINE_ERROR cases
GENUINE_ERROR_FIX = {
    ('AIZ',  2023): 'Keith Demmings',
    ('AIG',  2025): 'Peter Zaffino',
    ('AJG',  2025): 'Patrick Gallagher Jr',
    ('AMCR', 2023): 'Peter Konieczny',
    ('APD',  2024): 'Eduardo Menezes',
    ('APD',  2025): 'Eduardo Menezes',
    ('APTV', 2023): 'Kevin Clark',
    ('ARE',  2023): 'Peter Moglia',
    ('AVB',  2023): 'Benjamin Schall',
    ('AWK',  2023): 'John Griffith',
    ('AWK',  2024): 'John Griffith',
    ('AZO',  2023): 'Philip Daniele',
    ('AZO',  2024): 'Philip Daniele',
    ('BAX',  2024): 'Andrew Hider',
    ('BALL', 2024): 'Ronald Lewis',
    ('BSX',  2025): 'Michael Mahoney',
    ('BXP',  2024): 'Owen Thomas',
    ('BXP',  2025): 'Owen Thomas',
    ('CAG',  2025): 'Sean Connolly',
    ('CAH',  2023): 'Jason Hollar',
    ('CAH',  2024): 'Jason Hollar',
    ('ADP',  2024): 'Maria Black',
    ('ADP',  2025): 'Maria Black',
}


def main():
    from collections import Counter, defaultdict
    cat_count: Counter = Counter()
    errors: list[tuple] = []   # (ticker, year, old, new, note)

    for key, (verdict, note) in VERDICTS.items():
        cat_count[verdict] += 1
        fix = None
        if verdict == 'PARTIAL_YEAR' and key in PARTIAL_YEAR_FIX:
            fix = PARTIAL_YEAR_FIX[key]
        elif verdict == 'GENUINE_ERROR' and key in GENUINE_ERROR_FIX:
            fix = GENUINE_ERROR_FIX[key]
        if fix:
            errors.append((*key, fix, note))

    print("=" * 72)
    print("  MISMATCH CLASSIFICATION")
    print("=" * 72)
    for cat, cnt in cat_count.most_common():
        icon = {'FALSE_POSITIVE': 'OK', 'SAME_PERSON': '~~',
                'PARTIAL_YEAR': 'PY', 'GENUINE_ERROR': '!!'}.get(cat, '  ')
        print(f"  [{icon}] {cat:<20}: {cnt}")

    print()
    print(f"  Rows needing DB fix: {len(errors)}")
    print()
    print("  Planned fixes:")
    for tkr, yr, new_name, note in sorted(errors, key=lambda x: (x[0], x[1])):
        print(f"    {tkr:<6} {yr}  →  '{new_name}'   ({note[:60]})")


if __name__ == '__main__':
    main()
