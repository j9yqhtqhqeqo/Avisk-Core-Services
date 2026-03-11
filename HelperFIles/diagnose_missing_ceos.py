"""
diagnose_missing_ceos.py
------------------------
For each ticker/year in the missing-CEO list, check:
  1. Does t_data_source have a 10K row?
  2. Does the file exist on disk?
  3. If yes, what does _extract_ceo_from_sec_text return?
     If None, dump a short excerpt so we can see why patterns fail.

Usage (on VM or locally with DB access):
  python3 HelperFIles/diagnose_missing_ceos.py 2>&1 | tee /tmp/diag.txt
"""

from Services.CEODataService import (
    _extract_ceo_from_sec_text,
    _extract_text_from_file,
    _PROXY_RE,
)
from Utilities.Lookups import DB_Connection
import psycopg2.extras
import psycopg2
from collections import defaultdict
from pathlib import Path
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Missing list ──────────────────────────────────────────────────────────────
MISSING = """ABNB,Airbnb Inc,2012
ABNB,Airbnb Inc,2014
AEE,Ameren Corp,2025
AES,The AES Corporation,2024
AES,The AES Corporation,2025
AIG,American International Group Inc,2024
AKAM,Akamai Technologies Inc,2023
AKAM,Akamai Technologies Inc,2024
AKAM,Akamai Technologies Inc,2025
ALB,Albemarle Corp,2025
ALLE,Allegion PLC,2012
AMGN,Amgen Inc,2025
ANSS,ANSYS Inc,2025
AOS,Smith AO Corporation,2014
AOS,Smith AO Corporation,2015
AOS,Smith AO Corporation,2016
AOS,Smith AO Corporation,2017
APA,APA Corporation,2025
APO,Apollo Global Management LLC Class A,2024
APO,Apollo Global Management LLC Class A,2025
APTV,Aptiv PLC,2015
APTV,Aptiv PLC,2024
APTV,Aptiv PLC,2025
AVB,AvalonBay Communities Inc,2024
AVY,Avery Dennison Corp,2024
AVY,Avery Dennison Corp,2025
BALL,Ball Corporation,2025
BEN,Franklin Resources Inc,2024
BEN,Franklin Resources Inc,2025
BF,Brown-Forman Corporation,2025
BMY,Bristol-Myers Squibb Company,2024
BMY,Bristol-Myers Squibb Company,2025
BRK,Berkshire Hathaway Inc,2025
BRO,Brown & Brown Inc,2024
BRO,Brown & Brown Inc,2025
CARR,Carrier Global Corp,2012
CARR,Carrier Global Corp,2013
CARR,Carrier Global Corp,2014
CARR,Carrier Global Corp,2015
CARR,Carrier Global Corp,2016
CB,Chubb Ltd,2025
CBRE,CBRE Group Inc Class A,2024
CBRE,CBRE Group Inc Class A,2025
CCI,Crown Castle,2025
CEG,Constellation Energy Corp,2016
CEG,Constellation Energy Corp,2018
CF,CF Industries Holdings Inc,2020
CF,CF Industries Holdings Inc,2021
CL,Colgate-Palmolive Company,2025
CME,CME Group Inc,2024
CME,CME Group Inc,2025
CMG,Chipotle Mexican Grill Inc,2025
CMI,Cummins Inc,2024
CMI,Cummins Inc,2025
COO,The Cooper Companies Inc,2025
CPT,Camden Property Trust,2024
CPT,Camden Property Trust,2025
CRWD,Crowdstrike Holdings Inc,2012
CRWD,Crowdstrike Holdings Inc,2013
CRWD,Crowdstrike Holdings Inc,2014
CRWD,Crowdstrike Holdings Inc,2015
CRWD,Crowdstrike Holdings Inc,2016
CSX,CSX Corporation,2024
CSX,CSX Corporation,2025
CVS,CVS Health Corp,2024
CVS,CVS Health Corp,2025
CZR,Caesars Entertainment Corporation,2025
D,Dominion Energy Inc,2025
DASH,DoorDash Inc,2012
DASH,DoorDash Inc,2013
DASH,DoorDash Inc,2014
DASH,DoorDash Inc,2015
DASH,DoorDash Inc,2016
DECK,Deckers Outdoor Corporation,2025
DFS,Discover Financial Services,2025
DHI,DR Horton Inc,2025
DLR,Digital Realty Trust Inc,2024
DLR,Digital Realty Trust Inc,2025
DLTR,Dollar Tree Inc,2025
DOC,Healthpeak Properties Inc,2025
DOW,Dow Inc,2012
DOW,Dow Inc,2013
DOW,Dow Inc,2014
DOW,Dow Inc,2024
DOW,Dow Inc,2025
DVN,Devon Energy Corporation,2024
DVN,Devon Energy Corporation,2025
DXCM,DexCom Inc,2024
EG,Everest Group Ltd,2019
EG,Everest Group Ltd,2022
EMN,Eastman Chemical Company,2025
ENPH,Enphase Energy Inc,2012
ENPH,Enphase Energy Inc,2025
EQIX,Equinix Inc,2025
ETN,Eaton Corporation PLC,2024
ETN,Eaton Corporation PLC,2025
EVRG,Evergy Inc,2012
EVRG,Evergy Inc,2013
EVRG,Evergy Inc,2014
EVRG,Evergy Inc,2015
EW,Edwards Lifesciences Corp,2025
FANG,Diamondback Energy Inc,2025
FFIV,F5 Networks Inc,2024
FFIV,F5 Networks Inc,2025
FI,Fiserv Inc,2025
FOX,Fox Corp Class B,2012
FOX,Fox Corp Class B,2013
FOX,Fox Corp Class B,2014
FOX,Fox Corp Class B,2015
FOXA,Fox Corp Class A,2012
FTNT,Fortinet Inc,2025
FTV,Fortive Corp,2012
GEHC,GE HealthCare Technologies Inc,2012
GEHC,GE HealthCare Technologies Inc,2013
GEHC,GE HealthCare Technologies Inc,2014
GEHC,GE HealthCare Technologies Inc,2015
GEHC,GE HealthCare Technologies Inc,2016
GEHC,GE HealthCare Technologies Inc,2017
GEHC,GE HealthCare Technologies Inc,2019
GEN,Gen Digital Inc,2023
GEN,Gen Digital Inc,2024
GEN,Gen Digital Inc,2025
GIS,General Mills Inc,2025
GPC,Genuine Parts Co,2024
GPC,Genuine Parts Co,2025
GWW,WW Grainger Inc,2024
GWW,WW Grainger Inc,2025
HAS,Hasbro Inc,2024
HAS,Hasbro Inc,2025
HES,Hess Corporation,2024
HES,Hess Corporation,2025
HIG,Hartford Financial Services Group,2024
HIG,Hartford Financial Services Group,2025
HPE,Hewlett Packard Enterprise Co,2012
HPE,Hewlett Packard Enterprise Co,2013
IBM,International Business Machines,2025
IEX,IDEX Corporation,2025
IFF,International Flavors & Fragrances Inc,2024
IFF,International Flavors & Fragrances Inc,2025
INVH,Invitation Homes Inc,2012
INVH,Invitation Homes Inc,2013
INVH,Invitation Homes Inc,2014
IP,International Paper,2025
IPG,Interpublic Group of Companies Inc,2024
IPG,Interpublic Group of Companies Inc,2025
IQV,IQVIA Holdings Inc,2012
ITW,Illinois Tool Works Inc,2024
ITW,Illinois Tool Works Inc,2025
JNPR,Juniper Networks Inc,2025
K,Kellanova,2015
K,Kellanova,2018
K,Kellanova,2024
K,Kellanova,2025
KEY,KeyCorp,2024
KEY,KeyCorp,2025
KEYS,Keysight Technologies Inc,2012
KEYS,Keysight Technologies Inc,2024
KEYS,Keysight Technologies Inc,2025
KHC,Kraft Heinz Co,2012
KHC,Kraft Heinz Co,2013
KHC,Kraft Heinz Co,2024
KHC,Kraft Heinz Co,2025
KKR,KKR & Co LP,2025
KMI,Kinder Morgan Inc,2024
KMI,Kinder Morgan Inc,2025
KR,Kroger Company,2025
KVUE,Kenvue Inc,2012
KVUE,Kenvue Inc,2013
KVUE,Kenvue Inc,2014
KVUE,Kenvue Inc,2015
KVUE,Kenvue Inc,2016
KVUE,Kenvue Inc,2017
KVUE,Kenvue Inc,2018
KVUE,Kenvue Inc,2019
KVUE,Kenvue Inc,2020
KVUE,Kenvue Inc,2021
LIN,Linde plc Ordinary Shares,2012
LKQ,LKQ Corporation,2025
LMT,Lockheed Martin Corporation,2025
LVS,Las Vegas Sands Corp,2025
LW,Lamb Weston Holdings Inc,2012
LW,Lamb Weston Holdings Inc,2013
LW,Lamb Weston Holdings Inc,2014
LW,Lamb Weston Holdings Inc,2015
MAA,Mid-America Apartment Communities Inc,2024
MAA,Mid-America Apartment Communities Inc,2025
MAS,Masco Corporation,2023
MAS,Masco Corporation,2024
MAS,Masco Corporation,2025
MCD,McDonalds Corporation,2025
MDLZ,Mondelez International Inc,2025
MHK,Mohawk Industries Inc,2024
MHK,Mohawk Industries Inc,2025
MKTX,MarketAxess Holdings Inc,2024
MKTX,MarketAxess Holdings Inc,2025
MLM,Martin Marietta Materials Inc,2024
MLM,Martin Marietta Materials Inc,2025
MMC,Marsh & McLennan Companies Inc,2025
MNST,Monster Beverage Corp,2025
MO,Altria Group,2024
MO,Altria Group,2025
MPC,Marathon Petroleum Corp,2025
MPWR,Monolithic Power Systems Inc,2025
MRK,Merck & Company Inc,2025
MRNA,Moderna Inc,2012
MRNA,Moderna Inc,2013
MRNA,Moderna Inc,2014
MRNA,Moderna Inc,2015
MRNA,Moderna Inc,2016
MRNA,Moderna Inc,2017
MRNA,Moderna Inc,2025
MS,Morgan Stanley,2025
MTB,MT Bank Corporation,2025
MTCH,Match Group Inc,2012
MTCH,Match Group Inc,2024
MTCH,Match Group Inc,2025
MTD,Mettler-Toledo International Inc,2024
MTD,Mettler-Toledo International Inc,2025
NCLH,Norwegian Cruise Line Holdings Ltd,2025
NEM,Newmont Goldcorp Corp,2025
NTRS,Northern Trust Corporation,2025
NWS,News Corp B,2025
NWSA,News Corp A,2025
ON,ON Semiconductor Corporation,2025
ORLY,OReilly Automotive Inc,2025
OTIS,Otis Worldwide Corp,2012
OTIS,Otis Worldwide Corp,2013
OTIS,Otis Worldwide Corp,2014
OTIS,Otis Worldwide Corp,2015
OTIS,Otis Worldwide Corp,2016
OTIS,Otis Worldwide Corp,2017
PARA,Paramount Global Class B,2024
PARA,Paramount Global Class B,2025
PCG,PGE Corp,2025
PG,Procter & Gamble Company,2013
PG,Procter & Gamble Company,2014
PGR,Progressive Corp,2025
PLD,Prologis Inc,2025
PLTR,Palantir Technologies Inc,2013
PLTR,Palantir Technologies Inc,2015
PNW,Pinnacle West Capital Corp,2024
PPL,PPL Corporation,2025
PSA,Public Storage,2024
PWR,Quanta Services Inc,2024
PWR,Quanta Services Inc,2025
REGN,Regeneron Pharmaceuticals Inc,2025
RF,Regions Financial Corporation,2025
RJF,Raymond James Financial Inc,2025
ROP,Roper Technologies Inc,2024
ROP,Roper Technologies Inc,2025
RSG,Republic Services Inc,2025
SBUX,Starbucks Corporation,2025
SNA,Snap-On Inc,2025
SOLV,Solventum Corp,2012
SOLV,Solventum Corp,2013
SOLV,Solventum Corp,2014
SOLV,Solventum Corp,2015
SOLV,Solventum Corp,2016
SOLV,Solventum Corp,2017
SOLV,Solventum Corp,2018
SOLV,Solventum Corp,2019
SOLV,Solventum Corp,2020
SOLV,Solventum Corp,2021
SOLV,Solventum Corp,2022
SOLV,Solventum Corp,2023
STLD,Steel Dynamics Inc,2025
STT,State Street Corp,2024
STT,State Street Corp,2025
STX,Seagate Technology PLC,2024
STX,Seagate Technology PLC,2025
SW,Smurfit WestRock plc,2012
SW,Smurfit WestRock plc,2013
SW,Smurfit WestRock plc,2014
SW,Smurfit WestRock plc,2015
SW,Smurfit WestRock plc,2016
SW,Smurfit WestRock plc,2017
SW,Smurfit WestRock plc,2020
SW,Smurfit WestRock plc,2021
SW,Smurfit WestRock plc,2022
SW,Smurfit WestRock plc,2023
SWK,Stanley Black & Decker Inc,2024
SWK,Stanley Black & Decker Inc,2025
SYF,Synchrony Financial,2012
TDY,Teledyne Technologies Incorporated,2025
TER,Teradyne Inc,2022
TFC,Truist Financial Corp,2025
TPL,Texas Pacific Land Trust,2012
TPL,Texas Pacific Land Trust,2013
TRGP,Targa Resources Inc,2024
TROW,T Rowe Price Group Inc,2024
TROW,T Rowe Price Group Inc,2025
TSCO,Tractor Supply Company,2025
TXT,Textron Inc,2025
TYL,Tyler Technologies Inc,2024
TYL,Tyler Technologies Inc,2025
UAL,United Airlines Holdings Inc,2025
UBER,Uber Technologies Inc,2013
UDR,UDR Inc,2025
UNH,UnitedHealth Group Incorporated,2025
UPS,United Parcel Service Inc,2025
URI,United Rentals Inc,2025
VICI,VICI Properties Inc,2012
VICI,VICI Properties Inc,2013
VICI,VICI Properties Inc,2014
VICI,VICI Properties Inc,2015
VICI,VICI Properties Inc,2016
VLO,Valero Energy Corporation,2025
VLTO,Veralto Corporation,2012
VLTO,Veralto Corporation,2013
VLTO,Veralto Corporation,2014
VLTO,Veralto Corporation,2015
VLTO,Veralto Corporation,2016
VLTO,Veralto Corporation,2017
VLTO,Veralto Corporation,2018
VLTO,Veralto Corporation,2019
VLTO,Veralto Corporation,2020
VLTO,Veralto Corporation,2021
VLTO,Veralto Corporation,2022
VMC,Vulcan Materials Company,2024
VRSN,VeriSign Inc,2024
VRSN,VeriSign Inc,2025
VST,Vistra Energy Corp,2012
VST,Vistra Energy Corp,2013
VST,Vistra Energy Corp,2015
VST,Vistra Energy Corp,2016
VTRS,Viatris Inc,2012
VTRS,Viatris Inc,2013
VTRS,Viatris Inc,2014
VTRS,Viatris Inc,2015
VTRS,Viatris Inc,2016
VTRS,Viatris Inc,2017
VTRS,Viatris Inc,2018
WAT,Waters Corporation,2024
WAT,Waters Corporation,2025
WBA,Walgreens Boots Alliance Inc,2025
WBD,Warner Bros Discovery Inc,2025
WM,Waste Management Inc,2024
WM,Waste Management Inc,2025
WMB,Williams Companies Inc,2024
WMB,Williams Companies Inc,2025
WRB,W R Berkley Corp,2025
WTW,Willis Towers Watson PLC,2025
WYNN,Wynn Resorts Limited,2025
XEL,Xcel Energy Inc,2024
XEL,Xcel Energy Inc,2025"""

# ── Parse list ────────────────────────────────────────────────────────────────
tasks = []
for line in MISSING.strip().splitlines():
    parts = line.split(',', 2)
    if len(parts) == 3:
        tasks.append(
            (parts[0].strip(), parts[1].strip(), int(parts[2].strip())))

# ── Connect ───────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = True

# ── GCS candidate base paths ──────────────────────────────────────────────────
_gcs_root = '/opt/avisk/gcs-data'
_candidate_bases = [
    f"{_gcs_root}/Development/data/Stage0SourcePDFFiles/",
    f"{_gcs_root}/Production/data/Stage0SourcePDFFiles/",
]
# Also try PathConfiguration
try:
    from Utilities.PathConfiguration import PathConfiguration
    pc_path = PathConfiguration().get_stage0_input_path()
    if pc_path and pc_path not in _candidate_bases:
        _candidate_bases.insert(0, pc_path)
except Exception:
    pass

print(f"Checking {len(tasks)} missing CEO records...\n")
print(f"GCS base paths to check: {_candidate_bases}\n")
print("=" * 90)

# Counters for summary
no_db_row = []   # no t_data_source row at all
proxy_skipped = []   # only proxy/DEF14A rows
file_missing = []   # DB row exists but file not on disk
parse_fail = []   # file found, text extracted, but pattern returned None
success = []   # would resolve with pattern fix

# ── Main loop ─────────────────────────────────────────────────────────────────
for ticker, company, year in tasks:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT source_url, source_confidence_score, content_type
            FROM   t_data_source
            WHERE  content_type = 2
              AND  year = %s
              AND  (ticker ILIKE %s OR company_name ILIKE %s)
            ORDER BY source_confidence_score DESC NULLS LAST, unique_id DESC
            LIMIT 5
        """, (year, ticker, f'%{company[:20]}%'))
        rows = cur.fetchall()

    if not rows:
        no_db_row.append((ticker, year))
        continue

    all_proxy = True
    found_file = False
    found_text = False

    for row in rows:
        src = (row['source_url'] or '').strip()
        if not src:
            continue

        is_proxy = bool(_PROXY_RE.search(src))
        if is_proxy:
            continue
        all_proxy = False

        # Try to resolve file
        text = None
        if src.startswith('http://') or src.startswith('https://'):
            found_file = True  # treat URL as "available"
            # Don't actually fetch — just note it's a URL
            print(f"[URL ] {ticker:6} {year}  URL={src[:80]}")
            found_text = True  # assume fetchable; skip pattern test for URLs
            continue

        resolved = None
        for base in _candidate_bases:
            p = Path(base) / str(year) / src
            if p.exists():
                resolved = p
                break

        if resolved is None:
            file_missing.append((ticker, year, src))
            continue

        found_file = True
        text = _extract_text_from_file(resolved)
        if not text:
            parse_fail.append((ticker, year, str(resolved), 'empty_text'))
            continue

        found_text = True
        name = _extract_ceo_from_sec_text(text)
        if name:
            success.append((ticker, year, name, str(resolved)))
            print(f"[OK  ] {ticker:6} {year}  → {name}  ({resolved.name})")
        else:
            parse_fail.append((ticker, year, str(resolved), 'pattern_miss'))
            # Dump excerpt around "Chief Executive"
            excerpt_idx = text.lower().find('chief executive')
            if excerpt_idx >= 0:
                snippet = text[max(0, excerpt_idx - 200):excerpt_idx + 300]
                snippet = re.sub(r'\n{3,}', '\n\n', snippet).strip()
            else:
                snippet = text[:500]
            print(f"[MISS] {ticker:6} {year}  file={resolved.name}")
            print(f"       Excerpt:")
            for ln in snippet.splitlines()[:20]:
                print(f"         {ln}")
            print()

    if all_proxy:
        proxy_skipped.append((ticker, year))

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SUMMARY")
print("=" * 90)
print(
    f"  No t_data_source row at all : {len(no_db_row):>4}  → need FMP/AI/web fallback")
print(
    f"  Only proxy/DEF14A in DB     : {len(proxy_skipped):>4}  → need FMP/AI/web fallback")
print(
    f"  DB row but file missing     : {len(file_missing):>4}  → GCS mount / path issue")
print(
    f"  File found, pattern missed  : {len(parse_fail):>4}  → regex fix needed")
print(
    f"  Would resolve with fix      : {len(success):>4}  → pattern already works")
print()

# Group pattern misses by failure subtype
pattern_misses = [(t, y, f, s)
                  for t, y, f, s in parse_fail if s == 'pattern_miss']
if pattern_misses:
    print(
        f"\nPattern misses ({len(pattern_misses)} cases) — need new regex patterns:")
    for t, y, f, _ in pattern_misses[:30]:
        print(f"  {t:6} {y}  {Path(f).name}")

if file_missing:
    print(
        f"\nFile-missing cases ({len(file_missing)}) — file in DB but not on disk:")
    # Group by ticker
    by_ticker = defaultdict(list)
    for t, y, s in file_missing:
        by_ticker[t].append(y)
    for t in sorted(by_ticker):
        print(f"  {t:6}: years {sorted(by_ticker[t])}")

conn.close()
