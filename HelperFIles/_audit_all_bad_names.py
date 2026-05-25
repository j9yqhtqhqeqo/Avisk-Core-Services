"""
_audit_all_bad_names.py
Query t_ceo for every suspicious name found in the distinct-name audit.
Prints ticker/year for each so we know exactly what to fix.
"""
import psycopg2, sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

def show(label, names):
    found = []
    for n in names:
        cur.execute(
            "SELECT ceo_name, ticker, year, source FROM t_ceo WHERE ceo_name=%s ORDER BY ticker, year",
            (n,)
        )
        rows = cur.fetchall()
        for r in rows:
            found.append(r)
    if found:
        print(f"\n{'─'*70}")
        print(f"  {label} ({len(found)} rows)")
        print(f"{'─'*70}")
        for r in found:
            print(f"  [{r[1]:<6}] {r[2]}  '{r[0]}'  [{r[3]}]")
    else:
        print(f"  {label}: (none found)")

# ── 🔴 Non-person / garbage ──────────────────────────────────────────────────
show("🔴 NON-PERSON — company / division names", [
    'Aflac Incorporated', 'AIG Re', 'Ampere Computing', 'Baker Hughes',
    'BNP Paribas Securities', 'Building Automation', 'Cooper Companies',
    'Exelon Utilities', 'Fingerhut Companies', 'Ford China',
    'Hewlett Packard Enterprise', 'Laboratoires Majorelle', 'Linde Engineering',
    'Loews Hotels', 'Medallion Midstream', 'Swedish Match',
])
show("🔴 NON-PERSON — document / section terms", [
    'Announces CEO Transition', 'Attacks Biden', 'Customer Satisfaction',
    'Dodges Bullet', 'Effective Date', 'Employment History',
    'Enterprise Clients', 'Exhibit Description', 'Filed Herewith',
    'Inclusion Council', 'Insider Trading Policy', 'Investor Relations Andres',
    'Just Made', 'Key Persons', 'Segment Disclosures',
    'Street Journal', 'Subsequent Events', 'Transcript Date Thursday',
    'Transition Date', 'Wall Street',
])
show("🔴 NON-PERSON — fixable headline fragments", [
    'Greg Abel Pledges', 'Howard Schultz Pays', 'Intel Appoints Lip',
])

# ── 🟠 Reversed names ────────────────────────────────────────────────────────
show("🟠 REVERSED — name in wrong order", [
    'Chambers John', 'Liveris Andrew',
])

# ── 🟡 Duplicate variants — same person ──────────────────────────────────────
show("🟡 DUPE — Jensen Huang variants", ['Jen-Hsun Huang'])
show("🟡 DUPE — Ginni Rometty variants", ['Virginia Rometty'])
show("🟡 DUPE — Tim Cook variants", ['Timothy Cook'])
show("🟡 DUPE — Clifton Pemble variants", ['Cliff Pemble', 'Clifford Pemble'])
show("🟡 DUPE — Tom Bené variants", ['Thomas Bene'])
show("🟡 DUPE — Ed Bastian variants", ['Edward Bastian'])
show("🟡 DUPE — Ed Breen variants", ['Edward Breen'])
show("🟡 DUPE — Jamie Dimon variants", ['James Dimon'])
show("🟡 DUPE — Chuck Robbins variants", ['Charles Robbins'])
show("🟡 DUPE — Charlie Scharf variants", ['Charles Scharf'])
show("🟡 DUPE — Dan Glaser variants", ['Daniel Glaser'])
show("🟡 DUPE — Dan Houston variants", ['Daniel Houston'])
show("🟡 DUPE — Dave Lesar variants", ['David Lesar'])
show("🟡 DUPE — Dave Regnery variants", ['David Regnery'])
show("🟡 DUPE — Frank D'Souza variants", ['Francisco D\'Souza'])
show("🟡 DUPE — Jim Cashman variants", ['James Cashman III'])
show("🟡 DUPE — Jim Cracchiolo variants", ['James Cracchiolo'])
show("🟡 DUPE — Jim Fitterling variants", ['James Fitterling'])
show("🟡 DUPE — Jim Robo variants", ['James Robo'])
show("🟡 DUPE — James Taiclet Jr variants", ['James Taiclet'])
show("🟡 DUPE — Matt Maddox variants", ['Matthew Maddox'])
show("🟡 DUPE — Matt Meloy variants", ['Matthew Meloy'])
show("🟡 DUPE — Mike Kaufmann variants", ['Michael Kaufmann'])
show("🟡 DUPE — Mike McMullen variants", ['Michael McMullen'])
show("🟡 DUPE — Mike Roman variants", ['Michael Roman'])
show("🟡 DUPE — Michael McManus Jr variants", ['Michael McManus'])
show("🟡 DUPE — Olivier Le Peuch variants", ['Olivier Peuch'])
show("🟡 DUPE — Patrick Gallagher Jr variants", ['Patrick Gallagher'])
show("🟡 DUPE — Rick Dreiling variants", ['Richard Dreiling'])
show("🟡 DUPE — Rick McVey variants", ['Richard McVey'])
show("🟡 DUPE — Rick Muncrief variants", ['Richard Muncrief'])
show("🟡 DUPE — Rob Painter variants", ['Robert Painter'])
show("🟡 DUPE — Rob Sands variants", ['Robert Sands'])
show("🟡 DUPE — Sam Hazen variants", ['Samuel Hazen'])
show("🟡 DUPE — Steve Luczo variants", ['Stephen Luczo'])
show("🟡 DUPE — Steve Milligan variants", ['Stephen Milligan'])
show("🟡 DUPE — Steve Rusckowski variants", ['Stephen Rusckowski'])
show("🟡 DUPE — Tim Archer variants", ['Timothy Archer'])
show("🟡 DUPE — Tom Leighton variants", ['Thomson Leighton'])
show("🟡 DUPE — Tom Folliard variants", ['Thomas Folliard'])
show("🟡 DUPE — Tom Polen variants", ['Thomas Polen'])
show("🟡 DUPE — Tom Reeg variants", ['Thomas Reeg'])
show("🟡 DUPE — Tom Rutledge variants", ['Thomas Rutledge'])
show("🟡 DUPE — Walt Bettinger variants", ['Walter Bettinger', 'Walter Bettinger II'])
show("🟡 DUPE — Benjamin Moreland variants", ['Ben Moreland'])
show("🟡 DUPE — David McCulloch typo", ['David McCulloh'])
show("🟡 DUPE — René Jones accent", ['Rene Jones'])
show("🟡 DUPE — Stéphane Bancel accent", ['Stephane Bancel'])
show("🟡 DUPE — Andrés Gluski accent", ['Andres Gluski'])
show("🟡 DUPE — Carol Tomé accent", ['Carol Tome'])
show("🟡 DUPE — Eric Mark Green typo", ['Eric Mark Edwards'])
show("🟡 DUPE — Albert White variants", ['Albert White III'])
show("🟡 DUPE — Alfred Kelly Jr variants", ['Alfred Kelly'])
show("🟡 DUPE — DG Macpherson remaining", ['DG Macpherson'])

cur.close()
conn.close()
print("\n\nDone.")
