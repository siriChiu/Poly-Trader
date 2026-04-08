"""
模型排行榜引擎 — 在固定金字塔框架下比較多個 ML 模型。

核心原則：
  1. 固定的金字塔交易框架（20/30/50 + SL/TP）
  2. 模型只提供入場信號（信心分數）
  3. Walk-Forward 驗證（Expanding Window），嚴格防過擬合
  4. 綜合排名：ROI + 勝率 + 穩定性 - 過擬合懲罰
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtesting.strategy_lab import run_hybrid_backtest, run_rule_backtest

# ─── Anti-Overfitting 配置 ───
WALK_FORWARD_WINDOW_MONTHS = 4  # 訓練視窗
WALK_FORWARD_STEP_MONTHS = 1    # 每次推進 1 個月
MIN_TRAIN_SAMPLES = 500         # 最少訓練樣本

@dataclass
class FoldResult:
    """單一折疊的結果"""
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_samples: int
    test_samples: int
    roi: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0

@dataclass
class ModelScore:
    """模型的綜合得分"""
    model_name: str
    avg_roi: float = 0.0
    avg_win_rate: float = 0.0
    avg_trades: float = 0.0
    avg_max_drawdown: float = 0.0
    avg_sharpe: float = 0.0
    avg_profit_factor: float = 0.0
    std_roi: float = 0.0
    train_test_gap: float = 0.0  # 訓練集與測試集的差距（過擬合指標）
    composite_score: float = 0.0  # 綜合排名分數
    folds: List[FoldResult] = field(default_factory=list)
    train_accuracy: float = 0.0  # 訓練集分類準確率
    test_accuracy: float = 0.0   # 測試集分類準確率

class ModelLeaderboard:
    """模型排行榜"""

    SUPPORTED_MODELS = [
        'rule_baseline', 'logistic_regression', 'xgboost',
        'lightgbm', 'catboost', 'random_forest', 'mlp', 'svm', 'ensemble'
    ]

    def __init__(self, data_df: pd.DataFrame):
        """
        Args:
            data_df: 必須包含 timestamp, close_price, label_spot_long_win,
                      feat_4h_bias50, feat_4h_rsi14 等欄位
        """
        self.data = data_df.copy()
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data = self.data.sort_values('timestamp').reset_index(drop=True)

    def _get_walk_forward_splits(self) -> List[Tuple[str, str, str, str]]:
        """產生 Walk-Forward 折疊列表: (train_start, train_end, test_start, test_end)"""
        ts = self.data['timestamp']
        data_start = ts.min()
        data_end = ts.max()
        total_months = int((data_end.year - data_start.year) * 12 + (data_end.month - data_start.month))

        splits = []
        step = WALK_FORWARD_STEP_MONTHS
        window = WALK_FORWARD_WINDOW_MONTHS

        # 從第 window 個月開始，每個 month 做一次 test
        for i in range(window, total_months):
            train_end = data_start + pd.DateOffset(months=i)
            test_end = data_start + pd.DateOffset(months=i + step)
            train_start = data_start
            test_start = train_end

            if test_end > data_end:
                test_end = data_end

            splits.append((
                train_start.strftime('%Y-%m-%d'),
                train_end.strftime('%Y-%m-%d'),
                test_start.strftime('%Y-%m-%d'),
                test_end.strftime('%Y-%m-%d'),
            ))

        return splits if splits else [
            (data_start.strftime('%Y-%m-%d'),
             (data_start + pd.DateOffset(months=6)).strftime('%Y-%m-%d'),
             (data_start + pd.DateOffset(months=6)).strftime('%Y-%m-%d'),
             data_end.strftime('%Y-%m-%d'))
        ]

    def _train_model(self, X_train, y_train, model_name):
        """訓練單一模型"""
        if model_name == 'xgboost':
            from xgboost import XGBClassifier
            m = XGBClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                colsample_bytree=0.6, subsample=0.7,
                scale_pos_weight=1.0, reg_alpha=0.1, reg_lambda=1.0,
                random_state=42, eval_metric='logloss', verbosity=0
            )
            m.fit(X_train, y_train)
            return m
        elif model_name == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier
            m = RandomForestClassifier(
                n_estimators=200, max_depth=8, min_samples_leaf=30,
                class_weight='balanced', random_state=42, n_jobs=-1
            )
            m.fit(X_train, y_train)
            return m
        elif model_name == 'logistic_regression':
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X_train)
            m = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
            m.fit(X_s, y_train)
            m.scaler = scaler
            return m
        elif model_name == 'mlp':
            from sklearn.neural_network import MLPClassifier
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X_train)
            m = MLPClassifier(
                hidden_layer_sizes=(64, 32), activation='relu',
                alpha=0.01, max_iter=500, random_state=42, early_stopping=True
            )
            m.fit(X_s, y_train)
            m.scaler = scaler
            return m
        elif model_name == 'svm':
            from sklearn.svm import SVC
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X_train)
            m = SVC(probability=True, C=1.0, gamma='scale', random_state=42)
            m.fit(X_s, y_train)
            m.scaler = scaler
            return m
        elif model_name == 'lightgbm':
            try:
                import lightgbm as lgb
                m = lgb.LGBMClassifier(
                    n_estimators=200, max_depth=6, learning_rate=0.05,
                    num_leaves=31, reg_alpha=0.1, reg_lambda=1.0,
                    random_state=42, verbose=-1
                )
                m.fit(X_train, y_train)
                return m
            except ImportError:
                return None
        elif model_name == 'catboost':
            try:
                from catboost import CatBoostClassifier
                m = CatBoostClassifier(
                    iterations=300, depth=4, learning_rate=0.05,
                    l2_leaf_reg=5.0, loss_function='Logloss',
                    random_seed=42, verbose=False
                )
                m.fit(X_train, y_train)
                return m
            except ImportError:
                return None
        elif model_name == 'ensemble':
            """Average voting from XGBoost + RF + LR"""
            from xgboost import XGBClassifier
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X_train)
            m1 = XGBClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                colsample_bytree=0.6, subsample=0.7, random_state=42,
                eval_metric='logloss', verbosity=0)
            m1.fit(X_train, y_train)
            m2 = RandomForestClassifier(
                n_estimators=200, max_depth=8, min_samples_leaf=30,
                class_weight='balanced', random_state=42, n_jobs=-1)
            m2.fit(X_train, y_train)
            m3 = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
            m3.fit(X_s, y_train)
            m1.scaler = scaler  # attach scaler for predict
            m2.scaler = scaler
            return (m1, m2, m3)  # tuple as "model"
        return None

    def _get_confidence(self, model, X_test, model_name):
        """取得信心分數"""
        try:
            if model_name == 'ensemble':
                m1, m2, m3 = model
                X_s = m1.scaler.transform(X_test)
                p1 = m1.predict_proba(X_test)[:, 1]
                p2 = m2.predict_proba(X_test)[:, 1]
                p3 = m3.predict_proba(X_s)[:, 1]
                return (p1 + p2 + p3) / 3.0
            elif model_name in ['logistic_regression', 'mlp', 'svm']:
                X_s = model.scaler.transform(X_test)
                return model.predict_proba(X_s)[:, 1]
            else:
                return model.predict_proba(X_test)[:, 1]
        except:
            return np.full(len(X_test), 0.5)

    def _run_single_fold(self, train_df, test_df, model_name):
        """跑單一折疊"""
        # 準備特徵
        feature_cols = [c for c in train_df.columns if c.startswith('feat_')]
        # 加入價格
        feature_cols_full = feature_cols + ['close_price']

        X_train = train_df[feature_cols].fillna(0).values
        y_train = train_df['label_spot_long_win'].fillna(0).astype(int).values  # 1 = spot-long target achieved

        X_test = test_df[feature_cols].fillna(0).values
        y_test = test_df['label_spot_long_win'].fillna(0).astype(int).values

        if model_name == 'rule_baseline':
            # 用 bias50 反轉作為信心：bias50 越低，越該買
            confidence = np.clip(1.0 - (test_df['feat_4h_bias50'].values + 5) / 15.0, 0.0, 1.0)
            train_acc = 0.0
            test_acc = 0.5
        else:
            # 訓練模型
            model = self._train_model(X_train, y_train, model_name)
            if model is None:
                return None
            # 置信度: 預測 buy_win (class=0) 的機率
            confidence = self._get_confidence(model, X_test, model_name)
            # 準確率
            train_acc = (model.predict(X_train) == y_train).mean()
            test_acc = (model.predict(X_test) == y_test).mean()

        # 回測
        prices = test_df['close_price'].values
        timestamps = test_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').values
        bias50 = test_df['feat_4h_bias50'].fillna(0).values
        nose = test_df['feat_nose'].fillna(0.5).values
        pulse = test_df['feat_pulse'].fillna(0.5).values
        ear = test_df['feat_ear'].fillna(0).values

        # 金字塔參數
        params = {
            'entry': {
                'bias50_max': 1.0, 'nose_max': 0.40, 'pulse_min': 0,
                'layer2_bias_max': -1.5, 'layer3_bias_max': -3.5,
                'confidence_min': 0.45,  # 模型信心閾值
            },
            'layers': [0.20, 0.30, 0.50],
            'stop_loss': -0.05,
            'take_profit_bias': 4.0,
            'take_profit_roi': 0.08,
        }

        result = run_hybrid_backtest(
            prices.tolist(), timestamps.tolist(), bias50.tolist(), bias50.tolist(),
            nose.tolist(), pulse.tolist(), ear.tolist(), confidence.tolist(),
            params
        )

        return FoldResult(
            fold=0,
            train_start=str(train_df['timestamp'].min().date()),
            train_end=str(train_df['timestamp'].max().date()),
            test_start=str(test_df['timestamp'].min().date()),
            test_end=str(test_df['timestamp'].max().date()),
            train_samples=len(train_df),
            test_samples=len(test_df),
            roi=result.roi,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=0.0,
            profit_factor=result.profit_factor,
        ), confidence, result, train_acc, test_acc

    def evaluate_model(self, model_name: str) -> Optional[ModelScore]:
        """評估單一模型的 Walk-Forward 表現"""
        splits = self._get_walk_forward_splits()
        folds = []
        all_train_accs = []
        all_test_accs = []

        for i, (ts, te, test_s, test_e) in enumerate(splits[:4]):  # 最多跑 4 折避免太慢
            train_df = self.data[(self.data['timestamp'] >= ts) & (self.data['timestamp'] < te)]
            test_df = self.data[(self.data['timestamp'] >= test_s) & (self.data['timestamp'] < test_e)]

            if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
                continue

            result = self._run_single_fold(train_df, test_df, model_name)
            if result is not None:
                fr, _, _, train_acc, test_acc = result
                fr.fold = i
                folds.append(fr)
                all_train_accs.append(train_acc)
                all_test_accs.append(test_acc)

        if not folds:
            return None

        # 統計
        rois = [f.roi for f in folds]
        wrs = [f.win_rate for f in folds]
        scores = ModelScore(
            model_name=model_name,
            avg_roi=np.mean(rois),
            avg_win_rate=np.mean(wrs),
            avg_trades=np.mean([f.total_trades for f in folds]),
            avg_max_drawdown=np.mean([f.max_drawdown for f in folds]),
            std_roi=np.std(rois),
            train_accuracy=np.mean(all_train_accs) if all_train_accs else 0,
            test_accuracy=np.mean(all_test_accs) if all_test_accs else 0,
            folds=folds,
        )

        # Overfitting penalty
        scores.train_test_gap = scores.train_accuracy - scores.test_accuracy
        scores.composite_score = (
            0.4 * scores.avg_roi +
            0.3 * (scores.avg_win_rate - 0.5) +
            0.2 * (1.0 - scores.train_test_gap) -
            0.1 * scores.std_roi  # 穩定性
        )

        return scores

    def run_all_models(self, model_names: Optional[List[str]] = None) -> List[ModelScore]:
        """跑所有模型的評估，回傳排好序的 leaderboard"""
        if model_names is None:
            model_names = self.SUPPORTED_MODELS

        results = []
        for name in model_names:
            t0 = time.time()
            print(f"  評估 {name}...")
            score = self.evaluate_model(name)
            if score:
                results.append(score)
                print(f"    ✅ {name}: ROI={score.avg_roi:+.1%}, Composite={score.composite_score:.4f} ({time.time()-t0:.1f}s)")
            else:
                print(f"    ❌ {name}: 資料不足")

        # 排序：按 composite_score 降冪
        results.sort(key=lambda x: x.composite_score, reverse=True)
        return results
