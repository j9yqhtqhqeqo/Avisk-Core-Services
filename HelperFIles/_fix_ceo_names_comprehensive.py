"""
_fix_ceo_names_comprehensive.py
--------------------------------
Fixes all bad CEO names found in the comprehensive audit:
  🔴  Non-person / garbage  →  correct CEO or NULL (for pipeline re-run)
  🟠  Reversed names        →  correct name order
  🟡  Duplicate variants    →  canonical preferred name

Run with:
    DEPLOYMENT_ENV=development python HelperFIles/_fix_ceo_names_comprehensive.py

Set DRY_RUN = False to commit.
"""
import psycopg2, sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

DRY_RUN = False  # ← flip to False to commit

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()

fixed = 0
nulled = 0
not_found = 0


def _apply(old, new, note='', ticker=None, year=None):
    """Update rows WHERE ceo_name=old (optionally filtered by ticker/year)."""
    global fixed, nulled, not_found
    params = [old]
    sql = "SELECT ceo_id, ticker, year, ceo_name, source FROM t_ceo WHERE ceo_name=%s"
    if ticker:
        sql += " AND ticker=%s"; params.append(ticker)
    if year:
        sql += " AND year=%s";   params.append(year)
    sql += " ORDER BY ticker, year"
    cur.execute(sql, params)
    rows = cur.fetchall()
    if not rows:
        print(f"  ⚠️  NOT FOUND  '{old}'"
              + (f"  [{ticker}]" if ticker else "")
              + (f"  {year}" if year else ""))
        not_found += 1
        return
    for (ceo_id, tk, yr, name, src) in rows:
        if new is None:
            action, new_src = 'NULL ', 'needs_rerun'
            nulled += 1
        else:
            action, new_src = 'FIX  ', 'manual_fix'
            fixed += 1
        print(f"  {action} [{tk:<6}] {yr}  '{name}'  →  "
              + (f"'{new}'" if new else "NULL")
              + (f"  | {note}" if note else ""))
        if not DRY_RUN:
            cur.execute(
                "UPDATE t_ceo SET ceo_name=%s, source=%s, modify_dt=NOW() WHERE ceo_id=%s",
                (new, new_src, ceo_id)
            )


SEP = "=" * 70

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🔴  NON-PERSON — company / division names  →  correct CEO")
print(SEP)

_apply('Aflac Incorporated',    'Daniel Amos',       'AFL CEO since 1990',                  ticker='AFL')
_apply('AIG Re',                'Peter Zaffino',     'AIG CEO since 2021',                  ticker='AIG')
_apply('Ampere Computing',      'Jane Fraser',       'Citi CEO since 2021',                 ticker='C')
_apply('Baker Hughes',          'Lal Karsanbhai',    'Emerson CEO since 2021',              ticker='EMR')
_apply('BNP Paribas Securities','Ronald O\'Hanley',  'State Street CEO since 2019',         ticker='STT')
_apply('Building Automation',   'Vimal Kapur',       'Honeywell CEO since Jun 2023',        ticker='HON')
_apply('Cooper Companies',      'Albert White',      'Cooper Companies CEO since 2018',     ticker='COO')
_apply('Exelon Utilities',      'Calvin Butler',     'Exelon CEO since Mar 2023',           ticker='EXC')
_apply('Fingerhut Companies',   'William Lansing',   'FICO CEO since 2012',                 ticker='FICO')
_apply('Ford China',            'Jim Farley',        'Ford CEO since Oct 2020',             ticker='F')
_apply('Hewlett Packard Enterprise', None,           'JNPR acquired by HPE Jan 2024 — re-run', ticker='JNPR')
_apply('Laboratoires Majorelle','Albert Bourla',     'Pfizer CEO since 2019',               ticker='PFE')
_apply('Linde Engineering',     'Sanjiv Lamba',      'Linde CEO since Mar 2022',            ticker='LIN')
_apply('Loews Hotels',          'James Tisch',       'Loews CEO since 1998',                ticker='L')
_apply('Medallion Midstream',   'Pierce Norton II',  'ONEOK CEO since 2014',                ticker='OKE')
_apply('Swedish Match',         'Jacek Olczak',      'Philip Morris CEO since 2021',        ticker='PM')

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🔴  NON-PERSON — document / headline garbage  →  correct CEO or NULL")
print(SEP)

_apply('Announces CEO Transition', 'Duke Austin',       'Quanta Services CEO since 2019',   ticker='PWR')
_apply('Attacks Biden',            'Michael Wirth',     'Chevron CEO since 2018',           ticker='CVX', year=2024)
_apply('Customer Satisfaction',    None,                'AutoZone — CEO Phil Daniele, needs re-run', ticker='AZO')
_apply('Dodges Bullet',            'Joaquin Duato',     'J&J CEO since 2022',               ticker='JNJ')
_apply('Effective Date',           None,                'Vistra pre-IPO (2016) — needs re-run', ticker='VST')
_apply('Employment History',       None,                'BMS CEO Christopher Boerner — needs re-run', ticker='BMY')
_apply('Enterprise Clients',       'Gregory Case',      'Aon CEO since 2005',               ticker='AON')
_apply('Exhibit Description',      'Robert Thomson',    'News Corp CEO since 2013')   # covers NWS + NWSA
_apply('Filed Herewith',           'Richard Campo',     'Camden Property CEO',              ticker='CPT')
_apply('Inclusion Council',        'William Brown',     '3M CEO since May 2024',            ticker='MMM', year=2024)
_apply('Insider Trading Policy',   'Donald Allan',      'SWK CEO since 2022',               ticker='SWK', year=2024)
_apply('Investor Relations Andres','Andrés Gluski',     'AES CEO since 2011',               ticker='AES')
_apply('Just Made',                'Warren Buffett',    'Berkshire CEO until Jan 2025',     ticker='BRK', year=2024)
_apply('Key Persons',              'Dominic Addesso',   'Everest Re CEO until 2020',        ticker='EG')
_apply('Segment Disclosures',      None,                'DOC/Healthpeak post-merger — needs re-run', ticker='DOC')
_apply('Street Journal',           'Donald Allan',      'SWK CEO since 2022',               ticker='SWK', year=2025)
_apply('Subsequent Events',        'Joseph Russell',    'Public Storage CEO since 2019',    ticker='PSA')
_apply('Transcript Date Thursday', 'Craig Billings',    'Wynn CEO since 2022',              ticker='WYNN')
_apply('Transition Date',          'Daniel Florness',   'Fastenal CEO since 2015',          ticker='FAST')
_apply('Wall Street',              'Michael Wirth',     'Chevron CEO since 2018',           ticker='CVX', year=2025)

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🔴  NON-PERSON — fixable headline fragments")
print(SEP)

_apply('Greg Abel Pledges',    'Greg Abel',      'Berkshire CEO since Jan 2025',  ticker='BRK', year=2025)
_apply('Howard Schultz Pays',  None,             'Wrong company ticker DAY — needs re-run', ticker='DAY')
_apply('Intel Appoints Lip',   'Lip-Bu Tan',     'Intel CEO since Mar 2024',      ticker='INTC')

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🟠  REVERSED NAMES")
print(SEP)

_apply('Chambers John',  'John Chambers',  'Cisco CEO 2015-2017',  ticker='CSCO')
_apply('Liveris Andrew', 'Jim Fitterling', 'DOW CEO since 2018 — Liveris retired 2018', ticker='DOW')

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🟡  NORMALIZE — accented characters")
print(SEP)

_apply('Rene Jones',     'René Jones',     'Correct accent')
_apply('Stephane Bancel','Stéphane Bancel', 'Correct accent')
_apply('Andres Gluski',  'Andrés Gluski',  'Correct accent')
_apply('Carol Tome',     'Carol Tomé',      'Correct accent')

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("🟡  NORMALIZE — preferred/common name vs legal name")
print(SEP)

_apply('Jen-Hsun Huang',    'Jensen Huang',     'NVDA preferred name')
_apply('Virginia Rometty',  'Ginni Rometty',    'IBM preferred name')
_apply('Timothy Cook',      'Tim Cook',         'AAPL preferred name')
_apply('Clifford Pemble',   'Clifton Pemble',   'GRMN legal first name')
_apply('Cliff Pemble',      'Clifton Pemble',   'GRMN legal first name')
_apply('Thomas Bene',       'Tom Bené',         'SYY preferred name with accent')
_apply('Edward Bastian',    'Ed Bastian',       'DAL preferred name')
_apply('Edward Breen',      'Ed Breen',         'DD preferred name')
_apply('James Dimon',       'Jamie Dimon',      'JPM preferred name')
_apply('Charles Robbins',   'Chuck Robbins',    'CSCO preferred name')
_apply('Charles Scharf',    'Charlie Scharf',   'WFC/V/BK preferred name')
_apply('Daniel Glaser',     'Dan Glaser',       'MMC preferred name')
_apply('Daniel Houston',    'Dan Houston',      'PFG preferred name')
_apply('David Lesar',       'Dave Lesar',       'HAL/CNP preferred name')
_apply('David Regnery',     'Dave Regnery',     'TT preferred name')
_apply("Francisco D'Souza", "Frank D'Souza",    'CTSH preferred name')
_apply('James Cashman III', 'Jim Cashman',      'ANSS preferred name')
_apply('James Cracchiolo',  'Jim Cracchiolo',   'AMP preferred name')
_apply('James Fitterling',  'Jim Fitterling',   'DOW preferred name')
_apply('James Robo',        'Jim Robo',         'NEE preferred name')
_apply('James Taiclet',     'James Taiclet Jr', 'LMT full name (Jr suffix)')
_apply('Matthew Maddox',    'Matt Maddox',      'WYNN preferred name')
_apply('Matthew Meloy',     'Matt Meloy',       'TRGP preferred name')
_apply('Michael Kaufmann',  'Mike Kaufmann',    'CAH preferred name')
_apply('Michael McMullen',  'Mike McMullen',    'A preferred name')
_apply('Michael Roman',     'Mike Roman',       'MMM preferred name')
_apply('Michael McManus',   'Michael McManus Jr','NDSN full name (Jr suffix)')
_apply('Olivier Peuch',     'Olivier Le Peuch', 'SLB full surname')
_apply('Patrick Gallagher', 'Patrick Gallagher Jr', 'AJG full name (Jr suffix)')
_apply('Richard Dreiling',  'Rick Dreiling',    'DG preferred name')
_apply('Richard McVey',     'Rick McVey',       'MKTX preferred name')
_apply('Richard Muncrief',  'Rick Muncrief',    'DVN preferred name')
_apply('Robert Painter',    'Rob Painter',      'TRMB preferred name')
_apply('Robert Sands',      'Rob Sands',        'STZ preferred name')
_apply('Samuel Hazen',      'Sam Hazen',        'HCA preferred name')
_apply('Stephen Luczo',     'Steve Luczo',      'STX preferred name')
_apply('Stephen Milligan',  'Steve Milligan',   'WDC preferred name')
_apply('Stephen Rusckowski','Steve Rusckowski', 'DGX preferred name')
_apply('Timothy Archer',    'Tim Archer',       'LRCX preferred name')
_apply('Thomson Leighton',  'Tom Leighton',     'AKAM preferred name')
_apply('Thomas Folliard',   'Tom Folliard',     'KMX preferred name')
_apply('Thomas Polen',      'Tom Polen',        'BDX preferred name')
_apply('Thomas Reeg',       'Tom Reeg',         'CZR preferred name')
_apply('Thomas Rutledge',   'Tom Rutledge',     'CHTR preferred name')
_apply('Walter Bettinger',  'Walt Bettinger',   'SCHW preferred name')
_apply('Walter Bettinger II','Walt Bettinger',  'SCHW preferred name')
_apply('Ben Moreland',      'Benjamin Moreland','CCI full name')
_apply('Albert White III',  'Albert White',     'COO — III suffix not used professionally')
_apply('Alfred Kelly',      'Alfred Kelly Jr',  'V full name (Jr suffix)')
_apply('David McCulloh',    'David McCulloch',  'EQT — typo fix (McCulloh → McCulloch)')
_apply('Eric Mark Edwards', 'Eric Mark Green',  'WST — wrong surname, Green is correct')
_apply('DG Macpherson',     'Donald Macpherson','GWW — remaining rows if any')

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("SUMMARY")
print(SEP)
print(f"  Fixed with correct name : {fixed:>4}")
print(f"  Nulled (needs re-run)   : {nulled:>4}")
print(f"  Not found               : {not_found:>4}")
print(f"  Total rows affected     : {fixed + nulled:>4}")

if DRY_RUN:
    conn.rollback()
    print("\n  ✅  DRY RUN — nothing committed. Set DRY_RUN=False to apply.")
else:
    conn.commit()
    print("\n  ✅  All changes committed to t_ceo.")

cur.close()
conn.close()
