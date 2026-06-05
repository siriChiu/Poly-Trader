#!/usr/bin/env python3
"""Verify customer-safe alternative proof consistency between API and artifact.

The probe compares `/api/execution/overview.customer_safe_alternative_proof`
with `data/customer_safe_alternative_proof.json`. It uses stable compact
projections so the API can omit bulky source artifacts while still proving the
customer-facing safe lane, aliases, counts, fail-closed flags, and secret-safe
surface mirror the PM artifact.
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


STABLE_KEYS = (
    "artifact",
    "generated_at",
    "canary_ready",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "support_rows",
    "minimum_support_rows",
    "support_gap",
    "blocking_gate",
    "primary_blocking_gate",
    "blocking_gates",
    "breaker_release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "topk_deployable_rows",
    "topk_risk_qualified_rows",
    "topk_runtime_blocked_candidate_rows",
    "topk_support_context_status",
    "topk_support_context_freshness_status",
    "topk_support_context_deployment_blocking",
    "topk_live_truth_overlay_blocker",
    "venue_runtime_ready",
    "venue_status",
    "blocked_live_lane_count",
    "alternative_solution_required",
    "alternative_solution_option_count",
    "alternative_solution_options",
    "selected_alternative_solution",
    "selected_alternative",
    "selected_next_customer_artifact",
    "selected_next_artifact",
    "next_customer_action_count",
)
SUMMARY_KEYS = (
    "canary_ready",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "support_rows",
    "minimum_support_rows",
    "support_gap",
    "blocking_gate",
    "primary_blocking_gate",
    "blocking_gates",
    "breaker_release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "topk_deployable_rows",
    "topk_risk_qualified_rows",
    "topk_runtime_blocked_candidate_rows",
    "topk_support_context_status",
    "topk_support_context_freshness_status",
    "topk_support_context_deployment_blocking",
    "topk_live_truth_overlay_blocker",
    "venue_runtime_ready",
    "venue_status",
    "blocked_live_lane_count",
    "alternative_solution_required",
    "alternative_solution_option_count",
    "alternative_solution_options",
    "selected_alternative_solution",
    "selected_alternative",
    "selected_next_customer_artifact",
    "selected_next_artifact",
    "next_customer_action_count",
)
REQUIRED_KEYS = (
    "artifact",
    "generated_at",
    "canary_ready",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "support_rows",
    "minimum_support_rows",
    "support_gap",
    "blocking_gate",
    "primary_blocking_gate",
    "breaker_release_ready",
    "topk_deployable_rows",
    "venue_runtime_ready",
    "alternative_solution_required",
    "alternative_solution_option_count",
    "alternative_solution_options",
    "selected_alternative_solution",
    "selected_alternative",
    "selected_next_customer_artifact",
    "selected_next_artifact",
    "blocked_live_lane_count",
    "next_customer_action_count",
)
ALTERNATIVE_SOLUTION_KEYS = (
    "id",
    "role",
    "next_artifact",
    "deployable",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "reference_window",
    "reference_rows",
)
NEXT_ACTION_KEYS = (
    "id",
    "surface",
    "mode",
    "expected_evidence",
    "verify_command",
    "breaker_release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "support_rows",
    "minimum_support_rows",
    "support_gap",
    "topk_deployable_rows",
    "topk_support_context_status",
    "topk_support_context_freshness_status",
    "topk_support_context_deployment_blocking",
    "topk_live_truth_overlay_blocker",
    "venue_runtime_ready",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
)
BLOCKED_LANE_KEYS = (
    "id",
    "blocking_gate",
    "blocked_actions",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "allowed_alternative",
)
RELEASE_CONDITION_KEYS = (
    "primary_blocking_gate",
    "breaker_release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "support_rows",
    "minimum_support_rows",
    "support_gap",
    "support_route_verdict",
    "topk_deployable_rows",
    "topk_support_context_status",
    "topk_support_context_freshness_status",
    "topk_support_context_deployment_blocking",
    "topk_live_truth_overlay_blocker",
    "venue_runtime_ready",
    "venue_status",
)
PORTFOLIO_KEYS = (
    "pm_challenge_answered",
    "option_count",
    "selected_option",
    "selected_next_artifact",
    "time_to_evidence_bucket",
    "missing_capability_class",
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
ALLOWED_SECRETISH_KEYS = {"secret_safe", "secrets_redacted", "credential_values_redacted"}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
        raise SystemExit("expected JSON bundle on stdin, --overview-file, or --base-url")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    overview = _mapping(
        payload.get("execution_overview")
        or payload.get("overview")
        or payload.get("api_execution_overview")
    )
    artifact = _mapping(
        payload.get("artifact")
        or payload.get("customer_safe_alternative_artifact")
        or payload.get("customer_safe_alternative_proof_artifact")
    )
    if not overview:
        raise SystemExit("stdin bundle must include execution_overview")
    return overview, artifact


def _overview_proof(overview_payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(overview_payload.get("customer_safe_alternative_proof"))


def _summary(proof: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(proof.get("summary"))


def _project(source: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: source.get(key) for key in keys if key in source}


def _rows_by_id(rows: Any, keys: Sequence[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _list(rows):
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            continue
        result[row_id] = _project(row, keys)
    return result


def _blocked_lanes_by_id(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _list(rows):
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            continue
        projected = _project(row, BLOCKED_LANE_KEYS)
        release_condition = _project(_mapping(row.get("release_condition")), RELEASE_CONDITION_KEYS)
        if release_condition:
            projected["release_condition"] = release_condition
        result[row_id] = projected
    return result


def _stable_signature(proof: Mapping[str, Any]) -> dict[str, Any]:
    signature = {key: proof.get(key) for key in STABLE_KEYS if key in proof}
    alternatives = _rows_by_id(proof.get("alternative_solutions"), ALTERNATIVE_SOLUTION_KEYS)
    if alternatives:
        signature["alternative_solutions"] = alternatives
    next_actions = _rows_by_id(proof.get("next_customer_actions"), NEXT_ACTION_KEYS)
    if next_actions:
        signature["next_customer_actions"] = next_actions
    blocked_lanes = _blocked_lanes_by_id(proof.get("blocked_live_lanes"))
    if blocked_lanes:
        signature["blocked_live_lanes"] = blocked_lanes
    portfolio = _project(_mapping(proof.get("alternative_solution_portfolio")), PORTFOLIO_KEYS)
    if portfolio:
        signature["alternative_solution_portfolio"] = portfolio
    return signature


def _compare_signatures(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    left_sig = _stable_signature(left)
    right_sig = _stable_signature(right)
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(left_sig) & set(right_sig)):
        if left_sig[key] != right_sig[key]:
            mismatches.append({"field": key, "overview": left_sig[key], "artifact": right_sig[key]})
    return mismatches


def _required_missing(proof: Mapping[str, Any]) -> list[str]:
    missing = [key for key in REQUIRED_KEYS if key not in proof]
    for key in ("summary", "alternative_solutions", "next_customer_actions", "blocked_live_lanes"):
        if key not in proof:
            missing.append(key)
    return sorted(set(missing))


def _summary_mismatches(proof: Mapping[str, Any], source_name: str) -> list[dict[str, Any]]:
    quick = _summary(proof)
    if not quick:
        return [{"source": source_name, "field": "summary", "expected": "present", "actual": None}]
    signature = _stable_signature(proof)
    mismatches: list[dict[str, Any]] = []
    for key in SUMMARY_KEYS:
        if key not in signature and key not in quick:
            continue
        expected = signature.get(key)
        actual = quick.get(key)
        if expected != actual:
            mismatches.append({"source": source_name, "field": key, "expected": expected, "actual": actual})
    return mismatches


def _alias_mismatches(proof: Mapping[str, Any], source_name: str) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    summary = _summary(proof)
    alternative_solutions = _list(proof.get("alternative_solutions"))
    expected_count = len([row for row in alternative_solutions if isinstance(row, dict)])
    count_fields = {
        "alternative_solution_option_count": proof.get("alternative_solution_option_count"),
        "alternative_solution_options": proof.get("alternative_solution_options"),
        "summary.alternative_solution_option_count": summary.get("alternative_solution_option_count"),
        "summary.alternative_solution_options": summary.get("alternative_solution_options"),
    }
    for field, actual in count_fields.items():
        if actual != expected_count:
            mismatches.append({"source": source_name, "field": field, "expected": expected_count, "actual": actual})

    alias_pairs = (
        ("selected_alternative_solution", "selected_alternative"),
        ("selected_next_customer_artifact", "selected_next_artifact"),
    )
    for left_key, right_key in alias_pairs:
        left = proof.get(left_key)
        right = proof.get(right_key)
        if left != right:
            mismatches.append({"source": source_name, "field": right_key, "expected": left, "actual": right})
        summary_left = summary.get(left_key)
        summary_right = summary.get(right_key)
        if summary_left != left:
            mismatches.append(
                {"source": source_name, "field": f"summary.{left_key}", "expected": left, "actual": summary_left}
            )
        if summary_right != right:
            mismatches.append(
                {"source": source_name, "field": f"summary.{right_key}", "expected": right, "actual": summary_right}
            )

    portfolio = _mapping(proof.get("alternative_solution_portfolio"))
    if portfolio:
        portfolio_expectations = {
            "alternative_solution_portfolio.option_count": expected_count,
            "alternative_solution_portfolio.selected_option": proof.get("selected_alternative_solution"),
            "alternative_solution_portfolio.selected_next_artifact": proof.get("selected_next_customer_artifact"),
        }
        actual_values = {
            "alternative_solution_portfolio.option_count": portfolio.get("option_count"),
            "alternative_solution_portfolio.selected_option": portfolio.get("selected_option"),
            "alternative_solution_portfolio.selected_next_artifact": portfolio.get("selected_next_artifact"),
        }
        for field, expected in portfolio_expectations.items():
            actual = actual_values.get(field)
            if actual != expected:
                mismatches.append({"source": source_name, "field": field, "expected": expected, "actual": actual})
    return mismatches


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


def _fail_closed_violation_paths(node: Any, path: tuple[str, ...] = ()) -> list[str]:
    paths: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in {
                "canary_ready",
                "live_exposure_allowed",
                "order_submission_enabled",
                "risk_on_order_enabled",
                "live_order_submitted",
                "deployable",
            } and value is True:
                paths.append(".".join((*path, key_text)))
                continue
            paths.extend(_fail_closed_violation_paths(value, (*path, key_text)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            paths.extend(_fail_closed_violation_paths(item, (*path, str(index))))
    return paths


def build_summary(
    overview_payload: Mapping[str, Any],
    artifact_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    overview_proof = _overview_proof(overview_payload)
    artifact_proof = _mapping(artifact_payload)
    mismatches = (
        _compare_signatures(overview_proof, artifact_proof)
        if overview_proof and artifact_proof
        else []
    )
    overview_missing = (
        _required_missing(overview_proof)
        if overview_proof
        else ["customer_safe_alternative_proof"]
    )
    artifact_missing = (
        _required_missing(artifact_proof)
        if artifact_proof
        else ["customer_safe_alternative_proof_artifact"]
    )
    summary_mismatches = _summary_mismatches(overview_proof, "overview") + _summary_mismatches(
        artifact_proof,
        "artifact",
    )
    alias_mismatches = _alias_mismatches(overview_proof, "overview") + _alias_mismatches(
        artifact_proof,
        "artifact",
    )
    overview_fail_closed_violations = _fail_closed_violation_paths(overview_proof)
    artifact_fail_closed_violations = _fail_closed_violation_paths(artifact_proof)
    secret_like_key_paths = [
        f"overview.{path}" for path in _secret_like_key_paths(overview_proof)
    ] + [f"artifact.{path}" for path in _secret_like_key_paths(artifact_proof)]
    api_consistent = bool(overview_proof and artifact_proof and not mismatches)
    summary_consistent = not summary_mismatches
    aliases_consistent = not alias_mismatches
    overview_fail_closed = bool(overview_proof and not overview_fail_closed_violations)
    artifact_fail_closed = bool(artifact_proof and not artifact_fail_closed_violations)
    fail_closed = overview_fail_closed and artifact_fail_closed
    secret_safe = not secret_like_key_paths
    strict_ok = bool(
        api_consistent
        and summary_consistent
        and aliases_consistent
        and fail_closed
        and secret_safe
        and not overview_missing
        and not artifact_missing
    )
    overview_sig = _stable_signature(overview_proof)
    artifact_sig = _stable_signature(artifact_proof)
    return {
        "probe": "customer_safe_alternative_api_consistency",
        "strict_ok": strict_ok,
        "api_consistent": api_consistent,
        "summary_consistent": summary_consistent,
        "aliases_consistent": aliases_consistent,
        "overview_proof_present": bool(overview_proof),
        "artifact_proof_present": bool(artifact_proof),
        "overview_missing_required_fields": overview_missing,
        "artifact_missing_required_fields": artifact_missing,
        "overview_artifact_mismatches": mismatches,
        "summary_mismatches": summary_mismatches,
        "alias_mismatches": alias_mismatches,
        "overview_fail_closed": overview_fail_closed,
        "artifact_fail_closed": artifact_fail_closed,
        "fail_closed": fail_closed,
        "overview_fail_closed_violations": overview_fail_closed_violations,
        "artifact_fail_closed_violations": artifact_fail_closed_violations,
        "secret_safe": secret_safe,
        "secret_like_key_paths": secret_like_key_paths,
        "alternative_solution_required": overview_sig.get("alternative_solution_required"),
        "alternative_solution_options": overview_sig.get("alternative_solution_options"),
        "selected_alternative": overview_sig.get("selected_alternative"),
        "selected_next_artifact": overview_sig.get("selected_next_artifact"),
        "support_rows": overview_sig.get("support_rows"),
        "support_gap": overview_sig.get("support_gap"),
        "blocking_gate": overview_sig.get("blocking_gate"),
        "topk_deployable_rows": overview_sig.get("topk_deployable_rows"),
        "venue_status": overview_sig.get("venue_status"),
        "artifact_generated_at": artifact_sig.get("generated_at"),
        "overview_generated_at": overview_sig.get("generated_at"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Fetch live /api/execution/overview from this base URL.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout for --base-url.")
    parser.add_argument("--overview-file", type=Path, help="Saved /api/execution/overview JSON.")
    parser.add_argument(
        "--artifact-file",
        type=Path,
        help="Standalone data/customer_safe_alternative_proof.json artifact.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when consistency, aliases, summary, fail-closed, or secret checks fail.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit single-line JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.base_url and args.overview_file:
        raise SystemExit("--base-url and --overview-file are mutually exclusive")
    if args.base_url:
        overview_payload = _fetch_json(f"{args.base_url.rstrip('/')}/api/execution/overview", timeout=args.timeout)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    elif args.overview_file:
        overview_payload = _load_json(args.overview_file)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    else:
        overview_payload, stdin_artifact = _load_stdin_bundle()
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else stdin_artifact

    summary = build_summary(overview_payload, artifact_payload)
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
