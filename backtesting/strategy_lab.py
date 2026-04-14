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
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

STRATEGIES_DIR = Path(os.path.expanduser("~/.hermes/poly-trader/strategies"))
STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_SCHEMA_VERSION = 2
INTERNAL_STRATEGY_PREFIXES = ("tmp_", "debug_", "scratch_")
INTERNAL_STRATEGY_NAMES = {"test", "unnamed", "unnamed_strategy"}


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
    return (name or "unnamed_strategy").strip().replace(" ", "_").lower()


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

# Heartbeat #715: the bull ALLOW + D lane still contained a small but fully losing
# overextended 4H pocket. Mirror predictor.py so Strategy Lab/backtests and live
# inference share the same ALLOW-lane veto semantics.
OVEREXTENDED_4H_BB_PCT_B_MIN = 1.0
OVEREXTENDED_4H_DIST_BB_LOWER_MIN = 10.0
OVEREXTENDED_4H_DIST_SWING_LOW_MIN = 11.0


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
    if str(capital_management.get("mode") or CAPITAL_MODE_CLASSIC) == CAPITAL_MODE_RESERVE:
        entry_fraction = (_coerce_float(capital_management.get("base_entry_fraction")) or 0.10) * 100
        reserve_trigger = (_coerce_float(capital_management.get("reserve_trigger_drawdown")) or 0.10) * 100
        description_bits.append(f"先用 {entry_fraction:.0f}% 建倉，回撤達 {reserve_trigger:.0f}% 後才啟用後守資金")

    return {
        "title": title,
        "description": "；".join(description_bits),
        "strategy_type": definition.get("type") or "rule_based",
        "model_name": model_name,
        "model_summary": MODEL_SUMMARY_MAP.get(model_name, f"{model_name}：自訂交易模型。"),
    }


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
    return cleaned


def _sanitize_strategy_record(data: Dict[str, Any], fallback_name: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    name = (data.get("name") or fallback_name or "Unnamed Strategy").strip()
    definition = _sanitize_definition(data.get("definition"))
    last_results = _sanitize_results(data.get("last_results"))
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
        "is_internal": bool(data.get("is_internal")) or _is_internal_strategy(name),
        "metadata": _sanitize_json_like(data.get("metadata")) or _build_strategy_metadata(name, definition),
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
    if base_gate == "ALLOW" and structure_quality < 0.35:
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



def _compute_entry_quality(
    bias50_value: float,
    nose_value: float,
    pulse_value: float,
    ear_value: float,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> float:
    bias_score = _clamp01((-bias50_value + 2.4) / 5.0)
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

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
    capital_cfg  = _capital_management_config(params)
    stop_loss    = params.get("stop_loss", -0.05)     # -5%
    tp_bias      = params.get("take_profit_bias", 4.0)  # bias50 > 4% 止盈
    tp_roi       = params.get("take_profit_roi", 0.08)  # ROI > 8% 止盈

    cash = initial_capital
    position = 0.0
    entry_layers: List[Dict] = []  # {price, coins, layer}
    result = BacktestResult()
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    consec_loss = 0
    max_consec_loss = 0

    top_k_cutoff = None
    if top_k_percent > 0:
        entry_quality_series = []
        for i in range(len(prices)):
            regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
            if not _regime_allowed(regime, allowed_regimes):
                continue
            b200 = bias200[i] if i < len(bias200) else 0
            bb_pct_b_val = bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None
            dist_bb_lower_val = dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None
            dist_swing_low_val = dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None
            regime_gate = _compute_regime_gate(
                b200,
                regime,
                regime_min,
                bb_pct_b_val,
                dist_bb_lower_val,
                dist_swing_low_val,
            )
            if regime_gate == "BLOCK":
                continue
            b50 = bias50[i] if i < len(bias50) else 0
            n_val = nose[i] if i < len(nose) else 0.5
            p_val = pulse[i] if i < len(pulse) else 0.5
            e_val = ear[i] if i < len(ear) else 0.0
            quality = _compute_entry_quality(
                b50,
                n_val,
                p_val,
                e_val,
                bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None,
                dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None,
                dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None,
            )
            if quality >= entry_quality_min:
                entry_quality_series.append(quality)
        top_k_cutoff = _top_k_cutoff(entry_quality_series, top_k_percent)

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        n_val = nose[i] if i < len(nose) else 0.5
        p_val = pulse[i] if i < len(pulse) else 0.5
        e_val = ear[i] if i < len(ear) else 0.0
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
        regime_gate = _compute_regime_gate(b200, regime, regime_min)
        entry_quality = _compute_entry_quality(
            b50,
            n_val,
            p_val,
            e_val,
            bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None,
            dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None,
            dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None,
        )
        allowed_layers = _allowed_layers_for_signal(regime_gate, entry_quality, len(layers_pct))

        # 更新權益
        if position > 0:
            avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
            equity = cash + position * p

        # ── 止損 ──
        if position > 0 and entry_layers:
            avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
            pnl_pct = (p - avg) / avg
            if pnl_pct <= stop_loss:
                pnl = (p - avg) * position
                cash += p * position
                result.trades.append({
                    "entry": avg, "exit": p, "pnl": pnl,
                    "roi": pnl / initial_capital, "layers": len(entry_layers),
                    "reason": "stop_loss", "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
                    "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
                    "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
                    "entry_quality": entry_layers[0].get("entry_quality"),
                    "allowed_layers": entry_layers[0].get("allowed_layers"),
                    "capital_mode": entry_layers[0].get("capital_mode"),
                })
                position = 0
                entry_layers = []
                consec_loss += 1
                if consec_loss > max_consec_loss:
                    max_consec_loss = consec_loss
                continue

        # ── 止盈 ──
        if position > 0 and entry_layers:
            avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
            pnl_pct = (p - avg) / avg
            if b50 > tp_bias or pnl_pct > tp_roi:
                pnl = (p - avg) * position
                cash += p * position
                reason = "tp_bias" if b50 > tp_bias else "tp_roi"
                result.trades.append({
                    "entry": avg, "exit": p, "pnl": pnl,
                    "roi": pnl / initial_capital, "layers": len(entry_layers),
                    "reason": reason, "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
                    "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
                    "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
                    "entry_quality": entry_layers[0].get("entry_quality"),
                    "allowed_layers": entry_layers[0].get("allowed_layers"),
                    "capital_mode": entry_layers[0].get("capital_mode"),
                })
                position = 0
                entry_layers = []
                if pnl > 0:
                    consec_loss = 0
                continue

        # ── 進場判定 ──
        can_enter = (
            regime_gate != "BLOCK"
            and allowed_layers > 0
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and (top_k_cutoff is None or entry_quality >= top_k_cutoff)
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
        })

    # 平倉未結部位
    if position > 0 and entry_layers:
        avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
        pnl = (prices[-1] - avg) * position
        cash += prices[-1] * position
        result.trades.append({
            "entry": avg, "exit": prices[-1], "pnl": pnl,
            "roi": pnl / initial_capital, "layers": len(entry_layers),
            "reason": "end_of_data", "timestamp": timestamps[-1] if timestamps else "",
            "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
            "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
            "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
            "entry_quality": entry_layers[0].get("entry_quality"),
            "allowed_layers": entry_layers[0].get("allowed_layers"),
        })

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
) -> BacktestResult:
    """混合模式：4H 規則過濾 + ML 信心分數入場。"""
    entry = params.get("entry", {})
    bias50_max   = entry.get("bias50_max", -3.0)
    conf_min     = entry.get("confidence_min", 0.35)  # ML 信心閾值
    regime_min   = entry.get("regime_bias200_min", -10.0)
    entry_quality_min = float(entry.get("entry_quality_min", 0.0) or 0.0)
    allowed_regimes = _normalize_allowed_regimes(entry.get("allowed_regimes"))
    top_k_percent = float(entry.get("top_k_percent", 0.0) or 0.0)

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
    capital_cfg  = _capital_management_config(params)
    stop_loss    = params.get("stop_loss", -0.05)
    tp_bias      = params.get("take_profit_bias", 4.0)
    tp_roi       = params.get("take_profit_roi", 0.08)

    cash = initial_capital
    position = 0.0
    entry_layers: List[Dict] = []
    result = BacktestResult()
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    consec_loss = 0
    max_consec_loss = 0

    top_k_cutoff = None
    if top_k_percent > 0:
        eligible_confidence = []
        for i in range(len(prices)):
            regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
            if not _regime_allowed(regime, allowed_regimes):
                continue
            b200 = bias200[i] if i < len(bias200) else 0
            bb_pct_b_val = bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None
            dist_bb_lower_val = dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None
            dist_swing_low_val = dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None
            regime_gate = _compute_regime_gate(
                b200,
                regime,
                regime_min,
                bb_pct_b_val,
                dist_bb_lower_val,
                dist_swing_low_val,
            )
            if regime_gate == "BLOCK":
                continue
            b50 = bias50[i] if i < len(bias50) else 0
            conf = model_confidence[i] if i < len(model_confidence) else 0.5
            base_quality = _compute_entry_quality(
                b50,
                nose[i] if i < len(nose) else 0.5,
                pulse[i] if i < len(pulse) else 0.5,
                ear[i] if i < len(ear) else 0.0,
                bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None,
                dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None,
                dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None,
            )
            quality = round(0.6 * _clamp01(conf) + 0.4 * base_quality, 4)
            if quality >= entry_quality_min and conf >= conf_min:
                eligible_confidence.append(conf)
        top_k_cutoff = _top_k_cutoff(eligible_confidence, top_k_percent)

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        conf = model_confidence[i] if i < len(model_confidence) else 0.5
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"
        regime_gate = _compute_regime_gate(b200, regime, regime_min)
        entry_quality = round(
            0.6 * _clamp01(conf)
            + 0.4
            * _compute_entry_quality(
                b50,
                nose[i] if i < len(nose) else 0.5,
                pulse[i] if i < len(pulse) else 0.5,
                ear[i] if i < len(ear) else 0.0,
                bb_pct_b_4h[i] if bb_pct_b_4h and i < len(bb_pct_b_4h) else None,
                dist_bb_lower_4h[i] if dist_bb_lower_4h and i < len(dist_bb_lower_4h) else None,
                dist_swing_low_4h[i] if dist_swing_low_4h and i < len(dist_swing_low_4h) else None,
            ),
            4,
        )
        allowed_layers = _allowed_layers_for_signal(regime_gate, entry_quality, len(layers_pct))

        if position > 0 and entry_layers:
            avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
            equity = cash + position * p

            # 止損
            pnl_pct = (p - avg) / avg
            if pnl_pct <= stop_loss:
                pnl = (p - avg) * position
                cash += p * position
                result.trades.append({
                    "entry": avg, "exit": p, "pnl": pnl,
                    "roi": pnl / initial_capital, "layers": len(entry_layers),
                    "reason": "stop_loss", "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
                    "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
                    "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
                    "entry_quality": entry_layers[0].get("entry_quality"),
                    "allowed_layers": entry_layers[0].get("allowed_layers"),
                    "capital_mode": entry_layers[0].get("capital_mode"),
                })
                position = 0; entry_layers = []
                consec_loss += 1
                max_consec_loss = max(max_consec_loss, consec_loss)
                continue

            # 止盈
            if b50 > tp_bias or pnl_pct > tp_roi:
                pnl = (p - avg) * position
                cash += p * position
                reason = "tp_bias" if b50 > tp_bias else "tp_roi"
                result.trades.append({
                    "entry": avg, "exit": p, "pnl": pnl,
                    "roi": pnl / initial_capital, "layers": len(entry_layers),
                    "reason": reason, "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
                    "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
                    "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
                    "entry_quality": entry_layers[0].get("entry_quality"),
                    "allowed_layers": entry_layers[0].get("allowed_layers"),
                    "capital_mode": entry_layers[0].get("capital_mode"),
                })
                position = 0; entry_layers = []
                if pnl > 0: consec_loss = 0
                continue

        # 進場: 4H 過濾 + ML 信心 > 閾值 + quality-based layers
        can_enter = (
            regime_gate != "BLOCK"
            and allowed_layers > 0
            and _regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and (top_k_cutoff is None or conf >= top_k_cutoff)
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

        if equity > peak_equity: peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd: max_dd = dd
        invested_value = position * p
        result.equity_curve.append({
            "timestamp": timestamps[i] if i < len(timestamps) else "",
            "equity": round(equity, 2),
            "position_pct": round((invested_value / initial_capital) if initial_capital > 0 else 0.0, 4),
            "position_layers": len(entry_layers),
        })

    if position > 0 and entry_layers:
        avg = sum(l["price"] * l["coins"] for l in entry_layers) / sum(l["coins"] for l in entry_layers)
        pnl = (prices[-1] - avg) * position
        cash += prices[-1] * position
        result.trades.append({
            "entry": avg, "exit": prices[-1], "pnl": pnl,
            "roi": pnl / initial_capital, "layers": len(entry_layers),
            "reason": "end_of_data", "timestamp": timestamps[-1] if timestamps else "",
            "entry_timestamp": entry_layers[0].get("timestamp", "") if entry_layers else "",
            "entry_regime": entry_layers[0].get("regime", "unknown") if entry_layers else "unknown",
            "regime_gate": entry_layers[0].get("regime_gate", "ALLOW") if entry_layers else "ALLOW",
            "entry_quality": entry_layers[0].get("entry_quality"),
            "allowed_layers": entry_layers[0].get("allowed_layers"),
        })

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
            data["is_internal"] = existing.get("is_internal", False) or data.get("is_internal", False)
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
