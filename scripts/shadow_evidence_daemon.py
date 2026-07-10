#!/usr/bin/env python3
"""Run the Poly-Trader shadow evidence daemon.

Default mode loops forever.  Use --once for scheduler/cron ticks.  The daemon
forces paper/shadow dry-run mode and never submits real orders.
"""
from __future__ import annotations

import argparse
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
from execution.shadow_evidence_daemon import (
    DEFAULT_COLLECT_INTERVAL_SECONDS,
    DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS,
    DEFAULT_SHADOW_EVIDENCE_RUN_ID,
    run_shadow_evidence_cycle,
)
from utils.logger import setup_logger

logger = setup_logger(__name__, log_file="data/live_trading/shadow_evidence_daemon.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect paper/shadow evidence continuously without submitting orders")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="Path to config.yaml")
    parser.add_argument("--once", action="store_true", help="Run one collection tick and exit")
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_COLLECT_INTERVAL_SECONDS, help="Seconds between daemon ticks")
    parser.add_argument("--review-interval-hours", type=float, default=DEFAULT_OPERATOR_REVIEW_INTERVAL_HOURS, help="How often the operator should review accumulated evidence")
    parser.add_argument("--run-id", default=DEFAULT_SHADOW_EVIDENCE_RUN_ID, help="Stable live_runner run id used for audit rows/JSONL")
    parser.add_argument("--no-collect", action="store_true", help="Skip market collection before each tick")
    parser.add_argument("--no-preprocess", action="store_true", help="Skip feature preprocessing before each tick")
    parser.add_argument("--refresh-model", action="store_true", help="Refresh/retrain the live runner model artifact")
    parser.add_argument("--quiet-if-not-due", action="store_true", help="Only print when operator confirmation is due or a safety issue occurs")
    return parser.parse_args()


def _summary_for_stdout(artifact: Dict[str, Any]) -> Dict[str, Any]:
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    review = artifact.get("operator_review") if isinstance(artifact.get("operator_review"), dict) else {}
    latest = artifact.get("latest_decision") if isinstance(artifact.get("latest_decision"), dict) else {}
    guardrail = artifact.get("guardrail") if isinstance(artifact.get("guardrail"), dict) else {}
    return {
        "status": artifact.get("status"),
        "updated_at": artifact.get("updated_at"),
        "operator_message": artifact.get("operator_message"),
        "confirmation_due": review.get("confirmation_due"),
        "next_operator_review_at": review.get("next_operator_review_at"),
        "cycles_completed": summary.get("cycles_completed"),
        "total_decisions": summary.get("total_decisions"),
        "candidate_decisions": summary.get("candidate_decisions"),
        "pending_outcomes": summary.get("pending_outcomes"),
        "resolved_outcomes": summary.get("resolved_outcomes"),
        "latest_action": latest.get("action") or latest.get("cycle_action"),
        "latest_reason": latest.get("reason") or latest.get("cycle_reason"),
        "order_submission_enabled": guardrail.get("order_submission_enabled"),
        "risk_on_order_enabled": guardrail.get("risk_on_order_enabled"),
        "live_order_submitted": guardrail.get("live_order_submitted"),
        "artifact_path": artifact.get("artifact_path"),
    }


def _should_print(args: argparse.Namespace, artifact: Dict[str, Any]) -> bool:
    if not args.quiet_if_not_due:
        return True
    review = artifact.get("operator_review") if isinstance(artifact.get("operator_review"), dict) else {}
    guardrail = artifact.get("guardrail") if isinstance(artifact.get("guardrail"), dict) else {}
    return bool(review.get("confirmation_due") or guardrail.get("live_order_submitted"))


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    db_url = (config.get("database") or {}).get("url")
    if not db_url:
        raise SystemExit("database.url is required in config")
    stop_requested = False

    def _handle_stop(_signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    while not stop_requested:
        session = init_db(str(db_url))
        try:
            artifact = run_shadow_evidence_cycle(
                config=config,
                session=session,
                run_id=args.run_id,
                collect_market=not args.no_collect,
                preprocess=not args.no_preprocess,
                refresh_model=args.refresh_model,
                interval_seconds=max(1, int(args.interval_seconds)),
                review_interval_hours=max(0.1, float(args.review_interval_hours)),
            )
            logger.info("shadow evidence tick: %s", json.dumps(_summary_for_stdout(artifact), ensure_ascii=False, sort_keys=True))
            if _should_print(args, artifact):
                print(json.dumps(_summary_for_stdout(artifact), ensure_ascii=False, indent=2, sort_keys=True), flush=True)
        finally:
            session.close()
        if args.once:
            break
        sleep_until = time.monotonic() + max(1, int(args.interval_seconds))
        while not stop_requested and time.monotonic() < sleep_until:
            time.sleep(min(1.0, sleep_until - time.monotonic()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
