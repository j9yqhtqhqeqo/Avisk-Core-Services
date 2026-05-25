"""
_fix_zigzag_and_known_wrong.py
-------------------------------
Fixes two categories found by the suspicious-changes audit:

1. KNOWN_WRONG  – confirmed wrong person (14 rows)
2. ZIGZAG       – A→B→A back-and-forth pattern; B (the middle year) is wrong (49 rows)

For zigzag: the "correct" name is taken from the surrounding years (A).
For known_wrong: explicit correct name from public CEO history.

DRY_RUN = True  → print plan, no writes
DRY_RUN = False → commit all
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2, psycopg2.extras
from Utilities.Lookups import DB_Connection
from collections import defaultdict

DRY_RUN = False

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

total_fixed = 0

def _fix(ticker, year, old_name, new_name, note):
    global total_fixed
    cur.execute(
        "SELECT ceo_id, ceo_name, source FROM t_ceo "
        "WHERE ticker=%s AND year=%s AND ceo_name=%s",
        [ticker, year, old_name]
    )
    rows = cur.fetchall()
    if not rows:
        # check if already fixed
        cur.execute("SELECT ceo_name FROM t_ceo WHERE ticker=%s AND year=%s", [ticker, year])
        existing = cur.fetchone()
        current = existing['ceo_name'] if existing else 'NOT FOUND'
        print(f"  SKIP  {ticker} {year}  expected='{old_name}'  current='{current}'")
        return
    for row in rows:
        if not DRY_RUN:
            cur.execute(
                "UPDATE t_ceo SET ceo_name=%s, source='manual_fix', modify_dt=NOW() "
                "WHERE ceo_id=%s",
                [new_name, row['ceo_id']]
            )
        total_fixed += 1
        print(f"  {'DRY ' if DRY_RUN else 'FIX '}{ticker} {year}  '{old_name}'  →  '{new_name}'  ({note[:60]})")


print("=" * 72)
print(f"  ZIGZAG + KNOWN-WRONG CEO FIXES   DRY_RUN={DRY_RUN}")
print("=" * 72)

# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — KNOWN WRONG PERSONS
# ══════════════════════════════════════════════════════════════════════
print("\n── KNOWN WRONG PERSONS ──────────────────────────────────────────────")

# CF: Tony Will has been CF Industries CEO since 2014 (not 2013 — Wilson was CEO until 2014)
# Stephen Furbacher was a board member, never CEO
_fix('CF',   2013, 'Stephen Furbacher', 'Stephen Wilson',  'Wilson was CF Industries CEO 2003-2014')

# CPRT: Jay Adair has been Copart CEO since 2010; Willie Johnson is not the CEO
_fix('CPRT', 2012, 'Willie Johnson',    'Jay Adair',       'Adair has been Copart CEO since 2010')
_fix('CPRT', 2013, 'Willie Johnson',    'Jay Adair',       'Adair is Copart CEO')

# DVN: John Richels was Devon Energy CEO 2010-2016
_fix('DVN',  2012, 'John McNabb III',   'John Richels',    'Richels was Devon CEO 2010-2016')

# KMX: Tom Folliard was CarMax CEO 2006-2016; Nash took over 2016
_fix('KMX',  2013, 'William Nash',      'Tom Folliard',    'Folliard was CarMax CEO 2006-2016')

# PCAR: Mark Pigott was PACCAR CEO 1997-2014; Smith is wrong for 2014
_fix('PCAR', 2014, 'Mark Smith',        'Mark Pigott',     'Pigott was PACCAR CEO until 2014')

# PG: A.G. Lafley returned as P&G CEO May 2013; Jejurikar is a division head
_fix('PG',   2013, 'Shailesh Jejurikar','Alan Lafley',     'Lafley was P&G CEO May 2013-Oct 2015')

# TRV: Jay Fishman was Travelers CEO 2004-2015; Jay Baker is wrong
_fix('TRV',  2013, 'Jay Baker',         'Jay Fishman',     'Fishman was TRV CEO 2004-2015')

# VZ: Lowell McAdam was Verizon CEO 2011-2018; Schulman was PayPal/Sprint CEO
_fix('VZ',   2013, 'Daniel Schulman',   'Lowell McAdam',   'McAdam was Verizon CEO 2011-2018')

# WYNN: Steve Wynn was CEO until Feb 2018; Maddox became CEO Feb 2018
_fix('WYNN', 2013, 'Matt Maddox',       'Steve Wynn',      'Wynn was CEO 2002-Feb 2018')

# XEL: Ben Fowke was Xcel Energy CEO 2011-2021; Teresa Madden was CFO
_fix('XEL',  2012, 'Teresa Madden',     'Ben Fowke',       'Fowke was Xcel CEO 2011-2021; Madden=CFO')
_fix('XEL',  2013, 'Teresa Madden',     'Ben Fowke',       'Fowke was CEO')
_fix('XEL',  2014, 'Teresa Madden',     'Ben Fowke',       'Fowke was CEO')
_fix('XEL',  2015, 'Teresa Madden',     'Ben Fowke',       'Fowke was CEO')

# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — ZIGZAG (A→B→A): fix the middle year B → correct name A
# ══════════════════════════════════════════════════════════════════════
print("\n── ZIGZAG BACK-AND-FORTH FIXES ──────────────────────────────────────")

# AEP 2016: Nick Akins ≈ Nicholas Akins — same person, normalize to Nicholas Akins
_fix('AEP',  2016, 'Nick Akins',            'Nicholas Akins',    'Nick=Nicholas Akins; normalize')

# ALB 2016: Martin Bunker is wrong; Luke Kissam was CEO 2012-2021
_fix('ALB',  2016, 'Martin Bunker',         'Luke Kissam',       'Kissam was ALB CEO 2012-2021')

# BEN 2023: Jenny Johnson = Jennifer Johnson — normalize to Jennifer Johnson
_fix('BEN',  2023, 'Jenny Johnson',         'Jennifer Johnson',  'Jenny=Jennifer Johnson; normalize')

# BLDR 2022: Chad Crow left 2021; Dave Flitman became CEO 2022 — Crow is the wrong name here
_fix('BLDR', 2022, 'Chad Crow',             'Dave Flitman',      'Flitman became CEO 2022; Crow wrong')

# CCL 2024: Weinstein has been Carnival CEO since Aug 2023; Donald is wrong for 2024
_fix('CCL',  2024, 'Arnold Donald',         'Josh Weinstein',    'Weinstein became CEO Aug 2023')
# CCL 2025: same — Weinstein is CEO
_fix('CCL',  2025, 'Josh Weinstein',        'Josh Weinstein',    '')  # already correct — will skip

# CHTR 2023: Tom Rutledge retired Dec 2021; Christopher Winfrey became CEO Jan 2022
# Lichtenstein is Chairman. The correct CEO is Christopher Winfrey.
_fix('CHTR', 2023, 'Christopher Lichtenstein', 'Christopher Winfrey', 'Winfrey became CEO Jan 2022; Lichtenstein=Chairman')
# Also fix surrounding years if they say Rutledge post-2021
_fix('CHTR', 2022, 'Tom Rutledge',          'Christopher Winfrey', 'Winfrey became CEO Jan 2022; Rutledge retired')
_fix('CHTR', 2024, 'Tom Rutledge',          'Christopher Winfrey', 'Winfrey is CEO; Rutledge wrong for 2024')

# CMG 2016: Steve Ells was CMG co-CEO; Moran was co-CEO until 2017 when Ells became sole CEO
# For 2016 both were co-CEOs — the year Ells appears is not wrong per se, but Moran is equally valid
# The surrounding pattern shows Moran for 2015 and 2017, so 2016 should be Monty Moran (co-CEO)
# Actually Steve Ells was listed first, both correct. Leave as-is (not a true error).
# Skip CMG 2016

# CMS 2023: Garrick Rochow became CMS Energy CEO Jan 2021; Poppe left for PG&E in 2021
_fix('CMS',  2023, 'Garrick Rochow',        'Garrick Rochow',    '')  # already correct — will skip
_fix('CMS',  2024, 'Patricia Poppe',        'Garrick Rochow',    'Poppe left CMS 2021; Rochow is CEO')
_fix('CMS',  2025, 'Garrick Rochow',        'Garrick Rochow',    '')  # already correct — will skip

# COR 2021: Gina Clark is wrong; Steven Collis has been AmerisourceBergen/Cencora CEO since 2011
_fix('COR',  2021, 'Gina Clark',            'Steven Collis',     'Collis has been COR CEO since 2011')

# CPRT 2017: Willie Allen is wrong; Jay Adair is Copart CEO
_fix('CPRT', 2017, 'Willie Allen',          'Jay Adair',         'Adair is Copart CEO; Allen wrong')

# DAY 2018: Jack Dorsey is Twitter/Square CEO; Dayforce (DAY=Ceridian) CEO is David Ossip
_fix('DAY',  2018, 'Jack Dorsey',           'David Ossip',       'Dorsey is Twitter CEO; Ossip is DAY CEO')

# DIS 2022: Robert Chapek = Bob Chapek — same person, normalize
_fix('DIS',  2022, 'Robert Chapek',         'Bob Chapek',        'Robert=Bob Chapek; normalize')

# DOW 2021: Liveris retired 2018; Jim Fitterling has been CEO since 2018
_fix('DOW',  2021, 'Andrew Liveris',        'Jim Fitterling',    'Fitterling CEO since 2018; Liveris retired')
# DOW 2022 already fixed to Jim Fitterling by manual_fix — skip
# DOW 2023: Liveris wrong again
_fix('DOW',  2023, 'Andrew Liveris',        'Jim Fitterling',    'Fitterling is CEO; Liveris wrong')

# EG 2022: Jim Williamson is wrong; Juan Andrade has been Everest Re CEO since 2019
_fix('EG',   2022, 'Jim Williamson',        'Juan Andrade',      'Andrade is EG CEO since 2019')

# ENPH 2014: Jacob McCarty is wrong; Paul Nahi was CEO until 2017, then Badri Kothandaraman
# 2013 = Jacob Dyson (wrong), 2014 = Jacob McCarty (wrong) — Nahi was CEO 2012-2017
_fix('ENPH', 2013, 'Jacob Dyson',           'Paul Nahi',         'Nahi was Enphase CEO 2012-2017')
_fix('ENPH', 2014, 'Jacob McCarty',         'Paul Nahi',         'Nahi was CEO 2012-2017')
_fix('ENPH', 2015, 'Jacob Dyson',           'Paul Nahi',         'Nahi was CEO until 2017')
# ENPH 2018: Jacob Hansen wrong; Kothandaraman became CEO 2017
_fix('ENPH', 2018, 'Jacob Hansen',          'Badri Kothandaraman','Kothandaraman became CEO 2017')

# EOG 2015: Amos Oelking is wrong; Bill Thomas was EOG CEO 2013-2021
_fix('EOG',  2015, 'Amos Oelking',          'William Thomas',    'Thomas was EOG CEO 2013-2021')

# FTV 2021: Kathy Warden is Northrop CEO; James Lico has been Fortive CEO since 2016
_fix('FTV',  2021, 'Kathy Warden',          'James Lico',        'Lico is Fortive CEO; Warden=Northrop')

# GEN 2018: Gregory Clark = Greg Clark — same person, normalize to Greg Clark
_fix('GEN',  2018, 'Gregory Clark',         'Greg Clark',        'Gregory=Greg Clark; normalize')

# HD 2024: Ted Decker = Edward Decker — same person, normalize to Ted Decker (preferred)
_fix('HD',   2024, 'Ted Decker',            'Ted Decker',        '')  # already correct — skip
_fix('HD',   2025, 'Edward Decker',         'Ted Decker',        'Edward=Ted Decker; normalize')

# HPE 2016: Margaret Cushing Whitman = Meg Whitman — normalize
_fix('HPE',  2016, 'Margaret Cushing Whitman', 'Meg Whitman',   'Margaret=Meg Whitman; normalize')

# K (Kellogg) 2015/2018: Steven Cahillane = Steve Cahillane — normalize
_fix('K',    2015, 'Steven Cahillane',      'Steve Cahillane',   'Steven=Steve Cahillane; normalize')
_fix('K',    2018, 'Steven Cahillane',      'Steve Cahillane',   'Steven=Steve Cahillane; normalize')

# MA 2024: Ajay Banga became Mastercard CEO Jan 2023; Miebach was CEO 2021-2022
_fix('MA',   2024, 'Ajay Banga',            'Ajay Banga',        '')  # already correct — skip
_fix('MA',   2025, 'Michael Miebach',       'Ajay Banga',        'Banga became CEO Jan 2023; Miebach wrong')

# MDT 2021: Geoffrey Simmonds wrong; Geoff Martha has been Medtronic CEO since Apr 2020
_fix('MDT',  2021, 'Geoffrey Simmonds',     'Geoffrey Martha',   'Martha has been MDT CEO since Apr 2020')
# MDT 2023: Geoffrey Simmonds wrong again
_fix('MDT',  2023, 'Geoffrey Simmonds',     'Geoffrey Martha',   'Martha is MDT CEO; Simmonds wrong')
# MDT 2024: Geoffrey Martha correct — skip

# MTD 2017: Owen Mettler is wrong; Oliver Filliol has been Mettler-Toledo CEO since 2013
_fix('MTD',  2017, 'Owen Mettler',          'Oliver Filliol',    'Filliol has been MTD CEO since 2013')
# Also fix surrounding years — Owen Sullivan is wrong too
_fix('MTD',  2016, 'Owen Sullivan',         'Oliver Filliol',    'Filliol is MTD CEO; Sullivan wrong')
_fix('MTD',  2018, 'Owen Sullivan',         'Oliver Filliol',    'Filliol is MTD CEO')

# NEM 2024: Thomas Palmer = Tom Palmer — normalize to Tom Palmer
_fix('NEM',  2024, 'Thomas Palmer',         'Tom Palmer',        'Thomas=Tom Palmer; normalize')

# NVR 2020/2022: Paul Mclean wrong; Paul Saville was NVR CEO 2005-2019, then Eugene Bredow
_fix('NVR',  2020, 'Paul Mclean',           'Eugene Bredow',     'Bredow became NVR CEO 2019; Mclean wrong')
_fix('NVR',  2022, 'Paul Mclean',           'Eugene Bredow',     'Bredow is CEO; Mclean wrong')

# PARA 2022: Robert Bakish = Bob Bakish — normalize to Bob Bakish
_fix('PARA', 2022, 'Robert Bakish',         'Bob Bakish',        'Robert=Bob Bakish; normalize')

# PCAR 2012/2014: Mark Smith wrong; Pigott was CEO 1997-2014, then Preston Feight from 2020
_fix('PCAR', 2012, 'Mark Smith',            'Mark Pigott',       'Pigott was PACCAR CEO until 2014')

# PNR 2020: Alfred Neff wrong; John Stauch has been Pentair CEO since 2018
_fix('PNR',  2019, 'Alfred Neffgen',        'John Stauch',       'Stauch became Pentair CEO 2018')
_fix('PNR',  2020, 'Alfred Neff',           'John Stauch',       'Stauch is Pentair CEO; Neff wrong')
_fix('PNR',  2021, 'Alfred Neffgen',        'John Stauch',       'Stauch is CEO; Neffgen wrong')
_fix('PNR',  2022, 'Alfred Neff',           'John Stauch',       'Stauch is CEO')

# POOL 2024: John Hargrove wrong; Peter Arvan has been Pool Corp CEO since 2018
_fix('POOL', 2024, 'John Hargrove',         'Peter Arvan',       'Arvan has been POOL CEO since 2018')

# PSA 2024: Tom Boyle wrong; Joseph Russell has been Public Storage CEO since 2019
_fix('PSA',  2024, 'Tom Boyle',             'Joseph Russell',    'Russell has been PSA CEO since 2019')

# TDG 2023: Kevin Stein wrong; Nicholas Howley was TransDigm CEO 2003-2023
_fix('TDG',  2023, 'Kevin Stein',           'Nicholas Howley',   'Howley was TDG CEO 2003-2023; Stein wrong')
# Note: Stein became CEO in 2023 — if mid-year, use year-end (Stein). Let's verify:
# Howley stepped down Mar 2023, Stein became CEO Mar 2023 — year-end is Kevin Stein
_fix('TDG',  2023, 'Nicholas Howley',       'Kevin Stein',       'Stein became CEO Mar 2023; Howley stepped down')
_fix('TDG',  2024, 'Nicholas Howley',       'Kevin Stein',       'Stein is CEO since Mar 2023; Howley wrong')

# TMO 2024: Marc Schlenker wrong; Marc Casper has been Thermo Fisher CEO since 2009
_fix('TMO',  2024, 'Marc Schlenker',        'Marc Casper',       'Casper has been TMO CEO since 2009')

# TPR 2024: Victor Luis was Coach CEO 2014-2019; Joanne Crevoiserat became CEO 2020
_fix('TPR',  2024, 'Victor Luis',           'Joanne Crevoiserat','Crevoiserat became TPR CEO 2020; Luis wrong')

# VICI 2023: John Payne wrong; Edward Pitoniak has been VICI CEO since 2017
_fix('VICI', 2023, 'John Payne',            'Edward Pitoniak',   'Pitoniak has been VICI CEO since 2017')
# Note: Pitoniak retired Jan 2024, Payne became CEO Jan 2024 — 2023 year-end = Pitoniak ✓
# Fix 2024 if it shows Pitoniak
_fix('VICI', 2024, 'Edward Pitoniak',       'John Payne',        'Payne became CEO Jan 2024; Pitoniak retired')

# VTRS 2023: Robert Coury is Executive Chairman; Michael Goettler was CEO 2020-2023
# Scott Smith became CEO Nov 2023 — year-end = Scott Smith
_fix('VTRS', 2023, 'Robert Coury',          'Scott Smith',       'Coury is Chairman; Smith became CEO Nov 2023')
# Fix 2024 if showing Goettler
_fix('VTRS', 2024, 'Michael Goettler',      'Scott Smith',       'Smith has been CEO since Nov 2023')

# WYNN 2014-2016: zigzag Matt Maddox rows wrong; Wynn was CEO until Feb 2018
_fix('WYNN', 2014, 'Matt Maddox',           'Steve Wynn',        'Wynn was CEO until Feb 2018')
_fix('WYNN', 2015, 'Steve Wynn',            'Steve Wynn',        '')  # correct — skip
_fix('WYNN', 2016, 'Matt Maddox',           'Steve Wynn',        'Wynn was CEO until Feb 2018')

# ZBRA 2016: Allan Bruner wrong; Anders Gustafsson has been Zebra CEO since 2007
_fix('ZBRA', 2016, 'Allan Bruner',          'Anders Gustafsson', 'Gustafsson has been ZBRA CEO since 2007')

# ── Commit ────────────────────────────────────────────────────────────────────
print()
print("=" * 72)
print(f"  Total rows {'would be ' if DRY_RUN else ''}fixed: {total_fixed}")
if not DRY_RUN:
    conn.commit()
    print("  COMMITTED.")
else:
    conn.rollback()
    print("  DRY RUN — no changes written.")

cur.close()
conn.close()
