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
)
RESULT_INT_FIELDS = ("total_trades", "wins", "losses", "max_consecutive_losses")


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
    cleaned = {"run_at": results.get("run_at")}
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
) -> BacktestResult:
    """純規則回測：bias50 + 特徵條件 + 金字塔 + SL/TP。"""
    # ── 解包參數 ──
    entry = params.get("entry", {})
    bias50_max   = entry.get("bias50_max", -3.0)     # bias50 上限才進場
    nose_max     = entry.get("nose_max", 0.40)        # nose (RSI) 上限
    pulse_min    = entry.get("pulse_min", 0.0)        # pulse 下限（放量確認）
    regime_min   = entry.get("regime_bias200_min", -10.0)  # bias200 下限（允許熊市做多？）

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
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

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        n_val = nose[i] if i < len(nose) else 0.5
        p_val = pulse[i] if i < len(pulse) else 0.5
        e_val = ear[i] if i < len(ear) else 0.0
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"

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
                })
                position = 0
                entry_layers = []
                if pnl > 0:
                    consec_loss = 0
                continue

        # ── 進場判定 ──
        can_enter = (b50 <= bias50_max and n_val <= nose_max
                     and p_val >= pulse_min and b200 >= regime_min)

        if can_enter and position == 0 and len(layers_pct) > 0:
            # Layer 1
            buy_amt = initial_capital * layers_pct[0]
            coins = buy_amt / p
            cash -= buy_amt
            position += coins
            entry_layers.append({
                "price": p, "coins": coins, "layer": 1,
                "timestamp": timestamps[i] if i < len(timestamps) else "",
                "regime": regime,
            })

        elif can_enter and len(entry_layers) == 1 and len(layers_pct) > 1:
            # Layer 2: 需要 bias50 更低
            layer2_bias = entry.get("layer2_bias_max", bias50_max - 1.5)
            if b50 <= layer2_bias:
                buy_amt = initial_capital * layers_pct[1]
                coins = buy_amt / p
                cash -= buy_amt
                position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 2,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                })

        elif can_enter and len(entry_layers) == 2 and len(layers_pct) > 2:
            # Layer 3: 需要 bias50 更低
            layer3_bias = entry.get("layer3_bias_max", bias50_max - 3.0)
            dist_sl_ok = True  # 如果提供了 swing_low 條件
            if b50 <= layer3_bias:
                buy_amt = initial_capital * layers_pct[2]
                coins = buy_amt / p
                cash -= buy_amt
                position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 3,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                })

        # 更新最大回撤
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

        result.equity_curve.append({"timestamp": timestamps[i] if i < len(timestamps) else "", "equity": round(equity, 2)})

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
) -> BacktestResult:
    """混合模式：4H 規則過濾 + ML 信心分數入場。"""
    entry = params.get("entry", {})
    bias50_max   = entry.get("bias50_max", -3.0)
    conf_min     = entry.get("confidence_min", 0.35)  # ML 信心閾值
    regime_min   = entry.get("regime_bias200_min", -10.0)

    layers_pct   = params.get("layers", [0.20, 0.30, 0.50])
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

    for i in range(len(prices)):
        p = prices[i]
        b50 = bias50[i] if i < len(bias50) else 0
        b200 = bias200[i] if i < len(bias200) else 0
        conf = model_confidence[i] if i < len(model_confidence) else 0.5
        regime = regimes[i] if regimes and i < len(regimes) and regimes[i] else "unknown"

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
                })
                position = 0; entry_layers = []
                if pnl > 0: consec_loss = 0
                continue

        # 進場: 4H 過濾 + ML 信心 > 閾值
        can_enter = (b50 <= bias50_max and conf >= conf_min and b200 >= regime_min)

        if can_enter and position == 0 and len(layers_pct) > 0:
            buy_amt = initial_capital * layers_pct[0]
            coins = buy_amt / p
            cash -= buy_amt; position += coins
            entry_layers.append({
                "price": p, "coins": coins, "layer": 1,
                "timestamp": timestamps[i] if i < len(timestamps) else "",
                "regime": regime,
            })
        elif can_enter and len(entry_layers) == 1 and len(layers_pct) > 1:
            layer2_bias = entry.get("layer2_bias_max", bias50_max - 1.5)
            if b50 <= layer2_bias:
                buy_amt = initial_capital * layers_pct[1]
                coins = buy_amt / p
                cash -= buy_amt; position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 2,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                })
        elif can_enter and len(entry_layers) == 2 and len(layers_pct) > 2:
            layer3_bias = entry.get("layer3_bias_max", bias50_max - 3.0)
            if b50 <= layer3_bias:
                buy_amt = initial_capital * layers_pct[2]
                coins = buy_amt / p
                cash -= buy_amt; position += coins
                entry_layers.append({
                    "price": p, "coins": coins, "layer": 3,
                    "timestamp": timestamps[i] if i < len(timestamps) else "",
                    "regime": regime,
                })

        if equity > peak_equity: peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd: max_dd = dd
        result.equity_curve.append({"timestamp": timestamps[i] if i < len(timestamps) else "", "equity": round(equity, 2)})

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
        roi = _coerce_float(r.get("roi"))
        return roi if roi is not None else -999
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
