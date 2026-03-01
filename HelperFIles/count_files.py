"""
count_files.py - quick count of file breakdown
"""
from Utilities.Lookups import DB_Connection
import psycopg2
import sys
import os
sys.path.insert(0, "/opt/avisk/app")
os.chdir("/opt/avisk/app")
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()
cur.execute("""
  SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE original_source_url ILIKE '%sec.gov/Archives/edgar%') AS edgar,
    COUNT(*) FILTER (WHERE original_source_url NOT ILIKE '%sec.gov/Archives/edgar%'
                        OR original_source_url IS NULL) AS non_edgar,
    COUNT(*) FILTER (WHERE source_url ILIKE '%.pdf') AS pdfs,
    COUNT(*) FILTER (WHERE source_url ILIKE '%.htm%') AS htms,
    COUNT(*) FILTER (WHERE source_url ILIKE '%.txt') AS txts
  FROM t_data_source WHERE source_type = 'file'
""")
r = cur.fetchone()
print(f"Total file rows : {r[0]:,}")
print(f"EDGAR           : {r[1]:,}")
print(f"Non-EDGAR       : {r[2]:,}")
print(f"PDFs            : {r[3]:,}")
print(f"HTMs            : {r[4]:,}")
print(f"TXTs            : {r[5]:,}")
cur.close()
conn.close()
