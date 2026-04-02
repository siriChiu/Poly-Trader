"""
回測引擎 v4 — sell-win aware, regime aware, cost model, buy & hold benchmark
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized, RawMarketData
from model.predictor import load_predictor
from utils.logger import setup_logger

logger = setup_logger(__name__)


def calc_fib_levels(high: float, low: float) -> Dict[str, float]:
    diff = high - low
    return {
        "0.0": low, "0.236": low + diff * 0.236,
        "0.382": low + diff * 0.382, "0.5": low + diff * 0.5,
        "0.618": low + diff * 0.618, "0.786": low + diff * 0.786,
        "1.0": high,
    }

PYRAMID_TIERS = [
    {"conf": 0.65, "ratio": 0.05, "label": "Tier1"},
    {"conf": 0.70, "ratio": 0.04, "label": "Tier2"},
    {"conf": 0.75, "ratio": 0.03, "label": "Tier3"},
    {"conf": 0.80, "ratio": 0.03, "label": "Tier4"},
]
MAX_TOTAL_EXPOSURE = 0.20


class BacktestEngine:
    def __init__(self, session, initial_capital=10000, confidence_threshold=0.65,
                 max_position_ratio=0.20, stop_loss_pct=0.03, take_profit_pct=0.06,
                 symbol="BTC/USDT", pyramid_mode="confidence",
                 commission_rate=0.001, slippage_bps=5):
        self.session = session
        self.initial_capital = initial_capital
        self.confidence_threshold = confidence_threshold
        self.max_position_ratio = max_position_ratio
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.symbol = symbol
        self.pyramid_mode = pyramid_mode
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps
        self.predictor = load_predictor()
        self.positions: List[Dict] = []
        self.equity_curve = []
        self.trade_log = []
        self.total_commissions = 0.0
        self.total_slippage_cost = 0.0

    def _apply_cost(self, notional: float) -> float:
        comm = notional * self.commission_rate
        slip = notional * (self.slippage_bps / 10000.0)
        self.total_commissions += comm
        self.total_slippage_cost += slip
        return comm + slip

    def _total_position_value(self, price):
        return sum(p["qty"] * price for p in self.positions)

    def _avg_entry_price(self):
        if not self.positions: return 0.0
        tq = sum(p["qty"] for p in self.positions)
        tc = sum(p["qty"] * p["entry_price"] for p in self.positions)
        return tc / tq if tq > 0 else 0.0

    def load_historical_features(self, start_date=None, end_date=None):
        q = self.session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
        if start_date: q = q.filter(FeaturesNormalized.timestamp >= start_date)
        if end_date: q = q.filter(FeaturesNormalized.timestamp <= end_date)
        rows = q.all()
        if not rows: return pd.DataFrame()
        data = [{"timestamp": r.timestamp, "symbol": getattr(r, "symbol", self.symbol),
                 "feat_eye": r.feat_eye, "feat_ear": r.feat_ear, "feat_nose": r.feat_nose,
                 "feat_tongue": r.feat_tongue, "feat_body": r.feat_body,
                 "feat_pulse": r.feat_pulse, "feat_aura": r.feat_aura, "feat_mind": r.feat_mind,
                 "feat_whisper": getattr(r, "feat_whisper", 0.0), "feat_tone": getattr(r, "feat_tone", 0.0),
                 "feat_chorus": getattr(r, "feat_chorus", 0.0), "feat_hype": getattr(r, "feat_hype", 0.0),
                 "feat_oracle": getattr(r, "feat_oracle", 0.0), "feat_shock": getattr(r, "feat_shock", 0.0),
                 "feat_tide": getattr(r, "feat_tide", 0.0), "feat_storm": getattr(r, "feat_storm", 0.0),
                 "regime_label": getattr(r, "regime_label", None)} for r in rows]
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def load_historical_prices(self, timestamps):
        rows = self.session.query(RawMarketData).filter(
            RawMarketData.symbol == self.symbol.replace("/", "")).order_by(RawMarketData.timestamp).all()
        if not rows: return pd.Series(dtype=float)
        prices = {r.timestamp: r.close_price for r in rows}
        return pd.Series(prices).reindex(timestamps, method="ffill")

    def _should_pyramid_confidence(self, confidence, equity, price):
        tier = len(self.positions)
        if tier >= len(PYRAMID_TIERS): return None
        nt = PYRAMID_TIERS[tier]
        if confidence >= nt["conf"]:
            exp = self._total_position_value(price) / equity if equity > 0 else 0
            if exp + nt["ratio"] <= MAX_TOTAL_EXPOSURE:
                return nt
        return None

    def _should_pyramid_fibonacci(self, confidence, price, price_series, ts):
        if confidence < self.confidence_threshold: return None
        if len(self.positions) >= len(PYRAMID_TIERS): return None
        lb = price_series.loc[:ts].tail(48)
        if len(lb) < 10: return None
        high, low = lb.max(), lb.min()
        fib = calc_fib_levels(high, low)
        for key in ["0.618", "0.5", "0.382"]:
            if abs(price - fib[key]) / fib[key] < 0.005:
                return PYRAMID_TIERS[len(self.positions)]
        return None

    def _sell_win(self, sell_pnl: float) -> int:
        return 1 if sell_pnl > 0 else 0

    def run(self, features_df, price_series):
        logger.info(
            f"Backtest v4: capital={self.initial_capital}, mode={self.pyramid_mode}, n={len(features_df)}, commission={self.commission_rate}, slippage={self.slippage_bps}bps"
        )
        equity = self.initial_capital
        first_price = None

        for _, row in features_df.iterrows():
            ts = row["timestamp"]
            price = price_series.get(ts, None)
            if isinstance(price, pd.Series): price = price.iloc[-1]
            if price is None or (isinstance(price, float) and pd.isna(price)): continue
            if first_price is None:
                first_price = price

            features = {c: row.get(c) for c in ["feat_eye","feat_ear","feat_nose","feat_tongue","feat_body","feat_pulse","feat_aura","feat_mind","feat_whisper","feat_tone","feat_chorus","feat_hype","feat_oracle","feat_shock","feat_tide","feat_storm"]}
            confidence = self.predictor.predict_proba(features)
            regime = row.get("regime_label", None)

            if self.positions:
                avg = self._avg_entry_price()
                pnl_pct = (price - avg) / avg
                sell, reason = False, ""
                if pnl_pct <= -self.stop_loss_pct: sell, reason = True, "STOP_LOSS"
                elif pnl_pct >= self.take_profit_pct: sell, reason = True, "TAKE_PROFIT"
                elif confidence < 0.4 and pnl_pct > 0.01: sell, reason = True, "SIGNAL_EXIT"
                if sell:
                    gross_pnl = sum((price - p["entry_price"]) * p["qty"] for p in self.positions)
                    notional = sum(price * p["qty"] for p in self.positions)
                    cost = self._apply_cost(notional)
                    net_pnl = gross_pnl - cost
                    equity += net_pnl
                    self.trade_log.append({
                        "timestamp": ts, "action": "SELL", "price": price,
                        "amount": sum(p["qty"] for p in self.positions),
                        "confidence": confidence, "pnl": net_pnl,
                        "gross_pnl": gross_pnl, "commission_slippage": cost,
                        "reason": reason, "tiers_closed": len(self.positions),
                        "regime_label": regime, "sell_win": self._sell_win(net_pnl)
                    })
                    self.positions = []

            if self.pyramid_mode == "confidence":
                ti = self._should_pyramid_confidence(confidence, equity, price)
            else:
                ti = self._should_pyramid_fibonacci(confidence, price, price_series, ts)
            if ti:
                sz = equity * ti["ratio"]
                cost = self._apply_cost(sz)
                net_sz = sz - cost
                qty = round(net_sz / price, 4)
                if qty > 0:
                    self.positions.append({"qty": qty, "entry_price": price, "tier": ti["label"]})
                    self.trade_log.append({
                        "timestamp": ts, "action": "BUY", "price": price,
                        "amount": qty, "confidence": confidence,
                        "tier": ti["label"], "tier_num": len(self.positions),
                        "commission_slippage": cost, "regime_label": regime
                    })

            if self.positions:
                unreal = sum((price - p["entry_price"]) * p["qty"] for p in self.positions)
                real = sum(t.get("pnl", 0) for t in self.trade_log if t.get("pnl") is not None)
                equity = self.initial_capital + real + unreal
            else:
                equity = self.initial_capital + sum(t.get("pnl", 0) for t in self.trade_log if t.get("pnl") is not None)
            self.equity_curve.append({"timestamp": ts, "equity": equity})

        if self.positions:
            lp = price_series.iloc[-1]
            gross_pnl = sum((lp - p["entry_price"]) * p["qty"] for p in self.positions)
            notional = sum(lp * p["qty"] for p in self.positions)
            cost = self._apply_cost(notional)
            net_pnl = gross_pnl - cost
            self.trade_log.append({
                "timestamp": features_df.iloc[-1]["timestamp"], "action": "SELL",
                "price": lp, "amount": sum(p["qty"] for p in self.positions),
                "pnl": net_pnl, "gross_pnl": gross_pnl,
                "commission_slippage": cost, "reason": "END",
                "sell_win": self._sell_win(net_pnl), "regime_label": features_df.iloc[-1].get("regime_label", None)
            })
        return self._build_results(features_df, price_series, first_price)

    def _build_results(self, features_df, price_series, first_price):
        eq = pd.DataFrame(self.equity_curve).set_index("timestamp") if self.equity_curve else pd.DataFrame()
        bh_curve = None
        bh_return = 0.0
        if first_price and not eq.empty and not price_series.empty:
            last_price = price_series.iloc[-1]
            bh_prices = price_series.reindex(eq.index, method="ffill")
            bh_curve = self.initial_capital * (bh_prices / first_price)
            bh_curve.name = "buy_hold"
            bh_return = (last_price / first_price - 1) * 100

        sells = [t for t in self.trade_log if t.get("pnl") is not None]
        wins = [t for t in sells if t.get("pnl", 0) > 0]
        tr = (eq["equity"].iloc[-1] / self.initial_capital - 1) * 100 if not eq.empty else 0
        pk = eq["equity"].expanding().max() if not eq.empty else pd.Series()
        dd = abs(((eq["equity"] - pk) / pk).min()) * 100 if not eq.empty else 0
        alpha = tr - bh_return
        sell_win_rate = len([t for t in sells if t.get("sell_win", 0) == 1]) / len(sells) if sells else 0
        regime_win = {}
        for t in sells:
            regime = t.get("regime_label") or "unknown"
            regime_win.setdefault(regime, {"wins": 0, "total": 0})
            regime_win[regime]["total"] += 1
            regime_win[regime]["wins"] += 1 if t.get("sell_win", 0) == 1 else 0
        regime_sell_win_rate = {k: (v["wins"] / v["total"] if v["total"] else 0) for k, v in regime_win.items()}

        return {
            "equity_curve": eq, "buy_hold_curve": bh_curve,
            "trade_log": pd.DataFrame(self.trade_log),
            "final_equity": eq["equity"].iloc[-1] if not eq.empty else self.initial_capital,
            "initial_capital": self.initial_capital,
            "total_trades": len(sells),
            "total_buys": len([t for t in self.trade_log if t["action"] == "BUY"]),
            "win_rate": len(wins) / len(sells) * 100 if sells else 0,
            "sell_win_rate": sell_win_rate * 100,
            "total_return": tr, "max_drawdown": dd,
            "buy_hold_return": bh_return, "alpha": alpha,
            "total_commissions": self.total_commissions,
            "total_slippage_cost": self.total_slippage_cost,
            "total_trading_cost": self.total_commissions + self.total_slippage_cost,
            "avg_tiers": sum(t.get("tiers_closed", 1) for t in sells) / len(sells) if sells else 0,
            "regime_sell_win_rate": regime_sell_win_rate,
        }


def run_backtest(session, start_date=None, end_date=None, initial_capital=10000,
                 confidence_threshold=0.65, max_position_ratio=0.20,
                 stop_loss_pct=0.03, take_profit_pct=0.06, symbol="BTC/USDT",
                 pyramid_mode="confidence", commission_rate=0.001, slippage_bps=5):
    bt = BacktestEngine(session, initial_capital, confidence_threshold,
                        max_position_ratio, stop_loss_pct, take_profit_pct,
                        symbol, pyramid_mode, commission_rate, slippage_bps)
    feat = bt.load_historical_features(start_date, end_date)
    if feat.empty: return None
    px = bt.load_historical_prices(feat["timestamp"].tolist())
    if px.empty: return None
    return bt.run(feat, px)
