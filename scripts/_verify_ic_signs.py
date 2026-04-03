#!/usr/bin/env python
"""Verify ic_signs.json is valid JSON and count NaN fields."""
import json

with open('/home/kazuha/Poly-Trader/model/ic_signs.json') as f:
    data = json.load(f)

nan_count = sum(1 for v in data['ic_map'].values() if v is None)
print(f'Valid JSON: True')
print(f'NaN fields: {nan_count}')
print(f'Total fields: {len(data["ic_map"])}')
print(f'Non-zero IC fields: {sum(1 for v in data["ic_map"].values() if v is not None and abs(v) > 0.001)}')
