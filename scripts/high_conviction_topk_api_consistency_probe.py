#!/usr/bin/env python3
"""Verify high-conviction Top-K consistency between API and artifact.

The probe compares `/api/models/leaderboard.high_conviction_topk` with
`data/high_conviction_topk_oos_matrix.json`.  It intentionally compares stable
contract fields only: API request-time live support overlays may update
freshness timestamps and live-truth generated_at, but counts, gate state,
support rows, breaker release math, and the nearest candidate must not drift.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


COUNT_KEYS = (
    "row_count",
    "deployable_count",
    "risk_qualified_count",
    "runtime_blocked_candidate_count",
)
TOP_LEVEL_KEYS = (
    "generated_at",
    "target_col",
    "samples",
    "top_k_grid",
    *COUNT_KEYS,
)
SUPPORT_KEYS = (
    "support_route_verdict",
    "support_governance_route",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
)
NEAREST_KEYS = (
    "model",
    "feature_profile",
    "regime",
    "top_k",
    "oos_roi",
    "win_rate",
    "profit_factor",
    "max_drawdown",
    "worst_fold",
    "trade_count",
    "support_route",
    "support_governance_route",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "deployable_verdict",
    "deployment_candidate_tier",
    "gate_failures",
    "model_gate_failures",
    "live_gate_failures",
    "oos_gate_passed",
    "blocked_only_by_live_guardrails",
)
FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "api_secret",
    "secret_token",
    "client_secret",
    "password",
    "passphrase",
    "private_key",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
)
ALLOWED_SECRETISH_KEYS = {"freshness", "freshness_status", "freshness_blocker"}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object in {path}")
    return payload


def _fetch_json(url: str, *, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to fetch JSON from {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object from {url}")
    return payload


def _load_stdin_bundle() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected JSON bundle on stdin, --leaderboard-file, or --base-url")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    leaderboard = _mapping(
        payload.get("leaderboard")
        or payload.get("api_leaderboard")
        or payload.get("models_leaderboard")
    )
    artifact = _mapping(
        payload.get("artifact")
        or payload.get("high_conviction_topk_artifact")
        or payload.get("high_conviction_topk_oos_matrix")
    )
    if not leaderboard:
        raise SystemExit("stdin bundle must include leaderboard")
    return leaderboard, artifact


def _api_topk(leaderboard_payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(leaderboard_payload.get("high_conviction_topk"))


def _row_is_risk_qualified(row: Mapping[str, Any]) -> bool:
    if row.get("deployable_verdict") == "deployable":
        return True
    if row.get("deployment_candidate_tier") in {"runtime_blocked_oos_pass", "deployable"}:
        return True
    return bool(row.get("oos_gate_passed") is True and not _list(row.get("model_gate_failures")))


def _row_is_runtime_blocked_candidate(row: Mapping[str, Any]) -> bool:
    if row.get("deployment_candidate_tier") == "runtime_blocked_oos_pass":
        return True
    return bool(row.get("blocked_only_by_live_guardrails") is True)


def _artifact_count(artifact: Mapping[str, Any], key: str, rows: list[Any]) -> int:
    explicit = {
        "row_count": _first_present(artifact.get("row_count"), len(rows)),
        "deployable_count": _first_present(artifact.get("deployable_rows"), artifact.get("deployable_count")),
        "risk_qualified_count": _first_present(artifact.get("risk_qualified_rows"), artifact.get("risk_qualified_count")),
        "runtime_blocked_candidate_count": _first_present(
            artifact.get("runtime_blocked_candidate_rows"),
            artifact.get("runtime_blocked_candidate_count"),
        ),
    }.get(key)
    if explicit is not None:
        return _to_int(explicit)
    row_mappings = [row for row in rows if isinstance(row, dict)]
    if key == "deployable_count":
        return sum(1 for row in row_mappings if row.get("deployable_verdict") == "deployable")
    if key == "risk_qualified_count":
        return sum(1 for row in row_mappings if _row_is_risk_qualified(row))
    if key == "runtime_blocked_candidate_count":
        return sum(1 for row in row_mappings if _row_is_runtime_blocked_candidate(row))
    return len(row_mappings)


def _support_context(source: Mapping[str, Any]) -> dict[str, Any]:
    support = _mapping(source.get("support_context"))
    return support if support else dict(source)


def _nearest_candidate(source: Mapping[str, Any]) -> dict[str, Any]:
    for candidate in (
        source.get("nearest_deployable_candidate"),
        _list(source.get("nearest_deployable_rows"))[0] if _list(source.get("nearest_deployable_rows")) else None,
        _list(source.get("best_rows"))[0] if _list(source.get("best_rows")) else None,
        _list(source.get("rows"))[0] if _list(source.get("rows")) else None,
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _signature(source: Mapping[str, Any], *, source_type: str) -> dict[str, Any]:
    rows = _list(source.get("rows"))
    support = _support_context(source)
    nearest = _nearest_candidate(source)
    signature: dict[str, Any] = {}
    for key in TOP_LEVEL_KEYS:
        if key in COUNT_KEYS:
            if source_type == "artifact":
                signature[key] = _artifact_count(source, key, rows)
            else:
                signature[key] = _to_int(
                    _first_present(
                        source.get(key),
                        source.get(key.replace("_count", "_rows")),
                    )
                )
        elif key in source:
            signature[key] = source.get(key)
    for key in SUPPORT_KEYS:
        value = _first_present(source.get(key), support.get(key))
        if value is not None:
            signature[f"support.{key}"] = value
    for key in NEAREST_KEYS:
        value = nearest.get(key)
        if key == "model" and value is None:
            value = nearest.get("model_name")
        if value is not None:
            signature[f"nearest.{key}"] = value
    return signature


def _compare_signatures(api_topk: Mapping[str, Any], artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    api_sig = _signature(api_topk, source_type="api")
    artifact_sig = _signature(artifact, source_type="artifact")
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(api_sig) & set(artifact_sig)):
        if api_sig[key] != artifact_sig[key]:
            mismatches.append({"field": key, "api": api_sig[key], "artifact": artifact_sig[key]})
    return mismatches


def _required_missing(source: Mapping[str, Any], *, source_type: str) -> list[str]:
    signature = _signature(source, source_type=source_type)
    required = {
        "generated_at",
        "target_col",
        "samples",
        "row_count",
        "deployable_count",
        "risk_qualified_count",
        "runtime_blocked_candidate_count",
        "support.support_route_verdict",
        "support.deployment_blocker",
        "support.current_live_structure_bucket",
        "support.current_live_structure_bucket_rows",
        "support.minimum_support_rows",
        "support.current_live_structure_bucket_gap_to_minimum",
        "support.release_ready",
        "nearest.model",
        "nearest.top_k",
        "nearest.deployable_verdict",
        "nearest.deployment_candidate_tier",
    }
    return sorted(key for key in required if key not in signature)


def _artifact_internal_mismatches(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _list(artifact.get("rows"))
    if not rows:
        return [{"field": "rows", "expected": "present", "actual": None}]
    expected = {
        "row_count": len([row for row in rows if isinstance(row, dict)]),
        "deployable_rows": _artifact_count({}, "deployable_count", rows),
        "risk_qualified_rows": _artifact_count({}, "risk_qualified_count", rows),
        "runtime_blocked_candidate_rows": _artifact_count({}, "runtime_blocked_candidate_count", rows),
    }
    actual = {
        "row_count": _to_int(_first_present(artifact.get("row_count"), len(rows))),
        "deployable_rows": _to_int(_first_present(artifact.get("deployable_rows"), artifact.get("deployable_count"))),
        "risk_qualified_rows": _to_int(_first_present(artifact.get("risk_qualified_rows"), artifact.get("risk_qualified_count"))),
        "runtime_blocked_candidate_rows": _to_int(
            _first_present(
                artifact.get("runtime_blocked_candidate_rows"),
                artifact.get("runtime_blocked_candidate_count"),
            )
        ),
    }
    return [
        {"field": key, "expected": expected[key], "actual": actual[key]}
        for key in sorted(expected)
        if expected[key] != actual[key]
    ]


def _blocked_by_live_gate(source: Mapping[str, Any], *, source_type: str) -> bool:
    signature = _signature(source, source_type=source_type)
    support_route_deployable = signature.get("support.support_route_deployable")
    deployment_blocker = signature.get("support.deployment_blocker")
    release_ready = signature.get("support.release_ready")
    rows = _to_int(signature.get("support.current_live_structure_bucket_rows"))
    minimum = _to_int(signature.get("support.minimum_support_rows"))
    gap = _to_int(signature.get("support.current_live_structure_bucket_gap_to_minimum"))
    return bool(
        support_route_deployable is False
        or deployment_blocker
        or release_ready is False
        or (minimum > 0 and rows < minimum)
        or gap > 0
    )


def _fail_closed_under_blockers(source: Mapping[str, Any], *, source_type: str) -> bool:
    if not source:
        return False
    blocked = _blocked_by_live_gate(source, source_type=source_type)
    if not blocked:
        return True
    signature = _signature(source, source_type=source_type)
    if source.get("deployment_ready") is True:
        return False
    if _to_int(signature.get("deployable_count")) > 0:
        return False
    nearest = _nearest_candidate(source)
    if nearest.get("deployable_verdict") == "deployable":
        return False
    for row in _list(source.get("best_rows")) + _list(source.get("nearest_deployable_rows")) + _list(source.get("rows")):
        if isinstance(row, dict) and row.get("deployable_verdict") == "deployable":
            return False
    return True


def _secret_like_key_paths(node: Any, path: tuple[str, ...] = ()) -> list[str]:
    paths: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            lowered = key_text.lower().replace("-", "_")
            if lowered not in ALLOWED_SECRETISH_KEYS and any(
                fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS
            ):
                paths.append(".".join((*path, key_text)))
                continue
            paths.extend(_secret_like_key_paths(value, (*path, key_text)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            paths.extend(_secret_like_key_paths(item, (*path, str(index))))
    return paths


def build_summary(
    leaderboard_payload: Mapping[str, Any],
    artifact_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    api_topk = _api_topk(leaderboard_payload)
    artifact = _mapping(artifact_payload)
    mismatches = _compare_signatures(api_topk, artifact) if api_topk and artifact else []
    api_missing = _required_missing(api_topk, source_type="api") if api_topk else ["high_conviction_topk"]
    artifact_missing = _required_missing(artifact, source_type="artifact") if artifact else ["high_conviction_topk_oos_matrix"]
    artifact_internal_mismatches = _artifact_internal_mismatches(artifact) if artifact else []
    api_fail_closed = _fail_closed_under_blockers(api_topk, source_type="api")
    artifact_fail_closed = _fail_closed_under_blockers(artifact, source_type="artifact")
    secret_like_key_paths = [
        f"api.{path}" for path in _secret_like_key_paths(api_topk)
    ] + [f"artifact.{path}" for path in _secret_like_key_paths(artifact)]
    api_sig = _signature(api_topk, source_type="api")
    artifact_sig = _signature(artifact, source_type="artifact")
    api_consistent = bool(api_topk and artifact and not mismatches)
    artifact_internal_consistent = not artifact_internal_mismatches
    fail_closed = api_fail_closed and artifact_fail_closed
    secret_safe = not secret_like_key_paths
    strict_ok = bool(
        api_consistent
        and artifact_internal_consistent
        and fail_closed
        and secret_safe
        and not api_missing
        and not artifact_missing
    )
    return {
        "probe": "high_conviction_topk_api_consistency",
        "strict_ok": strict_ok,
        "api_consistent": api_consistent,
        "api_topk_present": bool(api_topk),
        "artifact_present": bool(artifact),
        "api_missing_required_fields": api_missing,
        "artifact_missing_required_fields": artifact_missing,
        "api_artifact_mismatches": mismatches,
        "artifact_internal_consistent": artifact_internal_consistent,
        "artifact_internal_mismatches": artifact_internal_mismatches,
        "api_fail_closed_under_blockers": api_fail_closed,
        "artifact_fail_closed_under_blockers": artifact_fail_closed,
        "fail_closed_under_blockers": fail_closed,
        "secret_safe": secret_safe,
        "secret_like_key_paths": secret_like_key_paths,
        "generated_at": api_sig.get("generated_at"),
        "artifact_generated_at": artifact_sig.get("generated_at"),
        "row_count": api_sig.get("row_count"),
        "deployable_count": api_sig.get("deployable_count"),
        "risk_qualified_count": api_sig.get("risk_qualified_count"),
        "runtime_blocked_candidate_count": api_sig.get("runtime_blocked_candidate_count"),
        "support_route_verdict": api_sig.get("support.support_route_verdict"),
        "deployment_blocker": api_sig.get("support.deployment_blocker"),
        "current_live_structure_bucket_rows": api_sig.get("support.current_live_structure_bucket_rows"),
        "minimum_support_rows": api_sig.get("support.minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": api_sig.get("support.current_live_structure_bucket_gap_to_minimum"),
        "release_ready": api_sig.get("support.release_ready"),
        "nearest_model": api_sig.get("nearest.model"),
        "nearest_top_k": api_sig.get("nearest.top_k"),
        "nearest_deployable_verdict": api_sig.get("nearest.deployable_verdict"),
        "nearest_deployment_candidate_tier": api_sig.get("nearest.deployment_candidate_tier"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Fetch live /api/models/leaderboard from this base URL.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout for --base-url.")
    parser.add_argument("--leaderboard-file", type=Path, help="Saved /api/models/leaderboard JSON.")
    parser.add_argument(
        "--artifact-file",
        type=Path,
        help="Standalone data/high_conviction_topk_oos_matrix.json artifact.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when API/artifact, internal counts, fail-closed, or secret checks fail.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit single-line JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.base_url and args.leaderboard_file:
        raise SystemExit("--base-url and --leaderboard-file are mutually exclusive")
    if args.base_url:
        leaderboard_payload = _fetch_json(f"{args.base_url.rstrip('/')}/api/models/leaderboard", timeout=args.timeout)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    elif args.leaderboard_file:
        leaderboard_payload = _load_json(args.leaderboard_file)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    else:
        leaderboard_payload, stdin_artifact = _load_stdin_bundle()
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else stdin_artifact

    summary = build_summary(leaderboard_payload, artifact_payload)
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
        )
    )
    return 1 if args.strict and not summary["strict_ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
