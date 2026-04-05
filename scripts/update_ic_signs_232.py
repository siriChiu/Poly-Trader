#!/usr/bin/env python3
"""Update ic_signs.json with new TW-IC values and add neg_ic_feats."""
import json
import os

# Current TW-IC values from heartbeat_comprehensive.py
tw_ic = {
    'Eye': 0.1361, 
    'Ear': -0.0656, 
    'Nose': -0.0299, 
    'Tongue': 0.5505, 
    'Body': 0.5127, 
    'Pulse': -0.2907, 
    'Aura': -0.1733, 
    'Mind': -0.2040
}

# Full IC from calc_ic_stdlib.py (latest run)
full_ic = {
    'Eye': 0.0412, 'Ear': -0.0512, 'Nose': -0.0455, 'Tongue': 0.0445,
    'Body': 0.0502, 'Pulse': -0.0069, 'Aura': -0.0374, 'Mind': -0.0242
}

# Stats from calc_ic_stdlib.py (recent 5000)
stats = {
    'Eye': {'ic': 0.0570, 'n': 4829, 'std': 0.8281, 'unique': 4818, 'range': [-8.867, 10.4963], 'status': 'ok'},
    'Ear': {'ic': -0.0348, 'n': 4829, 'std': 0.0246, 'unique': 4815, 'range': [-0.1402, 0.1219], 'status': 'warning'},
    'Nose': {'ic': -0.0405, 'n': 4829, 'std': 0.1716, 'unique': 4814, 'range': [0.0002, 0.9761], 'status': 'warning'},
    'Tongue': {'ic': 0.0522, 'n': 4829, 'std': 0.4093, 'unique': 4829, 'range': [-0.0008, 2.2929], 'status': 'ok'},
    'Body': {'ic': 0.1113, 'n': 4829, 'std': 0.5248, 'unique': 4426, 'range': [-2.8132, 1.0], 'status': 'ok'},
    'Pulse': {'ic': -0.0324, 'n': 4829, 'std': 0.2525, 'unique': 4828, 'range': [0.0, 1.0], 'status': 'warning'},
    'Aura': {'ic': -0.0449, 'n': 4829, 'std': 0.0316, 'unique': 4825, 'range': [-0.1772, 0.0957], 'status': 'warning'},
    'Mind': {'ic': -0.0296, 'n': 4829, 'std': 0.0536, 'unique': 4825, 'range': [-0.2534, 0.121], 'status': 'warning'},
}

# neg_ic_feats: features with negative IC that need to be flipped
# Based on TW-IC: Ear(-0.066), Pulse(-0.291), Aura(-0.173), Mind(-0.204)
neg_ic_feats = ['feat_ear', 'feat_pulse', 'feat_aura', 'feat_mind']

from datetime import datetime
result = {
    'timestamp': datetime.now().isoformat(),
    'n_records': 9093,
    'n_matched': 8929,
    'ics_full': full_ic,
    'ics_recent': {k: tw_ic[k] for k in tw_ic},  # Use TW-IC as recent
    'stats': stats,
    'tw_ic': tw_ic,
    'neg_ic_feats': neg_ic_feats,
}

with open('/home/kazuha/Poly-Trader/data/ic_signs.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f"Updated ic_signs.json with TW-IC values")
print(f"  TW-IC pass: {sum(1 for v in tw_ic.values() if abs(v) >= 0.05)}/8")
print(f"  neg_ic_feats: {neg_ic_feats}")
print(f"  Full IC: {full_ic}")
print(f"  Timestamp: {result['timestamp']}")
