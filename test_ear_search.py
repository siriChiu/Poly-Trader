import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from data_ingestion.ear_polymarket import fetch_events, extract_market_probability

for q in ["bitcoin", "crypto", "fed", "rate", "election", None]:
    events = fetch_events(query=q, limit=30)
    if events:
        probs = []
        for e in events:
            for m in e.get("markets", []):
                p = extract_market_probability(m)
                if p is not None:
                    probs.append(p)
        in_range = [p for p in probs if 0.2 <= p <= 0.8]
        print(f"query={q}: {len(events)} events, {len(probs)} probs, {len(in_range)} in 0.2-0.8")
        if probs:
            print(f"  All probs: {sorted(set(probs))[:10]}")
    else:
        print(f"query={q}: no events")
