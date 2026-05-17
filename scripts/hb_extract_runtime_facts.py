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
import re
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


SENSITIVE_TEXT_REPLACEMENTS = (
    ("COINGLASS", "[REDACTED]"),
    ("CoinGlass", "[REDACTED]"),
)


def redact_sensitive_text(value: Any) -> Any:
    """Remove concrete credential/source names from compact cron facts.

    Runtime artifacts may include concrete secret/env-var names. Cron reports
    need the blocker class and operator action, not exact provider/env
    identifiers. Keep generic words such as "credential" because they describe
    the required operator proof.
    """
    if not isinstance(value, str):
        return value
    text = re.sub(
        r"\b[A-Z][A-Z0-9_]*(?:API[_-]?KEY|APIKEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)[A-Z0-9_]*\b",
        "[REDACTED]",
        value,
    )
    for needle, replacement in SENSITIVE_TEXT_REPLACEMENTS:
        text = text.replace(needle, replacement)
    return text


def _compact_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return counts


def compact_source_blockers(summary_source_blockers: dict[str, Any] | None) -> dict[str, Any]:
    """Project source coverage/auth/TLS blockers without dumping full artifacts."""
    if not isinstance(summary_source_blockers, dict):
        summary_source_blockers = {}
    raw_rows = summary_source_blockers.get("blocked_features") or []
    rows = [row for row in raw_rows if isinstance(row, dict)]

    top_blockers: list[dict[str, Any]] = []
    for row in rows[:5]:
        top_blockers.append(
            {
                "key": row.get("key"),
                "quality_flag": row.get("quality_flag"),
                "history_class": row.get("history_class"),
                "coverage_pct": row.get("coverage_pct"),
                "archive_window_coverage_pct": row.get("archive_window_coverage_pct"),
                "forward_archive_ready": row.get("forward_archive_ready"),
                "forward_archive_status": row.get("forward_archive_status"),
                "latest_status": row.get("raw_snapshot_latest_status"),
                "latest_age_min": row.get("raw_snapshot_latest_age_min"),
                "operator_action": redact_sensitive_text(
                    first_present(row.get("raw_snapshot_latest_operator_action"), row.get("recommended_action"))
                ),
                "message": redact_sensitive_text(row.get("raw_snapshot_latest_message")),
            }
        )

    return {
        "blocked_count": first_present(summary_source_blockers.get("blocked_count"), len(rows) if rows else None),
        "history_class_counts": _compact_counts(rows, "history_class"),
        "quality_flag_counts": _compact_counts(rows, "quality_flag"),
        "top_blockers": top_blockers,
    }


def compact_venue_readiness(metadata_smoke: dict[str, Any] | None) -> dict[str, Any]:
    """Project venue runtime proof status for cron/productization reports."""
    if not isinstance(metadata_smoke, dict):
        metadata_smoke = {}
    raw_venues = metadata_smoke.get("venues") or []
    if not isinstance(raw_venues, list):
        raw_venues = []

    venues: list[dict[str, Any]] = []
    for item in raw_venues[:5]:
        if not isinstance(item, dict):
            continue
        blockers = item.get("blockers") if isinstance(item.get("blockers"), list) else []
        venues.append(
            {
                "venue": item.get("venue"),
                "ok": item.get("ok"),
                "adapter_supported": item.get("adapter_supported"),
                "enabled_in_config": item.get("enabled_in_config"),
                "credentials_configured": item.get("credentials_configured"),
                "proof_state": item.get("proof_state"),
                "readiness_state": item.get("readiness_state"),
                "runtime_ready": item.get("runtime_ready"),
                "blockers": blockers[:6],
                "operator_next_action": item.get("operator_next_action"),
                "verify_next": item.get("verify_next"),
            }
        )

    blockers = metadata_smoke.get("runtime_ready_blockers")
    return {
        "generated_at": metadata_smoke.get("generated_at"),
        "venues_checked": metadata_smoke.get("venues_checked"),
        "all_ok": first_present(metadata_smoke.get("all_ok"), metadata_smoke.get("ok")),
        "runtime_ready": metadata_smoke.get("runtime_ready"),
        "runtime_ready_count": metadata_smoke.get("runtime_ready_count"),
        "readiness_scope": metadata_smoke.get("readiness_scope"),
        "readiness_state": metadata_smoke.get("readiness_state"),
        "runtime_ready_blockers": blockers[:8] if isinstance(blockers, list) else [],
        "venues": venues,
    }


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


def compact_legacy_supported_reference(legacy: Any) -> dict[str, Any] | None:
    """Project old supported-bucket evidence without making it look deployable.

    The live probe may carry a large ``legacy_supported_reference`` object with
    nested semantic-evidence rows. Cron summaries need the opposite: a compact
    current-state proof that old 53/50-style support is reference-only unless
    the support identity exactly matches the current live bucket semantics.
    """
    if not isinstance(legacy, dict):
        return None
    semantic = legacy.get("semantic_identity_evidence")
    if not isinstance(semantic, dict):
        semantic = {}
    rows = first_present(
        legacy.get("live_current_structure_bucket_rows"),
        legacy.get("current_live_structure_bucket_rows"),
    )
    supports_current_identity = semantic.get("supports_current_identity")
    promotable = semantic.get("promotable_to_same_identity_history")
    mismatched_fields = semantic.get("mismatched_fields") if isinstance(semantic.get("mismatched_fields"), list) else []
    missing_fields = semantic.get("missing_fields") if isinstance(semantic.get("missing_fields"), list) else []
    reference_only = bool(
        legacy.get("reference_only_reason")
        or supports_current_identity is False
        or promotable is False
        or mismatched_fields
        or missing_fields
    )
    return {
        "heartbeat": legacy.get("heartbeat"),
        "timestamp": legacy.get("timestamp"),
        "current_live_structure_bucket": first_present(
            legacy.get("live_current_structure_bucket"),
            legacy.get("current_live_structure_bucket"),
        ),
        "rows": rows,
        "minimum_support_rows": legacy.get("minimum_support_rows"),
        "support_route_verdict": legacy.get("support_route_verdict"),
        "support_governance_route": legacy.get("support_governance_route"),
        "reference_only": reference_only,
        "reference_only_reason": legacy.get("reference_only_reason"),
        "supports_current_identity": supports_current_identity,
        "promotable_to_same_identity_history": promotable,
        "semantic_evidence_verdict": semantic.get("verdict"),
        "mismatched_fields": mismatched_fields[:8],
        "missing_fields": missing_fields[:8],
    }


def _compact_circuit_scope(scope: dict[str, Any]) -> dict[str, Any]:
    release = scope.get("release_condition") if isinstance(scope.get("release_condition"), dict) else {}
    streak = scope.get("streak") if isinstance(scope.get("streak"), dict) else {}
    recent = scope.get("recent_window") if isinstance(scope.get("recent_window"), dict) else {}
    tail = scope.get("tail_pathology") if isinstance(scope.get("tail_pathology"), dict) else {}
    return {
        "triggered": scope.get("triggered"),
        "triggered_by": scope.get("triggered_by"),
        "release_ready": first_present(scope.get("release_ready"), release.get("release_ready")),
        "current_streak": first_present(release.get("current_streak"), streak.get("count")),
        "streak_threshold": first_present(release.get("streak_must_be_below"), streak.get("threshold")),
        "recent_window": first_present(release.get("recent_window"), recent.get("window_size")),
        "recent_win_rate_floor": first_present(release.get("recent_win_rate_floor"), recent.get("trigger_floor")),
        "current_recent_window_win_rate": first_present(
            release.get("current_recent_window_win_rate"),
            recent.get("win_rate"),
        ),
        "current_recent_window_wins": first_present(
            release.get("current_recent_window_wins"),
            recent.get("wins"),
            tail.get("wins_in_recent_window"),
        ),
        "required_recent_window_wins": release.get("required_recent_window_wins"),
        "additional_recent_window_wins_needed": release.get("additional_recent_window_wins_needed"),
        "losses_in_recent_window": first_present(recent.get("losses"), tail.get("losses_in_recent_window")),
        "loss_share": tail.get("loss_share"),
    }


def _circuit_operator_summary(verdict: Any, aligned_scope: dict[str, Any]) -> str | None:
    needed = aligned_scope.get("additional_recent_window_wins_needed")
    wins = aligned_scope.get("current_recent_window_wins")
    required = aligned_scope.get("required_recent_window_wins")
    window = aligned_scope.get("recent_window")
    release_ready = aligned_scope.get("release_ready")
    release_math_ready = needed is not None and wins is not None and required is not None and window is not None
    if verdict == "canonical_breaker_active":
        if release_math_ready:
            return (
                "熔斷審計：金字塔 24h 仍是即時部署阻塞；"
                f"最近 {window} 筆目前 {wins}/{window} 勝，解除至少需要 {required} 勝，還差 {needed} 勝；"
                "買入 / 加倉維持關閉，減風險路徑保留。"
            )
        if release_ready is False:
            return "熔斷審計：金字塔 24h 尚未達解除條件；買入 / 加倉維持關閉，減風險路徑保留。"
        return None
    if verdict != "mixed_horizon_false_positive":
        return None
    if release_ready is True:
        return "熔斷審計：混合週期訊號屬誤報；金字塔 24h 解除條件已達標，但不可因此繞過目前即時精準支持阻塞。"
    if release_math_ready:
        return (
            "熔斷審計：金字塔 24h 尚未達解除條件；"
            f"最近 {window} 筆目前 {wins}/{window} 勝，解除至少需要 {required} 勝，還差 {needed} 勝；"
            "買入 / 加倉維持關閉，減風險路徑保留。"
        )
    if needed is not None:
        return f"熔斷審計：金字塔 24h 尚未達解除條件，還差 {needed} 筆勝樣本；買入 / 加倉維持關閉，減風險路徑保留。"
    return "熔斷審計：金字塔 24h 尚未確認解除；買入 / 加倉維持關閉，減風險路徑保留。"


def compact_circuit_breaker_audit(summary_audit: dict[str, Any], artifact_audit: dict[str, Any]) -> dict[str, Any]:
    """Project circuit-breaker release math without heavyweight row previews.

    The raw audit includes recent-window row examples for debugging. Cron reports only
    need the canonical-vs-mixed horizon verdict and release counters, especially when
    mixed-horizon false positives must not obscure the current-live support blocker.
    """
    if not isinstance(summary_audit, dict):
        summary_audit = {}
    if not isinstance(artifact_audit, dict):
        artifact_audit = {}

    def merged_mapping(key: str) -> dict[str, Any]:
        artifact_value = artifact_audit.get(key) if isinstance(artifact_audit.get(key), dict) else {}
        summary_value = summary_audit.get(key) if isinstance(summary_audit.get(key), dict) else {}
        return {**artifact_value, **summary_value}

    root = merged_mapping("root_cause")
    thresholds = merged_mapping("trigger_thresholds")
    mixed = merged_mapping("mixed_scope")
    aligned = merged_mapping("aligned_scope")
    compact_aligned = _compact_circuit_scope(aligned)
    verdict = root.get("verdict")
    return {
        "heartbeat": first_present(summary_audit.get("heartbeat"), artifact_audit.get("heartbeat")),
        "target_col": first_present(summary_audit.get("target_col"), artifact_audit.get("target_col")),
        "canonical_horizon_minutes": thresholds.get("horizon_minutes"),
        "verdict": verdict,
        "summary": root.get("summary"),
        "recommended_patch": root.get("recommended_patch"),
        "operator_guardrail_summary": _circuit_operator_summary(verdict, compact_aligned),
        "mixed_scope": _compact_circuit_scope(mixed),
        "aligned_scope": compact_aligned,
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
    circuit_breaker: dict[str, Any] | None = None,
    execution_metadata_smoke: dict[str, Any] | None = None,
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
    summary_circuit = summary.get("circuit_breaker_audit") or {}
    if not isinstance(summary_circuit, dict):
        summary_circuit = {}
    if not isinstance(circuit_breaker, dict):
        circuit_breaker = {}
    if not isinstance(execution_metadata_smoke, dict):
        execution_metadata_smoke = {}

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
            "reason": support_progress.get("reason"),
            "current_rows": support_progress.get("current_rows"),
            "minimum_support_rows": support_progress.get("minimum_support_rows"),
            "gap_to_minimum": support_progress.get("gap_to_minimum"),
            "previous_rows": support_progress.get("previous_rows"),
            "delta_vs_previous": support_progress.get("delta_vs_previous"),
            "support_rows_needed": first_present(
                support_progress.get("support_rows_needed"),
                support_progress.get("gap_to_minimum"),
                probe.get("current_live_structure_bucket_gap_to_minimum"),
            ),
            "regression_basis": support_progress.get("regression_basis"),
            "stagnant_run_count": support_progress.get("stagnant_run_count"),
            "stalled_support_accumulation": support_progress.get("stalled_support_accumulation"),
            "escalate_to_blocker": support_progress.get("escalate_to_blocker"),
            "regressed_from_supported": support_progress.get("regressed_from_supported"),
            "recent_supported_rows": support_progress.get("recent_supported_rows"),
            "recent_supported_heartbeat": support_progress.get("recent_supported_heartbeat"),
            "delta_vs_recent_supported": support_progress.get("delta_vs_recent_supported"),
            "legacy_supported_reference": compact_legacy_supported_reference(legacy),
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
        "source_blockers": compact_source_blockers(
            summary.get("source_blockers") if isinstance(summary.get("source_blockers"), dict) else None
        ),
        "venue_readiness": compact_venue_readiness(execution_metadata_smoke),
        "q15": compact_q15(q15),
        "circuit_breaker": compact_circuit_breaker_audit(summary_circuit, circuit_breaker),
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
    circuit_breaker = load("data/circuit_breaker_audit.json")
    execution_metadata_smoke = load("data/execution_metadata_smoke.json")
    out = build_runtime_facts(
        probe=probe,
        drill=drill,
        summary=summary,
        summary_path=summary_path,
        issues=issues,
        topk=topk,
        q15=q15,
        circuit_breaker=circuit_breaker,
        execution_metadata_smoke=execution_metadata_smoke,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
