#!/usr/bin/env python3
"""Extract compact heartbeat runtime facts for cron reports.

This script is intentionally conservative: it emits only scalar/current-state facts
needed by heartbeat summaries and avoids dumping heavyweight artifact rows.  The
heartbeat runner writes both numbered summaries (``heartbeat_<N>_summary.json``)
and alias summaries (for example ``heartbeat_fast_summary.json``); prefer the
newest summary by artifact timestamp so cron reports do not accidentally read an
older alias after a numbered run.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        return {"_missing": rel}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic helper
        return {"_error": f"{rel}: {exc}"}
    return payload if isinstance(payload, dict) else {"_error": f"{rel}: expected JSON object"}


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_latest_summary() -> tuple[str | None, dict[str, Any]]:
    candidates: list[tuple[datetime, str, dict[str, Any]]] = []
    for path in DATA_DIR.glob("heartbeat_*_summary.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        ts = _parse_timestamp(payload.get("timestamp") or payload.get("generated_at"))
        if ts is None:
            ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        candidates.append((ts, str(path.relative_to(ROOT)), payload))
    if not candidates:
        return None, {}
    candidates.sort(key=lambda item: item[0])
    _, rel_path, payload = candidates[-1]
    return rel_path, payload


def pick(mapping: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: mapping.get(key) for key in keys}


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def row_count(value: Any) -> int | None:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    return None


def compact_topk(summary_topk: dict[str, Any], artifact_topk: dict[str, Any]) -> dict[str, Any]:
    rows = first_present(summary_topk.get("rows"), artifact_topk.get("row_count"), artifact_topk.get("rows"))
    nearest = summary_topk.get("nearest_deployable_candidate") or artifact_topk.get("nearest_deployable_candidate") or {}
    if not isinstance(nearest, dict):
        nearest = {}
    return {
        "generated_at": first_present(summary_topk.get("generated_at"), artifact_topk.get("generated_at")),
        "freshness": first_present(
            summary_topk.get("artifact_freshness_status"),
            artifact_topk.get("artifact_freshness_status"),
            artifact_topk.get("freshness"),
        ),
        "artifact_age_minutes": first_present(summary_topk.get("artifact_age_minutes"), artifact_topk.get("artifact_age_minutes")),
        "artifact_stale_after_minutes": first_present(
            summary_topk.get("artifact_stale_after_minutes"),
            artifact_topk.get("artifact_stale_after_minutes"),
        ),
        "artifact_deployment_blocking": first_present(
            summary_topk.get("artifact_deployment_blocking"),
            artifact_topk.get("artifact_deployment_blocking"),
        ),
        "rows": row_count(rows),
        "deployable_rows": first_present(summary_topk.get("deployable_rows"), artifact_topk.get("deployable_rows")),
        "risk_qualified_rows": first_present(summary_topk.get("risk_qualified_rows"), artifact_topk.get("risk_qualified_rows")),
        "runtime_blocked_candidates": first_present(
            summary_topk.get("runtime_blocked_candidate_rows"),
            summary_topk.get("runtime_blocked_candidates"),
            artifact_topk.get("runtime_blocked_candidate_rows"),
            artifact_topk.get("runtime_blocked_candidates"),
        ),
        "nearest_candidate": pick(
            nearest,
            "model",
            "feature_profile",
            "regime",
            "top_k",
            "deployment_candidate_tier",
            "oos_gate_passed",
            "deployable_verdict",
            "support_route_deployable",
            "deployment_blocker",
            "allowed_layers",
        ),
    }


def compact_q15(q15: dict[str, Any]) -> dict[str, Any]:
    current = q15.get("current_live") if isinstance(q15.get("current_live"), dict) else {}
    route = q15.get("support_route") if isinstance(q15.get("support_route"), dict) else {}
    return {
        "generated_at": q15.get("generated_at"),
        "current_live_structure_bucket": first_present(
            q15.get("current_live_structure_bucket"),
            current.get("current_live_structure_bucket"),
            (route.get("support_identity") or {}).get("current_live_structure_bucket") if isinstance(route.get("support_identity"), dict) else None,
        ),
        "support_route_verdict": first_present(q15.get("support_route_verdict"), route.get("verdict")),
        "current_live_structure_bucket_rows": first_present(
            q15.get("current_live_structure_bucket_rows"),
            current.get("current_live_structure_bucket_rows"),
            route.get("current_live_structure_bucket_rows"),
        ),
        "minimum_support_rows": first_present(q15.get("minimum_support_rows"), route.get("minimum_support_rows")),
        "gap_to_minimum": first_present(q15.get("gap_to_minimum"), route.get("current_live_structure_bucket_gap_to_minimum")),
        "scope_applicability_status": (q15.get("scope_applicability") or {}).get("status") if isinstance(q15.get("scope_applicability"), dict) else None,
    }


def build_runtime_facts(
    *,
    probe: dict[str, Any],
    drill: dict[str, Any],
    summary: dict[str, Any],
    summary_path: str | None,
    issues: dict[str, Any],
    topk: dict[str, Any],
    q15: dict[str, Any],
) -> dict[str, Any]:
    blocker_summary = drill.get("support_blocker_summary") or {}
    if not isinstance(blocker_summary, dict):
        blocker_summary = {}
    support_progress = probe.get("support_progress") or (probe.get("deployment_blocker_details") or {}).get("support_progress") or {}
    if not isinstance(support_progress, dict):
        support_progress = {}
    legacy = support_progress.get("legacy_supported_reference")
    db_counts = summary.get("db_counts") or {}
    if not isinstance(db_counts, dict):
        db_counts = {}
    summary_topk = summary.get("high_conviction_topk") or {}
    if not isinstance(summary_topk, dict):
        summary_topk = {}

    return {
        "summary_path": summary_path,
        "summary_generated_at": summary.get("timestamp") or summary.get("generated_at"),
        "heartbeat": summary.get("heartbeat"),
        "mode": summary.get("mode"),
        "stats": pick(summary.get("stats") or {}, "passed", "total", "elapsed_seconds") if isinstance(summary.get("stats"), dict) else {},
        "counts": {
            "raw": db_counts.get("raw_market_data"),
            "features": db_counts.get("features_normalized"),
            "labels": db_counts.get("labels"),
            "latest_raw_timestamp": db_counts.get("latest_raw_timestamp"),
        },
        "simulated_pyramid_win": db_counts.get("simulated_pyramid_win_rate"),
        "probe": pick(
            probe,
            "generated_at",
            "target_col",
            "signal",
            "confidence",
            "should_trade",
            "allowed_layers",
            "allowed_layers_raw",
            "deployment_blocker",
            "runtime_closure_state",
            "current_live_structure_bucket",
            "current_live_structure_bucket_rows",
            "minimum_support_rows",
            "current_live_structure_bucket_gap_to_minimum",
            "support_route_verdict",
            "support_governance_route",
        ),
        "api_trade_guardrail": pick(
            probe,
            "api_trade_guardrail_active",
            "api_trade_buy_guardrail",
            "api_trade_add_exposure_guardrail",
            "api_trade_guardrail_code",
            "api_trade_allowed_risk_off_sides",
        ),
        "recommended_patch": pick(
            drill,
            "recommended_patch_profile",
            "recommended_patch_status",
            "recommended_patch_reference_scope",
            "recommended_patch_reference_source",
            "recommended_patch_support_route",
            "recommended_patch_gap_to_minimum",
            "recommended_patch_current_live_structure_bucket_rows",
            "recommended_patch_minimum_support_rows",
        ),
        "support_progress": {
            "status": support_progress.get("status"),
            "current_rows": support_progress.get("current_rows"),
            "minimum_support_rows": support_progress.get("minimum_support_rows"),
            "gap_to_minimum": support_progress.get("gap_to_minimum"),
            "regression_basis": support_progress.get("regression_basis"),
            "stagnant_run_count": support_progress.get("stagnant_run_count"),
            "legacy_supported_reference": legacy,
        },
        "support_blocker_summary": pick(
            blocker_summary,
            "operator_summary",
            "operator_next_action",
            "deployment_blocker_reason",
            "current_live_structure_bucket",
            "current_live_structure_bucket_rows",
            "minimum_support_rows",
            "gap_to_minimum",
            "recommended_patch_profile",
            "recommended_patch_status",
            "recommended_patch_reference_scope",
            "recommended_patch_reference_source",
            "recommended_patch_reference_only",
            "legacy_promotable_to_same_identity_history",
        ),
        "topk": compact_topk(summary_topk, topk),
        "q15": compact_q15(q15),
        "docs_sync": pick(summary.get("docs_sync") or {}, "ok", "stale_docs", "auto_synced", "written_docs") if isinstance(summary.get("docs_sync"), dict) else {},
        "issues_active_count": len(issues.get("issues", [])) if isinstance(issues.get("issues"), list) else None,
    }


def main() -> None:
    probe = load("data/live_predict_probe.json")
    drill = load("data/live_decision_quality_drilldown.json")
    summary_path, summary = load_latest_summary()
    issues = load("issues.json")
    topk = load("data/high_conviction_topk_oos_matrix.json")
    q15 = load("data/q15_support_audit.json")
    out = build_runtime_facts(
        probe=probe,
        drill=drill,
        summary=summary,
        summary_path=summary_path,
        issues=issues,
        topk=topk,
        q15=q15,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
