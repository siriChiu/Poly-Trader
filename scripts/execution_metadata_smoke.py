from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from execution.metadata_smoke import run_metadata_smoke
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "execution_metadata_smoke.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only exchange metadata smoke verification")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol to inspect (default: BTCUSDT)")
    parser.add_argument(
        "--venues",
        nargs="*",
        default=["okx"],
        help="Venues to inspect (default: okx)",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config.yaml")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Where to write the JSON report")
    return parser.parse_args()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    payload = run_metadata_smoke(config, symbol=args.symbol, venues=_normalize_venues(args.venues))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok_count", 0) > 0 else 1



def _normalize_venues(values: Iterable[str]) -> list[str]:
    return [str(v).strip().lower() for v in values if str(v).strip()]


if __name__ == "__main__":
    raise SystemExit(main())
