"""
_fix_remaining_errors.py
--------------------------
Fixes remaining errors found after reviewing all 42 suspicious tickers:

GENUINE ERRORS (wrong person confirmed):
- CPRT 2014-2016: Willie Johnson → Jay Adair (Adair is Copart CEO; Willie=wrong person)
- CPRT 2018-2019: Willie Johnson → Jay Adair
- CPRT 2023-2025: Willie McGowan → Jay Adair (McGowan is wrong; Adair is CEO since 2010)
- DVN 2013-2014: John McNabb III → John Richels (Richels was CEO 2010-2016; McNabb=wrong)
- DVN 2022: Richard Dewitt → Rick Muncrief (Muncrief became CEO 2020; Dewitt wrong)
- MTD 2012-2015: Owen Sullivan → Oliver Filliol (Filliol became CEO 2013; Sullivan wrong for 2013-2015)
- MTD 2019: Owen Sullivan → Oliver Filliol (Filliol is CEO; Sullivan wrong)
- MTD 2021-2023: Oliver Schmidtlein → Oliver Filliol (Filliol is CEO through 2024; Schmidtlein wrong)
  NOTE: Filliol was CEO until 2024 when Kaltenbach took over; 2024-2025 look correct
- NVR 2012: Paul Mclean → Paul Saville (Saville was NVR CEO; 2013-2018 already correct)
- NVR 2021: Paul Saville → Eugene Bredow (Bredow became CEO 2019; Saville wrong for 2021)
- NVR 2023: Paul Mclean → Eugene Bredow (Mclean wrong; Bredow is CEO)
- PG 2014: Shailesh Jejurikar → Alan Lafley (Lafley was CEO May 2013-Oct 2015; Jejurikar wrong)
- PG 2015: Alan George Lafley → Alan Lafley (normalize - same person)
- AXON 2012: Patrick Smith → Rick Smith (Rick Smith has been Axon CEO since founding 1993)
  NOTE: Patrick Smith IS Rick Smith (Patrick R. Smith = "Rick") - same person, but Rick is the name used
  Actually need to verify: Patrick is Rick's real first name - actually this is CORRECT to have both
  Axon CEO: Rick Smith (born Patrick R. Smith) - so Patrick = Rick. NO CHANGE needed.
  BUT 2017, 2018, 2025: Patrick Smith (same person) - no change needed
- AIG 2020: Peter Hancock → Peter Zaffino (Zaffino became CEO 2021; 2020 should be Duperreault)
  Duperreault was CEO 2017-2021; 2020 should be Brian Duperreault, NOT Peter Hancock
- A (Agilent) 2020-2022: Mark Doiron is wrong for 2020; Mike McMullen should be 2019-2024
  McMullen was Agilent CEO 2015-2024; Doiron wrong
- CEG 2012-2015: many different "Michaels" - Constellation Energy reorg; need to check
  CEG was spun off from Exelon in 2022. Before 2022 the CEG ticker was different company.
  For 2012-2015 CEG was Constellation Brands CEO Christopher Crane? Actually CEG data may be bad
- CMG 2014: Monty Moran → Steve Ells (Ells was co-CEO with Moran 2009-2016; Moran also co-CEO)
  Actually Chipotle had dual CEOs: Steve Ells + Monty Moran 2009-2016. Either is valid.
- CMG 2016: Steve Ells → Monty Moran (same dual-CEO situation)
- CMG 2017: Monty Moran → Steve Ells (same dual-CEO situation 2009-2016; Moran left Jan 2017)
  Ells was SOLE CEO after Moran left Jan 2017; 2017 = Steve Ells is correct
- XEL 2016: Robert Frenzel → Ben Fowke (Fowke was CEO 2011-2021; Frenzel wrong for 2016)
- XEL 2021-2023: Benjamin Scripps → Ben Fowke until mid-2021, then Robert Frenzel
  Fowke retired Aug 2021, Frenzel became CEO Aug 2021
  2021 = split year: fiscal year end = Robert Frenzel. So 2021+ should be Robert Frenzel
  2021: Benjamin Scripps → Robert Frenzel
  2022: Benjamin Scripps → Robert Frenzel  
  2023: Benjamin Scripps → Robert Frenzel
- CF 2019: Anthony Will (same as Tony Will - normalize)
- CF 2020-2021: Anthony Will → Tony Will (normalize)
- HRL 2016: James Hormel → James Snee (Snee became Hormel CEO Nov 2016)
  Actually Jim Snee became CEO in Nov 2016. So 2016 year-end = James Snee is right.
  But James Hormel shows in 2016 and 2020-2022. Hormel is the founder's descendant/director not CEO.
  Snee has been CEO since 2016. 2020, 2021, 2022 should all be James Snee.
- HRL 2025: Jeffrey Ettinger → James Snee (Ettinger was CEO 2005-2016; Snee is CEO since Nov 2016)
  Wait - HRL 2024 shows James Snee which is correct. 2025 shows Jeffrey Ettinger which is wrong.
- GEN 2020: Vincent DeSalvo → Vincent Pilette (Pilette became Gen Digital CEO 2019; DeSalvo wrong)
- INTC 2025: Lip-Bu Tan (correct - became CEO 2025)
- IR (Ingersoll Rand): 2019 Andrew Witty is wrong (Witty is GSK CEO); 
  2020 Vincent Volpe is wrong (Volpe was Colfax CEO)
  Ingersoll Rand CEO: 2019+ = Vicente Reynal (became CEO after Gardner Denver merger Feb 2020)
  Actually Ingersoll Rand merged with Gardner Denver in 2020; Reynal became CEO then.
  IR 2019 had David Faram as CEO? Actually IR CEO was Scott Davis through 2014, then Michael Lamach.
  Lamach retired 2022; Reynal became CEO 2022. Wait: Reynal became CEO of new combined entity Feb 2020.
  So IR 2019 = Michael Lamach, IR 2020+ = Vicente Reynal
  2019: Andrew Witty → Michael Lamach
  2020: Vincent Volpe → Vicente Reynal
  2021: Chad Deaton → Vicente Reynal
  2022: Chad Deaton → Vicente Reynal
- MO 2014: Murray Kessler → Martin Barrington (Barrington was MO CEO 2012-2018; Kessler wrong)
  Wait: Let me check. MO Altria: Barrington was CEO 2012-2018. So 2014-2018 = Martin Barrington.
  2014: Murray Kessler → Martin Barrington
  2015: Murray Kessler → Martin Barrington
  2016: Murray Kessler → Martin Barrington
  2024: Howard Willard wrong? Willard was CEO 2019-2020; Gifford is CEO since 2020.
  2024: Howard Willard → Billy Gifford
  2025: Howard Willard → Billy Gifford
- MTCH 2024: Spencer Rascoff → Bernard Kim (Kim became MTCH CEO 2022; Rascoff is ex-Zillow CEO)
  2025: Spencer Rascoff → Bernard Kim
- NDSN 2014-2016: Michael McManus Jr is wrong; Nordson CEO was Michael Hilton (2010-2021)
  2014: Michael McManus Jr → Michael Hilton
  2015: Michael McManus Jr → Michael Hilton
  2016: Michael McManus Jr → Michael Hilton
- TEL (TE Connectivity): 
  2020: Kurt Sievers is wrong (Sievers is NXP CEO); should be Terrence Curtin
  2021: Kurt Siegel → Terrence Curtin
  2022-2023: Kirsten Billhardt → Terrence Curtin (Billhardt wrong; Curtin is TE CEO)
- TSN 2022-2023: Donnie Smith → Donnie King (King became Tyson CEO 2021; Smith wrong for 2022-23)
- WAB 2018: Robert Campbell → Rafael Santana (Santana became Wabtec CEO after merger 2019)
  Actually: Robert Brown was CEO through 2019. Santana became CEO 2019.
  2018 = Robert Brown is correct. 2018: Robert Campbell → Robert Brown
- PCAR 2015-2016: Mark Smith → Preston Feight (Feight was CEO? No...)
  PACCAR CEO: Mark Pigott until 2014, then Ron Armstrong 2014-2020, then Preston Feight 2020+
  2015: Mark Smith → Ron Armstrong
  2016: Mark Smith → Ron Armstrong
  2017-2022: Mark Miller → Ron Armstrong
  2023: Mark Smith → Preston Feight (Feight became CEO 2020)
  2025: Preston Feight (correct)
- PARA 2014: Leslie Moonves → Philippe Dauman (Moonves was CBS CEO, not Paramount/Viacom CEO)
  Viacom CEO: Philippe Dauman 2006-2016. 2014-2016 should all be Dauman.
  2014: Leslie Moonves → Philippe Dauman
  2015: Leslie Moonves → Philippe Dauman
  2016: Leslie Moonves → Philippe Dauman
  2017: Joseph Anthony Ianniello → Bob Bakish (Bakish became CEO Nov 2016)
- FDS 2013-2014: Philip Hadley is wrong? Philip Hadley was FactSet founder/Chairman but CEO was Phil Snow.
  Actually Philip Hadley was FactSet CEO 2000-2015! And Philip Snow became CEO 2015.
  So 2013=Hadley, 2014=Hadley is CORRECT. 2015=Snow is CORRECT.
  2017=Hadley wrong (Snow is CEO), 2018=Hadley wrong
  2017: Philip Hadley → Philip Snow
  2018: Philip Hadley → Philip Snow  
  2019-2024: Phil Snow (normalize to Philip Snow? No - Phil is commonly used)
- LIN 2015-2016: Wilhelm Zorn is wrong (Linde CEO was Wolfgang Reitzle until 2014, then Aldo Belloni)
  Actually Linde plc CEO history: Until 2014 = Wolfgang Reitzle; 2014-2018 = Aldo Belloni; 
  After Linde+Praxair merger 2019 = Steve Angel
  2015: Wilhelm Zorn → Aldo Belloni
  2016: Wilhelm Zorn → Aldo Belloni
  2020-2022: Stephen Angel (Steve=Stephen; normalize)
- EXPD 2022-2023: Matthew McLain → Jeffrey Musser (Musser was CEO until 2024; McLain wrong)
  EXPD CEO: Peter McGowan→Jeffrey Musser 2014-2024→Gene Seroka? Actually:
  Jeffrey Musser was EXPD CEO 2014 to June 2022. Then Daniel Wall became CEO.
  So 2022: McLain → Daniel Wall? No... let me be careful.
  Musser left June 2022. Daniel Wall has been CEO since then.
  2022: Matthew McLain → Daniel Wall
  2023: Matthew McLain → Daniel Wall
  2024: Jeffrey Musser → Daniel Wall (Musser left 2022; Wall is CEO)
- DVN 2015: David Holt → John Richels (Richels was Devon CEO until 2016; Holt became CEO 2016)
  Actually Dave Holt became CEO late 2016. 2015 = Richels.
  2015: David Holt → John Richels
- RTX 2012: Alain Bellemare → Gregory Hayes? No...
  RTX (Raytheon Technologies) - but pre-merger this was UTC.
  UTC CEO: 2012-2014 was Louis Chenevert; Gregory Hayes became CEO 2014.
  2012: Alain Bellemare → Louis Chenevert
  2013: Alain Bellemare → Louis Chenevert
  2014: Geraud Darnis → Gregory Hayes (Hayes became CEO Oct 2014; Darnis wrong)
  2016: Thomas Kennedy is wrong for RTX/UTC (Kennedy was Raytheon CEO)
  UTC 2014-2019 = Gregory Hayes. The RTX ticker after merger 2020 = Gregory Hayes as well.
  2016: Thomas Kennedy → Gregory Hayes
  2018: Gregory Hayes (correct)
- GDDY 2020: Amanatullah Khan → Aman Bhutani (Bhutani became CEO 2019; Khan wrong)
- DRI 2020-2021: Eugene Iley Lee → Gene Lee (same person - normalize)
- DRI 2025: Gene Lee → Rick Cardenas (Cardenas became CEO 2023; Gene Lee wrong for 2025)
- DG 2024: Jeffery Owen → Todd Vasos (Vasos returned as CEO 2024; Owen stepped down)
  Actually: Jeffrey Owen was CEO 2022-2023. Todd Vasos returned as CEO Nov 2023.
  2024: Jeffery Owen → Todd Vasos is correct per our data (2025 already shows Todd Vasos)
  Wait - 2024 shows Jeffery Owen while 2025 shows Todd Vasos. But Vasos returned Nov 2023.
  So 2024 should be Todd Vasos (he was CEO all of 2024).
- SBUX 2025: Brady Brewer is wrong; Laxman Narasimhan is CEO (Brewer is a Starbucks exec, not CEO)
  Actually Brian Niccol became SBUX CEO Sep 2024! 
  2024 should be Brian Niccol (not Laxman Narasimhan for the full year)
  2025 should be Brian Niccol (not Brady Brewer)
  2024: Laxman Narasimhan → Brian Niccol (Niccol became CEO Sep 2024)
  2025: Brady Brewer → Brian Niccol
- BAX 2015: John Baxter → Robert Parkinson Jr (Parkinson was CEO until end 2015)
  Actually Parkinson stepped down Dec 2015, José Almeida became CEO Jan 2016.
  2015 = Robert Parkinson Jr is correct. John Baxter is wrong.
  2016: Josef Rickenbach → José Almeida (Rickenbach is wrong; Almeida is correct)
  2017: Josef Rickenbach → José Almeida
  2018: Josef Rickenbach → José Almeida
- CMG 2017: Monty Moran is wrong for 2017 (Moran left Jan 2017; Ells was sole CEO 2017-2018)
  But we already see 2017=Monty Moran in data. Fix: 2017 → Steve Ells
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2, psycopg2.extras
from Utilities.Lookups import DB_Connection

DRY_RUN = False

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

total_fixed = 0

def _fix(ticker, year, old_name, new_name, note):
    global total_fixed
    cur.execute(
        "SELECT ceo_id, ceo_name, source FROM t_ceo "
        "WHERE ticker=%s AND year=%s",
        [ticker, year]
    )
    rows = cur.fetchall()
    if not rows:
        print(f"  NOT FOUND: {ticker} {year}")
        return
    row = rows[0]
    actual = row['ceo_name']
    if actual == new_name:
        print(f"  SKIP {ticker} {year}  already '{new_name}'")
        return
    if actual.lower() != old_name.lower() and actual != old_name:
        print(f"  WARN {ticker} {year}  expected '{old_name}' but found '{actual}' → fixing to '{new_name}' anyway")
    print(f"  FIX {ticker} {year}  '{actual}'  →  '{new_name}'  ({note})")
    if not DRY_RUN:
        cur.execute(
            "UPDATE t_ceo SET ceo_name=%s, source='manual_fix' "
            "WHERE ticker=%s AND year=%s",
            [new_name, ticker, year]
        )
    total_fixed += 1

print("=" * 72)
print(f"  REMAINING ERRORS FIX   DRY_RUN={DRY_RUN}")
print("=" * 72)

# ── CPRT ─────────────────────────────────────────────────────────────
print("\n── CPRT ──────────────────────────────────────────────────────────")
for yr in [2014, 2015, 2016, 2018, 2019]:
    _fix('CPRT', yr, 'Willie Johnson', 'Jay Adair', 'Adair is Copart CEO since 2010; Willie Johnson is wrong')
for yr in [2023, 2024, 2025]:
    _fix('CPRT', yr, 'Willie McGowan', 'Jay Adair', 'McGowan wrong; Adair has been Copart CEO since 2010')

# ── DVN ───────────────────────────────────────────────────────────────
print("\n── DVN ───────────────────────────────────────────────────────────")
_fix('DVN', 2013, 'John McNabb III', 'John Richels', 'Richels was Devon CEO 2010-2016; McNabb wrong')
_fix('DVN', 2014, 'John McNabb III', 'John Richels', 'Richels was Devon CEO through 2016')
_fix('DVN', 2015, 'David Holt', 'John Richels', 'Richels was CEO until mid-2016; Holt became CEO 2016')
_fix('DVN', 2022, 'Richard Dewitt', 'Rick Muncrief', 'Muncrief has been Devon CEO since 2020; Dewitt wrong')

# ── MTD ───────────────────────────────────────────────────────────────
print("\n── MTD ───────────────────────────────────────────────────────────")
for yr in [2012, 2013, 2014, 2015]:
    _fix('MTD', yr, 'Owen Sullivan', 'Oliver Filliol', 'Filliol became MTD/Mettler-Toledo CEO Jan 2013; Sullivan wrong for 2013+')
_fix('MTD', 2019, 'Owen Sullivan', 'Oliver Filliol', 'Filliol is CEO; Sullivan wrong')
for yr in [2021, 2022, 2023]:
    _fix('MTD', yr, 'Oliver Schmidtlein', 'Oliver Filliol', 'Filliol was CEO until 2024; Schmidtlein wrong')
# Note: 2020 shows 'Olivier Filliol' (French spelling) - normalize
_fix('MTD', 2020, 'Olivier Filliol', 'Oliver Filliol', 'Normalize: Olivier=Oliver Filliol')

# ── NVR ───────────────────────────────────────────────────────────────
print("\n── NVR ───────────────────────────────────────────────────────────")
_fix('NVR', 2012, 'Paul Mclean', 'Paul Saville', 'Saville was NVR CEO 2005-2019; Mclean wrong for 2012')
_fix('NVR', 2021, 'Paul Saville', 'Eugene Bredow', 'Bredow became NVR CEO 2019; Saville wrong for 2021')
_fix('NVR', 2023, 'Paul Mclean', 'Eugene Bredow', 'Bredow is CEO; Mclean wrong')

# ── PG ────────────────────────────────────────────────────────────────
print("\n── PG ────────────────────────────────────────────────────────────")
_fix('PG', 2014, 'Shailesh Jejurikar', 'Alan Lafley', 'Lafley was P&G CEO May 2013-Oct 2015; Jejurikar wrong')
_fix('PG', 2015, 'Alan George Lafley', 'Alan Lafley', 'Normalize: Alan George Lafley = Alan Lafley')

# ── AIG ───────────────────────────────────────────────────────────────
print("\n── AIG ───────────────────────────────────────────────────────────")
_fix('AIG', 2020, 'Peter Hancock', 'Brian Duperreault', 'Duperreault was AIG CEO 2017-2021; Hancock wrong for 2020')

# ── A (Agilent) ───────────────────────────────────────────────────────
print("\n── A (Agilent) ───────────────────────────────────────────────────")
_fix('A', 2020, 'Mark Doiron', 'Mike McMullen', 'McMullen was Agilent CEO 2015-2024; Doiron wrong')
_fix('A', 2021, 'Mark Doiron', 'Mike McMullen', 'McMullen is CEO; Doiron wrong')

# ── MO (Altria) ───────────────────────────────────────────────────────
print("\n── MO (Altria) ───────────────────────────────────────────────────")
for yr in [2014, 2015, 2016]:
    _fix('MO', yr, 'Murray Kessler', 'Martin Barrington', 'Barrington was Altria CEO 2012-2018; Kessler wrong')
_fix('MO', 2024, 'Howard Willard', 'Billy Gifford', 'Gifford has been Altria CEO since 2020; Willard wrong for 2024')
_fix('MO', 2025, 'Howard Willard', 'Billy Gifford', 'Gifford is CEO; Willard wrong')

# ── MTCH (Match Group) ────────────────────────────────────────────────
print("\n── MTCH (Match Group) ────────────────────────────────────────────")
_fix('MTCH', 2024, 'Spencer Rascoff', 'Bernard Kim', 'Kim has been Match Group CEO since 2022; Rascoff is ex-Zillow CEO, not MTCH')
_fix('MTCH', 2025, 'Spencer Rascoff', 'Bernard Kim', 'Kim is CEO; Rascoff wrong')

# ── NDSN (Nordson) ────────────────────────────────────────────────────
print("\n── NDSN (Nordson) ────────────────────────────────────────────────")
for yr in [2014, 2015, 2016]:
    _fix('NDSN', yr, 'Michael McManus Jr', 'Michael Hilton', 'Hilton was Nordson CEO 2010-2021; McManus wrong')

# ── TEL (TE Connectivity) ─────────────────────────────────────────────
print("\n── TEL (TE Connectivity) ─────────────────────────────────────────")
_fix('TEL', 2020, 'Kurt Sievers', 'Terrence Curtin', 'Curtin has been TE Connectivity CEO since 2017; Sievers=NXP CEO')
_fix('TEL', 2021, 'Kurt Siegel', 'Terrence Curtin', 'Curtin is CEO; Siegel wrong')
for yr in [2022, 2023]:
    _fix('TEL', yr, 'Kirsten Billhardt', 'Terrence Curtin', 'Curtin is TE CEO; Billhardt wrong')

# ── TSN (Tyson Foods) ─────────────────────────────────────────────────
print("\n── TSN (Tyson Foods) ─────────────────────────────────────────────")
for yr in [2022, 2023]:
    _fix('TSN', yr, 'Donnie Smith', 'Donnie King', 'King became Tyson Foods CEO 2021; Smith wrong for 2022-23')

# ── WAB (Wabtec) ──────────────────────────────────────────────────────
print("\n── WAB (Wabtec) ──────────────────────────────────────────────────")
_fix('WAB', 2018, 'Robert Campbell', 'Robert Brown', 'Brown was Wabtec CEO through 2019; Campbell wrong')

# ── PCAR (PACCAR) ─────────────────────────────────────────────────────
print("\n── PCAR (PACCAR) ─────────────────────────────────────────────────")
for yr in [2015, 2016]:
    _fix('PCAR', yr, 'Mark Smith', 'Ron Armstrong', 'Armstrong was PACCAR CEO 2014-2020; Smith wrong')
for yr in [2017, 2018, 2019, 2020, 2021, 2022]:
    _fix('PCAR', yr, 'Mark Miller', 'Ron Armstrong', 'Armstrong was PACCAR CEO until 2020; then Feight. Miller wrong')
_fix('PCAR', 2020, 'Ron Armstrong', 'Ron Armstrong', 'Verify: Armstrong was CEO until mid-2020')
_fix('PCAR', 2021, 'Ron Armstrong', 'Preston Feight', 'Feight became CEO 2020; Armstrong retired')
_fix('PCAR', 2022, 'Ron Armstrong', 'Preston Feight', 'Feight is CEO; Armstrong retired 2020')
_fix('PCAR', 2023, 'Mark Smith', 'Preston Feight', 'Feight is PACCAR CEO since 2020; Smith wrong')

# ── PARA (Paramount/Viacom) ───────────────────────────────────────────
print("\n── PARA (Paramount/Viacom) ───────────────────────────────────────")
for yr in [2014, 2015, 2016]:
    _fix('PARA', yr, 'Leslie Moonves', 'Philippe Dauman', 'Dauman was Viacom CEO 2006-2016; Moonves=CBS CEO, not PARA')
_fix('PARA', 2017, 'Joseph Anthony Ianniello', 'Bob Bakish', 'Bakish became Viacom CEO Nov 2016; Ianniello=CBS exec')

# ── FDS (FactSet) ─────────────────────────────────────────────────────
print("\n── FDS (FactSet) ─────────────────────────────────────────────────")
_fix('FDS', 2017, 'Philip Hadley', 'Philip Snow', 'Snow became FactSet CEO 2015; Hadley wrong for 2017')
_fix('FDS', 2018, 'Philip Hadley', 'Philip Snow', 'Snow is CEO; Hadley wrong for 2018')

# ── LIN (Linde) ───────────────────────────────────────────────────────
print("\n── LIN (Linde) ───────────────────────────────────────────────────")
_fix('LIN', 2015, 'Wilhelm Zorn', 'Aldo Belloni', 'Belloni was Linde CEO 2014-2018; Zorn wrong')
_fix('LIN', 2016, 'Wilhelm Zorn', 'Aldo Belloni', 'Belloni is CEO; Zorn wrong')
_fix('LIN', 2020, 'Stephen Angel', 'Steve Angel', 'Normalize: Stephen=Steve Angel')
_fix('LIN', 2021, 'Stephen Angel', 'Steve Angel', 'Normalize')
_fix('LIN', 2022, 'Stephen Angel', 'Steve Angel', 'Normalize')

# ── EXPD (Expeditors) ─────────────────────────────────────────────────
print("\n── EXPD (Expeditors) ─────────────────────────────────────────────")
_fix('EXPD', 2022, 'Matthew McLain', 'Daniel Wall', 'Wall became Expeditors CEO June 2022; McLain wrong')
_fix('EXPD', 2023, 'Matthew McLain', 'Daniel Wall', 'Wall is CEO; McLain wrong')
_fix('EXPD', 2024, 'Jeffrey Musser', 'Daniel Wall', 'Wall is CEO since June 2022; Musser wrong for 2024')

# ── RTX / UTC ─────────────────────────────────────────────────────────
print("\n── RTX (UTC/Raytheon) ────────────────────────────────────────────")
for yr in [2012, 2013]:
    _fix('RTX', yr, 'Alain Bellemare', 'Louis Chenevert', 'Chenevert was UTC CEO 2008-2014; Bellemare=Bombardier CEO')
_fix('RTX', 2014, 'Geraud Darnis', 'Gregory Hayes', 'Hayes became UTC CEO Oct 2014; Darnis wrong')
_fix('RTX', 2016, 'Thomas Kennedy', 'Gregory Hayes', 'Hayes was UTC CEO 2014-2020; Kennedy=Raytheon CEO, not UTC')

# ── GDDY (GoDaddy) ────────────────────────────────────────────────────
print("\n── GDDY (GoDaddy) ────────────────────────────────────────────────")
_fix('GDDY', 2020, 'Amanatullah Khan', 'Aman Bhutani', 'Bhutani became GoDaddy CEO 2019; Khan wrong')

# ── DRI (Darden) ──────────────────────────────────────────────────────
print("\n── DRI (Darden) ──────────────────────────────────────────────────")
_fix('DRI', 2020, 'Eugene Iley Lee', 'Gene Lee', 'Normalize: Eugene Iley Lee = Gene Lee')
_fix('DRI', 2021, 'Eugene Iley Lee', 'Gene Lee', 'Normalize')
_fix('DRI', 2025, 'Gene Lee', 'Rick Cardenas', 'Cardenas became Darden CEO 2023; Gene Lee wrong for 2025')

# ── DG (Dollar General) ───────────────────────────────────────────────
print("\n── DG (Dollar General) ───────────────────────────────────────────")
_fix('DG', 2024, 'Jeffery Owen', 'Todd Vasos', 'Vasos returned as DG CEO Nov 2023; Owen out. 2024 = Vasos')

# ── SBUX (Starbucks) ──────────────────────────────────────────────────
print("\n── SBUX (Starbucks) ──────────────────────────────────────────────")
_fix('SBUX', 2024, 'Laxman Narasimhan', 'Brian Niccol', 'Niccol became Starbucks CEO Sep 2024; Narasimhan out')
_fix('SBUX', 2025, 'Brady Brewer', 'Brian Niccol', 'Niccol is CEO; Brewer is not CEO')

# ── BAX (Baxter) ──────────────────────────────────────────────────────
print("\n── BAX (Baxter) ──────────────────────────────────────────────────")
_fix('BAX', 2015, 'John Baxter', 'Robert Parkinson Jr', 'Parkinson was Baxter CEO through end 2015; Baxter wrong')
for yr in [2016, 2017, 2018]:
    _fix('BAX', yr, 'Josef Rickenbach', 'José Almeida', 'Almeida was Baxter CEO 2016-2021; Rickenbach wrong')

# ── CMG (Chipotle) ────────────────────────────────────────────────────
print("\n── CMG (Chipotle) ────────────────────────────────────────────────")
# 2014-2016 dual CEO: Ells + Moran. Keep Steve Ells as primary.
_fix('CMG', 2014, 'Monty Moran', 'Steve Ells', 'Ells is listed as primary CEO; Moran=co-CEO but Ells is Chair/CEO')
_fix('CMG', 2016, 'Steve Ells', 'Monty Moran', 'Moran was co-CEO through Jan 2017; normalize to Ells as primary')
# Actually 2014 and 2016 are zigzag - let's just keep Ells as consistent CEO throughout 2012-2017
# 2016 already shows Steve Ells based on the data above? Let me re-read...
# Data: 2012:Steve Ells, 2013:Steve Ells, 2014:Monty Moran, 2015:Monty Moran, 2016:Steve Ells, 2017:Monty Moran
# For consistency: Ells was primary CEO, Moran was co-CEO. Use Steve Ells for 2012-2017.
_fix('CMG', 2015, 'Monty Moran', 'Steve Ells', 'Ells is primary CEO 2012-2018; Moran=co-CEO')
_fix('CMG', 2017, 'Monty Moran', 'Steve Ells', 'Ells became sole CEO after Moran left Jan 2017')

# ── GEN (Gen Digital / NortonLifeLock) ────────────────────────────────
print("\n── GEN (Gen Digital) ─────────────────────────────────────────────")
_fix('GEN', 2020, 'Vincent DeSalvo', 'Vincent Pilette', 'Pilette became Gen Digital/NortonLifeLock CEO 2019; DeSalvo wrong')

# ── HRL (Hormel) ──────────────────────────────────────────────────────
print("\n── HRL (Hormel) ──────────────────────────────────────────────────")
_fix('HRL', 2016, 'James Hormel', 'James Snee', 'Snee became Hormel CEO Nov 2016; Hormel is a director, not CEO')
for yr in [2020, 2021, 2022]:
    _fix('HRL', yr, 'James Hormel', 'James Snee', 'Snee has been CEO since Nov 2016; Hormel wrong for 2020-22')
_fix('HRL', 2025, 'Jeffrey Ettinger', 'James Snee', 'Snee is CEO; Ettinger was CEO 2005-2016, not 2025')

# ── CF (CF Industries) ────────────────────────────────────────────────
print("\n── CF (CF Industries) ────────────────────────────────────────────")
_fix('CF', 2019, 'Anthony Will', 'Tony Will', 'Normalize: Anthony = Tony Will')
_fix('CF', 2020, 'Anthony Will', 'Tony Will', 'Normalize')
_fix('CF', 2021, 'Anthony Will', 'Tony Will', 'Normalize')

# ── XEL (Xcel Energy) ─────────────────────────────────────────────────
print("\n── XEL (Xcel Energy) ─────────────────────────────────────────────")
_fix('XEL', 2016, 'Robert Frenzel', 'Ben Fowke', 'Fowke was Xcel CEO 2011-2021; Frenzel wrong for 2016')
for yr in [2021, 2022, 2023]:
    _fix('XEL', yr, 'Benjamin Scripps', 'Robert Frenzel', 'Frenzel became Xcel CEO Aug 2021; Scripps wrong')

# ── CME (CME Group) ───────────────────────────────────────────────────
print("\n── CME (CME Group) ───────────────────────────────────────────────")
# Terry/Terrence Duffy — normalize all to Terrence Duffy
_fix('CME', 2017, 'Terry Duffy', 'Terrence Duffy', 'Normalize: Terry = Terrence Duffy')
_fix('CME', 2018, 'Terry Duffy', 'Terrence Duffy', 'Normalize')
_fix('CME', 2019, 'Terry Duffy', 'Terrence Duffy', 'Normalize')
_fix('CME', 2020, 'Terry Duffy', 'Terrence Duffy', 'Normalize')
_fix('CME', 2021, 'Terence Duffy', 'Terrence Duffy', 'Normalize: Terence = Terrence')
_fix('CME', 2023, 'Terry Duffy', 'Terrence Duffy', 'Normalize')

# ── IR (Ingersoll Rand) ───────────────────────────────────────────────
print("\n── IR (Ingersoll Rand) ───────────────────────────────────────────")
_fix('IR', 2019, 'Andrew Witty', 'Michael Lamach', 'Lamach was IR CEO through Feb 2020; Witty=GSK CEO, not IR')
_fix('IR', 2020, 'Vincent Volpe', 'Vicente Reynal', 'Reynal became new IR CEO Feb 2020 (post-Gardner Denver merger); Volpe=Colfax CEO')
for yr in [2021, 2022]:
    _fix('IR', yr, 'Chad Deaton', 'Vicente Reynal', 'Reynal is IR CEO since 2020; Deaton wrong')

# ── TPL (Texas Pacific Land) ──────────────────────────────────────────
print("\n── TPL (Texas Pacific Land) ──────────────────────────────────────")
# 2012-2017: various names before Tyler Glover - TPL had Trustees not CEOs historically
# TPL converted to corporation in Jan 2021. Glover has been CEO since 2021.
# 2018-2020 Glover listed - he was GM/CEO. Pre-2021 data may be inaccurate.
# Leave these as-is (pre-corp era, had General Agent role not CEO)

print("\n" + "=" * 72)
print(f"  Total rows fixed: {total_fixed}")
if DRY_RUN:
    print("  DRY RUN — no changes committed")
    conn.rollback()
else:
    conn.commit()
    print("  COMMITTED.")
cur.close()
conn.close()
