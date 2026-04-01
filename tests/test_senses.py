"""
逐個測試多感官模組
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

print("=== Testing each sense module ===\n")

print("1. Eye (Binance)...")
try:
    from data_ingestion.eye_binance import get_eye_feature
    r = get_eye_feature()
    print(f"   Result: {r}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n2. Ear (Polymarket)...")
try:
    from data_ingestion.ear_polymarket import get_ear_feature
    r = get_ear_feature()
    print(f"   Result: {r}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n3. Nose (Binance Futures)...")
try:
    from data_ingestion.nose_futures import get_nose_feature
    r = get_nose_feature()
    print(f"   Result: {r}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n4. Tongue (Fear & Greed)...")
try:
    from data_ingestion.tongue_sentiment import get_tongue_feature
    r = get_tongue_feature()
    print(f"   Result: {r}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n5. Body (DefiLlama)...")
try:
    from data_ingestion.body_defillama import get_body_feature
    r = get_body_feature()
    print(f"   Result: {r}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n=== Done ===")
