"""Heartbeat #225 data collection - DB analysis and market data"""
import sqlite3, os, json

home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
db_path = os.path.join(home, 'poly_trader.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)

# Raw data
for t in tables:
    if 'raw' in t.lower() or t == 'market_data':
        c.execute(f'PRAGMA table_info({t})')
        cols = [r[1] for r in c.fetchall()]
        print(f'\nTable {t} columns: {cols}')
        c.execute(f'SELECT COUNT(*) FROM {t}')
        cnt = c.fetchone()[0]
        print(f'  Rows: {cnt}')
        if 'close' in cols:
            c.execute(f'SELECT close FROM {t} WHERE close IS NOT NULL ORDER BY rowid DESC LIMIT 5')
            for r in c.fetchall():
                print(f'  Recent close: {r[0]}')
        if 'timestamp' in cols:
            c.execute(f'SELECT timestamp FROM {t} ORDER BY rowid DESC LIMIT 3')
            for r in c.fetchall():
                print(f'  Recent ts: {r[0]}')

# Labels
for t in tables:
    if 'label' in t.lower():
        c.execute(f'PRAGMA table_info({t})')
        schema = c.fetchall()
        print(f'\nTable {t}:')
        for col in schema:
            print(f'  {col}')
        c.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'  Rows: {c.fetchone()[0]}')
        c.execute(f'SELECT * FROM {t} LIMIT 5')
        print(f'  Sample: {c.fetchall()[:5]}')
        # Check for sell_win column
        col_names = [r[1] for r in schema]
        for cn in col_names:
            if 'sell' in cn.lower() or 'win' in cn.lower():
                c.execute(f'SELECT ({cn})::float FROM {t} WHERE ({cn}) IS NOT NULL LIMIT 5')
                c.execute(f'SELECT {cn}, COUNT(*) FROM {t} GROUP BY {cn}')
                print(f'  {cn} distribution: {c.fetchall()[:10]}')
        # Check all numeric columns
        c.execute(f'SELECT * FROM {t} LIMIT 1')
        sample = c.fetchone()
        if sample:
            print(f'  First row values: {list(zip(col_names, sample))}')
        # Aggregate for sell_win-like columns
        for cn in col_names:
            c.execute(f'SELECT COUNT({cn}) as cnt, AVG({cn}) as avg FROM {t} WHERE {cn} IS NOT NULL')
            r = c.fetchone()
            if r[0] > 0:
                print(f'  {cn}: count={r[0]}, avg={r[1]}')

# Features
for t in tables:
    if 'feature' in t.lower():
        c.execute(f'PRAGMA table_info({t})')
        cols = [r[1] for r in c.fetchall()]
        print(f'\nTable {t} ({len(cols)} cols): {cols}')
        c.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'  Rows: {c.fetchone()[0]}')

# Derivatives data
print('\n--- Latest market metrics ---')
# Try to find BTC price
for t in tables:
    c.execute(f'PRAGMA table_info({t})')
    cols = [r[1] for r in c.fetchall()]
    if 'close' in cols:
        c.execute(f'SELECT close FROM {t} WHERE close IS NOT NULL ORDER BY rowid DESC LIMIT 1')
        r = c.fetchone()
        if r:
            print(f'BTC Price (from {t}): {r[0]}')
            break

conn.close()
