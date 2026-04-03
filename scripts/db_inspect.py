import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from engine.db import engine
print("DB path:", engine.url)
from sqlalchemy import text

with engine.connect() as conn:
    for table in ['raw_market_data', 'features_normalized', 'labels', 'raw_events', 'trade_history']:
        try:
            r = conn.execute(text(f"SELECT count(*) FROM {table}"))
            print(f"{table}: {r.scalar()}")
        except Exception as e:
            print(f"{table}: ERROR - {e}")
