import sqlite3
db_path = r"C:\Users\Kazuha\repo\poly-trader\poly_trader.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("PRAGMA table_info(raw_market_data)")
existing_cols = [r[1] for r in c.fetchall()]

new_cols = {
    "tongue_sentiment": "FLOAT",
    "volatility": "FLOAT",
    "oi_roc": "FLOAT",
    "body_label": "TEXT",
}

added = 0
for col, dtype in new_cols.items():
    if col not in existing_cols:
        c.execute(f"ALTER TABLE raw_market_data ADD COLUMN {col} {dtype}")
        print(f"Added column: {col}")
        added += 1

conn.commit()
c.execute("PRAGMA table_info(raw_market_data)")
print(f"\nTotal columns: {len(c.fetchall())}")
conn.close()
print(f"Done: {added} columns added")
