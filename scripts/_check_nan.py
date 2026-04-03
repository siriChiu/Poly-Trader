#!/usr/bin/env python
"""Quick check of ic_signs.json for NaN values."""
import json, math

with open('/home/kazuha/Poly-Trader/model/ic_signs.json') as f:
    content = f.read()

content_clean = content.replace('NaN', 'null')
data = json.loads(content_clean)

nan_count = sum(1 for v in data['ic_map'].values() if v is None)
print(f'Total fields in ic_map: {len(data["ic_map"])}')
print(f'NaN fields: {nan_count}')
print('\nNaN keys:')
nan_keys = [k for k,v in data['ic_map'].items() if v is None]
for k in nan_keys:
    print(f'  {k}')
