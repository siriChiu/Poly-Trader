"""Step 2 - Check DB structure and compute IC properly"""
import json, os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

# Read the ic_signs.json from last heartbeat
with open('data/ic_signs.json') as f:
    ic_data = json.load(f)

print("=== ic_signs.json timestamp:", ic_data.get('timestamp'))
print("=== Matched records:", ic_data['n_matched'])
print("Full ICs:", json.dumps(ic_data['ics_full'], indent=2))
print("Recent ICs:", json.dumps(ic_data['ics_recent'], indent=2))
print("Stats:", json.dumps(ic_data['stats'], indent=2))
