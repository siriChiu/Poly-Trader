"""
回測引擎：在歷史數據上模擬策略執行
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.models import FeaturesNormalized, RawMarketData
from model.predictor import DummyPredictor, load_latest_features
from execution.risk_control import check_position_size, round_down, calculate_stop_loss
from utils.logger import setup_logger

logger = setup_logger(__name__)

class BacktestEngine:
    def __init__(
        self,
        session: Session,
        initial_capital: float = 10000.0,
        confidence_threshold: float = 0.7,
        max_position_ratio: float = 0.05,
        stop_loss_pct: float = 0.03,
        symbol: str = "BTC/USDT"
    ):
        self.session = session
        self.initial_capital = initial_capital
        self.confidence_threshold = confidence_threshold
        self.max_position_ratio = max_position_ratio
        self.stop_loss_pct = stop_loss_pct
        self.symbol = symbol

        self.predictor = DummyPredictor()
        self.capital = initial_capital
        self.position = 0.0  # 持有数量
        self.entry_price = 0.0
        self.equity_curve = []  # list of (timestamp, equity)
        self.trade_log = []     # list of trade dicts

    def load_historical_features(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """載入歷史特徵數據"""
        query = self.session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
        if start_date:
            query = query.filter(FeaturesNormalized.timestamp >= start_date)
        if end_date:
            query = query.filter(FeaturesNormalized.timestamp <= end_date)
        rows = query.all()
        if not rows:
            return pd.DataFrame()
        data = []
        for r in rows:
            data.append({
                "timestamp": r.timestamp,
                "feat_eye_dist": r.feat_eye_dist,
                "feat_ear_zscore": r.feat_ear_zscore,
                "feat_nose_sigmoid": r.feat_nose_sigmoid,
                "feat_tongue_pct": r.feat_tongue_pct,
                "feat_body_roc": r.feat_body_roc
            })
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def load_historical_prices(self, timestamps: List[datetime]) -> pd.Series:
        """根據時間戳載入對應的收盤價（從 RawMarketData）"""
        # 簡化：假設 RawMarketData 有對應的時間戳
        # 這裡可以根據需要做向前填充
        query = self.session.query(RawMarketData).filter(
            RawMarketData.symbol == self.symbol.replace("/", "")
        ).order_by(RawMarketData.timestamp)
        rows = query.all()
        if not rows:
            return pd.Series()
        prices = {}
        for r in rows:
            prices[r.timestamp] = r.close_price
        # 構建 Series
        price_series = pd.Series(prices)
        # 重索引到要求的 timestamps（向前填充）
        price_series = price_series.reindex(timestamps, method='ffill')
        return price_series

    def run(self, features_df: pd.DataFrame, price_series: pd.Series) -> Dict:
        """
        執行回測 main loop。
        假設 features_df 的 timestamp 與 price_series index 對齊。
        """
        logger.info(f"開始回測：初始資本={self.initial_capital}, 樣本數={len(features_df)}")

        equity = self.initial_capital
        for idx, row in features_df.iterrows():
            ts = row["timestamp"]
            price = price_series.get(ts)
            if price is None or pd.isna(price):
                continue

            # 1. 構造特徵字典
            features = {
                "feat_eye_dist": row["feat_eye_dist"],
                "feat_ear_zscore": row["feat_ear_zscore"],
                "feat_nose_sigmoid": row["feat_nose_sigmoid"],
                "feat_tongue_pct": row["feat_tongue_pct"],
                "feat_body_roc": row["feat_body_roc"]
            }

            # 2. 預測
            confidence = self.predictor.predict(features)

            # 3. 決策與下單
            if confidence >= self.confidence_threshold and self.position == 0:
                # 開多單
                position_size = check_position_size(equity, confidence, self.max_position_ratio)
                qty = position_size / price
                qty = round_down(qty, 0.001)  # 最小交易單位假設
                if qty > 0:
                    self.position = qty
                    self.entry_price = price
                    self.trade_log.append({
                        "timestamp": ts,
                        "action": "BUY",
                        "price": price,
                        "amount": qty,
                        "confidence": confidence
                    })
            elif self.position > 0:
                # 檢查止損
                stop_price = calculate_stop_loss(self.entry_price, self.stop_loss_pct, "BUY")
                if price <= stop_price:
                    # 止損平倉
                    pnl = (price - self.entry_price) * self.position
                    equity += pnl
                    self.trade_log.append({
                        "timestamp": ts,
                        "action": "SELL",
                        "price": price,
                        "amount": self.position,
                        "confidence": confidence,
                        "pnl": pnl
                    })
                    self.position = 0.0
                    self.entry_price = 0.0

            # 4. 更新權益
            if self.position > 0:
                # 倉位市值
                mark_to_market = (price - self.entry_price) * self.position
                equity = self.initial_capital + sum(t.get("pnl", 0) for t in self.trade_log if t.get("pnl") is not None) + mark_to_market
            else:
                equity = self.initial_capital + sum(t.get("pnl", 0) for t in self.trade_log if t.get("pnl") is not None)

            self.equity_curve.append({"timestamp": ts, "equity": equity})

        # 回測結束，強制平倉（若有持倉）
        if self.position > 0:
            last_price = price_series.iloc[-1]
            pnl = (last_price - self.entry_price) * self.position
            self.trade_log.append({
                "timestamp": features_df.iloc[-1]["timestamp"],
                "action": "SELL",
                "price": last_price,
                "amount": self.position,
                "confidence": None,
                "pnl": pnl
            })
            self.position = 0

        # 構建結果
        equity_df = pd.DataFrame(self.equity_curve).set_index("timestamp")
        trades_df = pd.DataFrame(self.trade_log)
        return {
            "equity_curve": equity_df,
            "trade_log": trades_df,
            "final_equity": equity
        }

def run_backtest(
    session: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    initial_capital: float = 10000.0,
    confidence_threshold: float = 0.7,
    max_position_ratio: float = 0.05,
    stop_loss_pct: float = 0.03,
    symbol: str = "BTC/USDT"
) -> Optional[Dict]:
    """
    便捷函數：載入數據 → 執行回測 → 返回結果
    """
    from sqlalchemy import create_engine
    # 確保 session 關聯的連接可用
    try:
        engine = session.get_bind()
    except Exception:
        # session 可能不活躍，需重新創建
        return None

    engine_bt = BacktestEngine(
        session=session,
        initial_capital=initial_capital,
        confidence_threshold=confidence_threshold,
        max_position_ratio=max_position_ratio,
        stop_loss_pct=stop_loss_pct,
        symbol=symbol
    )

    features_df = engine_bt.load_historical_features(start_date, end_date)
    if features_df.empty:
        logger.error("無歷史特徵數據可供回測")
        return None

    # 載入價格
    price_series = engine_bt.load_historical_prices(features_df["timestamp"].tolist())
    if price_series.empty:
        logger.error("無歷史價格數據")
        return None

    results = engine_bt.run(features_df, price_series)
    return results

if __name__ == "__main__":
    print("Backtest engine loaded. Use run_backtest() function.")
