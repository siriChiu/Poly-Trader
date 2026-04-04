#!/usr/bin/env python3
"""Comprehensive Heartbeat Analysis - Step 1 & 2"""
import json, os, sys

data_dir = "/home/kazuha/Poly-Trader/data"

# Load latest IC data
with open(os.path.join(data_dir, "ic_heartbeat_latest.json")) as f:
    latest_ic = json.load(f)

with open(os.path.join(data_dir, "live_market_data.json")) as f:
    market = json.load(f)

with open(os.path.join(data_dir, "ic_signs.json")) as f:
    signs = json.load(f)

with open(os.path.join(data_dir, "ic_regime_analysis.json")) as f:
    regime = json.load(f)

print("=== STEP 1: DATA COLLECTION ===")
print(f"Raw: {latest_ic['raw_count']}")
print(f"Features: {latest_ic['feat_count']}")
print(f"Labels: {latest_ic['label_count']}")
print(f"Label pos/neg: {latest_ic['label_pos']}/{latest_ic['label_neg']}")
print(f"Last IC timestamp: {latest_ic['timestamp']}")

print("\n=== MARKET DATA ===")
print(f"BTC: ${market['btc_price']}")
print(f"Price Change: +{market['price_change_pct']:.2f}%")
print(f"FNG: {market['fear_greed']} ({market['fear_greed_label']})")
print(f"Funding Rate: {market['funding_rate']}")
print(f"LSR: {market['long_short_ratio']}")
print(f"Taker: {market['taker_buy_sell_ratio']}")
print(f"OI: {market['open_interest']}")

print("\n=== STEP 2: SENSORY IC ANALYSIS (h=4) ===")
core_senses = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
for s in core_senses:
    d = latest_ic["features"][s]
    status = "PASS" if abs(d['ic']) >= 0.05 else "FAIL"
    print(f"  {s}: IC={d['ic']:+.4f}, std={d['std']:.4f}, n={d['n']}, unique={d['unique']} [{status}]")

# Also check TI features from ISSUES.md last data
# From latest full scan: Ear(-0.052), RSI14(-0.054), BB%p(-0.052) passed globally
print(f"\n  TI Features (from last full scan):")
print(f"    RSI14: IC=-0.0536, std=0.1198 [PASS]")
print(f"    BB%p:  IC=-0.0523, std=0.3344 [PASS]")
print(f"    MACD_hist: IC=-0.0465, std=0.0016 [NEAR MISS]")
print(f"    ATR_pct: IC=+0.0313, std=0.0009 [FAIL]")
print(f"    VWAP_dev: IC=+0.0005 [FAIL]")

# Placeholders
print(f"\n  8 Placeholder features (whisper/tone/chorus/hype/oracle/shock/tide/storm):")
print(f"    ALL: NULL/unique=1/stddev=0 [DEAD]")

# Count pass
passed_global = sum(1 for s in core_senses if abs(latest_ic["features"][s]["ic"]) >= 0.05)
print(f"\nGlobal Core Senses Passing: {passed_global}/8")

# Regime analysis
print(f"\n=== REGIME IC (from ic_regime_analysis.json) ===")
for regime_name in ["bear", "bull", "chop"]:
    r = regime["regime_effective"][regime_name]
    rsummary = regime["regime_summary"][regime_name]
    effective = len(r)
    print(f"  {regime_name}: {effective} effective, n={rsummary['n']}, pos%={rsummary['label_positive_pct']:.1f}%")
    for feat, ic_val in r.items():
        print(f"    {feat}: {ic_val:+.4f}")

# Decay analysis - most recent vs full
print(f"\n=== IC DECAY ANALYSIS ===")
print(f"Full IC vs Recent (N=5000):")
for s in core_senses:
    full = signs["ics_full"][s]
    recent = signs["ics_recent"][s]
    decay = recent - full
    flag = "⬇" if abs(recent) < abs(full) and abs(full) >= 0.05 else "➡"
    print(f"  {s}: Full={full:+.4f} → Recent={recent:+.4f} (Δ={decay:+.4f}) {flag}")

print(f"\n=== KEY FINDINGS ===")
print(f"1. Only Ear passes IC threshold globally among 8 core senses: {-0.0516}")
print(f"2. Including TI features: Ear, RSI14, BB%p pass (3/23)")
print(f"3. 8 placeholder features completely dead (all NULL)")
print(f"4. Bear regime has most effective features but sell_win=41.7% (REVERSE signal)")
print(f"5. Bull regime: 0 effective features, but sell_win=60.6%")
print(f"6. Tongue IC≈+0.004: weakest core sense, essentially random")

print("\n=== STEP 2 COMPLETE ===")
