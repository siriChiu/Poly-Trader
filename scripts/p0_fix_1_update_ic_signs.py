#!/usr/bin/env python3
"""P0 Fix 1: Copy neg_ic_feats from model/ic_signs.json to data/ic_signs.json"""
import json
from datetime import datetime

# Load model's correct neg_ic_feats
with open('/home/kazuha/Poly-Trader/model/ic_signs.json') as f:
    model_ic = json.load(f)

# Load current data/ic_signs.json
with open('/home/kazuha/Poly-Trader/data/ic_signs.json') as f:
    data_ic = json.load(f)

# Add neg_ic_feats if missing
if 'neg_ic_feats' not in data_ic:
    data_ic['neg_ic_feats'] = model_ic['neg_ic_feats']
    print(f"Added neg_ic_feats: {len(data_ic['neg_ic_feats'])} features")

# Update TW-IC section with latest values
tw_ic = {
    'Eye': 0.1361, 'Ear': -0.0656, 'Nose': -0.0299,
    'Tongue': 0.5505, 'Body': 0.5127, 'Pulse': -0.2907,
    'Aura': -0.1733, 'Mind': -0.2040
}
data_ic['tw_ic'] = tw_ic
data_ic['timestamp'] = datetime.now().isoformat()

with open('/home/kazuha/Poly-Trader/data/ic_signs.json', 'w') as f:
    json.dump(data_ic, f, indent=2)

print(f"data/ic_signs.json updated: neg_ic_feats now has {len(data_ic['neg_ic_feats'])} features")
print(f"TW-IC: {sum(1 for v in tw_ic.values() if abs(v) >= 0.05)}/8 pass")
print(f"Timestamp: {data_ic['timestamp']}")
