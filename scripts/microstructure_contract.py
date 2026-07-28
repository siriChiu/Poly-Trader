#!/usr/bin/env python3
"""Generate the fail-closed microstructure/order-flow contract artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.microstructure import DEFAULT_ARTIFACT_PATH, write_microstructure_contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    contract = write_microstructure_contract(args.output)
    if args.format == "json":
        print(json.dumps(contract, ensure_ascii=False, indent=2))
    else:
        print(
            "microstructure_contract: "
            f"status={contract['status']} "
            f"source={contract['source']['freshness_status']} "
            f"coverage={contract['coverage']['coverage_ratio']:.3f} "
            f"forecast_edge_bps={contract['forecast_edge_bps']} "
            f"decision={contract['decision_contract']['status']} "
            f"artifact={args.output}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
