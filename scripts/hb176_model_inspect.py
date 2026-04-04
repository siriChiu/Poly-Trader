#!/usr/bin/env python3
"""HB #176 - Model inspection"""
import pickle, os, json

for path in ['model/xgb_model.pkl', 'model/regime_models.pkl', 'model/ic_signs.json']:
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f'{path}: exists={exists}, size={size}')

# Load regime models
with open('model/regime_models.pkl', 'rb') as f:
    rm = pickle.load(f)
if isinstance(rm, dict):
    print(f'Regime models: {list(rm.keys())}')
    for k, v in rm.items():
        if isinstance(v, dict):
            print(f'  {k}: keys={list(v.keys())[:5]}')
        else:
            print(f'  {k}: type={type(v).__name__}')

# Load xgb model
with open('model/xgb_model.pkl', 'rb') as f:
    gm = pickle.load(f)
if isinstance(gm, dict):
    print(f'Global model keys: {list(gm.keys())}')
    if 'clf' in gm:
        print(f'  clf type: {type(gm["clf"]).__name__}')
        if hasattr(gm['clf'], 'max_depth'):
            print(f'  max_depth: {gm["clf"].max_depth}')
        if hasattr(gm['clf'], 'feature_names_in_'):
            print(f'  feature_names: {list(gm["clf"].feature_names_in_)[:10]}...')
else:
    print(f'Global model type: {type(gm).__name__}')

# ic_signs.json
with open('model/ic_signs.json') as f:
    ics = json.load(f)
print(f'IC signs: {json.dumps(ics, indent=2)}')
