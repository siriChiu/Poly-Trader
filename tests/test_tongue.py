import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

"""
Test Tongue v3 (FNG + Volatility + Funding rate)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from data_ingestion.tongue_sentiment import (
    get_tongue_feature,
    fetch_fng,
    fetch_recent_volatility,
    fetch_funding_rate,
    compute_tongue_score,
)

print("=== Testing Tongue v3 ===\n")

fng = fetch_fng()
print(f"FNG: {fng}")

vol = fetch_recent_volatility()
print(f"Volatility: {vol}")

fr = fetch_funding_rate()
print(f"Funding Rate: {fr}")

result = compute_tongue_score(fng, vol, fr)
print(f"\nSentiment Score: {result}")

print(f"\n=== Full Module Output ===")
full = get_tongue_feature()
print(full)
