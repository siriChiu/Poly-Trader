import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from backtesting.model_leaderboard import MIN_TRAIN_SAMPLES, ModelLeaderboard
from config import load_config
from model.personal_release import evaluate_candidate_release, resolve_personal_release_policy
from server.routes.api import DB_PATH, load_model_leaderboard_frame

TOP_PCTS = [0.01, 0.02, 0.05, 0.10]
MODELS = ["xgboost", "random_forest", "logistic_regression"]
OUT_PATH = Path("data/high_conviction_topk_oos_matrix.json")
LEGACY_OUT_PATH = Path("model/topk_walkforward_precision.json")
LIVE_PROBE_PATH = Path("data/live_predict_probe.json")
CIRCUIT_BREAKER_AUDIT_PATH = Path("data/circuit_breaker_audit.json")
LIVE_PROBE_REFRESH_SCRIPT = PROJECT_ROOT / "scripts" / "hb_predict_probe.py"
MINIMUM_DEPLOYMENT_GATES = {
    "min_trades": 50,
    "min_win_rate": 0.60,
    "max_drawdown": 0.08,
    "min_profit_factor": 1.50,
    "worst_fold": "non_negative_or_above_baseline",
    "support_route": "deployable",
}
LIVE_GUARDRAIL_FAILURES = {"support_route_not_deployable", "deployment_blocker_active", "breaker_release_not_ready"}
ARTIFACT_STALE_AFTER_MINUTES = 60.0
LIVE_PROBE_STALE_AFTER_MINUTES = 30.0


def artifact_freshness_fields(generated_at: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Machine-readable freshness/deployment-blocking contract for Top-K artifacts."""
    checked_at = now or datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "artifact_freshness_status": "unavailable",
        "artifact_freshness_reason": "missing_generated_at",
        "artifact_age_minutes": None,
        "artifact_stale_after_minutes": ARTIFACT_STALE_AFTER_MINUTES,
        "artifact_deployment_blocking": True,
        "artifact_freshness_checked_at": checked_at.isoformat(),
    }
    if not generated_at:
        return payload
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        if generated_dt.tzinfo is None:
            generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        payload["artifact_freshness_reason"] = "invalid_generated_at"
        return payload
    age_minutes = max((checked_at - generated_dt).total_seconds(), 0.0) / 60.0
    status = "fresh" if age_minutes <= ARTIFACT_STALE_AFTER_MINUTES else "stale"
    payload.update(
        {
            "artifact_freshness_status": status,
            "artifact_freshness_reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
            "artifact_age_minutes": age_minutes,
            "artifact_deployment_blocking": status != "fresh",
        }
    )
    return payload


def live_probe_freshness_fields(generated_at: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Freshness contract for live support context used by Top-K deployment gates."""
    checked_at = now or datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "status": "unavailable",
        "reason": "missing_generated_at",
        "generated_at": generated_at,
        "checked_at": checked_at.isoformat(),
        "age_minutes": None,
        "stale_after_minutes": LIVE_PROBE_STALE_AFTER_MINUTES,
        "deployment_blocking": True,
    }
    if not generated_at:
        return payload
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        if generated_dt.tzinfo is None:
            generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        payload["reason"] = "invalid_generated_at"
        return payload
    age_minutes = max((checked_at - generated_dt).total_seconds(), 0.0) / 60.0
    status = "fresh" if age_minutes <= LIVE_PROBE_STALE_AFTER_MINUTES else "stale"
    payload.update(
        {
            "status": status,
            "reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
            "age_minutes": age_minutes,
            "deployment_blocking": status != "fresh",
        }
    )
    return payload


def _load_probe_payload(probe_path: Path = LIVE_PROBE_PATH) -> tuple[dict[str, Any], Optional[str]]:
    if not probe_path.exists():
        return {}, "missing_live_probe"
    try:
        payload = json.loads(probe_path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "unreadable_live_probe"
    if not isinstance(payload, dict):
        return {}, "invalid_live_probe_payload"
    return payload, None


def _probe_freshness_from_path(probe_path: Path = LIVE_PROBE_PATH) -> dict[str, Any]:
    payload, error = _load_probe_payload(probe_path)
    generated_at = payload.get("generated_at") or payload.get("feature_timestamp") if payload else None
    freshness = live_probe_freshness_fields(generated_at)
    if error and freshness.get("reason") == "missing_generated_at":
        freshness["reason"] = error
    return freshness


def _load_circuit_breaker_release_condition(path: Path = CIRCUIT_BREAKER_AUDIT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    candidates = [
        payload.get("release_condition"),
        payload.get("aligned_scope", {}).get("release_condition") if isinstance(payload.get("aligned_scope"), dict) else None,
        payload.get("canonical_scope"),
    ]
    keys = {
        "release_ready",
        "blocked_by",
        "streak_release_ready",
        "recent_win_rate_release_ready",
        "streak_must_be_below",
        "current_streak",
        "recent_window",
        "recent_win_rate_floor",
        "current_recent_window_win_rate",
        "current_recent_window_wins",
        "required_recent_window_wins",
        "additional_recent_window_wins_needed",
    }
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        release = {key: candidate.get(key) for key in keys if candidate.get(key) is not None}
        if release.get("release_ready") is not None:
            return release
    return {}


def _refresh_live_predict_probe_if_stale(probe_path: Path = LIVE_PROBE_PATH) -> dict[str, Any]:
    before = _probe_freshness_from_path(probe_path)
    result: dict[str, Any] = {
        "attempted": False,
        "status": "skipped_fresh_probe" if not before.get("deployment_blocking") else "stale_probe_detected",
        "reason": before.get("reason"),
        "before": before,
        "after": before,
        "refresh_script": str(LIVE_PROBE_REFRESH_SCRIPT),
    }
    if not before.get("deployment_blocking"):
        return result
    if not LIVE_PROBE_REFRESH_SCRIPT.exists():
        result.update({
            "status": "refresh_unavailable",
            "error": "missing_hb_predict_probe_script",
        })
        return result
    result["attempted"] = True
    try:
        completed = subprocess.run(
            [sys.executable, str(LIVE_PROBE_REFRESH_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except Exception as exc:
        result.update({
            "status": "refresh_failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
        return result

    after = _probe_freshness_from_path(probe_path)
    result["after"] = after
    result["returncode"] = completed.returncode
    if completed.returncode != 0:
        result.update({
            "status": "refresh_failed",
            "error": f"hb_predict_probe_exit_{completed.returncode}",
        })
    elif after.get("deployment_blocking"):
        result.update({
            "status": "refresh_still_stale",
            "error": after.get("reason"),
        })
    else:
        result.update({
            "status": "refreshed",
            "error": None,
        })
    return result


def _stale_live_support_context(context: dict, freshness: dict[str, Any]) -> dict:
    source_generated_at = context.get("source_live_probe_generated_at")
    source_artifact = context.get("live_truth_source_artifact")
    minimum_rows = context.get("minimum_support_rows") or 50
    try:
        minimum_rows = int(minimum_rows)
    except (TypeError, ValueError):
        minimum_rows = 50
    reference_keys = (
        "current_live_structure_bucket",
        "current_live_structure_bucket_rows",
        "minimum_support_rows",
        "current_live_structure_bucket_gap_to_minimum",
        "support_route_verdict",
        "support_governance_route",
        "deployment_blocker",
        "runtime_closure_state",
        "support_progress_status",
        "source_live_probe_generated_at",
        "live_truth_source_artifact",
    )
    return {
        "generated_at": source_generated_at,
        "source_artifact": source_artifact,
        "support_context_status": "stale_live_probe_shadow_only",
        "support_context_freshness": freshness,
        "live_truth_freshness": freshness,
        "support_context_refresh": context.get("support_context_refresh"),
        "live_truth_overlay_applied": False,
        "live_truth_overlay_blocker": freshness.get("reason") or "stale_live_probe",
        "source_live_probe_generated_at": source_generated_at,
        "live_truth_source_artifact": source_artifact,
        "stale_support_context_reference": {
            key: context.get(key) for key in reference_keys if context.get(key) is not None
        },
        "support_route_verdict": "stale_live_support_context",
        "support_governance_route": "stale_live_support_context",
        "support_governance_reference_evidence": {
            "reference_only": True,
            "reason": "stale_live_probe",
            "source_live_probe_generated_at": source_generated_at,
            "source_artifact": source_artifact,
        },
        "support_route_deployable": False,
        "deployment_blocker": "stale_live_support_context",
        "runtime_closure_state": "stale_live_support_context_shadow_only",
        "current_live_structure_bucket": "stale_live_support_context",
        "current_live_structure_bucket_rows": 0,
        "minimum_support_rows": minimum_rows,
        "current_live_structure_bucket_gap_to_minimum": minimum_rows,
        "allowed_layers": 0,
        "signal": "ABSTAIN",
        "execution_guardrail_reason": "live_support_context_stale; high_conviction_topk_shadow_only",
        "release_ready": False,
        "support_progress_status": "stale_live_probe_shadow_only",
        "support_rows_needed": minimum_rows,
    }


def _round_or_none(value: Any, digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return round(numeric, digits)


def _safe_profit_factor(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = abs(float(pnl[pnl < 0].sum()))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def _max_drawdown_from_pnl(pnl: pd.Series) -> Optional[float]:
    if pnl.empty:
        return None
    cumulative = pnl.cumsum()
    peak = cumulative.cummax()
    drawdown = peak - cumulative
    return round(float(drawdown.max()), 4)


def _pnl_series_for_subset(sub: pd.DataFrame) -> pd.Series:
    for col in ["simulated_pyramid_pnl", "future_return_pct"]:
        if col in sub.columns:
            return pd.to_numeric(sub[col], errors="coerce").fillna(0.0).astype(float)
    return pd.Series([], dtype=float)


def _load_support_context(*, auto_refresh: bool = False) -> dict:
    """Load current-live support/blocker truth so top-k candidates fail closed."""
    probe_path = LIVE_PROBE_PATH
    refresh_status = _refresh_live_predict_probe_if_stale(probe_path) if auto_refresh else None
    if not probe_path.exists():
        context = {
            "support_route_verdict": "not_evaluated",
            "deployment_blocker": "unknown",
        }
        if refresh_status is not None:
            context["support_context_refresh"] = refresh_status
        return context
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except Exception:
        context = {
            "support_route_verdict": "not_evaluated",
            "deployment_blocker": "unreadable_live_probe",
        }
        if refresh_status is not None:
            context["support_context_refresh"] = refresh_status
        return context
    keys = [
        "support_route_verdict",
        "support_governance_route",
        "support_governance_reference_evidence",
        "support_route_deployable",
        "deployment_blocker",
        "runtime_closure_state",
        "current_live_structure_bucket",
        "current_live_structure_bucket_rows",
        "minimum_support_rows",
        "current_live_structure_bucket_gap_to_minimum",
        "allowed_layers",
        "signal",
        "execution_guardrail_reason",
        "release_ready",
        "current_streak",
        "recent_window",
        "current_recent_window_win_rate",
        "current_recent_window_wins",
        "required_recent_window_wins",
        "additional_recent_window_wins_needed",
    ]
    context = {key: probe.get(key) for key in keys if key in probe}
    if isinstance(context.get("recent_window"), dict):
        context["recent_window"] = context["recent_window"].get("window_size")
    blocker_details = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}
    release_condition = blocker_details.get("release_condition") if isinstance(blocker_details.get("release_condition"), dict) else {}
    if not release_condition and isinstance(probe.get("release_condition"), dict):
        release_condition = probe.get("release_condition")
    if not release_condition:
        release_condition = _load_circuit_breaker_release_condition()
    recent_window = blocker_details.get("recent_window") if isinstance(blocker_details.get("recent_window"), dict) else {}
    if not recent_window and isinstance(probe.get("recent_window"), dict):
        recent_window = probe.get("recent_window")

    def _first_present(*values):
        for value in values:
            if value is not None:
                return value
        return None

    if release_condition:
        context["release_condition"] = release_condition
    release_fallbacks = {
        "release_ready": _first_present(release_condition.get("release_ready"), blocker_details.get("release_ready")),
        "current_streak": _first_present(release_condition.get("current_streak"), blocker_details.get("streak"), probe.get("streak")),
        "recent_window": _first_present(release_condition.get("recent_window"), recent_window.get("window_size"), blocker_details.get("window_size"), probe.get("window_size")),
        "current_recent_window_win_rate": _first_present(release_condition.get("current_recent_window_win_rate"), recent_window.get("win_rate"), blocker_details.get("recent_window_win_rate"), probe.get("recent_window_win_rate")),
        "current_recent_window_wins": _first_present(release_condition.get("current_recent_window_wins"), recent_window.get("wins"), blocker_details.get("recent_window_wins"), probe.get("recent_window_wins")),
        "required_recent_window_wins": _first_present(release_condition.get("required_recent_window_wins"), blocker_details.get("required_recent_window_wins"), probe.get("required_recent_window_wins")),
        "additional_recent_window_wins_needed": _first_present(release_condition.get("additional_recent_window_wins_needed"), blocker_details.get("additional_recent_window_wins_needed"), probe.get("additional_recent_window_wins_needed")),
    }
    for context_key, value in release_fallbacks.items():
        if context.get(context_key) is None and value is not None:
            context[context_key] = value
    top_level_support_progress = probe.get("support_progress") if isinstance(probe.get("support_progress"), dict) else {}
    blocker_support_progress = blocker_details.get("support_progress") if isinstance(blocker_details.get("support_progress"), dict) else {}
    # Merge instead of choosing one source: live probes often expose current row
    # counts at top level while detailed progress status/reason lives under
    # deployment_blocker_details.support_progress.  Top-level values win for
    # overlapping current-count fields because they reflect the latest probe.
    support_progress = {**blocker_support_progress, **top_level_support_progress}
    fallback_map = {
        "current_live_structure_bucket_rows": "current_rows",
        "minimum_support_rows": "minimum_support_rows",
        "current_live_structure_bucket_gap_to_minimum": "gap_to_minimum",
    }
    for context_key, progress_key in fallback_map.items():
        if context.get(context_key) is None and support_progress.get(progress_key) is not None:
            context[context_key] = support_progress.get(progress_key)
    progress_field_map = {
        "support_progress_status": "status",
        "support_progress_reason": "reason",
        "support_progress_regression_basis": "regression_basis",
        "support_progress_stagnant_run_count": "stagnant_run_count",
        "support_progress_stalled_support_accumulation": "stalled_support_accumulation",
        "support_progress_escalate_to_blocker": "escalate_to_blocker",
        "support_delta_vs_previous": "delta_vs_previous",
        "support_previous_rows": "previous_rows",
        "support_rows_needed": "gap_to_minimum",
    }
    for context_key, progress_key in progress_field_map.items():
        if context.get(context_key) is None and support_progress.get(progress_key) is not None:
            context[context_key] = support_progress.get(progress_key)
    # Keep legacy top-level names used by older Strategy Lab/docs readers while
    # also exposing the namespaced support_progress_* row contract.
    alias_field_map = {
        "stagnant_run_count": "support_progress_stagnant_run_count",
        "stalled_support_accumulation": "support_progress_stalled_support_accumulation",
        "escalate_to_blocker": "support_progress_escalate_to_blocker",
    }
    for alias_key, context_key in alias_field_map.items():
        if context.get(alias_key) is None and context.get(context_key) is not None:
            context[alias_key] = context.get(context_key)
    probe_generated_at = probe.get("generated_at") or probe.get("feature_timestamp")
    if probe_generated_at:
        context["source_live_probe_generated_at"] = probe_generated_at
    context["live_truth_source_artifact"] = str(probe_path)
    if refresh_status is not None:
        context["support_context_refresh"] = refresh_status
    context.setdefault("support_route_verdict", "not_evaluated")
    context.setdefault("deployment_blocker", None)
    freshness = live_probe_freshness_fields(probe_generated_at)
    if freshness.get("deployment_blocking"):
        return _stale_live_support_context(context, freshness)
    context["support_context_status"] = "fresh_live_probe_overlay"
    context["support_context_freshness"] = freshness
    context["live_truth_freshness"] = freshness
    context["live_truth_overlay_applied"] = True
    return context


TOP_LEVEL_LIVE_GATE_SUMMARY_KEYS = (
    "support_route_verdict",
    "support_governance_route",
    "support_governance_reference_evidence",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "allowed_layers",
    "signal",
    "execution_guardrail_reason",
    "release_condition",
    "release_ready",
    "current_streak",
    "recent_window",
    "current_recent_window_win_rate",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "support_progress_status",
    "support_progress_reason",
    "support_progress_regression_basis",
    "support_progress_stagnant_run_count",
    "support_progress_stalled_support_accumulation",
    "support_progress_escalate_to_blocker",
    "stagnant_run_count",
    "stalled_support_accumulation",
    "escalate_to_blocker",
    "support_delta_vs_previous",
    "support_previous_rows",
    "support_rows_needed",
    "source_live_probe_generated_at",
    "live_truth_source_artifact",
    "support_context_status",
    "support_context_freshness",
    "support_context_refresh",
    "live_truth_freshness",
    "live_truth_overlay_applied",
    "live_truth_overlay_blocker",
    "stale_support_context_reference",
)


RELEASE_CONDITION_SCALAR_KEYS = {
    "release_ready",
    "current_streak",
    "recent_window",
    "current_recent_window_win_rate",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
}


def apply_top_level_live_gate_summary(result: dict, support_context: dict | None) -> dict:
    """Expose live guardrail/release math at artifact top level for cron/doc consumers.

    Rows already carry these fields and the full context stays nested under
    ``support_context``.  The top-level projection prevents lightweight artifact
    readers from reporting ``None`` for the canonical deployment blocker or
    circuit-breaker release counters when they intentionally avoid parsing every
    row.
    """
    context = dict(support_context or {})
    result["support_context"] = context
    release_condition = context.get("release_condition") if isinstance(context.get("release_condition"), dict) else {}
    live_gate_summary: dict[str, Any] = {}
    for key in TOP_LEVEL_LIVE_GATE_SUMMARY_KEYS:
        value = context.get(key)
        if value is None and key in RELEASE_CONDITION_SCALAR_KEYS:
            value = release_condition.get(key)
        if value is not None:
            result[key] = value
            live_gate_summary[key] = value
    if release_condition:
        result["release_condition"] = release_condition
        live_gate_summary["release_condition"] = release_condition
    if live_gate_summary:
        result["live_gate_summary"] = live_gate_summary
    else:
        result.pop("live_gate_summary", None)
    return result


def _coalesce_regime_label(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize merge/asof suffix variants into one lower-case regime_label column."""
    df = df.copy()
    candidates = [col for col in ["regime_label", "regime_label_y", "regime_label_x"] if col in df.columns]
    if not candidates:
        df["regime_label"] = "unknown"
        return df
    regime = df[candidates[0]]
    for col in candidates[1:]:
        regime = regime.combine_first(df[col])
    df["regime_label"] = regime.fillna("unknown").astype(str).str.lower()
    for col in ["regime_label_x", "regime_label_y"]:
        if col in df.columns:
            df = df.drop(columns=[col])
    return df


def load_frame() -> tuple[pd.DataFrame, str]:
    df = load_model_leaderboard_frame(DB_PATH)
    if df.empty:
        raise RuntimeError("empty leaderboard frame")

    conn = sqlite3.connect(DB_PATH)
    regime_df = pd.read_sql_query(
        "SELECT timestamp, COALESCE(regime_label, 'unknown') as regime_label FROM features_normalized",
        conn,
    )
    conn.close()
    regime_df["timestamp"] = pd.to_datetime(regime_df["timestamp"], format="mixed", utc=False)
    regime_df = regime_df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=False)
    df = df.sort_values("timestamp")
    df = pd.merge_asof(df, regime_df, on="timestamp", direction="nearest", tolerance=pd.Timedelta("10min"))
    df = _coalesce_regime_label(df)

    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in df.columns else "label_spot_long_win"
    df = df.dropna(subset=[target_col]).copy()
    df[target_col] = df[target_col].fillna(0).astype(int)
    return df, target_col


def summarize_subset(sub: pd.DataFrame, target_col: str) -> dict:
    wins = int(sub[target_col].sum())
    chronological = sub.sort_values("timestamp") if "timestamp" in sub.columns else sub
    pnl = _pnl_series_for_subset(chronological)
    oos_roi = _round_or_none(float(pnl.sum())) if not pnl.empty else None
    profit_factor = _safe_profit_factor(pnl)
    max_drawdown = _max_drawdown_from_pnl(pnl)
    regime_mix = {}
    if "regime_label" in sub.columns:
        regime_mix = {k: int(v) for k, v in sub["regime_label"].value_counts().to_dict().items()}
    return {
        "n": int(len(sub)),
        "trade_count": int(len(sub)),
        "win_rate": round(float(sub[target_col].mean()), 4) if len(sub) else None,
        "avg_score": round(float(sub["score"].mean()), 4) if len(sub) else None,
        "oos_roi": oos_roi,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "wins": wins,
        "losses": int(len(sub) - wins),
        "regime_mix": regime_mix,
    }


def _support_route_explicit_is_deployable(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "deployable", "supported"}
    return bool(value)


def _support_route_is_deployable(support_context: dict) -> bool:
    route = str(support_context.get("support_route_verdict") or support_context.get("support_route") or "").strip().lower()
    explicit = support_context.get("support_route_deployable")
    if explicit is not None:
        return _support_route_explicit_is_deployable(explicit)
    return route in {"deployable", "exact_bucket_supported", "support_route_deployable"}


def _deployment_blocker_active(support_context: dict) -> bool:
    blocker = support_context.get("deployment_blocker")
    if blocker is None:
        blocker = support_context.get("runtime_closure_state")
    text = str(blocker or "").strip().lower()
    return text not in {"", "none", "no_deployment_blocker", "breaker_clear", "support_closed_trade_floor_hold_only"}


def _explicit_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "ready", "release_ready"}:
            return True
        if text in {"0", "false", "no", "n", "not_ready", "blocked"}:
            return False
    return None


def _release_condition_not_ready(support_context: dict) -> bool:
    release_ready = _explicit_bool(support_context.get("release_ready"))
    if release_ready is False:
        return True
    release_condition = support_context.get("release_condition")
    if isinstance(release_condition, dict):
        release_ready = _explicit_bool(release_condition.get("release_ready"))
        if release_ready is False:
            return True
    return False


def _gate_failures(metrics: dict, worst_fold: Optional[float], support_context: dict, gates: dict) -> list[str]:
    failures: list[str] = []
    trade_count = int(metrics.get("trade_count", metrics.get("n", 0)) or 0)
    win_rate = metrics.get("win_rate")
    max_drawdown = metrics.get("max_drawdown")
    profit_factor = metrics.get("profit_factor")

    if trade_count < int(gates.get("min_trades", 50)):
        failures.append("min_trades_not_met")
    if win_rate is None or float(win_rate) < float(gates.get("min_win_rate", 0.60)):
        failures.append("min_win_rate_not_met")
    if max_drawdown is None or float(max_drawdown) > float(gates.get("max_drawdown", 0.08)):
        failures.append("max_drawdown_too_high")
    if profit_factor is None or float(profit_factor) < float(gates.get("min_profit_factor", 1.50)):
        failures.append("profit_factor_too_low")
    if worst_fold is None:
        failures.append("worst_fold_missing")
    elif str(gates.get("worst_fold", "")).startswith("non_negative") and float(worst_fold) < 0:
        failures.append("worst_fold_negative")
    if not _support_route_is_deployable(support_context):
        failures.append("support_route_not_deployable")
    if _deployment_blocker_active(support_context):
        failures.append("deployment_blocker_active")
    if _release_condition_not_ready(support_context):
        failures.append("breaker_release_not_ready")
    return failures


def _fold_slice_metrics(report: dict, top_key: str, regime: str) -> list[dict]:
    metrics: list[dict] = []
    for fold in report.get("folds", []) or []:
        if regime == "all":
            item = (fold.get("top_slices") or {}).get(top_key)
        else:
            item = ((fold.get("regime_top_slices") or {}).get(regime) or {}).get(top_key)
        if isinstance(item, dict):
            metrics.append(item)
    return metrics


def _worst_fold_roi(report: dict, top_key: str, regime: str) -> Optional[float]:
    values = [
        float(item["oos_roi"])
        for item in _fold_slice_metrics(report, top_key, regime)
        if item.get("oos_roi") is not None
    ]
    if not values:
        return None
    return round(min(values), 4)


def build_high_conviction_oos_matrix_rows(
    model_name: str,
    report: dict,
    support_context: Optional[dict] = None,
    feature_profile: str = "current_full",
    gates: Optional[dict] = None,
    release_policy: Optional[dict] = None,
) -> list[dict]:
    """Flatten aggregate/fold top-k evidence into strict and personal-release lanes."""
    support_context = dict(support_context or {"support_route_verdict": "not_evaluated"})
    gates = dict(gates or MINIMUM_DEPLOYMENT_GATES)
    release_policy = dict(release_policy or {})
    rows: list[dict] = []

    def _append_row(regime: str, top_key: str, metrics: dict) -> None:
        worst_fold = _worst_fold_roi(report, top_key, regime)
        failures = _gate_failures(metrics, worst_fold, support_context, gates)
        live_gate_failures = [failure for failure in failures if failure in LIVE_GUARDRAIL_FAILURES]
        model_gate_failures = [failure for failure in failures if failure not in LIVE_GUARDRAIL_FAILURES]
        oos_gate_passed = not model_gate_failures
        blocked_only_by_live_guardrails = bool(failures) and oos_gate_passed and bool(live_gate_failures)
        release_decision = evaluate_candidate_release(
            {
                "model": model_name,
                "feature_profile": feature_profile,
                "regime": regime,
                "top_k": top_key,
                "trade_count": int(metrics.get("trade_count", metrics.get("n", 0)) or 0),
                "wins": int(metrics.get("wins", 0) or 0),
                "losses": int(metrics.get("losses", 0) or 0),
                "win_rate": metrics.get("win_rate"),
                "oos_roi": metrics.get("oos_roi"),
                "profit_factor": metrics.get("profit_factor"),
                "max_drawdown": metrics.get("max_drawdown"),
                "worst_fold": worst_fold,
            },
            strict_failures=failures,
            support_context=support_context,
            policy=release_policy,
        )
        owner_release_ready = bool(
            release_decision.get("owner_approved")
            and release_decision.get("strategy_release_ready")
        )
        deployable_verdict = "deployable" if not failures else "not_deployable"
        if owner_release_ready:
            # Strategy release and live venue deployability are intentionally separate.
            # The owner-approved row is usable in the personal strategy lane, while
            # live execution still depends on exact model binding and technical gates.
            deployable_verdict = "not_live_deployable"
            deployment_candidate_tier = "owner_approved_personal_use"
        elif deployable_verdict == "deployable":
            deployment_candidate_tier = "deployable"
        elif blocked_only_by_live_guardrails:
            deployment_candidate_tier = "runtime_blocked_oos_pass"
        else:
            deployment_candidate_tier = "research_oos_gate_failed"
        rows.append(
            {
                "model": model_name,
                "feature_profile": feature_profile,
                "regime": regime,
                "top_k": top_key,
                "oos_roi": _round_or_none(metrics.get("oos_roi")),
                "win_rate": _round_or_none(metrics.get("win_rate")),
                "profit_factor": _round_or_none(metrics.get("profit_factor")),
                "max_drawdown": _round_or_none(metrics.get("max_drawdown")),
                "worst_fold": _round_or_none(worst_fold),
                "trade_count": int(metrics.get("trade_count", metrics.get("n", 0)) or 0),
                "avg_score": _round_or_none(metrics.get("avg_score")),
                "wins": int(metrics.get("wins", 0) or 0),
                "losses": int(metrics.get("losses", 0) or 0),
                "regime_mix": dict(metrics.get("regime_mix") or {}),
                "support_route": support_context.get("support_route_verdict", "not_evaluated"),
                "support_governance_route": support_context.get("support_governance_route"),
                "support_route_deployable": support_context.get("support_route_deployable"),
                "deployment_blocker": support_context.get("deployment_blocker"),
                "runtime_closure_state": support_context.get("runtime_closure_state"),
                "current_live_structure_bucket": support_context.get("current_live_structure_bucket"),
                "current_live_structure_bucket_rows": support_context.get("current_live_structure_bucket_rows"),
                "minimum_support_rows": support_context.get("minimum_support_rows"),
                "current_live_structure_bucket_gap_to_minimum": support_context.get("current_live_structure_bucket_gap_to_minimum"),
                "allowed_layers": support_context.get("allowed_layers"),
                "signal": support_context.get("signal"),
                "execution_guardrail_reason": support_context.get("execution_guardrail_reason"),
                "release_condition": support_context.get("release_condition"),
                "release_ready": support_context.get("release_ready"),
                "current_streak": support_context.get("current_streak"),
                "recent_window": support_context.get("recent_window"),
                "current_recent_window_win_rate": support_context.get("current_recent_window_win_rate"),
                "current_recent_window_wins": support_context.get("current_recent_window_wins"),
                "required_recent_window_wins": support_context.get("required_recent_window_wins"),
                "additional_recent_window_wins_needed": support_context.get("additional_recent_window_wins_needed"),
                "support_progress_status": support_context.get("support_progress_status"),
                "support_progress_reason": support_context.get("support_progress_reason"),
                "support_progress_regression_basis": support_context.get("support_progress_regression_basis"),
                "support_progress_stagnant_run_count": support_context.get("support_progress_stagnant_run_count"),
                "support_progress_stalled_support_accumulation": support_context.get("support_progress_stalled_support_accumulation"),
                "support_progress_escalate_to_blocker": support_context.get("support_progress_escalate_to_blocker"),
                "stagnant_run_count": support_context.get("stagnant_run_count"),
                "stalled_support_accumulation": support_context.get("stalled_support_accumulation"),
                "escalate_to_blocker": support_context.get("escalate_to_blocker"),
                "support_delta_vs_previous": support_context.get("support_delta_vs_previous"),
                "support_previous_rows": support_context.get("support_previous_rows"),
                "support_rows_needed": support_context.get("support_rows_needed"),
                "source_live_probe_generated_at": support_context.get("source_live_probe_generated_at"),
                "live_truth_source_artifact": support_context.get("live_truth_source_artifact"),
                "support_context_status": support_context.get("support_context_status"),
                "support_context_freshness": support_context.get("support_context_freshness"),
                "support_context_refresh": support_context.get("support_context_refresh"),
                "live_truth_freshness": support_context.get("live_truth_freshness"),
                "live_truth_overlay_applied": support_context.get("live_truth_overlay_applied"),
                "live_truth_overlay_blocker": support_context.get("live_truth_overlay_blocker"),
                "stale_support_context_reference": support_context.get("stale_support_context_reference"),
                "minimum_deployment_gates": gates,
                **release_decision,
                "deployable_verdict": deployable_verdict,
                "deployment_candidate_tier": deployment_candidate_tier,
                "gate_failures": failures,
                "model_gate_failures": model_gate_failures,
                "live_gate_failures": live_gate_failures,
                "oos_gate_passed": oos_gate_passed,
                "blocked_only_by_live_guardrails": blocked_only_by_live_guardrails,
            }
        )

    for top_key, metrics in (report.get("aggregate_top_slices") or {}).items():
        _append_row("all", top_key, metrics)
    for regime, slices in (report.get("aggregate_regime_top_slices") or {}).items():
        for top_key, metrics in (slices or {}).items():
            _append_row(str(regime), top_key, metrics)
    return rows


HIGH_CONVICTION_CANDIDATE_SUMMARY_KEYS = (
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
    "deployable_verdict",
    "deployment_candidate_tier",
    "gate_failures",
    "model_gate_failures",
    "live_gate_failures",
    "oos_gate_passed",
    "blocked_only_by_live_guardrails",
    "owner_approved",
    "owner_approval_decision_id",
    "owner_approved_by",
    "strategy_release_ready",
    "strategy_release_status",
    "statistical_gate_policy",
    "statistical_gate_blocking",
    "statistical_warnings",
    "technical_execution_blockers",
    "hard_gate_failures",
    "support_evidence_ratio",
    "model_evidence_ratio",
    "evidence_score",
    "evidence_tier",
    "recommended_max_layers",
    "technical_execution_gates_required",
    "support_route",
    "support_governance_route",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "allowed_layers",
    "signal",
    "execution_guardrail_reason",
    "release_condition",
    "release_ready",
    "current_streak",
    "recent_window",
    "current_recent_window_win_rate",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "support_progress_status",
    "support_progress_reason",
    "support_progress_regression_basis",
    "support_progress_stagnant_run_count",
    "support_progress_stalled_support_accumulation",
    "support_progress_escalate_to_blocker",
    "stagnant_run_count",
    "stalled_support_accumulation",
    "escalate_to_blocker",
    "support_delta_vs_previous",
    "support_previous_rows",
    "support_rows_needed",
    "source_live_probe_generated_at",
    "live_truth_source_artifact",
    "support_context_status",
    "support_context_freshness",
    "live_truth_freshness",
    "live_truth_overlay_applied",
    "live_truth_overlay_blocker",
    "stale_support_context_reference",
)


def _row_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _topk_row_gate_parts(row: dict) -> tuple[list[str], list[str], list[str], bool, bool, str]:
    gate_failures = _row_string_list(row.get("gate_failures"))
    model_gate_failures = _row_string_list(row.get("model_gate_failures"))
    live_gate_failures = _row_string_list(row.get("live_gate_failures"))
    if not model_gate_failures and not live_gate_failures:
        model_gate_failures = [item for item in gate_failures if item not in LIVE_GUARDRAIL_FAILURES]
        live_gate_failures = [item for item in gate_failures if item in LIVE_GUARDRAIL_FAILURES]
    explicit_oos = row.get("oos_gate_passed")
    oos_gate_passed = bool(explicit_oos) if explicit_oos is not None else not model_gate_failures
    explicit_runtime_blocked = row.get("blocked_only_by_live_guardrails")
    blocked_only_by_live_guardrails = (
        bool(explicit_runtime_blocked)
        if explicit_runtime_blocked is not None
        else bool(gate_failures) and oos_gate_passed and bool(live_gate_failures) and not model_gate_failures
    )
    deployment_candidate_tier = str(row.get("deployment_candidate_tier") or "")
    if not deployment_candidate_tier:
        if str(row.get("deployable_verdict") or "") == "deployable":
            deployment_candidate_tier = "deployable"
        elif blocked_only_by_live_guardrails:
            deployment_candidate_tier = "runtime_blocked_oos_pass"
        else:
            deployment_candidate_tier = "research_oos_gate_failed"
    return (
        gate_failures,
        model_gate_failures,
        live_gate_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        deployment_candidate_tier,
    )


def _sort_float(value: Any, default: float) -> float:
    parsed = _round_or_none(value, digits=8)
    return default if parsed is None else float(parsed)


def _risk_first_candidate_sort_key(row: dict) -> tuple:
    (
        gate_failures,
        model_gate_failures,
        _live_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        _tier,
    ) = _topk_row_gate_parts(row)
    return (
        bool(row.get("owner_approved") and row.get("strategy_release_ready")),
        str(row.get("deployable_verdict") or "") == "deployable",
        blocked_only_by_live_guardrails,
        oos_gate_passed,
        -len(model_gate_failures),
        -len(gate_failures),
        -_sort_float(row.get("max_drawdown"), 999.0),
        _sort_float(row.get("worst_fold"), -999.0),
        _sort_float(row.get("oos_roi"), -999.0),
        _sort_float(row.get("win_rate"), -999.0),
        _sort_float(row.get("profit_factor"), -999.0),
        _sort_float(row.get("trade_count"), -999.0),
    )


def _compact_high_conviction_candidate_row(row: dict) -> dict[str, Any]:
    if not isinstance(row, dict) or not row:
        return {}
    (
        gate_failures,
        model_gate_failures,
        live_gate_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        deployment_candidate_tier,
    ) = _topk_row_gate_parts(row)
    compact = {key: row.get(key) for key in HIGH_CONVICTION_CANDIDATE_SUMMARY_KEYS if row.get(key) is not None}
    compact.setdefault("gate_failures", gate_failures)
    compact.setdefault("model_gate_failures", model_gate_failures)
    compact.setdefault("live_gate_failures", live_gate_failures)
    compact.setdefault("oos_gate_passed", oos_gate_passed)
    compact.setdefault("blocked_only_by_live_guardrails", blocked_only_by_live_guardrails)
    compact.setdefault("deployment_candidate_tier", deployment_candidate_tier)
    compact.setdefault("deployable_verdict", row.get("deployable_verdict") or "not_deployable")
    return compact


def apply_top_level_candidate_summary(result: dict, *, limit: int = 6) -> dict:
    """Keep Top-K artifacts self-contained about nearest deployable/runtime-blocked rows.

    ``rows`` already contain the full matrix. Current-state docs and compact cron
    extractors also need a small, fail-closed pointer to the best candidate: a row
    that is fully deployable if one exists, otherwise an OOS-passing row blocked
    only by live guardrails. If none exists, fall back to the best ranked research
    row so operators still see why it is not deployable.
    """
    rows = [row for row in result.get("rows", []) if isinstance(row, dict)]
    if not rows:
        result.pop("nearest_deployable_rows", None)
        result.pop("nearest_deployable_candidate", None)
        result.pop("best_not_deployable", None)
        result.pop("highest_roi_not_deployable", None)
        return result

    ranked_rows = sorted(rows, key=_risk_first_candidate_sort_key, reverse=True)
    nearest_rows = [
        row
        for row in ranked_rows
        if (
            bool(row.get("owner_approved") and row.get("strategy_release_ready"))
            or str(row.get("deployable_verdict") or "") == "deployable"
            or _topk_row_gate_parts(row)[4]
        )
    ]
    if not nearest_rows:
        nearest_rows = ranked_rows[:1]

    highest_roi_not_deployable = max(
        [row for row in rows if str(row.get("deployable_verdict") or "") != "deployable"] or rows,
        key=lambda row: _sort_float(row.get("oos_roi"), -999.0),
    )

    compact_nearest_rows = [_compact_high_conviction_candidate_row(row) for row in nearest_rows[:limit]]
    compact_nearest_rows = [row for row in compact_nearest_rows if row]
    if compact_nearest_rows:
        result["nearest_deployable_rows"] = compact_nearest_rows
        result["nearest_deployable_candidate"] = compact_nearest_rows[0]
        result["best_not_deployable"] = compact_nearest_rows[0]
    else:
        result.pop("nearest_deployable_rows", None)
        result.pop("nearest_deployable_candidate", None)
        result.pop("best_not_deployable", None)
    highest_compact = _compact_high_conviction_candidate_row(highest_roi_not_deployable)
    if highest_compact:
        result["highest_roi_not_deployable"] = highest_compact
    else:
        result.pop("highest_roi_not_deployable", None)
    return result


def evaluate_model(data: pd.DataFrame, target_col: str, model_name: str) -> dict | None:
    lb = ModelLeaderboard(data, target_col=target_col)
    splits = lb._get_walk_forward_splits()
    feature_cols = [c for c in data.columns if c.startswith("feat_")]

    fold_reports = []
    all_test_rows = []
    for i, (ts, te, test_s, test_e) in enumerate(splits[:4]):
        train_df = data[(data["timestamp"] >= ts) & (data["timestamp"] < te)].copy()
        test_df = data[(data["timestamp"] >= test_s) & (data["timestamp"] < test_e)].copy()
        if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
            continue

        if model_name == "rule_baseline":
            score = (1.0 - (test_df["feat_4h_bias50"].fillna(0).values + 5) / 15.0).clip(0.0, 1.0)
        else:
            model = lb._train_model(
                train_df[feature_cols].fillna(0).values,
                train_df[target_col].values,
                model_name,
            )
            if model is None:
                return None
            score = lb._get_confidence(model, test_df[feature_cols].fillna(0).values, model_name)

        scored_cols = [
            col
            for col in [
                "timestamp",
                "regime_label",
                target_col,
                "close_price",
                "simulated_pyramid_pnl",
                "future_return_pct",
            ]
            if col in test_df.columns
        ]
        scored = test_df[scored_cols].copy()
        scored["score"] = score
        scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
        scored["fold"] = i
        all_test_rows.append(scored)

        top_slices = {}
        for pct in TOP_PCTS:
            n = max(1, int(len(scored) * pct))
            top_slices[f"top_{int(pct * 100)}pct"] = summarize_subset(scored.iloc[:n], target_col)

        regime_slices = {}
        for regime in sorted(scored["regime_label"].unique()):
            reg_df = scored[scored["regime_label"] == regime].reset_index(drop=True)
            if len(reg_df) < 20:
                continue
            regime_slices[regime] = {}
            for pct in TOP_PCTS:
                n = max(1, int(len(reg_df) * pct))
                regime_slices[regime][f"top_{int(pct * 100)}pct"] = summarize_subset(reg_df.iloc[:n], target_col)

        fold_reports.append(
            {
                "fold": i,
                "train_start": str(train_df["timestamp"].min()),
                "train_end": str(train_df["timestamp"].max()),
                "test_start": str(test_df["timestamp"].min()),
                "test_end": str(test_df["timestamp"].max()),
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "top_slices": top_slices,
                "regime_top_slices": regime_slices,
            }
        )

    if not fold_reports:
        return None

    combined = pd.concat(all_test_rows, ignore_index=True).sort_values("score", ascending=False).reset_index(drop=True)
    aggregate_top = {}
    for pct in TOP_PCTS:
        n = max(1, int(len(combined) * pct))
        aggregate_top[f"top_{int(pct * 100)}pct"] = summarize_subset(combined.iloc[:n], target_col)

    aggregate_regime = {}
    for regime in sorted(combined["regime_label"].unique()):
        reg_df = combined[combined["regime_label"] == regime].reset_index(drop=True)
        if len(reg_df) < 20:
            continue
        aggregate_regime[regime] = {}
        for pct in TOP_PCTS:
            n = max(1, int(len(reg_df) * pct))
            aggregate_regime[regime][f"top_{int(pct * 100)}pct"] = summarize_subset(reg_df.iloc[:n], target_col)

    return {
        "folds": fold_reports,
        "aggregate_top_slices": aggregate_top,
        "aggregate_regime_top_slices": aggregate_regime,
        "overall_oos_base_rate": round(float(combined[target_col].mean()), 4),
        "total_oos_rows": int(len(combined)),
    }


def main() -> None:
    data, target_col = load_frame()
    support_context = _load_support_context(auto_refresh=True)
    release_policy = resolve_personal_release_policy(load_config())
    generated_at = datetime.now(timezone.utc).isoformat()
    result = {
        "generated_at": generated_at,
        **artifact_freshness_fields(generated_at),
        "target_col": target_col,
        "samples": int(len(data)),
        "top_k_grid": [f"top_{int(pct * 100)}pct" for pct in TOP_PCTS],
        "minimum_deployment_gates": MINIMUM_DEPLOYMENT_GATES,
        "strategy_release_policy": release_policy,
        "support_context": support_context,
        "artifact": str(OUT_PATH),
        "rows": [],
        "models": {},
    }
    for model_name in MODELS:
        print(f"Evaluating {model_name}...")
        report = evaluate_model(data, target_col, model_name)
        if report is not None:
            result["models"][model_name] = report
            result["rows"].extend(
                build_high_conviction_oos_matrix_rows(
                    model_name,
                    report,
                    support_context=support_context,
                    release_policy=release_policy,
                )
            )
    result["row_count"] = len(result["rows"])
    result["deployable_rows"] = sum(1 for row in result["rows"] if row.get("deployable_verdict") == "deployable")
    result["owner_approved_rows"] = sum(1 for row in result["rows"] if row.get("strategy_release_status") == "owner_approved_personal_use")
    result["strategy_release_ready_rows"] = sum(1 for row in result["rows"] if row.get("strategy_release_ready"))
    result["risk_qualified_rows"] = sum(1 for row in result["rows"] if row.get("oos_gate_passed"))
    result["runtime_blocked_candidate_rows"] = sum(
        1 for row in result["rows"] if row.get("blocked_only_by_live_guardrails")
    )
    apply_top_level_live_gate_summary(result, support_context)
    apply_top_level_candidate_summary(result)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    LEGACY_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEGACY_OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
