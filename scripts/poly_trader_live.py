#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from database.models import init_db
from execution.live_runner import LiveTradingRunner, runner_interval_seconds
from utils.logger import setup_logger

logger = setup_logger(__name__, log_file="data/live_trading/poly_trader_live_cli.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone Poly-Trader live strategy runner")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="Path to config.yaml")
    parser.add_argument("--once", action="store_true", help="Run exactly one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Force paper execution even if config enables live trading")
    parser.add_argument("--refresh-model", action="store_true", help="Retrain and overwrite the frozen live model artifact")
    parser.add_argument("--no-collect", action="store_true", help="Skip market collection before the cycle")
    parser.add_argument("--no-preprocess", action="store_true", help="Skip feature preprocessing before the cycle")
    parser.add_argument("--no-submit", action="store_true", help="Do not submit orders; persist decisions only")
    parser.add_argument("--shadow-candidate", action="store_true", help="Force no-submit paper/shadow candidates for 24h evidence even when live entry gates are closed")
    parser.add_argument("--interval-seconds", type=int, default=None, help="Override live_runner.interval_seconds")
    parser.add_argument("--run-id", default=None, help="Stable run id for audit rows/logs")
    return parser.parse_args()


def _apply_runtime_overrides(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    cfg = copy.deepcopy(config or {})
    cfg.setdefault("live_runner", {})
    cfg.setdefault("trading", {})
    cfg.setdefault("execution", {})
    if args.interval_seconds is not None:
        cfg["live_runner"]["interval_seconds"] = max(1, int(args.interval_seconds))
    if args.dry_run:
        cfg["trading"]["dry_run"] = True
        cfg["execution"]["mode"] = "paper"
        cfg["execution"]["enable_live_trading"] = False
    if args.shadow_candidate:
        cfg["live_runner"]["shadow_candidate_enabled"] = True
        cfg["live_runner"]["shadow_evidence_mode"] = True
        cfg["trading"]["dry_run"] = True
        cfg["execution"]["mode"] = "paper"
        cfg["execution"]["enable_live_trading"] = False
    return cfg


def _decision_summary(decision: Dict[str, Any]) -> str:
    visible = {
        "run_id": decision.get("run_id"),
        "feature_timestamp": decision.get("feature_timestamp"),
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "order_submitted": bool(decision.get("order_submitted")),
        "dry_run": decision.get("dry_run"),
        "order_id": decision.get("order_id"),
        "model_confidence": decision.get("model_confidence"),
        "entry_quality": decision.get("entry_quality"),
    }
    return json.dumps(visible, ensure_ascii=False, sort_keys=True, default=str)


def main() -> int:
    args = parse_args()
    config = _apply_runtime_overrides(load_config(args.config), args)
    db_url = (config.get("database") or {}).get("url")
    if not db_url:
        raise SystemExit("database.url is required in config")

    session = init_db(str(db_url))
    runner = LiveTradingRunner(config, session, run_id=args.run_id)
    stop_requested = False

    def _handle_stop(_signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    try:
        runner.start_run(refresh_model=args.refresh_model)
        interval = runner_interval_seconds(config)
        while not stop_requested:
            decision = runner.run_cycle(
                collect_market=not args.no_collect,
                preprocess=not args.no_preprocess,
                submit_orders=not args.no_submit and not args.shadow_candidate,
            )
            summary = _decision_summary(decision)
            logger.info("live runner cycle: %s", summary)
            print(summary, flush=True)
            if args.once:
                break
            sleep_until = time.monotonic() + interval
            while not stop_requested and time.monotonic() < sleep_until:
                time.sleep(min(1.0, sleep_until - time.monotonic()))
        runner.stop_run("stopped")
        return 0
    except Exception:
        logger.exception("live runner failed")
        try:
            runner.stop_run("failed")
        finally:
            raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
