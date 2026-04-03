#!/usr/bin/env python3
"""Compare IC values: current heartbeat vs last recorded valid values from ISSUES.md"""
import json

# Current heartbeat #104 IC results (N=5000 recent data)
current_ic = {
    'Eye': +0.0224,
    'Ear': -0.0348,
    'Nose': -0.0464,
    'Tongue': -0.0161,
    'Body': -0.0103,
    'Pulse': -0.0023,
    'Aura': -0.0240,
    'Mind': -0.0255,
}

# Last valid IC from heartbeat #H101 (N=5000) as recorded in ISSUES.md
last_valid_ic = {
    'Eye': -0.0533,
    'Ear': -0.0733,
    'Nose': -0.0734,
    'Tongue': +0.0570,
    'Body': +0.0720,
    'Pulse': +0.1087,
    'Aura': +0.1067,
    'Mind': -0.1457,
}

print("=== IC Comparison: #H101 vs #104 (N=5000) ===\n")
print(f"{'Sense':<10} {'#H101':>10} {'#104':>10} {'|Abs H101|':>12} {'|Abs #104|':>12} {'Status':<20}")
print("-" * 76)

for sense in current_ic:
    h101 = last_valid_ic[sense]
    h104 = current_ic[sense]
    abs_h101 = abs(h101)
    abs_h104 = abs(h104)
    
    if abs_h104 >= 0.05:
        status = "✅ PASS"
    elif abs_h101 >= 0.05:
        status = "🔴 COLLAPSED (was valid)"
    else:
        status = "❌ FAIL (was also invalid)"
    
    delta = abs_h104 - abs_h101
    delta_str = f"({delta:+.4f})"
    
    print(f"{sense:<10} {h101:+10.4f} {h104:+10.4f} {abs_h101:12.4f} {abs_h104:12.4f} {status:<20} {delta_str}")

# Count valid/invalid
h101_valid = sum(1 for v in last_valid_ic.values() if abs(v) >= 0.05)
h104_valid = sum(1 for v in current_ic.values() if abs(v) >= 0.05)

print(f"\n#H101: {h101_valid}/8 senses valid (|IC| ≥ 0.05)")
print(f"#104: {h104_valid}/8 senses valid (|IC| ≥ 0.05)")
print(f"\nΔ: {h104_valid - h101_valid:+d} senses crossed threshold")

# Check if ic_signs.json was updated
try:
    with open('/home/kazuha/Poly-Trader/data/ic_signs.json', 'r') as f:
        data = json.load(f)
    print(f"\nic_signs.json last updated: {data.get('timestamp', 'unknown')}")
    print(f"N records: {data.get('n_records', 'unknown')}")
except Exception as e:
    print(f"\nCould not read ic_signs.json: {e}")
