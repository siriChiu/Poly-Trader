#!/usr/bin/env python3
"""Quick comparison of label target availability for training experiments."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from database.models import init_db
from model.train import load_training_data


def main() -> int:
    cfg = load_config()
    session = init_db(cfg["database"]["url"])
    try:
        for target in ["label_spot_long_win", "simulated_pyramid_win"]:
            loaded = load_training_data(session, target_col=target)
            if loaded is None:
                print(f"{target}: unavailable")
                continue
            X, y, y_return = loaded
            print(f"{target}: samples={len(X)}, positive_ratio={y.mean():.4f}, future_return_mean={y_return.mean():.5f}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
