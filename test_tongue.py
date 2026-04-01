import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from data_ingestion.tongue_sentiment import get_tongue_feature, fetch_ratio, LSR_URL, TAKER_URL, TOP_TRADER_URL, fetch_fng
from data_ingestion.tongue_sentiment import compute_sentiment_score

print("=== Testing Tongue v2 ===\n")

lsr = fetch_ratio(LSR_URL)
print(f"LSR: {len(lsr) if lsr else 0} items, last={lsr[-1] if lsr else 'N/A'}")

taker = fetch_ratio(TAKER_URL)
print(f"Taker: {len(taker) if taker else 0} items, last={taker[-1] if taker else 'N/A'}")

top = fetch_ratio(TOP_TRADER_URL)
print(f"Top Trader: {len(top) if top else 0} items, last={top[-1] if top else 'N/A'}")

fng = fetch_fng()
print(f"FNG: {fng}")

result = compute_sentiment_score(lsr, taker, top, fng)
print(f"\nSentiment Score: {result}")

print(f"\n=== Full Module Output ===")
full = get_tongue_feature()
print(full)
