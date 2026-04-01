import sqlite3
db = "C:/Users/Kazuha/repo/poly-trader/poly_trader.db"
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("PRAGMA table_info(raw_market_data)")
existing = [r[1] for r in c.fetchall()]
print("Current columns:", existing)
# Check which columns are missing
needed = ["tongue_sentiment", "volatility", "oi_roc", "body_label"]
for col in needed:
    if col not in existing:
        sql = "ALTER TABLE raw_market_data ADD COLUMN " + col + " FLOAT"
        c.execute(sql)
        print("Added:", col)
    else:
        print("Has:", col)
c.execute("PRAGMA table_info(raw_market_data)")
final = [r[1] for r in c.fetchall()]
print("Final columns:", final)
# Check feat count too
c.execute("SELECT COUNT(*) FROM raw_market_data")
raw = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM features_normalized")
feat = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM labels")
labels = c.fetchone()[0]
print("Raw:", raw, "Features:", feat, "Labels:", labels)
conn.commit()
conn.close()
print("DB fix complete!")
