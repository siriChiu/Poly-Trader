import sqlite3

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f'All tables: {tables}')

# Check features_normalized for ear and tongue columns specifically
print('\n=== features_normalized columns with ear/tongue ===')
cursor.execute('PRAGMA table_info(features_normalized)')
for col in cursor.fetchall():
    if 'ear' in col[1].lower() or 'tongue' in col[1].lower():
        print(f'  {col[1]} ({col[2]})')

# Check the actual column names more carefully
print('\n=== ALL features_normalized columns ===')
cursor.execute('PRAGMA table_info(features_normalized)')
for col in cursor.fetchall():
    print(f'  {col[1]} ({col[2]})')

# Look for columns containing '_zscore' or '_pct'
print('\n=== Looking for columns with _zscore or _pct ===')
cursor.execute('PRAGMA table_info(features_normalized)')
all_cols = [col[1] for col in cursor.fetchall()]
for c in all_cols:
    if 'zscore' in c.lower() or '_pct' in c.lower():
        print(f'  {c}')

conn.close()
