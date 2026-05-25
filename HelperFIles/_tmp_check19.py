import sys, os
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ['DEPLOYMENT_ENV'] = 'development'
import psycopg2
from Utilities.Lookups import DB_Connection
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()
tickers = ['AXON','CEG','CMG','CSX','DLTR','FDS','GEN','IFF','INTC','LIN','MTCH','OTIS','PCAR','PCG','PYPL','RTX','SBUX','TAP','TPL']
for t in tickers:
    cur.execute('SELECT year, ceo_name FROM t_ceo WHERE ticker=%s ORDER BY year', (t,))
    rows = cur.fetchall()
    print(t + ': ' + ', '.join(str(y)+':'+n for y,n in rows))
cur.close(); conn.close()
