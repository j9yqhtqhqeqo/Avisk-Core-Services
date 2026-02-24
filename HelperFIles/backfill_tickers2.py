import psycopg2
from Utilities.Lookups import DB_Connection
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')

EXTRA = {
    "African Rainbow Minerals": "ARI",
    "Alcoa Corp": "AA",
    "AngloGold Ashanti": "AU",
    "Antero Resources Corporation": "AR",
    "Apache Corporation": "APA",
    "BHP": "BHP",
    "Callon Petroleum": "CPE",
    "Chesapeake Energy": "CHK",
    "China Water Affairs Group": "CWAG",
    "Chord Energy": "CHRD",
    "Civitas Resources": "CIVI",
    "Coca-Cola Company (The)": "KO",
    "Codelco": "CODELCO",
    "Crescent Point Energy Corp.": "CPG",
    "Diversified Energy": "DEC",
    "EOG Resources, Inc.": "EOG",
    "Enerplus Resources (USA) Corporation": "ERF",
    "ExxonMobil": "XOM",
    "Gulfport Energy Corporation": "GPOR",
    "Ovintiv, Inc.": "OVV",
    "Permian Resources": "PR",
    "Pioneer Natural Resources Company": "PXD",
    "RTX Corporation": "RTX",
    "Range Resources ": "RRC",
    "Rio Tinto": "RIO",
    "SM Energy Company": "SM",
    "Seneca Resources Corporation": "SEN",
    "Sibanye Stillwater Limited": "SBSW",
    "Southwestern Energy Company": "SWN",
    "Sumitomo Metal Mining Co., Ltd.": "SMMYY",
    "Teck": "TECK",
    "Vital Energy": "VTLE",
    "XTO Energy, Inc.": "XTO",
    "VALE S.A.": "VALE",
    "FREEPORT-MCMORAN I": "FCX",
    "NEWMONT Corp /DE/": "NEM",
    "Gold Fields": "GFI",
}

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()
total = 0
for company, ticker in EXTRA.items():
    cur.execute(
        "UPDATE t_data_source SET ticker = %s WHERE company_name = %s AND ticker IS NULL",
        (ticker, company)
    )
    total += cur.rowcount
conn.commit()

cur.execute("SELECT COUNT(*) FROM t_data_source WHERE ticker IS NULL")
remaining = cur.fetchone()[0]
print(f"Updated: {total}  |  Still null: {remaining}")

if remaining:
    cur.execute("""
        SELECT DISTINCT company_name
        FROM t_data_source
        WHERE ticker IS NULL
        ORDER BY company_name
    """)
    print("Remaining unresolved:")
    for row in cur.fetchall():
        print(f"  {row[0]!r}")

cur.close()
conn.close()
