"""
策略引擎 — Rule-based + ML model backtesting for Poly-Trader

支援三種模式：
  1. rule_based   — 純規則（bias50、nose、pulse 條件 + 金字塔 + SL/TP）
  2. ml_model     — 用 ML 模型信心分數作為交易信號
  3. hybrid       — 4H 規則過濾 + ML 模型入場

策略定義為 JSON，存在 ~/.hermes/poly-trader/strategies/
"""
import json
import os
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

from model.q35_bias50_calibration import compute_piecewise_bias50_score

STRATEGIES_DIR = Path(os.path.expanduser("~/.hermes/poly-trader/strategies"))
STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_SCHEMA_VERSION = 2
INTERNAL_STRATEGY_PREFIXES = ("tmp_", "debug_", "scratch_", "auto_leaderboard_")
INTERNAL_STRATEGY_NAMES = {"unnamed", "unnamed_strategy"}
AUTO_STRATEGY_NAME_PREFIX = "Auto Leaderboard · "
MANUAL_COPY_STRATEGY_PREFIX = "Manual Copy · "


@dataclass
class BacktestResult:
    """單次回測結果"""
    roi: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_losses: int = 0
    trades: List[Dict] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)


def _strategy_slug(name: str) -> str:
    text = (name or "unnamed_strategy").strip().lower()
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._")
    return text or "unnamed_strategy"


def _strategy_path(name: str) -> Path:
    return STRATEGIES_DIR / f"{_strategy_slug(name)}.json"


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_internal_strategy(name: str, slug: Optional[str] = None) -> bool:
    normalized = (slug or _strategy_slug(name)).lower()
    return normalized in INTERNAL_STRATEGY_NAMES or any(normalized.startswith(prefix) for prefix in INTERNAL_STRATEGY_PREFIXES)


def _is_auto_leaderboard_strategy(name: str, slug: Optional[str] = None) -> bool:
    raw_name = str(name or "").strip()
    normalized = (slug or _strategy_slug(raw_name)).lower()
    return raw_name.startswith(AUTO_STRATEGY_NAME_PREFIX) or normalized.startswith("auto_leaderboard_")


def derive_editable_strategy_name(name: str) -> str:
    raw_name = str(name or "").strip() or "My Strategy"
    if raw_name.startswith(MANUAL_COPY_STRATEGY_PREFIX):
        return raw_name
    if raw_name.startswith(AUTO_STRATEGY_NAME_PREFIX):
        return f"{MANUAL_COPY_STRATEGY_PREFIX}{raw_name[len(AUTO_STRATEGY_NAME_PREFIX):].strip()}"
    return raw_name


def strategy_definition_signature(strategy_def: Optional[Dict[str, Any]]) -> str:
    sanitized = _sanitize_definition(strategy_def)
    return json.dumps(sanitized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sanitize_definition(strategy_def: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    strategy_def = strategy_def or {}
    params = strategy_def.get("params") if isinstance(strategy_def, dict) else {}
    if not isinstance(params, dict):
        params = {}
    return {
        "type": (strategy_def.get("type") if isinstance(strategy_def, dict) else None) or "rule_based",
        "params": params,
    }


RESULT_FLOAT_FIELDS = (
    "roi", "win_rate", "max_drawdown", "profit_factor", "total_pnl",
    "avg_win", "avg_loss",
    "avg_expected_win_rate", "avg_expected_pyramid_pnl", "avg_expected_pyramid_quality",
    "avg_expected_drawdown_penalty", "avg_expected_time_underwater", "avg_decision_quality_score",
)
RESULT_INT_FIELDS = ("total_trades", "wins", "losses", "max_consecutive_losses")

MODEL_SUMMARY_MAP = {
    "rule_baseline": "rule_baseline：不訓練 ML，直接用 4H Bias50 的深跌程度當作進場信心，適合驗證純規則框架。",
    "logistic_regression": "logistic_regression：線性分類器，容易解讀權重，適合當穩定基線模型。",
    "xgboost": "xgboost：非線性樹模型，能學到 4H 結構 × 1m 感官的交互作用，但也最容易過擬合。",
    "lightgbm": "lightgbm：梯度提升樹，訓練速度快，適合大量 tabular 特徵。",
    "catboost": "catboost：對雜訊與類別型特徵較穩定的 boosting 模型。",
    "random_forest": "random_forest：袋裝樹模型，穩定但通常比 boosting 保守。",
    "mlp": "mlp：多層感知器，能學非線性關係，但需要較乾淨且充足的樣本。",
    "svm": "svm：邊界型分類器，適合中小樣本，但大樣本時較慢。",
    "ensemble": "ensemble：混合多個模型的平均投票，用來降低單模型偏差。",
}

CAPITAL_MODE_CLASSIC = "classic_pyramid"
CAPITAL_MODE_RESERVE = "reserve_90"

STRATEGY_SLEEVE_LIBRARY: Dict[str, Dict[str, Any]] = {
    "trend": {
        "label": "趨勢承接",
        "summary": "順著既有 4H 結構承接 pullback，維持中頻主線節奏。",
    },
    "pullback": {
        "label": "回調承接",
        "summary": "等待較深 pullback 再進場，優先服務 bull / chop 的再部署窗口。",
    },
    "rebound": {
        "label": "深跌回補",
        "summary": "只在極端 oversold / crash pocket 嘗試反身回補，屬於反轉型 sleeve。",
    },
    "selective": {
        "label": "高信念精選",
        "summary": "提高品質門檻與 top-k 篩選，只保留最強交易候選。",
    },
    "capital_defense": {
        "label": "資金防守",
        "summary": "用 10/90 後守或 reserve-style 配置，延後主資金部署。",
    },
    "turning_point_exit": {
        "label": "轉折出場",
        "summary": "以區域頂部 / 轉折點作為主要出場與節奏收斂模組。",
    },
    "storm_recovery": {
        "label": "風暴解套",
        "summary": "用更快落袋與解套釋放機制處理高波動倉位回收。",
    },
}


def _ordered_unique_strings(items: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _infer_primary_sleeve_key(name: str, definition: Dict[str, Any]) -> str:
    params = definition.get("params") if isinstance(definition, dict) else {}
    params = params if isinstance(params, dict) else {}
    entry = params.get("entry") if isinstance(params.get("entry"), dict) else {}

    name_text = str(name or "").lower()
    top_k_percent = _coerce_float(entry.get("top_k_percent")) or 0.0
    confidence_min = _coerce_float(entry.get("confidence_min")) or 0.0
    entry_quality_min = _coerce_float(entry.get("entry_quality_min")) or 0.0
    bias50_max = _coerce_float(entry.get("bias50_max"))
    layer2_bias_max = _coerce_float(entry.get("layer2_bias_max"))
    layer3_bias_max = _coerce_float(entry.get("layer3_bias_max"))

    if (
        top_k_percent > 0
        or confidence_min >= 0.70
        or entry_quality_min >= 0.68
        or any(keyword in name_text for keyword in ("高勝率", "高把握", "low freq", "selective"))
    ):
        return "selective"
    if (
        (bias50_max is not None and bias50_max <= -0.9)
        or (layer3_bias_max is not None and layer3_bias_max <= -4.8)
        or any(keyword in name_text for keyword in ("深跌", "回補", "rebound"))
    ):
        return "rebound"
    if (
        (bias50_max is not None and bias50_max <= -0.25)
        or (layer2_bias_max is not None and layer2_bias_max <= -2.0)
        or any(keyword in name_text for keyword in ("pullback", "平衡承接", "回調"))
    ):
        return "pullback"
    return "trend"


def _infer_strategy_sleeves(name: str, definition: Dict[str, Any]) -> List[Dict[str, Any]]:
    params = definition.get("params") if isinstance(definition, dict) else {}
    params = params if isinstance(params, dict) else {}
    capital_management = params.get("capital_management") if isinstance(params.get("capital_management"), dict) else {}
    turning_point = params.get("turning_point") if isinstance(params.get("turning_point"), dict) else {}
    storm_unwind = params.get("storm_unwind") if isinstance(params.get("storm_unwind"), dict) else {}
    editor_modules = params.get("editor_modules") if isinstance(params.get("editor_modules"), list) else []

    sleeve_keys = [_infer_primary_sleeve_key(name, definition)]
    if str(capital_management.get("mode") or CAPITAL_MODE_CLASSIC) == CAPITAL_MODE_RESERVE or any(str(v) == "reserve_90" for v in editor_modules):
        sleeve_keys.append("capital_defense")
    if bool(turning_point.get("enabled")) or any(str(v) == "turning_point" for v in editor_modules):
        sleeve_keys.append("turning_point_exit")
    if bool(storm_unwind.get("enabled")) or any(str(v) == "storm_unwind" for v in editor_modules):
        sleeve_keys.append("storm_recovery")

    ordered = _ordered_unique_strings(sleeve_keys)
    sleeves: List[Dict[str, Any]] = []
    for idx, key in enumerate(ordered):
        info = STRATEGY_SLEEVE_LIBRARY.get(key, {"label": key, "summary": ""})
        sleeves.append({
            "key": key,
            "label": info.get("label") or key,
            "summary": info.get("summary") or "",
            "role": "primary" if idx == 0 else "secondary",
        })
    return sleeves


def build_regime_aware_sleeve_routing(
    *,
    regime_label: Optional[str],
    regime_gate: Optional[str],
    structure_bucket: Optional[str] = None,
    allowed_layers: Optional[int] = None,
    entry_quality: Optional[float] = None,
    deployment_blocker: Optional[str] = None,
    execution_guardrail_reason: Optional[str] = None,
) -> Dict[str, Any]:
    regime = str(regime_label or "unknown").lower()
    gate = str(regime_gate or "unknown").upper()
    normalized_structure_bucket = str(structure_bucket) if structure_bucket is not None else None
    primary_sleeves = ["trend", "pullback", "rebound", "selective"]
    layers = max(int(allowed_layers or 0), 0)
    quality = None if entry_quality is None else float(entry_quality)
    blocker = str(deployment_blocker or "").strip()
    guardrail = str(execution_guardrail_reason or "").strip()
    global_blocker_reason = None
    if blocker:
        global_blocker_reason = blocker.replace("_", " ")
    elif guardrail:
        global_blocker_reason = guardrail.replace("_", " ")
    elif gate == "BLOCK" or layers <= 0:
        global_blocker_reason = "runtime gate currently blocks deployment"

    def _entry(key: str, active: bool, why: str) -> Dict[str, Any]:
        info = STRATEGY_SLEEVE_LIBRARY.get(key, {"label": key, "summary": ""})
        return {
            "key": key,
            "label": info.get("label") or key,
            "summary": info.get("summary") or "",
            "status": "active" if active else "inactive",
            "why": why,
        }

    active_entries: List[Dict[str, Any]] = []
    inactive_entries: List[Dict[str, Any]] = []

    if global_blocker_reason:
        blocker_text = f"目前 {global_blocker_reason}，先凍結所有 primary sleeves。"
        inactive_entries = [_entry(key, False, blocker_text) for key in primary_sleeves]
    else:
        routing_rules = {
            "trend": (
                regime == "bull" and gate == "ALLOW",
                f"目前 regime={regime} 且 gate={gate}，順勢承接 sleeve 保持 active。",
                f"目前 regime={regime} / gate={gate}，趨勢承接 sleeve 暫不啟用。",
            ),
            "pullback": (
                regime in {"bull", "chop"} and gate in {"ALLOW", "CAUTION"},
                f"目前 regime={regime}，pullback 承接仍屬有效部署 lane。",
                f"目前 regime={regime} 不適合 pullback 承接，先保留其他 sleeves。",
            ),
            "rebound": (
                (regime in {"bull", "chop"} and gate == "CAUTION") or regime == "bear",
                f"目前 regime={regime} / gate={gate} 更接近 stress / oversold lane，深跌回補 sleeve 可啟用。",
                "目前尚未進入 stress / deep pullback lane，深跌回補 sleeve 先停用。",
            ),
            "selective": (
                layers > 0 and (quality is None or quality >= 0.55),
                f"allowed_layers={layers}{f' · entry_quality={quality:.2f}' if quality is not None else ''}，保留高信念精選 sleeve 作為最保守 lane。",
                f"目前 allowed_layers={layers}{f' / entry_quality={quality:.2f}' if quality is not None else ''}，尚不足以維持高信念精選 sleeve。",
            ),
        }
        for key in primary_sleeves:
            active, active_why, inactive_why = routing_rules[key]
            if active:
                active_entries.append(_entry(key, True, active_why))
            else:
                inactive_entries.append(_entry(key, False, inactive_why))

    active_count = len(active_entries)
    total_count = len(primary_sleeves)
    active_ratio_text = f"{active_count}/{total_count}"
    if active_entries:
        summary = (
            f"目前 regime={regime} / gate={gate} / bucket={normalized_structure_bucket or '—'}；"
            f"active sleeves {active_ratio_text}：{'、'.join(item['label'] for item in active_entries)}。"
        )
    else:
        summary = (
            f"目前 regime={regime} / gate={gate} / bucket={normalized_structure_bucket or '—'}；"
            f"active sleeves {active_ratio_text}，暫無可部署 primary sleeves。"
        )

    return {
        "current_regime": regime,
        "current_regime_gate": gate,
        "current_structure_bucket": normalized_structure_bucket,
        "active_count": active_count,
        "total_count": total_count,
        "active_ratio_text": active_ratio_text,
        "active_sleeves": active_entries,
        "inactive_sleeves": inactive_entries,
        "active_sleeve_keys": [item["key"] for item in active_entries],
        "inactive_sleeve_keys": [item["key"] for item in inactive_entries],
        "summary": summary,
        "global_blocker_reason": global_blocker_reason,
    }

# Heartbeat #715: the bull ALLOW + D lane still contained a small but fully losing
# overextended 4H pocket. Mirror predictor.py so Strategy Lab/backtests and live
# inference share the same ALLOW-lane veto semantics.
OVEREXTENDED_4H_BB_PCT_B_MIN = 1.0
OVEREXTENDED_4H_DIST_BB_LOWER_MIN = 10.0
OVEREXTENDED_4H_DIST_SWING_LOW_MIN = 11.0
# Heartbeat P0 follow-up: bull q15 pockets with still-stretched bias50 were slipping
# through as low-conviction CAUTION entries. Keep Strategy Lab aligned with live
# predictor by fail-closing these weak-structure bull pockets before they appear as
# valid runtime/backtest candidates.
BULL_Q15_BIAS50_OVEREXTENDED_MIN = 1.8
# P0 recent-pathology fix: the breaker-driving bull tail also includes q35/q65 rows
# where bias200 is extremely hot while structure is only mediocre, not fully broken.
# Mirror predictor.py so backtests do not keep advertising these lanes as CAUTION/
# ALLOW candidates.
BULL_HIGH_BIAS200_OVERHEAT_MIN = 9.0
BULL_HIGH_BIAS200_OVERHEAT_MAX_STRUCTURE_QUALITY = 0.75


def _sanitize_json_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_json_like(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_like(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_json_like(v) for v in value]
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    return value


def _sanitize_backtest_range_bounds(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    cleaned: Dict[str, Any] = {}
    if value.get("start") is not None:
        cleaned["start"] = value.get("start")
    if value.get("end") is not None:
        cleaned["end"] = value.get("end")
    if value.get("count") is not None:
        cleaned["count"] = _coerce_int(value.get("count"), 0)
    if value.get("span_days") is not None:
        cleaned["span_days"] = _coerce_float(value.get("span_days"))
    return cleaned


def _sanitize_backtest_range_meta(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    cleaned: Dict[str, Any] = {}
    requested = _sanitize_backtest_range_bounds(value.get("requested"))
    if requested:
        cleaned["requested"] = requested
    effective = _sanitize_backtest_range_bounds(value.get("effective"))
    if effective:
        cleaned["effective"] = effective
    available = _sanitize_backtest_range_bounds(value.get("available"))
    if available:
        cleaned["available"] = available
    if value.get("backfill_required") is not None:
        cleaned["backfill_required"] = bool(value.get("backfill_required"))
    if value.get("coverage_ok") is not None:
        cleaned["coverage_ok"] = bool(value.get("coverage_ok"))
    if value.get("missing_start_days") is not None:
        cleaned["missing_start_days"] = _coerce_float(value.get("missing_start_days"))
    if value.get("missing_end_days") is not None:
        cleaned["missing_end_days"] = _coerce_float(value.get("missing_end_days"))
    if value.get("row_count") is not None:
        cleaned["row_count"] = _coerce_int(value.get("row_count"), 0)
    if value.get("policy") is not None:
        cleaned["policy"] = _sanitize_json_like(value.get("policy"))
    return cleaned


def _merge_backtest_range_bounds(*candidates: Any) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in ("start", "end", "count", "span_days"):
            value = candidate.get(key)
            if value is not None and merged.get(key) is None:
                merged[key] = value
    return merged


def _backfill_strategy_backtest_range(last_results: Optional[Dict[str, Any]], definition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(last_results, dict):
        return last_results

    params = definition.get("params") if isinstance(definition, dict) else {}
    params = params if isinstance(params, dict) else {}
    definition_range = params.get("backtest_range") if isinstance(params.get("backtest_range"), dict) else {}
    definition_requested = {
        "start": definition_range.get("start"),
        "end": definition_range.get("end"),
    }

    chart_context = last_results.get("chart_context") if isinstance(last_results.get("chart_context"), dict) else {}
    chart_bounds = {
        "start": chart_context.get("start"),
        "end": chart_context.get("end"),
    }

    existing = _sanitize_backtest_range_meta(last_results.get("backtest_range"))
    requested = _merge_backtest_range_bounds(existing.get("requested"), definition_requested)
    effective = _merge_backtest_range_bounds(existing.get("effective"), requested, chart_bounds)

    # Do not let a trade-focused chart window rewrite the operator-facing
    # available/effective range. Older saved strategies often persisted only the
    # active trade window in chart_context, which made a 2-year backtest look like
    # it only had ~1 year of usable history. Prefer the explicit/requested/effective
    # bounds first; only fall back to chart_context if nothing else exists.
    available = _merge_backtest_range_bounds(effective, requested, existing.get("available"), chart_bounds)

    if not (requested or effective or available):
        return last_results

    merged_meta = dict(existing)
    if requested:
        merged_meta["requested"] = requested
    if effective:
        merged_meta["effective"] = effective
    if available:
        merged_meta["available"] = available
    if merged_meta.get("coverage_ok") is None and merged_meta.get("backfill_required") is None:
        if requested.get("start") and requested.get("end") and effective.get("start") and effective.get("end"):
            requested_matches_effective = (
                requested.get("start") == effective.get("start")
                and requested.get("end") == effective.get("end")
            )
            merged_meta["coverage_ok"] = requested_matches_effective
            merged_meta["backfill_required"] = not requested_matches_effective

    last_results["backtest_range"] = merged_meta
    return last_results


def _build_strategy_metadata(name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    params = definition.get("params") if isinstance(definition, dict) else {}
    if not isinstance(params, dict):
        params = {}
    entry = params.get("entry") if isinstance(params.get("entry"), dict) else {}
    layers = params.get("layers") if isinstance(params.get("layers"), list) else []
    capital_management = params.get("capital_management") if isinstance(params.get("capital_management"), dict) else {}
    model_name = str(params.get("model_name") or "rule_baseline")
    layer_text = " / ".join(f"{round(float(layer) * 100):.0f}%" for layer in layers[:3]) if layers else "20% / 30% / 50%"
    title = name or "Unnamed Strategy"
    sleeves = _infer_strategy_sleeves(title, definition)
    primary_sleeve = sleeves[0] if sleeves else {"key": "uncategorized", "label": "未分類 sleeve", "summary": ""}

    description_bits = []
    if len(layers) >= 3:
        description_bits.append(f"三層金字塔配置 {layer_text}")
    else:
        description_bits.append("固定倉位規則策略")
    if _coerce_float(entry.get("bias50_max")) is not None:
        description_bits.append(f"Bias50 ≤ {_coerce_float(entry.get('bias50_max')):.1f}% 才允許首層進場")
    if _coerce_float(entry.get("layer3_bias_max")) is not None:
        description_bits.append(f"第三層在 Bias50 ≤ {_coerce_float(entry.get('layer3_bias_max')):.1f}% 時加碼")
    if _coerce_float(params.get("stop_loss")) is not None:
        description_bits.append(f"止損 {(_coerce_float(params.get('stop_loss')) or 0.0) * 100:.0f}%")
    turning_point = params.get("turning_point") if isinstance(params.get("turning_point"), dict) else {}
    editor_modules = params.get("editor_modules") if isinstance(params.get("editor_modules"), list) else []
    if bool(turning_point.get("enabled")) or any(str(v) == "turning_point" for v in editor_modules):
        tp_exit = _coerce_float(turning_point.get("top_score_take_profit"))
        if tp_exit is not None:
            description_bits.append(f"頂部轉折 ≥ {tp_exit:.2f} 時啟用 exit gate")
        else:
            description_bits.append("啟用頂部轉折 exit gate")
    if str(capital_management.get("mode") or CAPITAL_MODE_CLASSIC) == CAPITAL_MODE_RESERVE:
        entry_fraction = (_coerce_float(capital_management.get("base_entry_fraction")) or 0.10) * 100
        reserve_trigger = (_coerce_float(capital_management.get("reserve_trigger_drawdown")) or 0.10) * 100
        description_bits.append(f"先用 {entry_fraction:.0f}% 建倉，回撤達 {reserve_trigger:.0f}% 後才啟用後守資金")

    sleeve_labels = [str(item.get("label") or item.get("key") or "").strip() for item in sleeves if str(item.get("label") or item.get("key") or "").strip()]
    sleeve_keys = [str(item.get("key") or "").strip() for item in sleeves if str(item.get("key") or "").strip()]
    secondary_labels = [label for label in sleeve_labels[1:] if label]
    sleeve_summary = f"主 sleeve：{primary_sleeve.get('label') or '未分類 sleeve'}"
    if secondary_labels:
        sleeve_summary += f"；附加：{'、'.join(secondary_labels)}"

    is_auto_leaderboard = _is_auto_leaderboard_strategy(title)
    source = "auto_leaderboard" if is_auto_leaderboard else "user_saved"
    source_label = "系統生成排行榜" if is_auto_leaderboard else "手動策略"

    return {
        "title": title,
        "description": "；".join(description_bits),
        "strategy_type": definition.get("type") or "rule_based",
        "model_name": model_name,
        "model_summary": MODEL_SUMMARY_MAP.get(model_name, f"{model_name}：自訂交易模型。"),
        "primary_sleeve_key": primary_sleeve.get("key") or "uncategorized",
        "primary_sleeve_label": primary_sleeve.get("label") or "未分類 sleeve",
        "sleeve_keys": sleeve_keys,
        "sleeve_labels": sleeve_labels,
        "sleeves": sleeves,
        "sleeve_summary": sleeve_summary,
        "source": source,
        "source_label": source_label,
        "immutable": is_auto_leaderboard,
        "editable_clone_required": is_auto_leaderboard,
    }


def _merge_strategy_metadata(name: str, definition: Dict[str, Any], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = _build_strategy_metadata(name, definition)
    incoming = _sanitize_json_like(metadata) if isinstance(metadata, dict) else {}
    if not isinstance(incoming, dict):
        incoming = {}
    merged = dict(base)
    merged.update(incoming)
    for key, value in base.items():
        if merged.get(key) in (None, "", [], {}):
            merged[key] = value
    return merged


def _sanitize_regime_breakdown(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "regime": item.get("regime") or "unknown",
            "trades": _coerce_int(item.get("trades"), 0),
            "wins": _coerce_int(item.get("wins"), 0),
            "losses": _coerce_int(item.get("losses"), 0),
            "roi": _coerce_float(item.get("roi")),
            "win_rate": _coerce_float(item.get("win_rate")),
            "profit_factor": _coerce_float(item.get("profit_factor")),
            "total_pnl": _coerce_float(item.get("total_pnl")),
        })
    return cleaned


def _sanitize_results(results: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(results, dict):
        return None
    cleaned = {
        "run_at": results.get("run_at"),
        "avg_entry_quality": _coerce_float(results.get("avg_entry_quality")),
        "avg_allowed_layers": _coerce_float(results.get("avg_allowed_layers")),
        "dominant_regime_gate": results.get("dominant_regime_gate"),
        "regime_gate_summary": _sanitize_json_like(results.get("regime_gate_summary") or {}),
        "decision_quality_horizon_minutes": _coerce_int(results.get("decision_quality_horizon_minutes"), 0),
        "decision_quality_label": results.get("decision_quality_label"),
        "target_col": results.get("target_col"),
    }
    for field in RESULT_FLOAT_FIELDS:
        cleaned[field] = _coerce_float(results.get(field))
    for field in RESULT_INT_FIELDS:
        cleaned[field] = _coerce_int(results.get(field), 0)
    cleaned["regime_breakdown"] = _sanitize_regime_breakdown(results.get("regime_breakdown"))
    if cleaned["wins"] == 0 and cleaned["losses"] == 0 and cleaned["total_trades"]:
        wins = round((cleaned.get("win_rate") or 0.0) * cleaned["total_trades"])
        cleaned["wins"] = wins
        cleaned["losses"] = max(cleaned["total_trades"] - wins, 0)
    if cleaned["total_trades"] == 0 and cleaned["wins"] + cleaned["losses"] > 0:
        cleaned["total_trades"] = cleaned["wins"] + cleaned["losses"]
    cleaned["benchmarks"] = _sanitize_json_like(results.get("benchmarks") or {})
    cleaned["equity_curve"] = _sanitize_json_like(results.get("equity_curve") or [])
    cleaned["trades"] = _sanitize_json_like(results.get("trades") or [])
    cleaned["score_series"] = _sanitize_json_like(results.get("score_series") or [])
    cleaned["chart_context"] = _sanitize_json_like(results.get("chart_context") or {})
    cleaned["backtest_range"] = _sanitize_backtest_range_meta(results.get("backtest_range") or {})
    return cleaned


def _sanitize_strategy_record(data: Dict[str, Any], fallback_name: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    name = (data.get("name") or fallback_name or "Unnamed Strategy").strip()
    definition = _sanitize_definition(data.get("definition"))
    last_results = _sanitize_results(data.get("last_results"))
    last_results = _backfill_strategy_backtest_range(last_results, definition)
    run_count = _coerce_int(data.get("run_count"), 0)
    if last_results is not None:
        run_count = max(run_count, 1)
    return {
        "schema_version": _coerce_int(data.get("schema_version"), STRATEGY_SCHEMA_VERSION),
        "name": name,
        "slug": _strategy_slug(name),
        "created_at": data.get("created_at") or data.get("updated_at") or datetime.now().isoformat(),
        "updated_at": data.get("updated_at") or data.get("created_at") or datetime.now().isoformat(),
        "definition": definition,
        "last_results": last_results,
        "run_count": run_count,
        "is_internal": _is_internal_strategy(name),
        "metadata": _merge_strategy_metadata(name, definition, data.get("metadata")),
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _compute_regime_gate(
    bias200_value: float,
    regime: str,
    regime_min: float,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
    bias50_value: Optional[float] = None,
) -> str:
    regime = (regime or "unknown").lower()
    if bias200_value < regime_min:
        return "BLOCK"
    if regime == "bear" and bias200_value <= -3.0:
        return "BLOCK"
    if regime in {"chop", "unknown"} or bias200_value < -1.0:
        base_gate = "CAUTION"
    else:
        base_gate = "ALLOW"

    structure_quality = _compute_4h_structure_quality(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )
    if structure_quality is None:
        return base_gate

    # Heartbeat #697: the narrowed bull+ALLOW+D pathology lane kept surfacing the
    # same 4H collapse pocket (`bb_pct_b`, `dist_bb_lower`, `dist_swing_low`).
    # If the higher-timeframe structure is this weak, do not keep advertising an
    # ALLOW gate just because bias200 is positive — downgrade the gate first.
    if base_gate == "ALLOW" and _is_4h_structure_overextended(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    ):
        return "BLOCK"
    if base_gate == "ALLOW" and structure_quality < 0.15:
        return "BLOCK"
    if base_gate == "ALLOW" and _is_bull_q15_bias50_overextended_pocket(
        regime=regime,
        structure_quality=structure_quality,
        bias50_value=bias50_value,
    ):
        return "BLOCK"
    if base_gate == "ALLOW" and _is_bull_high_bias200_overheat_pocket(
        regime=regime,
        bias200_value=bias200_value,
        structure_quality=structure_quality,
    ):
        return "BLOCK"
    # Heartbeat #718 parity: borderline ALLOW+q35 setups were too sparse to treat as
    # trustworthy ALLOW lanes. Keep Strategy Lab aligned with live predictor by
    # downgrading weak-but-not-collapsed 4H structure to CAUTION.
    if base_gate == "ALLOW" and structure_quality < 0.65:
        return "CAUTION"
    return base_gate


def _is_4h_structure_overextended(
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> bool:
    if bb_pct_b_value is None or dist_bb_lower_value is None or dist_swing_low_value is None:
        return False
    return (
        float(bb_pct_b_value) >= OVEREXTENDED_4H_BB_PCT_B_MIN
        and float(dist_bb_lower_value) >= OVEREXTENDED_4H_DIST_BB_LOWER_MIN
        and float(dist_swing_low_value) >= OVEREXTENDED_4H_DIST_SWING_LOW_MIN
    )


def _is_bull_q15_bias50_overextended_pocket(
    *,
    regime: Optional[str],
    structure_quality: Optional[float],
    bias50_value: Optional[float],
) -> bool:
    if str(regime or "").lower() != "bull":
        return False
    if structure_quality is None or bias50_value is None:
        return False
    quality = float(structure_quality)
    return 0.15 <= quality < 0.35 and float(bias50_value) >= BULL_Q15_BIAS50_OVEREXTENDED_MIN


def _is_bull_high_bias200_overheat_pocket(
    *,
    regime: Optional[str],
    bias200_value: Optional[float],
    structure_quality: Optional[float],
) -> bool:
    if str(regime or "").lower() != "bull":
        return False
    if bias200_value is None or structure_quality is None:
        return False
    quality = float(structure_quality)
    return (
        0.35 <= quality < BULL_HIGH_BIAS200_OVERHEAT_MAX_STRUCTURE_QUALITY
        and float(bias200_value) >= BULL_HIGH_BIAS200_OVERHEAT_MIN
    )


def _compute_4h_structure_quality(
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> Optional[float]:
    """Estimate whether the 4H structure is supportive, not just oversold.

    Heartbeat #694 found that the worst live decision-quality lane shared the same
    4H collapse pocket across three scopes: very low `feat_4h_bb_pct_b`,
    `feat_4h_dist_bb_lower`, and `feat_4h_dist_swing_low`. Those features were
    already present in DB/runtime diagnostics but were not influencing Strategy Lab's
    entry-quality baseline, so falling-knife structures could still look acceptable
    as long as bias50/nose/pulse/ear were decent.
    """

    components: List[tuple[float, float]] = []
    if bb_pct_b_value is not None:
        components.append((0.34, _clamp01(float(bb_pct_b_value))))
    if dist_bb_lower_value is not None:
        components.append((0.33, _clamp01(float(dist_bb_lower_value) / 8.0)))
    if dist_swing_low_value is not None:
        components.append((0.33, _clamp01(float(dist_swing_low_value) / 10.0)))
    if not components:
        return None

    total_weight = sum(weight for weight, _ in components)
    score = sum(weight * value for weight, value in components) / total_weight
    return round(float(score), 4)



def _structure_bucket(regime_gate: str, structure_quality: Optional[float]) -> Optional[str]:
    if not regime_gate:
        return None
    if structure_quality is None:
        quality_bucket = "missing"
    else:
        quality_value = float(structure_quality)
        if quality_value >= 0.85:
            quality_bucket = "q85"
        elif quality_value >= 0.65:
            quality_bucket = "q65"
        elif quality_value >= 0.35:
            quality_bucket = "q35"
        elif quality_value >= 0.15:
            quality_bucket = "q15"
        else:
            quality_bucket = "q00"
    reason = {
        "BLOCK": "structure_quality_block" if (structure_quality is not None and float(structure_quality) < 0.15) else "regime_gate_block",
        "CAUTION": "structure_quality_caution",
        "ALLOW": "base_allow",
    }.get(str(regime_gate), "unknown")
    return f"{regime_gate}|{reason}|{quality_bucket}"



def _compute_entry_quality(
    bias50_value: float,
    nose_value: float,
    pulse_value: float,
    ear_value: float,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
    regime_label: Optional[str] = None,
    regime_gate: Optional[str] = None,
    structure_bucket: Optional[str] = None,
) -> float:
    bias_score = compute_piecewise_bias50_score(
        bias50_value,
        regime_label=regime_label,
        regime_gate=regime_gate,
        structure_bucket=structure_bucket,
    )["score"]
    nose_score = _clamp01(1.0 - nose_value)
    pulse_score = _clamp01(pulse_value)
    ear_score = _clamp01(1.0 - abs(ear_value) * 5.0)
    base_quality = 0.40 * bias_score + 0.18 * nose_score + 0.27 * pulse_score + 0.15 * ear_score

    structure_quality = _compute_4h_structure_quality(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )
    if structure_quality is None:
        return round(base_quality, 4)

    return round(0.75 * base_quality + 0.25 * structure_quality, 4)


def _quality_label(entry_quality: float) -> str:
    if entry_quality >= 0.82:
        return "A"
    if entry_quality >= 0.68:
        return "B"
    if entry_quality >= 0.55:
        return "C"
    return "D"


def _allowed_layers_for_signal(regime_gate: str, entry_quality: float, max_layers: int) -> int:
    max_layers = max(0, int(max_layers))
    if regime_gate == "BLOCK" or entry_quality < 0.55:
        return 0
    if entry_quality < 0.68:
        return min(1, max_layers)
    if regime_gate == "CAUTION" or entry_quality < 0.70:
        return min(2, max_layers)
    return min(3, max_layers)


def _normalize_allowed_regimes(value: Any) -> Optional[set]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [part.strip().lower() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = [str(part).strip().lower() for part in value if str(part).strip()]
    else:
        return None
    allowed = {item for item in items if item}
    return allowed or None


def _regime_allowed(regime: str, allowed_regimes: Optional[set]) -> bool:
    if not allowed_regimes:
        return True
    return (regime or "unknown").lower() in allowed_regimes


def _top_k_cutoff(values: List[float], top_k_percent: float) -> Optional[float]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    if top_k_percent <= 0:
        return None
    top_k_percent = max(0.0, min(100.0, float(top_k_percent)))
    if top_k_percent >= 100.0:
        return min(clean)
    clean.sort(reverse=True)
    count = max(1, int(math.ceil(len(clean) * (top_k_percent / 100.0))))
    return clean[count - 1]


def _passes_rolling_top_k_gate(value: Optional[float], history: List[float], top_k_percent: float) -> bool:
    if value is None or top_k_percent <= 0:
        return True
    if not history:
        return True
    cutoff = _top_k_cutoff(history, top_k_percent)
    if cutoff is None:
        return True
    return float(value) >= float(cutoff)


def build_auto_strategy_candidates(model_candidates: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    selected_models = []
    for model_name in model_candidates or []:
        model_name = str(model_name or "").strip()
        if model_name and model_name not in selected_models:
            selected_models.append(model_name)
    if not selected_models:
        selected_models = ["random_forest", "logistic_regression"]

    candidates: List[Dict[str, Any]] = []

    def add_candidate(label: str, strategy_type: str, params: Dict[str, Any], *, model_name: Optional[str] = None) -> None:
        idx = len(candidates) + 1
        title = f"{AUTO_STRATEGY_NAME_PREFIX}{label} #{idx:02d}"
        merged_params = {
            "entry": {
                "pulse_min": 0.0,
                **(params.get("entry") or {}),
            },
            "layers": params.get("layers") or [0.2, 0.3, 0.5],
            "capital_management": params.get("capital_management") or {"mode": CAPITAL_MODE_CLASSIC, "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.10},
            "stop_loss": params.get("stop_loss", -0.05),
            "take_profit_bias": params.get("take_profit_bias", 4.0),
            "take_profit_roi": params.get("take_profit_roi", 0.08),
            "editor_modules": params.get("editor_modules") or [],
        }
        if isinstance(params.get("storm_unwind"), dict):
            merged_params["storm_unwind"] = dict(params.get("storm_unwind") or {})
        if isinstance(params.get("turning_point"), dict):
            merged_params["turning_point"] = dict(params.get("turning_point") or {})
        if model_name:
            merged_params["model_name"] = model_name
        definition = {
            "type": strategy_type,
            "params": merged_params,
        }
        candidates.append({
            "name": title,
            "definition": definition,
            "metadata": _build_strategy_metadata(title, definition),
        })

    add_candidate(
        "舊版 Baseline Rule（對照）",
        "rule_based",
        {
            "entry": {"bias50_max": 1.0, "nose_max": 0.40, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5, "entry_quality_min": 0.55, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            "investment_horizon": "medium",
        },
    )
    add_candidate(
        "新版預設 XGBoost Hybrid",
        "hybrid",
        {
            "entry": {"bias50_max": 0.0, "nose_max": 0.40, "layer2_bias_max": -1.0, "layer3_bias_max": -3.0, "confidence_min": 0.52, "entry_quality_min": 0.50, "top_k_percent": 0, "allowed_regimes": ["bull", "chop"]},
            "layers": [0.25, 0.25, 0.5],
            "stop_loss": -0.03,
            "take_profit_bias": 999.0,
            "take_profit_roi": 999.0,
            "editor_modules": ["turning_point"],
            "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.80, "min_profit_pct": 0.0},
        },
        model_name="xgboost",
    )
    add_candidate(
        "平衡承接 Rule（短期）",
        "rule_based",
        {
            "entry": {"bias50_max": 1.0, "nose_max": 0.40, "layer2_bias_max": -1.0, "layer3_bias_max": -2.0, "entry_quality_min": 0.48, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            "take_profit_bias": 2.8,
            "take_profit_roi": 0.05,
            "investment_horizon": "short",
        },
    )
    add_candidate(
        "平衡承接 Rule（長期）",
        "rule_based",
        {
            "entry": {"bias50_max": -0.5, "nose_max": 0.34, "layer2_bias_max": -2.5, "layer3_bias_max": -4.5, "entry_quality_min": 0.65, "top_k_percent": 0, "allowed_regimes": ["bull", "chop"]},
            "take_profit_bias": 5.2,
            "take_profit_roi": 0.12,
            "investment_horizon": "long",
        },
    )
    add_candidate(
        "深跌回補 Rule",
        "rule_based",
        {
            "entry": {"bias50_max": -1.0, "nose_max": 0.35, "layer2_bias_max": -2.8, "layer3_bias_max": -5.0, "entry_quality_min": 0.62, "top_k_percent": 0, "allowed_regimes": ["bull", "chop"]},
            "take_profit_bias": 4.5,
        },
    )
    add_candidate(
        "低頻高把握 Rule",
        "rule_based",
        {
            "entry": {"bias50_max": 0.5, "nose_max": 0.35, "layer2_bias_max": -2.0, "layer3_bias_max": -4.0, "entry_quality_min": 0.68, "top_k_percent": 10, "allowed_regimes": ["bear"]},
        },
    )
    add_candidate(
        "10/90 後守 Rule",
        "rule_based",
        {
            "entry": {"bias50_max": 0.5, "nose_max": 0.35, "layer2_bias_max": -2.5, "layer3_bias_max": -4.5, "entry_quality_min": 0.60, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            "capital_management": {"mode": CAPITAL_MODE_RESERVE, "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.10},
            "stop_loss": -0.07,
            "editor_modules": ["reserve_90"],
        },
    )
    add_candidate(
        "風暴斬倉 Rule",
        "rule_based",
        {
            "entry": {"bias50_max": 0.5, "nose_max": 0.35, "layer2_bias_max": -2.5, "layer3_bias_max": -4.5, "entry_quality_min": 0.60, "top_k_percent": 0, "allowed_regimes": ["bull", "chop"]},
            "capital_management": {"mode": CAPITAL_MODE_RESERVE, "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.08},
            "stop_loss": -0.04,
            "take_profit_bias": 3.2,
            "take_profit_roi": 0.06,
            "editor_modules": ["reserve_90", "storm_unwind"],
            "storm_unwind": {"enabled": True, "release_ratio": 0.25, "min_profit_pct": 0.01},
        },
    )
    add_candidate(
        "轉折狙擊 Rule",
        "rule_based",
        {
            "entry": {"bias50_max": 0.5, "nose_max": 0.42, "layer2_bias_max": -1.8, "layer3_bias_max": -3.8, "entry_quality_min": 0.52, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            "take_profit_bias": 2.6,
            "take_profit_roi": 0.05,
            "editor_modules": ["turning_point"],
            "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.68},
        },
    )
    add_candidate(
        "XGBoost 頂部轉折 Hybrid",
        "hybrid",
        {
            "entry": {"bias50_max": 0.5, "nose_max": 0.40, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5, "confidence_min": 0.58, "entry_quality_min": 0.56, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            "take_profit_bias": 10.0,
            "take_profit_roi": 0.50,
            "editor_modules": ["turning_point"],
            "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.68},
        },
        model_name="xgboost",
    )

    for model_name in selected_models[:2]:
        add_candidate(
            f"{model_name} 平衡 Hybrid",
            "hybrid",
            {
                "entry": {"bias50_max": 1.0, "nose_max": 0.40, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5, "confidence_min": 0.55, "entry_quality_min": 0.55, "top_k_percent": 0, "allowed_regimes": ["bull", "chop", "bear", "unknown"]},
            },
            model_name=model_name,
        )
        add_candidate(
            f"{model_name} 高勝率 Hybrid",
            "hybrid",
            {
                "entry": {"bias50_max": 1.0, "nose_max": 0.40, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5, "confidence_min": 0.75, "entry_quality_min": 0.68, "top_k_percent": 5, "allowed_regimes": ["bear"]},
            },
            model_name=model_name,
        )

    return candidates


def _capital_management_config(params: Dict[str, Any]) -> Dict[str, Any]:
    cfg = params.get("capital_management") if isinstance(params.get("capital_management"), dict) else {}
    mode = str(cfg.get("mode") or CAPITAL_MODE_CLASSIC)
    base_entry_fraction = _coerce_float(cfg.get("base_entry_fraction")) or 0.10
    reserve_trigger_drawdown = _coerce_float(cfg.get("reserve_trigger_drawdown")) or 0.10
    return {
        "mode": mode,
        "base_entry_fraction": _clamp01(base_entry_fraction),
        "reserve_trigger_drawdown": max(0.0, min(0.95, reserve_trigger_drawdown)),
    }


def _layer_budget(layer_index: int, layers_pct: List[float], initial_capital: float, capital_cfg: Dict[str, Any]) -> float:
    if layer_index < 0 or layer_index >= len(layers_pct):
        return 0.0
    if capital_cfg.get("mode") != CAPITAL_MODE_RESERVE:
        return max(0.0, initial_capital * float(layers_pct[layer_index]))

    base_entry_fraction = float(capital_cfg.get("base_entry_fraction") or 0.10)
    reserve_capital = max(0.0, initial_capital * (1.0 - base_entry_fraction))
    if layer_index == 0:
        return initial_capital * base_entry_fraction

    tail_weights = [max(0.0, float(v)) for v in layers_pct[1:]]
    tail_total = sum(tail_weights)
    if tail_total <= 0:
        return 0.0
    return reserve_capital * (tail_weights[layer_index - 1] / tail_total)


def _reserve_unlocked(capital_cfg: Dict[str, Any], entry_layers: List[Dict[str, Any]], current_price: float) -> bool:
    if capital_cfg.get("mode") != CAPITAL_MODE_RESERVE:
        return True
    if not entry_layers:
        return False
    trigger = float(capital_cfg.get("reserve_trigger_drawdown") or 0.10)
    anchor_price = float(entry_layers[0].get("price", 0.0) or 0.0)
    if anchor_price <= 0:
        return False
    drawdown = (current_price - anchor_price) / anchor_price
    return drawdown <= -trigger


def _storm_unwind_config(params: Dict[str, Any]) -> Dict[str, Any]:
    cfg = params.get("storm_unwind") if isinstance(params.get("storm_unwind"), dict) else {}
    editor_modules = params.get("editor_modules") if isinstance(params.get("editor_modules"), list) else []
    enabled = bool(cfg.get("enabled")) or any(str(v) == "storm_unwind" for v in editor_modules)
    release_ratio = _coerce_float(cfg.get("release_ratio"))
    if release_ratio is None:
        release_ratio = 0.25
    min_profit_pct = _coerce_float(cfg.get("min_profit_pct"))
    if min_profit_pct is None:
        min_profit_pct = 0.01
    return {
        "enabled": enabled,
        "release_ratio": _clamp01(release_ratio),
        "min_profit_pct": max(0.0, min(0.25, float(min_profit_pct))),
    }


def _investment_horizon_profile(params: Dict[str, Any]) -> str:
    value = str(params.get("investment_horizon") or "medium").strip().lower()
    if value in {"short", "medium", "long"}:
        return value
    return "medium"


def _turning_point_config(params: Dict[str, Any]) -> Dict[str, Any]:
    cfg = params.get("turning_point") if isinstance(params.get("turning_point"), dict) else {}
    editor_modules = params.get("editor_modules") if isinstance(params.get("editor_modules"), list) else []
    enabled = bool(cfg.get("enabled")) or any(str(v) == "turning_point" for v in editor_modules)
    bottom_score_min = _coerce_float(cfg.get("bottom_score_min"))
    top_score_take_profit = _coerce_float(cfg.get("top_score_take_profit"))
    return {
        "enabled": enabled,
        "bottom_score_min": _clamp01(bottom_score_min if bottom_score_min is not None else 0.60),
        "top_score_take_profit": _clamp01(top_score_take_profit if top_score_take_profit is not None else 0.70),
    }


def _adjust_value_by_horizon(value: float, horizon: str, *, short_delta: float = 0.0, long_delta: float = 0.0) -> float:
    if horizon == "short":
        return value + short_delta
    if horizon == "long":
        return value + long_delta
    return value


def _entry_layers_avg_price(entry_layers: List[Dict[str, Any]]) -> float:
    total_coins = sum(float(layer.get("coins") or 0.0) for layer in entry_layers)
    if total_coins <= 0:
        return 0.0
    return sum(float(layer.get("price") or 0.0) * float(layer.get("coins") or 0.0) for layer in entry_layers) / total_coins


def _close_all_layers(
    *,
    entry_layers: List[Dict[str, Any]],
    current_price: float,
    reason: str,
    timestamp: str,
    initial_capital: float,
    capital_mode: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sold_coins = sum(float(layer.get("coins") or 0.0) for layer in entry_layers)
    avg = _entry_layers_avg_price(entry_layers)
    pnl = sum((float(current_price) - float(layer.get("price") or 0.0)) * float(layer.get("coins") or 0.0) for layer in entry_layers)
    payload = {
        "entry": avg,
        "exit": float(current_price),
        "pnl": pnl,
        "roi": pnl / initial_capital if initial_capital else 0.0,
        "layers": len(entry_layers),
        "reason": reason,
        "timestamp": timestamp,
        "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
        "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
        "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
        "entry_quality": entry_layers[0].get("entry_quality") if entry_layers else None,
        "allowed_layers": entry_layers[0].get("allowed_layers") if entry_layers else None,
        "capital_mode": capital_mode or (entry_layers[0].get("capital_mode") if entry_layers else None),
        "sold_coins": sold_coins,
    }
    if extra:
        payload.update(extra)
    return payload


def _apply_storm_unwind_take_profit(
    *,
    entry_layers: List[Dict[str, Any]],
    current_price: float,
    timestamp: str,
    initial_capital: float,
    capital_mode: Optional[str],
    storm_cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not storm_cfg.get("enabled") or not entry_layers:
        return None
    profitable_layers = [layer for layer in entry_layers if float(current_price) > float(layer.get("price") or 0.0)]
    if not profitable_layers:
        return None
    profitable_realized = sum((float(current_price) - float(layer.get("price") or 0.0)) * float(layer.get("coins") or 0.0) for layer in profitable_layers)
    profitable_cost = sum(float(layer.get("price") or 0.0) * float(layer.get("coins") or 0.0) for layer in profitable_layers)
    if profitable_cost <= 0:
        return None
    profit_pct = profitable_realized / profitable_cost
    if profit_pct < float(storm_cfg.get("min_profit_pct") or 0.0):
        return None

    sold_layers: List[Dict[str, Any]] = [dict(layer) for layer in profitable_layers]
    sold_profitable_coins = sum(float(layer.get("coins") or 0.0) for layer in profitable_layers)
    remaining_layers = [dict(layer) for layer in entry_layers if float(current_price) <= float(layer.get("price") or 0.0)]
    trapped_layers = [layer for layer in remaining_layers if float(current_price) < float(layer.get("price") or 0.0)]
    trapped_layers.sort(key=lambda layer: float(layer.get("price") or 0.0), reverse=True)
    unwind_target = trapped_layers[0] if trapped_layers else None
    unwind_coins = 0.0
    unwind_entry_price = None
    if unwind_target is not None and sold_profitable_coins > 0:
        unwind_entry_price = float(unwind_target.get("price") or 0.0)
        unwind_coins = min(float(unwind_target.get("coins") or 0.0), sold_profitable_coins * float(storm_cfg.get("release_ratio") or 0.0))
        if unwind_coins > 0:
            sold_layers.append({**dict(unwind_target), "coins": unwind_coins, "storm_release": True})
            unwind_target["coins"] = max(0.0, float(unwind_target.get("coins") or 0.0) - unwind_coins)
    remaining_layers = [layer for layer in remaining_layers if float(layer.get("coins") or 0.0) > 1e-12]
    total_sold_coins = sum(float(layer.get("coins") or 0.0) for layer in sold_layers)
    if total_sold_coins <= 0:
        return None
    avg_entry = sum(float(layer.get("price") or 0.0) * float(layer.get("coins") or 0.0) for layer in sold_layers) / total_sold_coins
    pnl = sum((float(current_price) - float(layer.get("price") or 0.0)) * float(layer.get("coins") or 0.0) for layer in sold_layers)
    remaining_trapped_coins = sum(float(layer.get("coins") or 0.0) for layer in remaining_layers if float(current_price) < float(layer.get("price") or 0.0))
    highest_remaining_price = max((float(layer.get("price") or 0.0) for layer in remaining_layers), default=None)
    return {
        "trade": {
            "entry": avg_entry,
            "exit": float(current_price),
            "pnl": pnl,
            "roi": pnl / initial_capital if initial_capital else 0.0,
            "layers": len(sold_layers),
            "reason": "storm_unwind_tp",
            "timestamp": timestamp,
            "entry_timestamp": sold_layers[0].get("timestamp", "") if sold_layers else "",
            "entry_regime": sold_layers[0].get("regime", "unknown") if sold_layers else "unknown",
            "regime_gate": sold_layers[0].get("regime_gate", "ALLOW") if sold_layers else "ALLOW",
            "entry_quality": sold_layers[0].get("entry_quality") if sold_layers else None,
            "allowed_layers": sold_layers[0].get("allowed_layers") if sold_layers else None,
            "capital_mode": capital_mode or (sold_layers[0].get("capital_mode") if sold_layers else None),
            "sold_coins": total_sold_coins,
            "storm_unwind_enabled": True,
            "storm_released_coins": round(unwind_coins, 8),
            "storm_release_ratio": float(storm_cfg.get("release_ratio") or 0.0),
            "storm_release_from_price": unwind_entry_price,
            "remaining_trapped_coins": round(remaining_trapped_coins, 8),
            "highest_remaining_entry": highest_remaining_price,
        },
        "remaining_layers": remaining_layers,
        "sold_coins": total_sold_coins,
    }


def run_rule_backtest(
    prices: List[float],
    timestamps: List[str],
    bias50: List[float],
    bias200: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    params: Dict,
    initial_capital: float = 10000.0,
    regimes: Optional[List[str]] = None,
    bb_pct_b_4h: Optional[List[float]] = None,
    dist_bb_lower_4h: Optional[List[float]] = None,
    dist_swing_low_4h: Optional[List[float]] = None,
    local_bottom_score: Optional[List[float]] = None,
    local_top_score: Optional[List[float]] = None,
) -> BacktestResult:
    """純規則回測：bias50 + 特徵條件 + 金字塔 + SL/TP。"""
    # ── 解包參數 ──
    entry = params.get("entry", {})
    bias50_max   = entry.get("bias50_max", -3.0)     # bias50 上限才進場
    nose_max     = entry.get("nose_max", 0.40)        # nose (RSI) 上限
    pulse_min    = entry.get("pulse_min", 0.0)        # pulse 下限（放量確認）
    regime_min   = entry.get("regime_bias200_min", -10.0)  # bias200 下限（允許熊市做多？）
    entry_quality_min = float(entry.get("entry_quality_min", 0.0) or 0.0)
    allowed_regimes = _normalize_allowed_regimes(entry.get("allowed_regimes"))
    top_k_percent = float(entry.get("top_k_percent", 0.0) or 0.0)

    horizon_profile = _investment_horizon_profile(params)
    bias50_max = _adjust_value_by_horizon(float(bias50_max), horizon_profile, short_delta=1.0, long_delta=-1.0)
    nose_max = _adjust_value_by_horizon(float(nose_max), horizon_profile, short_delta=0.08, long_delta=-0.05)
    entry_quality_min = _clamp01(_adjust_value_by_horizon(float(entry_quality_min), horizon_profile, short_delta=-0.08, long_delta=0.08))

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
    capital_cfg  = _capital_management_config(params)
    storm_cfg    = _storm_unwind_config(params)
    turning_cfg  = _turning_point_config(params)
    stop_loss    = _adjust_value_by_horizon(float(params.get("stop_loss", -0.05)), horizon_profile, short_delta=0.02, long_delta=-0.03)
    tp_bias      = _adjust_value_by_horizon(float(params.get("take_profit_bias", 4.0)), horizon_profile, short_delta=-1.2, long_delta=1.2)
    tp_roi       = _adjust_value_by_horizon(float(params.get("take_profit_roi", 0.08)), horizon_profile, short_delta=-0.03, long_delta=0.04)

    cash = initial_capital
    position = 0.0
    entry_layers: List[Dict] = []  # {price, coins, layer}
    result = BacktestResult()
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    consec_loss = 0
    max_consec_loss = 0
    top_k_history: List[float] = []

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        n_val = nose[i] if i < len(nose) else 0.5
        p_val = pulse[i] if i < len(pulse) else 0.5
        e_val = ear[i] if i < len(ear) else 0.0
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
        bb_pct_b_value = bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None
        dist_bb_lower_value = dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None
        dist_swing_low_value = dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None
        bottom_score_value = local_bottom_score[i] if local_bottom_score and i < len(local_bottom_score) else 0.0
        top_score_value = local_top_score[i] if local_top_score and i < len(local_top_score) else 0.0
        regime_gate = _compute_regime_gate(
            b200,
            regime,
            regime_min,
            bb_pct_b_value,
            dist_bb_lower_value,
            dist_swing_low_value,
            bias50_value=b50,
        )
        structure_quality = _compute_4h_structure_quality(
            bb_pct_b_value=bb_pct_b_value,
            dist_bb_lower_value=dist_bb_lower_value,
            dist_swing_low_value=dist_swing_low_value,
        )
        structure_bucket = _structure_bucket(regime_gate, structure_quality)
        entry_quality = _compute_entry_quality(
            b50,
            n_val,
            p_val,
            e_val,
            bb_pct_b_value,
            dist_bb_lower_value,
            dist_swing_low_value,
            regime_label=regime,
            regime_gate=regime_gate,
            structure_bucket=structure_bucket,
        )
        allowed_layers = _allowed_layers_for_signal(regime_gate, entry_quality, len(layers_pct))

        # 更新權益
        if position > 0:
            avg = _entry_layers_avg_price(entry_layers)
            equity = cash + position * p

        # ── 止損 ──
        if position > 0 and entry_layers:
            avg = _entry_layers_avg_price(entry_layers)
            pnl_pct = (p - avg) / avg
            if pnl_pct <= stop_loss:
                trade_payload = _close_all_layers(
                    entry_layers=entry_layers,
                    current_price=p,
                    reason="stop_loss",
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                )
                cash += p * position
                result.trades.append(trade_payload)
                position = 0
                entry_layers = []
                consec_loss += 1
                if consec_loss > max_consec_loss:
                    max_consec_loss = consec_loss
                continue

        # ── 止盈 ──
        if position > 0 and entry_layers:
            avg = _entry_layers_avg_price(entry_layers)
            pnl_pct = (p - avg) / avg
            turning_take_profit = turning_cfg.get("enabled") and float(top_score_value) >= float(turning_cfg.get("top_score_take_profit") or 1.0)
            if b50 > tp_bias or pnl_pct > tp_roi or turning_take_profit:
                storm_event = _apply_storm_unwind_take_profit(
                    entry_layers=entry_layers,
                    current_price=p,
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                    capital_mode=capital_cfg.get("mode"),
                    storm_cfg=storm_cfg,
                )
                if storm_event is not None:
                    cash += p * float(storm_event.get("sold_coins") or 0.0)
                    position = max(0.0, position - float(storm_event.get("sold_coins") or 0.0))
                    entry_layers = storm_event.get("remaining_layers") or []
                    result.trades.append(storm_event["trade"])
                    if float(storm_event["trade"].get("pnl") or 0.0) > 0:
                        consec_loss = 0
                    continue
                trade_payload = _close_all_layers(
                    entry_layers=entry_layers,
                    current_price=p,
                    reason="tp_turning_point" if turning_take_profit else ("tp_bias" if b50 > tp_bias else "tp_roi"),
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                )
                cash += p * position
                result.trades.append(trade_payload)
                position = 0
                entry_layers = []
                if float(trade_payload.get("pnl") or 0.0) > 0:
                    consec_loss = 0
                continue

        top_k_pass = _passes_rolling_top_k_gate(entry_quality, top_k_history, top_k_percent)

        # ── 進場判定 ──
        turning_gate_ok = (not turning_cfg.get("enabled")) or float(bottom_score_value) >= float(turning_cfg.get("bottom_score_min") or 0.0)
        can_enter = (
            regime_gate != "BLOCK"
            and allowed_layers > 0
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and top_k_pass
            and turning_gate_ok
            and b50 <= bias50_max
            and n_val <= nose_max
            and p_val >= pulse_min
            and b200 >= regime_min
        )

        if can_enter and position == 0 and len(layers_pct) > 0 and allowed_layers >= 1:
            buy_amt = min(cash, _layer_budget(0, layers_pct, initial_capital, capital_cfg))
            if buy_amt > 0:
                coins = buy_amt / p
                cash -= buy_amt
                position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 1,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                    "regime_gate": regime_gate,
                    "entry_quality": entry_quality,
                    "allowed_layers": allowed_layers,
                    "capital_mode": capital_cfg.get("mode"),
                })

        elif can_enter and len(entry_layers) == 1 and len(layers_pct) > 1 and allowed_layers >= 2:
            layer2_bias = entry.get("layer2_bias_max", bias50_max - 1.5)
            if b50 <= layer2_bias and _reserve_unlocked(capital_cfg, entry_layers, p):
                buy_amt = min(cash, _layer_budget(1, layers_pct, initial_capital, capital_cfg))
                if buy_amt > 0:
                    coins = buy_amt / p
                    cash -= buy_amt
                    position += coins
                    entry_layers.append({
                        "price": p, "coins": coins, "layer": 2,
                        "timestamp": timestamps[i] if i < len(timestamps) else "",
                        "regime": regime,
                        "regime_gate": regime_gate,
                        "entry_quality": entry_quality,
                        "allowed_layers": allowed_layers,
                        "capital_mode": capital_cfg.get("mode"),
                    })

        elif can_enter and len(entry_layers) == 2 and len(layers_pct) > 2 and allowed_layers >= 3:
            layer3_bias = entry.get("layer3_bias_max", bias50_max - 3.0)
            if b50 <= layer3_bias and _reserve_unlocked(capital_cfg, entry_layers, p):
                buy_amt = min(cash, _layer_budget(2, layers_pct, initial_capital, capital_cfg))
                if buy_amt > 0:
                    coins = buy_amt / p
                    cash -= buy_amt
                    position += coins
                    entry_layers.append({
                        "price": p, "coins": coins, "layer": 3,
                        "timestamp": timestamps[i] if i < len(timestamps) else "",
                        "regime": regime,
                        "regime_gate": regime_gate,
                        "entry_quality": entry_quality,
                        "allowed_layers": allowed_layers,
                        "capital_mode": capital_cfg.get("mode"),
                    })

        if (
            top_k_percent > 0
            and regime_gate != "BLOCK"
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
        ):
            top_k_history.append(entry_quality)

        # 更新最大回撤
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

        invested_value = position * p
        result.equity_curve.append({
            "timestamp": timestamps[i] if i < len(timestamps) else "",
            "equity": round(equity, 2),
            "position_pct": round((invested_value / initial_capital) if initial_capital > 0 else 0.0, 4),
            "position_layers": len(entry_layers),
            "regime_gate": regime_gate,
            "structure_bucket": structure_bucket,
            "entry_quality": entry_quality,
            "allowed_layers": allowed_layers,
        })

    # 平倉未結部位
    if position > 0 and entry_layers:
        trade_payload = _close_all_layers(
            entry_layers=entry_layers,
            current_price=prices[-1],
            reason="end_of_data",
            timestamp=timestamps[-1] if timestamps else "",
            initial_capital=initial_capital,
        )
        cash += prices[-1] * position
        result.trades.append(trade_payload)

    # ── 統計 ──
    result.total_trades = len(result.trades)
    if result.total_trades > 0:
        result.wins = sum(1 for t in result.trades if t["pnl"] > 0)
        result.losses = result.total_trades - result.wins
        result.win_rate = result.wins / result.total_trades

        win_pnls = [t["pnl"] for t in result.trades if t["pnl"] > 0]
        loss_pnls = [t["pnl"] for t in result.trades if t["pnl"] <= 0]
        result.avg_win = sum(win_pnls) / max(len(win_pnls), 1)
        result.avg_loss = sum(loss_pnls) / max(len(loss_pnls), 1)

        result.total_pnl = sum(t["pnl"] for t in result.trades)
        result.roi = result.total_pnl / initial_capital

        gross_profit = sum(t["pnl"] for t in result.trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in result.trades if t["pnl"] <= 0))
        result.profit_factor = gross_profit / max(gross_loss, 0.01)

    result.max_drawdown = max_dd
    result.max_consecutive_losses = max_consec_loss

    return result


def run_hybrid_backtest(
    prices: List[float],
    timestamps: List[str],
    bias50: List[float],
    bias200: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    model_confidence: List[float],
    params: Dict,
    initial_capital: float = 10000.0,
    regimes: Optional[List[str]] = None,
    bb_pct_b_4h: Optional[List[float]] = None,
    dist_bb_lower_4h: Optional[List[float]] = None,
    dist_swing_low_4h: Optional[List[float]] = None,
    local_bottom_score: Optional[List[float]] = None,
    local_top_score: Optional[List[float]] = None,
) -> BacktestResult:
    """混合模式：4H 規則過濾 + ML 信心分數入場。"""
    entry = params.get("entry", {})
    bias50_max   = entry.get("bias50_max", -3.0)
    conf_min     = entry.get("confidence_min", 0.35)  # ML 信心閾值
    regime_min   = entry.get("regime_bias200_min", -10.0)
    entry_quality_min = float(entry.get("entry_quality_min", 0.0) or 0.0)
    allowed_regimes = _normalize_allowed_regimes(entry.get("allowed_regimes"))
    top_k_percent = float(entry.get("top_k_percent", 0.0) or 0.0)

    horizon_profile = _investment_horizon_profile(params)
    bias50_max = _adjust_value_by_horizon(float(bias50_max), horizon_profile, short_delta=1.0, long_delta=-1.0)
    conf_min = _clamp01(_adjust_value_by_horizon(float(conf_min), horizon_profile, short_delta=-0.10, long_delta=0.08))
    entry_quality_min = _clamp01(_adjust_value_by_horizon(float(entry_quality_min), horizon_profile, short_delta=-0.08, long_delta=0.08))

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
    capital_cfg  = _capital_management_config(params)
    storm_cfg    = _storm_unwind_config(params)
    turning_cfg  = _turning_point_config(params)
    stop_loss    = _adjust_value_by_horizon(float(params.get("stop_loss", -0.05)), horizon_profile, short_delta=0.02, long_delta=-0.03)
    tp_bias      = _adjust_value_by_horizon(float(params.get("take_profit_bias", 4.0)), horizon_profile, short_delta=-1.2, long_delta=1.2)
    tp_roi       = _adjust_value_by_horizon(float(params.get("take_profit_roi", 0.08)), horizon_profile, short_delta=-0.03, long_delta=0.04)

    cash = initial_capital
    position = 0.0
    entry_layers: List[Dict] = []
    result = BacktestResult()
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    consec_loss = 0
    max_consec_loss = 0
    top_k_history: List[float] = []

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        conf = model_confidence[i] if i < len(model_confidence) else 0.5
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
        bb_pct_b_value = bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None
        dist_bb_lower_value = dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None
        dist_swing_low_value = dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None
        bottom_score_value = local_bottom_score[i] if local_bottom_score and i < len(local_bottom_score) else 0.0
        top_score_value = local_top_score[i] if local_top_score and i < len(local_top_score) else 0.0
        regime_gate = _compute_regime_gate(
            b200,
            regime,
            regime_min,
            bb_pct_b_value,
            dist_bb_lower_value,
            dist_swing_low_value,
            bias50_value=b50,
        )
        structure_quality = _compute_4h_structure_quality(
            bb_pct_b_value=bb_pct_b_value,
            dist_bb_lower_value=dist_bb_lower_value,
            dist_swing_low_value=dist_swing_low_value,
        )
        structure_bucket = _structure_bucket(regime_gate, structure_quality)
        entry_quality = round(
            0.6 * _clamp01(conf)
            + 0.4
            * _compute_entry_quality(
                b50,
                nose[i] if i < len(nose) else 0.5,
                pulse[i] if i < len(pulse) else 0.5,
                ear[i] if i < len(ear) else 0.0,
                bb_pct_b_value,
                dist_bb_lower_value,
                dist_swing_low_value,
                regime_label=regime,
                regime_gate=regime_gate,
                structure_bucket=structure_bucket,
            ),
            4,
        )
        allowed_layers = _allowed_layers_for_signal(regime_gate, entry_quality, len(layers_pct))

        if position > 0 and entry_layers:
            avg = _entry_layers_avg_price(entry_layers)
            equity = cash + position * p

            # 止損
            pnl_pct = (p - avg) / avg
            if pnl_pct <= stop_loss:
                trade_payload = _close_all_layers(
                    entry_layers=entry_layers,
                    current_price=p,
                    reason="stop_loss",
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                )
                cash += p * position
                result.trades.append(trade_payload)
                position = 0; entry_layers = []
                consec_loss += 1
                max_consec_loss = max(max_consec_loss, consec_loss)
                continue

            # 止盈
            turning_take_profit = turning_cfg.get("enabled") and float(top_score_value) >= float(turning_cfg.get("top_score_take_profit") or 1.0)
            if b50 > tp_bias or pnl_pct > tp_roi or turning_take_profit:
                storm_event = _apply_storm_unwind_take_profit(
                    entry_layers=entry_layers,
                    current_price=p,
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                    capital_mode=capital_cfg.get("mode"),
                    storm_cfg=storm_cfg,
                )
                if storm_event is not None:
                    cash += p * float(storm_event.get("sold_coins") or 0.0)
                    position = max(0.0, position - float(storm_event.get("sold_coins") or 0.0)); entry_layers = storm_event.get("remaining_layers") or []
                    result.trades.append(storm_event["trade"])
                    if float(storm_event["trade"].get("pnl") or 0.0) > 0: consec_loss = 0
                    continue
                trade_payload = _close_all_layers(
                    entry_layers=entry_layers,
                    current_price=p,
                    reason="tp_turning_point" if turning_take_profit else ("tp_bias" if b50 > tp_bias else "tp_roi"),
                    timestamp=timestamps[i] if i < len(timestamps) else "",
                    initial_capital=initial_capital,
                )
                cash += p * position
                result.trades.append(trade_payload)
                position = 0; entry_layers = []
                if float(trade_payload.get("pnl") or 0.0) > 0: consec_loss = 0
                continue

        top_k_pass = _passes_rolling_top_k_gate(conf, top_k_history, top_k_percent)

        # 進場: 4H 過濾 + ML 信心 > 閾值 + quality-based layers
        turning_gate_ok = (not turning_cfg.get("enabled")) or float(bottom_score_value) >= float(turning_cfg.get("bottom_score_min") or 0.0)
        can_enter = (
            regime_gate != "BLOCK"
            and allowed_layers > 0
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and top_k_pass
            and turning_gate_ok
            and b50 <= bias50_max
            and conf >= conf_min
            and b200 >= regime_min
        )

        if can_enter and position == 0 and len(layers_pct) > 0 and allowed_layers >= 1:
            buy_amt = min(cash, _layer_budget(0, layers_pct, initial_capital, capital_cfg))
            if buy_amt > 0:
                coins = buy_amt / p
                cash -= buy_amt; position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 1,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                    "regime_gate": regime_gate,
                    "entry_quality": entry_quality,
                    "allowed_layers": allowed_layers,
                    "capital_mode": capital_cfg.get("mode"),
                })
        elif can_enter and len(entry_layers) == 1 and len(layers_pct) > 1 and allowed_layers >= 2:
            layer2_bias = entry.get("layer2_bias_max", bias50_max - 1.5)
            if b50 <= layer2_bias and _reserve_unlocked(capital_cfg, entry_layers, p):
                buy_amt = min(cash, _layer_budget(1, layers_pct, initial_capital, capital_cfg))
                if buy_amt > 0:
                    coins = buy_amt / p
                    cash -= buy_amt; position += coins
                    entry_layers.append({
                        "price": p, "coins": coins, "layer": 2,
                        "timestamp": timestamps[i] if i < len(timestamps) else "",
                        "regime": regime,
                        "regime_gate": regime_gate,
                        "entry_quality": entry_quality,
                        "allowed_layers": allowed_layers,
                        "capital_mode": capital_cfg.get("mode"),
                    })
        elif can_enter and len(entry_layers) == 2 and len(layers_pct) > 2 and allowed_layers >= 3:
            layer3_bias = entry.get("layer3_bias_max", bias50_max - 3.0)
            if b50 <= layer3_bias and _reserve_unlocked(capital_cfg, entry_layers, p):
                buy_amt = min(cash, _layer_budget(2, layers_pct, initial_capital, capital_cfg))
                if buy_amt > 0:
                    coins = buy_amt / p
                    cash -= buy_amt; position += coins
                    entry_layers.append({
                        "price": p, "coins": coins, "layer": 3,
                        "timestamp": timestamps[i] if i < len(timestamps) else "",
                        "regime": regime,
                        "regime_gate": regime_gate,
                        "entry_quality": entry_quality,
                        "allowed_layers": allowed_layers,
                        "capital_mode": capital_cfg.get("mode"),
                    })

        if (
            top_k_percent > 0
            and regime_gate != "BLOCK"
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and conf >= conf_min
        ):
            top_k_history.append(conf)

        if equity > peak_equity: peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd: max_dd = dd
        invested_value = position * p
        result.equity_curve.append({
            "timestamp": timestamps[i] if i < len(timestamps) else "",
            "equity": round(equity, 2),
            "position_pct": round((invested_value / initial_capital) if initial_capital > 0 else 0.0, 4),
            "position_layers": len(entry_layers),
            "regime_gate": regime_gate,
            "structure_bucket": structure_bucket,
            "entry_quality": entry_quality,
            "allowed_layers": allowed_layers,
        })

    if position > 0 and entry_layers:
        trade_payload = _close_all_layers(
            entry_layers=entry_layers,
            current_price=prices[-1],
            reason="end_of_data",
            timestamp=timestamps[-1] if timestamps else "",
            initial_capital=initial_capital,
        )
        cash += prices[-1] * position
        result.trades.append(trade_payload)

    result.total_trades = len(result.trades)
    if result.total_trades > 0:
        result.wins = sum(1 for t in result.trades if t["pnl"] > 0)
        result.losses = result.total_trades - result.wins
        result.win_rate = result.wins / result.total_trades
        win_pnls = [t["pnl"] for t in result.trades if t["pnl"] > 0]
        loss_pnls = [t["pnl"] for t in result.trades if t["pnl"] <= 0]
        result.avg_win = sum(win_pnls) / max(len(win_pnls), 1)
        result.avg_loss = sum(loss_pnls) / max(len(loss_pnls), 1)
        result.total_pnl = sum(t["pnl"] for t in result.trades)
        result.roi = result.total_pnl / initial_capital
        gross_profit = sum(t["pnl"] for t in result.trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in result.trades if t["pnl"] <= 0))
        result.profit_factor = gross_profit / max(gross_loss, 0.01)

    result.max_drawdown = max_dd
    result.max_consecutive_losses = max_consec_loss
    return result


# ─── Strategy Persistence ───

def save_strategy(name: str, strategy_def: Dict, results: Optional[Dict] = None) -> str:
    """儲存策略定義為 JSON。"""
    now = datetime.now().isoformat()
    path = _strategy_path(name)
    data = _sanitize_strategy_record(
        {
            "schema_version": STRATEGY_SCHEMA_VERSION,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "definition": strategy_def,
            "last_results": results,
            "run_count": 1 if results is not None else 0,
            "is_internal": _is_internal_strategy(name),
            "metadata": _build_strategy_metadata(name, strategy_def),
        },
        fallback_name=name,
    )
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                existing_raw = json.load(f)
            existing = _sanitize_strategy_record(existing_raw, fallback_name=name) or {}
            data["created_at"] = existing.get("created_at", data["created_at"])
            prev_runs = _coerce_int(existing.get("run_count"), 0)
            data["run_count"] = prev_runs + 1 if results is not None else prev_runs
            if results is None and existing.get("last_results") is not None:
                data["last_results"] = existing.get("last_results")
            data["is_internal"] = _is_internal_strategy(name)
            if results is None and existing.get("metadata"):
                data["metadata"] = existing.get("metadata")
        except Exception:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(path)


def load_all_strategies(include_internal: bool = False) -> List[Dict]:
    """載入所有已儲存的策略。"""
    strategies = []
    if not STRATEGIES_DIR.exists():
        return strategies
    for path in sorted(STRATEGIES_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            data = _sanitize_strategy_record(raw, fallback_name=path.stem.replace("_", " "))
            if not data:
                continue
            if data.get("is_internal") and not include_internal:
                continue
            strategies.append(data)
        except Exception:
            continue
    def sort_key(s):
        r = s.get("last_results") or {}
        decision_quality = _coerce_float(r.get("avg_decision_quality_score"))
        expected_win_rate = _coerce_float(r.get("avg_expected_win_rate"))
        drawdown_penalty = _coerce_float(r.get("avg_expected_drawdown_penalty"))
        roi = _coerce_float(r.get("roi"))
        trades = _coerce_int(r.get("total_trades"), 0)
        return (
            decision_quality if decision_quality is not None else -999,
            expected_win_rate if expected_win_rate is not None else -999,
            -(drawdown_penalty if drawdown_penalty is not None else 999),
            roi if roi is not None else -999,
            trades,
        )
    strategies.sort(key=sort_key, reverse=True)
    return strategies


def load_strategy(name: str) -> Optional[Dict]:
    """載入單一策略。"""
    path = _strategy_path(name)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return _sanitize_strategy_record(data, fallback_name=name)
    return None


def delete_strategy(name: str) -> bool:
    """刪除策略。"""
    path = _strategy_path(name)
    if path.exists():
        path.unlink()
        return True
    return False
