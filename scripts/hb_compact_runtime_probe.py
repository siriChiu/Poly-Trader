#!/usr/bin/env python3
"""Compact heartbeat runtime endpoint payloads into operator-safe summaries.

These probes intentionally read JSON from stdin so heartbeat verification can use the
same script against curl output, saved artifacts, or test fixtures without starting a
second application process.  The output is concise, stable JSON that keeps blocker-first
truth visible while avoiding accidental credential disclosure.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def _first_present(*values: Any) -> Any:
    """Return the first value that is present, preserving falsey values like 0/False."""

    for value in values:
        if value is not None:
            return value
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _find_first_key(node: Any, key: str) -> Any:
    """Depth-first search for the first exact key in a nested JSON object."""

    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _find_first_key(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_key(item, key)
            if found is not None:
                return found
    return None


def _find_all_keys(node: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(node, dict):
        if key in node:
            found.append(node[key])
        for value in node.values():
            found.extend(_find_all_keys(value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_all_keys(item, key))
    return found


def _pick(mapping: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: mapping[key] for key in keys if key in mapping}


def _redact(node: Any, key_path: Sequence[str] = ()) -> Any:
    """Redact obvious secret-bearing keys in output JSON."""

    if isinstance(node, dict):
        redacted: dict[str, Any] = {}
        for key, value in node.items():
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(value, (*key_path, key))
        return redacted
    if isinstance(node, list):
        return [_redact(item, key_path) for item in node]
    return node


def _live_runtime_truth(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(payload.get("execution"))
    surface = _mapping(payload.get("execution_surface_contract"))
    return _first_present(
        _mapping(execution.get("live_runtime_truth")) or None,
        _mapping(surface.get("live_runtime_truth")) or None,
        _mapping(payload.get("live_runtime_truth")) or None,
        {},
    )


def _high_conviction(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(payload.get("execution"))
    surface = _mapping(payload.get("execution_surface_contract"))
    return _first_present(
        _mapping(payload.get("high_conviction_topk")) or None,
        _mapping(execution.get("high_conviction_topk")) or None,
        _mapping(surface.get("high_conviction_topk")) or None,
        {},
    )


def compact_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    live = _live_runtime_truth(payload)
    details = _mapping(live.get("deployment_blocker_details"))
    support_progress = _mapping(live.get("support_progress"))
    high_conviction = _high_conviction(payload)
    high_conviction_support = _mapping(high_conviction.get("support_context"))

    return _redact(
        {
            "status": payload.get("status"),
            "current_live_structure_bucket": live.get("current_live_structure_bucket"),
            "deployment_blocker": live.get("deployment_blocker"),
            "deployment_blocker_source": live.get("deployment_blocker_source"),
            "deployment_blocker_reason": live.get("deployment_blocker_reason"),
            "support_route_verdict": _first_present(
                live.get("support_route_verdict"),
                details.get("support_route_verdict"),
            ),
            "support_governance_route": _first_present(
                live.get("support_governance_route"),
                details.get("support_governance_route"),
            ),
            "support_rows": _first_present(
                live.get("current_live_structure_bucket_rows"),
                live.get("support_rows"),
                details.get("current_live_structure_bucket_rows"),
                details.get("support_rows"),
            ),
            "minimum_support_rows": _first_present(
                live.get("minimum_support_rows"),
                details.get("minimum_support_rows"),
            ),
            "gap_to_minimum": _first_present(
                live.get("current_live_structure_bucket_gap_to_minimum"),
                live.get("gap_to_minimum"),
                details.get("current_live_structure_bucket_gap_to_minimum"),
                details.get("gap_to_minimum"),
            ),
            "support_progress_status": support_progress.get("status"),
            "support_progress_reason": support_progress.get("reason"),
            "runtime_closure_state": live.get("runtime_closure_state"),
            "release_ready": live.get("release_ready"),
            "allowed_layers": live.get("allowed_layers"),
            "signal": live.get("signal"),
            "high_conviction_deployable_rows": _first_present(
                high_conviction.get("deployable_count"),
                high_conviction.get("deployable_rows"),
            ),
            "high_conviction_runtime_blocked_candidates": high_conviction.get(
                "runtime_blocked_candidate_count"
            ),
            "high_conviction_support_route": high_conviction_support.get(
                "support_route_verdict"
            ),
            "high_conviction_deployment_blocker": high_conviction_support.get(
                "deployment_blocker"
            ),
        }
    )


def _leaderboard_rows(payload: Mapping[str, Any]) -> list[Any]:
    return _list(
        _first_present(
            payload.get("leaderboard"),
            payload.get("rows"),
            payload.get("models"),
            payload.get("items"),
        )
    )


def _first_row(rows: Any) -> dict[str, Any]:
    rows_list = _list(rows)
    if rows_list and isinstance(rows_list[0], dict):
        return rows_list[0]
    return {}


def compact_leaderboard(payload: Mapping[str, Any]) -> dict[str, Any]:
    high_conviction = _high_conviction(payload)
    support = _mapping(high_conviction.get("support_context"))
    nearest = _first_row(high_conviction.get("nearest_deployable_rows"))
    if not nearest:
        nearest = _first_row(high_conviction.get("best_rows"))

    leaderboard_rows = _leaderboard_rows(payload)
    leaderboard_count = _first_present(
        payload.get("count"),
        payload.get("leaderboard_count"),
        len(leaderboard_rows) if leaderboard_rows else None,
    )

    return _redact(
        {
            "leaderboard_count": leaderboard_count,
            "payload_stale": _first_present(payload.get("stale"), payload.get("payload_stale")),
            "selected_feature_profile": payload.get("selected_feature_profile"),
            "hc_deployable_rows": _first_present(
                high_conviction.get("deployable_count"),
                high_conviction.get("deployable_rows"),
            ),
            "hc_runtime_blocked_candidates": high_conviction.get(
                "runtime_blocked_candidate_count"
            ),
            "hc_bucket_rows": _first_present(
                support.get("current_live_structure_bucket_rows"),
                support.get("support_rows"),
            ),
            "hc_minimum_support_rows": support.get("minimum_support_rows"),
            "hc_gap": _first_present(
                support.get("current_live_structure_bucket_gap_to_minimum"),
                support.get("gap_to_minimum"),
            ),
            "hc_support_route": support.get("support_route_verdict"),
            "hc_deployment_blocker": support.get("deployment_blocker"),
            "hc_release_ready": support.get("release_ready"),
            "hc_nearest_model": _first_present(nearest.get("model"), nearest.get("model_name")),
            "hc_nearest_tier": nearest.get("deployment_candidate_tier"),
            "hc_nearest_support_route": _first_present(
                nearest.get("support_route"), nearest.get("support_route_verdict")
            ),
            "hc_nearest_deployment_blocker": nearest.get("deployment_blocker"),
        }
    )


def _flatten_blockers(values: Iterable[Any]) -> list[Any]:
    blockers: list[Any] = []
    for value in values:
        if isinstance(value, list):
            blockers.extend(value)
        elif value:
            blockers.append(value)
    # Preserve order while deduplicating simple scalar blockers.
    seen: set[str] = set()
    compacted: list[Any] = []
    for blocker in blockers:
        marker = json.dumps(blocker, ensure_ascii=False, sort_keys=True) if isinstance(blocker, (dict, list)) else str(blocker)
        if marker not in seen:
            seen.add(marker)
            compacted.append(blocker)
    return compacted


def compact_execution(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution_readiness = _mapping(payload.get("execution_readiness"))
    venue_dry_run_proof = _mapping(payload.get("venue_dry_run_proof"))
    blockers = _flatten_blockers(
        [
            *_find_all_keys(payload, "venue_blockers"),
            *_find_all_keys(payload, "execution_blockers"),
            *_find_all_keys(payload, "live_ready_blockers"),
            *_find_all_keys(payload, "blockers"),
        ]
    )

    return _redact(
        {
            "order_submission_enabled": _find_first_key(
                payload, "order_submission_enabled"
            ),
            "risk_on_order_enabled": _find_first_key(payload, "risk_on_order_enabled"),
            "venue_runtime_ready": _find_first_key(payload, "venue_runtime_ready"),
            "readiness_state": _first_present(
                _find_first_key(payload, "readiness_state"),
                execution_readiness.get("status"),
                venue_dry_run_proof.get("status"),
                _find_first_key(payload, "state"),
            ),
            "paper_shadow": _find_first_key(payload, "paper_shadow"),
            "shadow_rows": _find_first_key(payload, "shadow_rows"),
            "venue_blockers": blockers,
            "venue_dry_run_status": venue_dry_run_proof.get("status"),
            "lane_count": _first_present(
                _find_first_key(payload, "lane_count"),
                len(_list(_find_first_key(payload, "venue_lanes")))
                if _find_first_key(payload, "venue_lanes") is not None
                else None,
            ),
        }
    )


def _load_stdin() -> Mapping[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected JSON payload on stdin")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("status", "leaderboard", "execution"),
        help="Endpoint payload type to compact.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON instead of pretty-printed JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _load_stdin()
    if args.mode == "status":
        summary = compact_status(payload)
    elif args.mode == "leaderboard":
        summary = compact_leaderboard(payload)
    else:
        summary = compact_execution(payload)

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
