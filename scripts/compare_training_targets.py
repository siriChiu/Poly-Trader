#!/usr/bin/env python3
"""Compare training metrics for path-aware vs simulated pyramid targets."""

from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from database.models import init_db
from model.train import run_training

TARGETS = [
    ("label_spot_long_win", "Path-aware TP/DD"),
    ("simulated_pyramid_win", "Simulated Pyramid"),
]


def main() -> int:
    cfg = load_config()
    session = init_db(cfg["database"]["url"])
    results = []
    try:
        for target_col, label in TARGETS:
            ok = run_training(session, target_col=target_col)
            metrics_path = PROJECT_ROOT / "model" / "last_metrics.json"
            metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
            metrics.update({"target_col": target_col, "label": label, "ok": ok})
            results.append(metrics)
    finally:
        session.close()

    output_path = PROJECT_ROOT / "model" / "target_training_comparison.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
