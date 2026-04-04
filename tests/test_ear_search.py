"""
Ear (v3) test: test the Binance-based consensus functions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from data_ingestion.ear_polymarket import (
    get_ear_feature,
    fetch_funding_history,
    fetch_lsr_history,
)

print("=== Testing Ear v3 ===\n")

funding = fetch_funding_history(symbol="BTCUSDT", limit=8)
print(f"Funding history: {len(funding) if funding else 0} items, last={funding[-1] if funding else 'N/A'}")

lsr = fetch_lsr_history(symbol="BTCUSDT", limit=8)
print(f"LSR history: {len(lsr) if lsr else 0} items, last={lsr[-1] if lsr else 'N/A'}")

print(f"\n=== Full Module Output ===")
full = get_ear_feature()
print(full)
