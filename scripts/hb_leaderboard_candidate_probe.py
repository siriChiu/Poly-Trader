#!/usr/bin/env python3
"""Probe leaderboard candidate-governance output for heartbeat verification."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from server.routes import api as api_module  # noqa: E402

OUT_PATH = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"
LAST_METRICS_PATH = PROJECT_ROOT / "model" / "last_metrics.json"
LIVE_PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
BULL_POCKET_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
FEATURE_ABLATION_PATH = PROJECT_ROOT / "data" / "feature_group_ablation.json"
Q15_SUPPORT_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"


KNOWN_SKLEARN_FEATURE_NAME_WARNING_PATTERNS = (
    r"X has feature names, but LogisticRegression was fitted without feature names",
    r"X has feature names, but MLPClassifier was fitted without feature names",
    r"X has feature names, but SVC was fitted without feature names",
)


def _suppress_known_feature_name_warnings() -> None:
    """Hide noisy sklearn feature-name warnings from heartbeat probe stderr.

    The leaderboard probe reuses pre-fit sklearn models that were trained on ndarray
    inputs. During heartbeat governance we only need the resulting payload; repeated
    feature-name warnings drown out real stderr failures and make cron summaries hard
    to read. Keep the suppression narrowly scoped to the exact known warning strings.
    """
    for pattern in KNOWN_SKLEARN_FEATURE_NAME_WARNING_PATTERNS:
        warnings.filterwarnings(
            "ignore",
            message=pattern,
            category=UserWarning,
        )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _timestamp_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _payload_has_rows(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    helper = getattr(api_module, "_model_leaderboard_payload_has_rows", None)
    if callable(helper):
        try:
            return bool(helper(payload))
        except Exception:
            pass
    return bool(
        payload.get("leaderboard")
        or payload.get("placeholder_rows")
        or payload.get("placeholder_models")
    )


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    helper = getattr(api_module, "_normalize_model_leaderboard_payload", None)
    if callable(helper):
        try:
            normalized = helper(payload)
        except Exception:
            normalized = payload
        return normalized if isinstance(normalized, dict) else payload
    return payload


def _payload_missing_selection_fields(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return True
    rows = payload.get("leaderboard") or payload.get("placeholder_rows") or payload.get("placeholder_models") or []
    if not isinstance(rows, list) or not rows:
        return True
    first = rows[0] if isinstance(rows[0], dict) else {}
    return not bool(first.get("selected_feature_profile") and first.get("selected_deployment_profile"))


def _load_leaderboard_payload(*, allow_rebuild: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {}
    source: str | None = None
    updated_at = 0.0
    source_error: Any = None
    cache_error: Any = None

    cache_path = getattr(api_module, "MODEL_LB_CACHE_PATH", None)
    if cache_path and Path(cache_path).exists():
        try:
            cached = json.loads(Path(cache_path).read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                cached_payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else None
                legacy_payload = cached if cached_payload is None and isinstance(cached.get("leaderboard"), list) else None
                if cached_payload is not None and _payload_has_rows(cached_payload):
                    payload = _normalize_payload(cached_payload)
                    updated_at = float(cached.get("updated_at") or 0.0)
                    source_error = cached.get("error")
                    source = "model_leaderboard_cache"
                elif legacy_payload is not None and _payload_has_rows(legacy_payload):
                    payload = _normalize_payload(legacy_payload)
                    updated_at = Path(cache_path).stat().st_mtime
                    source_error = None
                    source = "model_leaderboard_cache"
                else:
                    cache_error = cached.get("error")
        except Exception as exc:
            cache_error = str(exc)

    try:
        snapshot = api_module._load_latest_model_leaderboard_snapshot_payload()
    except Exception as exc:
        snapshot = None
        cache_error = cache_error or str(exc)
    if isinstance(snapshot, dict):
        snapshot_payload = snapshot.get("payload")
        snapshot_updated_at = float(snapshot.get("updated_at") or 0.0)
        if isinstance(snapshot_payload, dict) and _payload_has_rows(snapshot_payload):
            if not payload or snapshot_updated_at > updated_at:
                payload = _normalize_payload(snapshot_payload)
                updated_at = snapshot_updated_at
                source_error = snapshot.get("error")
                source = "latest_persisted_snapshot"

    age_sec = max(int(time.time() - updated_at), 0) if updated_at else None
    stale = None if source is None else bool(age_sec is None or age_sec > 900)
    semantic_refresh_needed = bool(
        allow_rebuild
        and payload
        and _payload_missing_selection_fields(payload)
    )
    if semantic_refresh_needed:
        payload = {}
        updated_at = 0.0
        source_error = None
        source = None
        age_sec = None
        stale = None

    if not payload and allow_rebuild:
        payload = _normalize_payload(api_module._build_model_leaderboard_payload())
        updated_at = time.time()
        source_error = None
        source = "live_rebuild"
        age_sec = 0
        stale = False
    elif source == "live_rebuild":
        stale = False

    if source != "live_rebuild":
        age_sec = max(int(time.time() - updated_at), 0) if updated_at else None
        stale = None if source is None else bool(age_sec is None or age_sec > 900)

    meta = {
        "source": source,
        "updated_at": _timestamp_to_iso(updated_at),
        "cache_age_sec": age_sec,
        "stale": stale,
        "error": source_error,
        "cache_error": cache_error,
    }
    return payload if isinstance(payload, dict) else {}, meta



def _live_rebuild_leaderboard_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _normalize_payload(api_module._build_model_leaderboard_payload())
    updated_at = time.time()
    write_cache = getattr(api_module, "_write_model_leaderboard_cache", None)
    persist_snapshot = getattr(api_module, "_persist_model_leaderboard_snapshot", None)

    if callable(write_cache):
        try:
            write_cache(payload, updated_at)
        except Exception:
            pass
    if callable(persist_snapshot):
        try:
            persist_snapshot(payload)
        except Exception:
            pass

    return payload, {
        "source": "live_rebuild",
        "updated_at": _timestamp_to_iso(updated_at),
        "cache_age_sec": 0,
        "stale": False,
        "error": None,
        "cache_error": None,
    }


def _top_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    leaderboard = payload.get("leaderboard") or []
    placeholder_rows = payload.get("placeholder_rows") or []
    placeholder_models = payload.get("placeholder_models") or []
    top_source = "leaderboard"
    rows = leaderboard
    if not rows and placeholder_rows:
        rows = placeholder_rows
        top_source = "placeholder_rows"
    elif not rows and placeholder_models:
        rows = placeholder_models
        top_source = "placeholder_models"
    top = rows[0] if rows else {}
    return {
        "model_name": top.get("model_name"),
        "deployment_profile": top.get("deployment_profile"),
        "deployment_profile_label": top.get("deployment_profile_label"),
        "deployment_profile_source": top.get("deployment_profile_source"),
        "selected_deployment_profile": top.get("selected_deployment_profile"),
        "selected_deployment_profile_label": top.get("selected_deployment_profile_label"),
        "selected_deployment_profile_source": top.get("selected_deployment_profile_source"),
        "deployment_profiles_evaluated": top.get("deployment_profiles_evaluated"),
        "feature_profile": top.get("feature_profile"),
        "selected_feature_profile": top.get("selected_feature_profile"),
        "selected_feature_profile_source": top.get("selected_feature_profile_source"),
        "feature_profiles_evaluated": top.get("feature_profiles_evaluated"),
        "selected_feature_profile_blocker_applied": top.get("selected_feature_profile_blocker_applied"),
        "selected_feature_profile_blocker_reason": top.get("selected_feature_profile_blocker_reason"),
        "feature_profile_support_cohort": top.get("feature_profile_support_cohort"),
        "feature_profile_support_rows": top.get("feature_profile_support_rows"),
        "feature_profile_exact_live_bucket_rows": top.get("feature_profile_exact_live_bucket_rows"),
        "feature_profile_candidate_diagnostics": top.get("feature_profile_candidate_diagnostics"),
        "overall_score": top.get("overall_score"),
        "avg_decision_quality_score": top.get("avg_decision_quality_score"),
        "ranking_status": top.get("ranking_status"),
        "ranking_warning": top.get("ranking_warning"),
        "placeholder_reason": top.get("placeholder_reason"),
        "top_model_source": top_source,
        "leaderboard_warning": payload.get("leaderboard_warning"),
        "comparable_count": payload.get("comparable_count"),
        "placeholder_count": payload.get("placeholder_count"),
    }


def _production_profile_role(train_profile_source: Any) -> str:
    source = str(train_profile_source or "")
    if source == "bull_4h_pocket_ablation.exact_supported_profile":
        return "bull_exact_supported_production_profile"
    if source == "bull_4h_pocket_ablation.support_aware_profile":
        return "support_aware_production_profile"
    if source == "feature_group_ablation.recommended_profile":
        return "global_shrinkage_winner"
    return "production_profile_unspecified"


def _load_recent_support_history(
    *,
    current_entry: dict[str, Any] | None = None,
    limit: int | None = 5,
    data_dir: Path | None = None,
) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    current_observed_at = None
    current_heartbeat = None
    if current_entry and current_entry.get("live_current_structure_bucket"):
        current_observed_at = current_entry.get("observed_at")
        current_heartbeat = current_entry.get("heartbeat")
        history.append({k: v for k, v in current_entry.items() if k != "observed_at"})

    summaries_dir = data_dir or (PROJECT_ROOT / "data")
    summary_files = sorted(
        summaries_dir.glob("heartbeat_*_summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in summary_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        diag = payload.get("leaderboard_candidate_diagnostics") or {}
        if not isinstance(diag, dict) or not diag:
            legacy_probe = payload.get("leaderboard_candidate_probe") or {}
            legacy_alignment = legacy_probe.get("alignment") if isinstance(legacy_probe, dict) else {}
            if isinstance(legacy_alignment, dict) and legacy_alignment:
                diag = {
                    "live_current_structure_bucket": legacy_alignment.get("live_current_structure_bucket"),
                    "live_current_structure_bucket_rows": legacy_alignment.get("live_current_structure_bucket_rows"),
                    "minimum_support_rows": legacy_alignment.get("minimum_support_rows"),
                    "support_governance_route": legacy_alignment.get("support_governance_route"),
                }
            else:
                continue
        heartbeat = str(payload.get("heartbeat") or path.stem)
        payload_timestamp = payload.get("timestamp")
        payload_dt = _parse_iso_datetime(payload_timestamp)
        if (
            current_observed_at is not None
            and current_heartbeat == heartbeat
            and payload_dt is not None
            and abs((current_observed_at - payload_dt).total_seconds()) < 120
        ):
            continue
        governance_contract = diag.get("governance_contract") or {}
        candidate = {
            "heartbeat": heartbeat,
            "timestamp": payload_timestamp,
            "live_current_structure_bucket": diag.get("live_current_structure_bucket"),
            "live_current_structure_bucket_rows": int(diag.get("live_current_structure_bucket_rows") or 0),
            "minimum_support_rows": int(diag.get("minimum_support_rows") or governance_contract.get("minimum_support_rows") or 0),
            "support_governance_route": diag.get("support_governance_route") or governance_contract.get("support_governance_route"),
            "governance_verdict": governance_contract.get("verdict"),
        }
        if not candidate["live_current_structure_bucket"]:
            continue
        history.append(candidate)
        if limit is not None and len(history) >= limit:
            break
    return history


def _load_q15_support_progress_hint(
    *,
    current_bucket: Any,
    current_route: str | None,
    current_rows: int,
    minimum_support_rows: int,
) -> dict[str, Any] | None:
    q15_audit = _load_json(Q15_SUPPORT_AUDIT_PATH)
    scope_applicability = q15_audit.get("scope_applicability") or {}
    if scope_applicability and scope_applicability.get("active_for_current_live_row") is False:
        return None
    current_live = q15_audit.get("current_live") or {}
    support_route = q15_audit.get("support_route") or {}
    support_progress = support_route.get("support_progress") or {}
    if not support_progress:
        return None
    if current_live.get("current_live_structure_bucket") != current_bucket:
        return None
    if int(current_live.get("current_live_structure_bucket_rows") or 0) != current_rows:
        return None
    if int(support_route.get("minimum_support_rows") or 0) != int(minimum_support_rows or 0):
        return None
    q15_route = support_route.get("support_governance_route")
    if current_route and q15_route and q15_route != current_route:
        return None
    return support_progress



def _summarize_support_progress(
    *,
    current_bucket: Any,
    current_route: str | None,
    live_bucket_rows: Any,
    minimum_support_rows: int,
    current_label: str | None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    current_rows = int(live_bucket_rows or 0)
    q15_hint = _load_q15_support_progress_hint(
        current_bucket=current_bucket,
        current_route=current_route,
        current_rows=current_rows,
        minimum_support_rows=minimum_support_rows,
    )
    if q15_hint is not None:
        return q15_hint

    observed_at = datetime.now(timezone.utc)
    current_entry = {
        "heartbeat": str(current_label or "current"),
        "timestamp": observed_at.isoformat(),
        "observed_at": observed_at,
        "live_current_structure_bucket": current_bucket,
        "live_current_structure_bucket_rows": current_rows,
        "minimum_support_rows": int(minimum_support_rows or 0),
        "support_governance_route": current_route,
        "governance_verdict": None,
    }
    history = _load_recent_support_history(current_entry=current_entry, limit=None, data_dir=data_dir)
    same_bucket_history = [
        item for item in history
        if item.get("live_current_structure_bucket") == current_bucket
    ]
    recent_history = same_bucket_history[:5]

    previous = recent_history[1] if len(recent_history) > 1 else None
    delta_vs_previous = None
    previous_route_changed = False
    if previous is not None:
        previous_rows = int(previous.get("live_current_structure_bucket_rows") or 0)
        delta_vs_previous = current_rows - previous_rows
        previous_route_changed = previous.get("support_governance_route") != current_route

    stagnant_run_count = 0
    if previous is not None and int(previous.get("live_current_structure_bucket_rows") or 0) == current_rows:
        stagnant_run_count = 1
        for item in recent_history[1:]:
            if int(item.get("live_current_structure_bucket_rows") or 0) == current_rows:
                stagnant_run_count += 1
                continue
            break

    minimum = int(minimum_support_rows or 0)
    recent_supported = next(
        (
            item
            for item in same_bucket_history[1:]
            if int(item.get("live_current_structure_bucket_rows") or 0) >= minimum
            or item.get("support_governance_route") == "exact_live_bucket_supported"
        ),
        None,
    )
    recent_supported_rows = None if recent_supported is None else int(recent_supported.get("live_current_structure_bucket_rows") or 0)
    delta_vs_recent_supported = (
        None if recent_supported_rows is None else current_rows - recent_supported_rows
    )
    regressed_from_supported = recent_supported is not None and current_rows < minimum

    if current_route == "exact_live_bucket_supported" or current_rows >= minimum:
        status = "exact_supported"
        reason = "current live exact bucket 已達 minimum support，治理焦點可轉向 post-threshold leaderboard sync。"
    elif regressed_from_supported:
        status = "regressed_under_minimum"
        supported_ref = f"{recent_supported_rows}/{minimum}"
        heartbeat_ref = recent_supported.get("heartbeat") if isinstance(recent_supported, dict) else None
        if delta_vs_previous is not None and delta_vs_previous > 0:
            reason = (
                "current live exact support 最近曾達 minimum support"
                f"（最近一次 {supported_ref}{f'，heartbeat {heartbeat_ref}' if heartbeat_ref else ''}），"
                "目前雖較上一輪回補，但仍低於門檻。"
            )
        elif delta_vs_previous == 0:
            reason = (
                "current live exact support 最近曾達 minimum support"
                f"（最近一次 {supported_ref}{f'，heartbeat {heartbeat_ref}' if heartbeat_ref else ''}），"
                f"但目前仍停在 {current_rows}/{minimum}；這不是一般停滯，而是 support regression。"
            )
        else:
            reason = (
                f"current live exact support 自最近一次已就緒 {supported_ref}"
                f"{f'（heartbeat {heartbeat_ref}）' if heartbeat_ref else ''} 回落，"
                "需檢查 lane/bucket 是否切換或 support artifact 是否退化。"
            )
    elif previous is None:
        status = "no_recent_comparable_history"
        reason = "目前找不到同一 current live structure bucket 的最近 heartbeat 可比對；先持續累積 support。"
    elif delta_vs_previous and delta_vs_previous > 0:
        status = "accumulating"
        reason = "current live exact support 仍低於 minimum，但最近 heartbeat 已持續增加。"
        if previous_route_changed:
            reason += " route 已切換，代表 support pathology 正在從 proxy / fallback 轉向 exact rows 累積。"
    elif delta_vs_previous == 0:
        status = "stalled_under_minimum"
        reason = "current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。"
    else:
        status = "regressed_under_minimum"
        reason = "current live exact support 較上一輪回落，需檢查 lane/bucket 是否切換或 support artifact 是否退化。"

    history_for_display = list(recent_history)
    if recent_supported is not None and all(
        item.get("heartbeat") != recent_supported.get("heartbeat")
        for item in history_for_display
    ):
        if len(history_for_display) >= 5:
            history_for_display = [*history_for_display[:4], recent_supported]
        else:
            history_for_display.append(recent_supported)

    return {
        "status": status,
        "reason": reason,
        "current_rows": current_rows,
        "minimum_support_rows": minimum,
        "gap_to_minimum": max(minimum - current_rows, 0),
        "delta_vs_previous": delta_vs_previous,
        "previous_rows": None if previous is None else int(previous.get("live_current_structure_bucket_rows") or 0),
        "previous_route_changed": previous_route_changed,
        "previous_support_governance_route": None if previous is None else previous.get("support_governance_route"),
        "regressed_from_supported": regressed_from_supported,
        "recent_supported_rows": recent_supported_rows,
        "recent_supported_heartbeat": None if recent_supported is None else recent_supported.get("heartbeat"),
        "recent_supported_timestamp": None if recent_supported is None else recent_supported.get("timestamp"),
        "delta_vs_recent_supported": delta_vs_recent_supported,
        "stagnant_run_count": stagnant_run_count,
        "stalled_support_accumulation": status == "stalled_under_minimum",
        "escalate_to_blocker": status == "regressed_under_minimum" or (status == "stalled_under_minimum" and stagnant_run_count >= 3),
        "history": history_for_display,
    }


def _build_governance_contract(
    *,
    dual_profile_state: str,
    profile_split: dict[str, Any],
    support_governance_route: str | None,
    minimum_support_rows: int,
    live_bucket_rows: Any,
    support_progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    live_rows = int(live_bucket_rows or 0)
    gap_to_minimum = max(int(minimum_support_rows or 0) - live_rows, 0)
    split_required = bool(profile_split.get("split_required"))
    global_profile = profile_split.get("global_profile")
    production_profile = profile_split.get("production_profile")
    global_role = profile_split.get("global_profile_role")
    production_role = profile_split.get("production_profile_role")
    support_progress = support_progress or {}

    if dual_profile_state == "stale_alignment_snapshot":
        return {
            "verdict": "refresh_alignment_snapshot_before_interpreting_split",
            "treat_as_parity_blocker": False,
            "current_closure": "alignment_snapshot_stale",
            "reason": "leaderboard probe 的對齊快照落後於最新 train / bull pocket / feature ablation inputs；需先刷新 alignment artifact，再判讀 profile split 是否仍成立。",
            "recommended_action": "重跑 hb_leaderboard_candidate_probe.py，確認 current inputs recency 後再解讀 profile governance。",
            "global_profile": global_profile,
            "global_profile_role": global_role,
            "production_profile": production_profile,
            "production_profile_role": production_role,
            "support_governance_route": support_governance_route,
            "split_required": split_required,
            "minimum_support_rows": minimum_support_rows,
            "live_current_structure_bucket_rows": live_rows,
            "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
            "support_progress": support_progress,
        }

    if dual_profile_state == "post_threshold_profile_governance_stalled":
        return {
            "verdict": "post_threshold_governance_contract_needs_leaderboard_sync",
            "treat_as_parity_blocker": True,
            "current_closure": "exact_supported_but_leaderboard_not_synced",
            "reason": "exact live bucket 已達 minimum support，production profile 已升級為 exact-supported lane；若 leaderboard 仍停在 global winner，這是 post-threshold governance 未收斂，而不是健康的雙角色分工。",
            "recommended_action": "同步 leaderboard / heartbeat summary / docs，讓 leaderboard candidate governance 接上 exact-supported production profile，避免 fallback 語義殘留。",
            "global_profile": global_profile,
            "global_profile_role": global_role,
            "production_profile": production_profile,
            "production_profile_role": production_role,
            "support_governance_route": support_governance_route,
            "split_required": split_required,
            "minimum_support_rows": minimum_support_rows,
            "live_current_structure_bucket_rows": live_rows,
            "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
            "support_progress": support_progress,
        }

    if dual_profile_state == "train_exact_supported_profile_stale_under_minimum":
        return {
            "verdict": "train_profile_contract_stale_against_current_support",
            "treat_as_parity_blocker": False,
            "current_closure": "train_still_claims_exact_supported_profile_but_live_bucket_under_minimum",
            "reason": "train / runtime 仍沿用 exact-supported production profile，但 current live exact bucket 已回落到 minimum support 以下；這代表 production-profile 敘事落後於當前 support 事實，不能再直接把 train profile 當成 current-live closure。",
            "recommended_action": "下一輪至少重跑一次 full train / support-aware profile refresh，讓 feature_profile_meta 從 exact-supported 降回 support-aware 或重新證明 exact bucket 已恢復；在此之前，heartbeat / docs 必須把 current blocker 寫成 q35 exact support regression，而不是 exact-supported production readiness。",
            "global_profile": global_profile,
            "global_profile_role": global_role,
            "production_profile": production_profile,
            "production_profile_role": production_role,
            "support_governance_route": support_governance_route,
            "split_required": split_required,
            "minimum_support_rows": minimum_support_rows,
            "live_current_structure_bucket_rows": live_rows,
            "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
            "support_progress": support_progress,
        }

    if dual_profile_state == "leaderboard_global_winner_vs_train_support_fallback" and split_required:
        return {
            "verdict": "dual_role_governance_active",
            "treat_as_parity_blocker": False,
            "current_closure": "global_ranking_vs_support_aware_production_split",
            "reason": "目前 global winner 與 production winner 扮演不同角色：leaderboard 保留 global shrinkage winner 作排名基線，train / runtime 則沿用 support-aware 或 exact-supported production profile 描述 current live bull lane。這是治理分工，不是 parity drift。",
            "recommended_action": (
                "current live exact support 已連續停滯，下一輪若仍未增加應升級成 #PROFILE_GOVERNANCE_STALLED blocker。"
                if support_progress.get("escalate_to_blocker")
                else "文件與 heartbeat 應把 split 明寫為雙角色治理；在 exact support 未達標前，不要把 production profile fallback 誤報為 parity blocker。"
            ),
            "global_profile": global_profile,
            "global_profile_role": global_role,
            "production_profile": production_profile,
            "production_profile_role": production_role,
            "support_governance_route": support_governance_route,
            "split_required": split_required,
            "minimum_support_rows": minimum_support_rows,
            "live_current_structure_bucket_rows": live_rows,
            "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
            "support_progress": support_progress,
        }

    if split_required:
        return {
            "verdict": "dual_role_governance_active",
            "treat_as_parity_blocker": False,
            "current_closure": "dual_role_split_but_aligned",
            "reason": "雖然 global 與 production profile 角色不同，但當前 leaderboard / train / runtime 已對齊這個雙角色 contract，可視為健康治理狀態。",
            "recommended_action": "持續在 heartbeat summary / docs 保留雙角色說明，避免後續被誤讀成 parity drift。",
            "global_profile": global_profile,
            "global_profile_role": global_role,
            "production_profile": production_profile,
            "production_profile_role": production_role,
            "support_governance_route": support_governance_route,
            "split_required": split_required,
            "minimum_support_rows": minimum_support_rows,
            "live_current_structure_bucket_rows": live_rows,
            "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
            "support_progress": support_progress,
        }

    return {
        "verdict": "single_role_governance_ok",
        "treat_as_parity_blocker": False,
        "current_closure": "single_profile_alignment",
        "reason": "目前 global 與 production profile 已收斂成同一路徑，leaderboard / train / runtime 不需要額外 split 治理。",
        "recommended_action": "維持單一路徑治理，僅在 support contract 或 shrinkage winner 再次分岔時重開 split 解釋。",
        "global_profile": global_profile,
        "global_profile_role": global_role,
        "production_profile": production_profile,
        "production_profile_role": production_role,
        "support_governance_route": support_governance_route,
        "split_required": split_required,
        "minimum_support_rows": minimum_support_rows,
        "live_current_structure_bucket_rows": live_rows,
        "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
        "support_progress": support_progress,
    }


def _build_alignment(
    top_model: dict[str, Any],
    leaderboard_snapshot_created_at: str | None = None,
    alignment_evaluated_at: str | None = None,
) -> dict[str, Any]:
    last_metrics = _load_json(LAST_METRICS_PATH)
    live_probe = _load_json(LIVE_PROBE_PATH)
    bull_pocket = _load_json(BULL_POCKET_PATH)
    feature_ablation = _load_json(FEATURE_ABLATION_PATH)

    live_context = dict(bull_pocket.get("live_context") or {})
    probe_scope = (
        (live_probe.get("decision_quality_scope_diagnostics") or {}).get("regime_label+regime_gate+entry_quality_label")
        or {}
    )
    probe_live_bucket = (
        live_probe.get("current_live_structure_bucket")
        or live_probe.get("structure_bucket")
        or probe_scope.get("current_live_structure_bucket")
    )
    probe_live_bucket_rows = live_probe.get("current_live_structure_bucket_rows")
    if probe_live_bucket_rows is None:
        probe_live_bucket_rows = probe_scope.get("current_live_structure_bucket_rows")
    if probe_live_bucket:
        live_context["current_live_structure_bucket"] = probe_live_bucket
    if probe_live_bucket_rows is not None:
        live_context["current_live_structure_bucket_rows"] = int(probe_live_bucket_rows or 0)

    cohorts = bull_pocket.get("cohorts") or {}
    support_summary = bull_pocket.get("support_pathology_summary") or {}
    support_cohort = cohorts.get("bull_supported_neighbor_buckets_proxy") or {}
    exact_lane_proxy = cohorts.get("bull_exact_live_lane_proxy") or {}
    exact_bucket_proxy = cohorts.get("bull_live_exact_lane_bucket_proxy") or {}
    live_bucket_rows = live_context.get("current_live_structure_bucket_rows")
    minimum_support_rows = int(
        support_summary.get("minimum_support_rows")
        or live_probe.get("minimum_support_rows")
        or 0
    )
    live_bucket_gap_to_minimum = max(minimum_support_rows - int(live_bucket_rows or 0), 0)
    blocked_candidates = [
        {
            "feature_profile": row.get("feature_profile"),
            "feature_profile_source": row.get("feature_profile_source"),
            "support_cohort": row.get("support_cohort"),
            "support_rows": row.get("support_rows"),
            "exact_live_bucket_rows": row.get("exact_live_bucket_rows"),
            "blocker_reason": row.get("blocker_reason"),
        }
        for row in (top_model.get("feature_profile_candidate_diagnostics") or [])
        if row.get("blocker_applied")
    ]

    train_profile = last_metrics.get("feature_profile")
    train_profile_source = last_metrics.get("feature_profile_source") or last_metrics.get("feature_profile_meta", {}).get("source")
    global_recommended = feature_ablation.get("recommended_profile")
    leaderboard_selected = top_model.get("selected_feature_profile")
    production_profile = train_profile or leaderboard_selected

    leaderboard_snapshot_dt = _parse_iso_datetime(leaderboard_snapshot_created_at)
    alignment_evaluated_dt = _parse_iso_datetime(alignment_evaluated_at)
    train_trained_dt = _parse_iso_datetime(last_metrics.get("trained_at"))
    bull_pocket_dt = _parse_iso_datetime(bull_pocket.get("generated_at"))
    feature_ablation_dt = _parse_iso_datetime(feature_ablation.get("generated_at"))
    stale_against_train = bool(
        leaderboard_snapshot_dt and train_trained_dt and leaderboard_snapshot_dt < train_trained_dt
    )
    stale_against_bull_pocket = bool(
        leaderboard_snapshot_dt and bull_pocket_dt and leaderboard_snapshot_dt < bull_pocket_dt
    )
    stale_against_feature_ablation = bool(
        leaderboard_snapshot_dt and feature_ablation_dt and leaderboard_snapshot_dt < feature_ablation_dt
    )
    alignment_snapshot_stale = (
        stale_against_train or stale_against_bull_pocket or stale_against_feature_ablation
    )
    evaluated_before_train = bool(
        alignment_evaluated_dt and train_trained_dt and alignment_evaluated_dt < train_trained_dt
    )
    evaluated_before_bull_pocket = bool(
        alignment_evaluated_dt and bull_pocket_dt and alignment_evaluated_dt < bull_pocket_dt
    )
    evaluated_before_feature_ablation = bool(
        alignment_evaluated_dt and feature_ablation_dt and alignment_evaluated_dt < feature_ablation_dt
    )
    current_alignment_inputs_stale = (
        evaluated_before_train or evaluated_before_bull_pocket or evaluated_before_feature_ablation
    )

    support_governance_route = "no_support_proxy"
    if int(live_bucket_rows or 0) > 0:
        support_governance_route = (
            "exact_live_bucket_supported"
            if minimum_support_rows <= 0 or int(live_bucket_rows or 0) >= minimum_support_rows
            else "exact_live_bucket_present_but_below_minimum"
        )
    elif int(exact_bucket_proxy.get("rows") or 0) > 0:
        support_governance_route = "exact_live_bucket_proxy_available"
    elif int(exact_lane_proxy.get("rows") or 0) > 0:
        support_governance_route = "exact_live_lane_proxy_available"
    elif int(support_cohort.get("rows") or 0) > 0:
        support_governance_route = "supported_neighbor_only"

    dual_profile_state = "aligned"
    if leaderboard_selected != train_profile:
        if current_alignment_inputs_stale:
            dual_profile_state = "stale_alignment_snapshot"
        elif (
            support_governance_route == "exact_live_bucket_present_but_below_minimum"
            and train_profile_source == "bull_4h_pocket_ablation.exact_supported_profile"
        ):
            dual_profile_state = "train_exact_supported_profile_stale_under_minimum"
        elif (
            support_governance_route == "exact_live_bucket_supported"
            and train_profile_source == "bull_4h_pocket_ablation.exact_supported_profile"
        ):
            dual_profile_state = "post_threshold_profile_governance_stalled"
        else:
            dual_profile_state = "leaderboard_global_winner_vs_train_support_fallback"
    elif leaderboard_selected != global_recommended:
        # `_build_model_leaderboard_payload()` recomputes the current leaderboard in-process
        # and only *attaches* persisted snapshot history for recency/reference. When the
        # live probe and train already agree on the selected feature profile, an older
        # stored snapshot should not masquerade as a fresh governance drift blocker.
        # Keep the historical staleness surfaced in artifact_recency, but treat the
        # current alignment as healthy unless train and leaderboard actually diverge.
        dual_profile_state = "aligned"

    profile_split_required = bool(global_recommended and production_profile and global_recommended != production_profile)
    profile_split = {
        "global_profile": global_recommended,
        "global_profile_role": "global_shrinkage_winner",
        "global_profile_source": "feature_group_ablation.recommended_profile" if global_recommended else None,
        "production_profile": production_profile,
        "production_profile_role": _production_profile_role(train_profile_source),
        "production_profile_source": train_profile_source,
        "split_required": profile_split_required,
        "verdict": "dual_role_required" if profile_split_required else "single_role_ok",
        "reason": (
            "global winner 代表 recent global shrinkage / CV 穩定度；production winner 代表 current live bull lane 的支撐與治理語義，兩者不應再被混成同一個 profile。"
            if profile_split_required
            else "目前 global winner 與 production winner 一致，可視為單一路徑治理。"
        ),
    }
    support_progress = _summarize_support_progress(
        current_bucket=live_context.get("current_live_structure_bucket"),
        current_route=support_governance_route,
        live_bucket_rows=live_bucket_rows,
        minimum_support_rows=minimum_support_rows,
        current_label=os.getenv("HB_RUN_LABEL"),
    )
    governance_contract = _build_governance_contract(
        dual_profile_state=dual_profile_state,
        profile_split=profile_split,
        support_governance_route=support_governance_route,
        minimum_support_rows=minimum_support_rows,
        live_bucket_rows=live_bucket_rows,
        support_progress=support_progress,
    )

    return {
        "global_recommended_profile": global_recommended,
        "train_selected_profile": train_profile,
        "train_selected_profile_source": last_metrics.get("feature_profile_source") or last_metrics.get("feature_profile_meta", {}).get("source"),
        "train_support_cohort": last_metrics.get("feature_profile_meta", {}).get("support_cohort"),
        "train_support_rows": last_metrics.get("feature_profile_meta", {}).get("support_rows"),
        "train_exact_live_bucket_rows": last_metrics.get("feature_profile_meta", {}).get("exact_live_bucket_rows"),
        "leaderboard_selected_profile": leaderboard_selected,
        "leaderboard_selected_profile_source": top_model.get("selected_feature_profile_source"),
        "leaderboard_snapshot_created_at": leaderboard_snapshot_created_at,
        "alignment_evaluated_at": alignment_evaluated_at,
        "dual_profile_state": dual_profile_state,
        "profile_split": profile_split,
        "governance_contract": governance_contract,
        "current_alignment_inputs_stale": current_alignment_inputs_stale,
        "current_alignment_recency": {
            "inputs_current": not current_alignment_inputs_stale,
            "evaluated_before_train": evaluated_before_train,
            "evaluated_before_bull_pocket": evaluated_before_bull_pocket,
            "evaluated_before_feature_ablation": evaluated_before_feature_ablation,
            "train_trained_at": last_metrics.get("trained_at"),
            "bull_pocket_generated_at": bull_pocket.get("generated_at"),
            "feature_ablation_generated_at": feature_ablation.get("generated_at"),
        },
        "artifact_recency": {
            "alignment_snapshot_stale": alignment_snapshot_stale,
            "stale_against_train": stale_against_train,
            "stale_against_bull_pocket": stale_against_bull_pocket,
            "stale_against_feature_ablation": stale_against_feature_ablation,
            "train_trained_at": last_metrics.get("trained_at"),
            "bull_pocket_generated_at": bull_pocket.get("generated_at"),
            "feature_ablation_generated_at": feature_ablation.get("generated_at"),
        },
        "blocked_candidate_profiles": blocked_candidates,
        "live_regime_gate": live_probe.get("regime_gate"),
        "live_entry_quality_label": live_probe.get("entry_quality_label"),
        "live_execution_guardrail_reason": live_probe.get("execution_guardrail_reason"),
        "live_current_structure_bucket": live_context.get("current_live_structure_bucket"),
        "live_current_structure_bucket_rows": live_bucket_rows,
        "minimum_support_rows": minimum_support_rows,
        "live_current_structure_bucket_gap_to_minimum": live_bucket_gap_to_minimum,
        "support_progress": support_progress,
        "exact_bucket_root_cause": support_summary.get("exact_bucket_root_cause"),
        "support_blocker_state": support_summary.get("blocker_state"),
        "proxy_boundary_verdict": support_summary.get("proxy_boundary_verdict"),
        "proxy_boundary_reason": support_summary.get("proxy_boundary_reason"),
        "exact_lane_bucket_verdict": support_summary.get("exact_lane_bucket_verdict"),
        "exact_lane_toxic_bucket": support_summary.get("exact_lane_toxic_bucket"),
        "supported_neighbor_buckets": live_context.get("supported_neighbor_buckets") or [],
        "bull_support_aware_profile": support_cohort.get("recommended_profile"),
        "bull_support_neighbor_rows": support_cohort.get("rows"),
        "bull_exact_live_lane_proxy_profile": exact_lane_proxy.get("recommended_profile"),
        "bull_exact_live_lane_proxy_rows": exact_lane_proxy.get("rows"),
        "bull_live_exact_bucket_proxy_profile": exact_bucket_proxy.get("recommended_profile"),
        "bull_live_exact_bucket_proxy_rows": exact_bucket_proxy.get("rows"),
        "bull_exact_live_bucket_proxy_rows": exact_bucket_proxy.get("rows"),
        "support_governance_route": support_governance_route,
    }


def build_probe_result(*, allow_rebuild: bool = True, generated_at: str | None = None) -> dict[str, Any] | None:
    payload, payload_meta = _load_leaderboard_payload(allow_rebuild=allow_rebuild)
    if allow_rebuild and payload and payload_meta.get("stale"):
        try:
            payload, payload_meta = _live_rebuild_leaderboard_payload()
        except Exception:
            pass
    if not _payload_has_rows(payload):
        return None
    top_model = _top_model_payload(payload)
    snapshot_history = payload.get("snapshot_history") or []
    leaderboard_snapshot_created_at = None
    latest_snapshot_dt = None
    for item in snapshot_history:
        if not isinstance(item, dict):
            continue
        created_at = item.get("created_at")
        created_dt = _parse_iso_datetime(created_at)
        if created_dt is None:
            continue
        if latest_snapshot_dt is None or created_dt > latest_snapshot_dt:
            latest_snapshot_dt = created_dt
            leaderboard_snapshot_created_at = created_at
    payload_updated_at = payload_meta.get("updated_at")
    payload_updated_dt = _parse_iso_datetime(payload_updated_at)
    if payload_updated_dt is not None and (latest_snapshot_dt is None or payload_updated_dt > latest_snapshot_dt):
        leaderboard_snapshot_created_at = payload_updated_at
    generated_at = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "generated_at": generated_at,
        "leaderboard_snapshot_created_at": leaderboard_snapshot_created_at,
        "leaderboard_payload_source": payload_meta.get("source"),
        "leaderboard_payload_updated_at": payload_meta.get("updated_at"),
        "leaderboard_payload_cache_age_sec": payload_meta.get("cache_age_sec"),
        "leaderboard_payload_stale": payload_meta.get("stale"),
        "leaderboard_payload_error": payload_meta.get("error"),
        "leaderboard_payload_cache_error": payload_meta.get("cache_error"),
        "target_col": payload.get("target_col"),
        "leaderboard_count": payload.get("count", 0),
        "top_model": top_model,
        "alignment": _build_alignment(
            top_model,
            leaderboard_snapshot_created_at=leaderboard_snapshot_created_at,
            alignment_evaluated_at=generated_at,
        ),
    }


def main() -> int:
    _suppress_known_feature_name_warnings()
    result = build_probe_result(allow_rebuild=True)
    if result is None:
        raise RuntimeError("Unable to load leaderboard payload from cache, snapshot, or live rebuild")
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
