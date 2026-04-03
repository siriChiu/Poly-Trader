# -*- coding: utf-8 -*-
"""
Backfill multi-sense historical features v3 — fixes Pulse/Aura missing data, Body numerical explosion

Root cause:
- 6480/6497 raw records have volume and funding_rate all None
- Only 17 recent WebSocket rows have volume/fr
- So Pulse and Aura are necessarily 0.5/0.0 constants for historical data
- Body: old rolling calculation caused std explosion

Fix strategy:
1. Body: clip(-10, 10) prevents explosion
2. Pulse: correct fallback to 0.5 when volume insufficient
3. Aura: correct fallback to 0.5 when funding_rate insufficient
"""
import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
import math
import numpy as np
import pandas as pd
from database.models import RawMarketData, FeaturesNormalized
from server.dependencies import get_db
from server.senses import normalize_feature

SYMBOL = "BTCUSDT"
BATCH_SIZE = 1000
MIN_WINDOW = 10

FEAT_KEYS = [
    "feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid",
    "feat_tongue_pct", "feat_body_roc", "feat_pulse",
    "feat_aura", "feat_mind",
]


def load_raw_df(session):
    rows = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == SYMBOL)
        .order_by(RawMarketData.timestamp.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame()
    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "close_price": r.close_price,
            "volume": r.volume,
            "funding_rate": r.funding_rate,
            "fear_greed_index": r.fear_greed_index,
            "stablecoin_mcap": r.stablecoin_mcap,
            "polymarket_prob": r.polymarket_prob,
        })
    return pd.DataFrame(data)


def compute_one(df):
    """Compute 8 features from a growing window [0:end]."""
    n = len(df)
    if n < MIN_WINDOW:
        return None

    close = df["close_price"].dropna().astype(float)
    returns = close.pct_change()
    fr = df["funding_rate"].dropna().astype(float)
    vol = df["volume"].dropna().astype(float)

    feat = {"timestamp": df.iloc[-1]["timestamp"]}

    # 1. Eye: fr_cumsum_48
    if len(fr) >= 48:
        feat["feat_eye_dist"] = float(fr.tail(48).sum())
    elif len(fr) >= 8:
        feat["feat_eye_dist"] = float(fr.sum())
    else:
        feat["feat_eye_dist"] = 0.0

    # 2. Ear: mom_24
    if len(close) >= 25:
        c24 = float(close.iloc[-25])
        feat["feat_ear_zscore"] = float(close.iloc[-1] / c24 - 1) if c24 > 0 else 0.0
    elif len(close) >= 13:
        c12 = float(close.iloc[-13])
        feat["feat_ear_zscore"] = float(close.iloc[-1] / c12 - 1) if c12 > 0 else 0.0
    else:
        feat["feat_ear_zscore"] = 0.0

    # 3. Nose: RSI14 normalised
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        lg = float(gain.iloc[-1])
        ll = float(loss.iloc[-1]) if not loss.empty else 1e-9
        rsi = 100.0 if ll <= 0 else 100 - 100 / (1 + lg / ll)
        feat["feat_nose_sigmoid"] = float(rsi) / 100.0
    else:
        feat["feat_nose_sigmoid"] = 0.5

    # 4. Tongue: vol_ratio
    if len(returns) >= 144:
        v24 = float(returns.iloc[-24:].std())
        v144 = float(returns.iloc[-144:].std())
        feat["feat_tongue_pct"] = v24 / (v144 + 1e-10)
    elif len(returns) >= 24:
        vs = float(returns.iloc[-12:].std())
        vl = float(returns.std())
        feat["feat_tongue_pct"] = vs / (vl + 1e-10)
    else:
        feat["feat_tongue_pct"] = 1.0

    # 5. Body: vol z-score, clip(-10, 10)
    if len(returns) >= 48:
        vol48 = float(returns.iloc[-48:].std())
        rolling_std = returns.rolling(48).std().dropna().iloc[-288:]
        if len(rolling_std) > 5 and rolling_std.std() > 0:
            val = (vol48 - rolling_std.mean()) / rolling_std.std()
        else:
            ra = returns.rolling(48).std().dropna()
            if len(ra) > 5 and ra.std() > 0:
                val = (vol48 - ra.mean()) / ra.std()
            else:
                val = 0.0
        feat["feat_body_roc"] = max(-10.0, min(10.0, val))
    else:
        feat["feat_body_roc"] = 0.0

    # 6. Pulse: volume spike
    if len(vol) >= 12:
        vw = vol.iloc[-12:].values
        mv = float(vw[:-1].mean())
        sv = float(np.std(vw[:-1])) + 1e-10
        vz = (float(vw[-1]) - mv) / sv
        feat["feat_pulse"] = 1.0 / (1.0 + math.exp(-vz / 2.0))
    elif len(vol) >= 3:
        mv = float(vol.iloc[:-1].mean())
        sv = float(vol.iloc[:-1].std()) + 1e-10
        vz = (float(vol.iloc[-1]) - mv) / sv
        feat["feat_pulse"] = 1.0 / (1.0 + math.exp(-vz / 2.0))
    else:
        feat["feat_pulse"] = 0.5

    # 7. Aura: fr absolute normalised
    if len(fr) >= 2:
        fr_abs = float(abs(fr.iloc[-1]))
        roll_len = min(96, len(fr))
        fr_max = float(fr.abs().rolling(roll_len).max().iloc[-1])
        if fr_max > 1e-10:
            feat["feat_aura"] = fr_abs / fr_max
        else:
            feat["feat_aura"] = 0.0
    else:
        feat["feat_aura"] = 0.0

    # 8. Mind: 144-period return
    if len(close) >= 145:
        feat["feat_mind"] = float(close.iloc[-1] / close.iloc[-145] - 1)
    elif len(close) >= 25:
        feat["feat_mind"] = float(close.iloc[-1] / close.iloc[-25] - 1)
    else:
        feat["feat_mind"] = 0.0

    # Safety: NaN/Inf
    for k, v in feat.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            feat[k] = 0.0

    return feat


def main():
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Backfill Senses v3  [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(sep)

    session = get_db()
    df = load_raw_df(session)
    total = len(df)
    print(f"Raw records: {total}")
    if total < MIN_WINDOW:
        print("Insufficient data, skip")
        return

    saved = 0
    updated = 0
    batch = 0

    print(f"Backfilling {total - MIN_WINDOW + 1} rows...\n")

    for end_idx in range(MIN_WINDOW, total + 1):
        window = df.iloc[:end_idx]
        ts = window.iloc[-1]["timestamp"]

        feat = compute_one(window)
        if not feat:
            continue

        existing = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.timestamp == ts)
            .first()
        )

        if existing:
            for k in FEAT_KEYS:
                setattr(existing, k, feat.get(k))
            updated += 1
        else:
            record = FeaturesNormalized(
                timestamp=ts,
                **{k: feat.get(k) for k in FEAT_KEYS}
            )
            session.add(record)
            saved += 1

        batch += 1
        if batch % BATCH_SIZE == 0:
            session.commit()
            pct = end_idx / total * 100
            print(f"  Progress: {end_idx}/{total} ({pct:.0f}%) | new={saved} upd={updated}")

    session.commit()

    final_count = session.query(FeaturesNormalized).count()
    print(f"\n{sep}")
    print(f"  Backfill complete!")
    print(f"  New={saved}, Updated={updated}, Total={final_count}")

    # Verify: latest row with sense scores
    last = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp.desc())
        .first()
    )
    if last:
        sense_map = {
            "feat_eye_dist": "Eye",
            "feat_ear_zscore": "Ear",
            "feat_nose_sigmoid": "Nose",
            "feat_tongue_pct": "Tongue",
            "feat_body_roc": "Body",
            "feat_pulse": "Pulse",
            "feat_aura": "Aura",
            "feat_mind": "Mind",
        }
        print(f"\n  Latest feature values (ts={last.timestamp}):")
        for fk, name in sense_map.items():
            v = getattr(last, fk)
            s = normalize_feature(v, fk)
            print(f"    {name}: raw={v:.6f}  score={s:.4f}")

    print(sep)


if __name__ == "__main__":
    main()
