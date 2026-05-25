"""
_fix_gww_macpherson.py
Normalize GWW 'DG Macpherson' → 'Donald Macpherson' for 2019-2020.
"""
import psycopg2, sys
sys.path.insert(0, '.')
from Utilities.Lookups import DB_Connection

conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
conn.autocommit = False
cur = conn.cursor()

cur.execute(
    "UPDATE t_ceo SET ceo_name='Donald Macpherson', source='manual_fix', modify_dt=NOW() "
    "WHERE ticker='GWW' AND ceo_name='DG Macpherson'",
)
print(f"Rows updated: {cur.rowcount}")
conn.commit()
cur.close()
conn.close()
print("Done.")
