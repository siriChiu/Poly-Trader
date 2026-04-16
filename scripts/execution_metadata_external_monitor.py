from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.routes.api import (  # noqa: E402
    _build_execution_metadata_smoke_background_state,
    run_execution_metadata_smoke_background_governance,
)

DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "execution_metadata_external_monitor.json"
DEFAULT_INTERVAL_SECONDS = 300.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process-independent execution metadata governance monitor"
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol to inspect")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config.yaml")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Where to write the JSON report")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Expected cadence for external scheduler / cron invocations",
    )
    parser.add_argument(
        "--reason",
        default="external_cron_monitor",
        help="Reason label persisted into the governance artifact",
    )
    return parser.parse_args()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    summary = run_execution_metadata_smoke_background_governance(
        config,
        args.symbol,
        reason=args.reason,
        interval_seconds=args.interval_seconds,
    ) or {}
    governance = summary.get("governance") if isinstance(summary, dict) else {}
    background_monitor = _build_execution_metadata_smoke_background_state()
    output_payload = {
        "generated_at": _utc_now(),
        "checked_at": background_monitor.get("checked_at") or _utc_now(),
        "source": "external_process",
        "status": background_monitor.get("status") or "unknown",
        "reason": background_monitor.get("reason") or args.reason,
        "freshness_status": background_monitor.get("freshness_status"),
        "governance_status": background_monitor.get("governance_status"),
        "error": background_monitor.get("error"),
        "interval_seconds": args.interval_seconds,
        "symbol": args.symbol,
        "command": f"source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol {args.symbol}",
        "metadata_smoke_freshness": summary.get("freshness"),
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output_payload, ensure_ascii=False, indent=2))
    status = str(output_payload.get("status") or "")
    return 0 if status in {"healthy", "attention_required"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
