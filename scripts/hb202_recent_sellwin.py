"""Check recent sell_win trends by time segments."""
import sqlite3

conn = sqlite3.connect("poly_trader.db")
cur = conn.cursor()

# Last 100 by timestamp
cur.execute("SELECT timestamp, label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 100")
rows = cur.fetchall()
total = sum(1 for r in rows if r[1] == 1)
print(f"Last 100 by timestamp sell_win: {total/100:.3f} ({total}/100)")

# Newest rows
cur.execute("SELECT timestamp, label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY timestamp DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]}: sell_win={r[1]}")

# Labels since 2026-04-04
cur.execute("SELECT COUNT(*), AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL AND timestamp >= '2026-04-04'")
r = cur.fetchone()
if r and r[0]:
    print(f"Labels since 2026-04-04: {r[0]}, avg sell_win: {r[1]:.3f}")
else:
    print("No labels since 2026-04-04")

# Labels since 2026-04-03
cur.execute("SELECT COUNT(*), AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL AND timestamp >= '2026-04-03'")
r = cur.fetchone()
if r and r[0]:
    print(f"Labels since 2026-04-03: {r[0]}, avg sell_win: {r[1]:.3f}")

# Check the label timestamp range growth
cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM labels WHERE label_sell_win IS NOT NULL")
r = cur.fetchone()
print(f"Label timestamp range: {r[0]} to {r[1]}")

# How many labels per date in the recent days
cur.execute("""
    SELECT SUBSTR(timestamp, 1, 10) as date, COUNT(*), AVG(CAST(label_sell_win AS FLOAT))
    FROM labels WHERE label_sell_win IS NOT NULL
    AND timestamp >= '2026-04-01'
    GROUP BY date ORDER BY date
""")
for r in cur.fetchall():
    print(f"  {r[0]}: count={r[1]}, sell_win={r[2]:.3f}")

conn.close()
