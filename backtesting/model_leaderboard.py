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
from model import train as train_module

# ─── Anti-Overfitting 配置 ───
WALK_FORWARD_WINDOW_MONTHS = 4  # 訓練視窗
WALK_FORWARD_STEP_MONTHS = 1    # 每次推進 1 個月
MIN_TRAIN_SAMPLES = 500         # 最少訓練樣本


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mean(values: List[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _compute_decision_quality_score(
    win_rate: Optional[float],
    pyramid_quality: Optional[float],
    drawdown_penalty: Optional[float],
    time_underwater: Optional[float],
) -> Optional[float]:
    """Keep leaderboard scoring aligned with predictor decision-quality semantics."""
    if win_rate is None or pyramid_quality is None or drawdown_penalty is None or time_underwater is None:
        return None
    score = (
        0.45 * float(win_rate)
        + 0.25 * float(pyramid_quality)
        - 0.20 * float(drawdown_penalty)
        - 0.10 * float(time_underwater)
    )
    return round(float(score), 4)


def _summarize_trade_quality(result, trade_frame: Optional[pd.DataFrame] = None) -> Dict[str, float]:
    trades = list(getattr(result, 'trades', []) or [])
    if not trades:
        return {
            'avg_entry_quality': 0.0,
            'avg_allowed_layers': 0.0,
            'regime_gate_allow_ratio': 0.0,
            'trade_quality_score': 0.0,
            'avg_decision_quality_score': 0.0,
            'avg_expected_win_rate': 0.0,
            'avg_expected_pyramid_quality': 0.0,
            'avg_expected_drawdown_penalty': 0.0,
            'avg_expected_time_underwater': 0.0,
        }

    entry_quality_values = [float(t.get('entry_quality')) for t in trades if t.get('entry_quality') is not None]
    allowed_layers_values = [float(t.get('allowed_layers')) for t in trades if t.get('allowed_layers') is not None]
    gates = [str(t.get('regime_gate') or 'ALLOW').upper() for t in trades]
    allow_ratio = sum(1 for gate in gates if gate == 'ALLOW') / len(gates)
    caution_ratio = sum(1 for gate in gates if gate == 'CAUTION') / len(gates)
    avg_entry_quality = _mean(entry_quality_values)
    avg_allowed_layers = _mean(allowed_layers_values)

    drawdown_score = _clamp01(1.0 - float(getattr(result, 'max_drawdown', 0.0) or 0.0) / 0.35)
    profit_factor = float(getattr(result, 'profit_factor', 0.0) or 0.0)
    profit_factor_score = _clamp01((profit_factor - 1.0) / 1.5)
    win_rate_score = _clamp01((float(getattr(result, 'win_rate', 0.0) or 0.0) - 0.45) / 0.20)
    allowed_layers_score = _clamp01(avg_allowed_layers / 3.0)

    proxy_trade_quality_score = round(
        0.35 * avg_entry_quality
        + 0.20 * win_rate_score
        + 0.15 * drawdown_score
        + 0.15 * profit_factor_score
        + 0.10 * allow_ratio
        + 0.05 * (1.0 - caution_ratio)
        + 0.05 * allowed_layers_score,
        4,
    )

    avg_expected_win_rate = 0.0
    avg_expected_pyramid_quality = 0.0
    avg_expected_drawdown_penalty = 0.0
    avg_expected_time_underwater = 0.0
    avg_decision_quality_score = 0.0

    if trade_frame is not None and not trade_frame.empty and 'timestamp' in trade_frame.columns:
        entry_timestamps = {
            str(t.get('entry_timestamp'))
            for t in trades
            if t.get('entry_timestamp')
        }
        if entry_timestamps:
            ts_strings = trade_frame['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            aligned = trade_frame.loc[ts_strings.isin(entry_timestamps)].copy()
            if not aligned.empty:
                def _avg_if_present(col: str) -> Optional[float]:
                    if col not in aligned.columns:
                        return None
                    series = pd.to_numeric(aligned[col], errors='coerce').dropna()
                    if series.empty:
                        return None
                    return round(float(series.mean()), 4)

                avg_expected_win_rate = _avg_if_present('simulated_pyramid_win') or 0.0
                avg_expected_pyramid_quality = _avg_if_present('simulated_pyramid_quality') or 0.0
                avg_expected_drawdown_penalty = _avg_if_present('simulated_pyramid_drawdown_penalty') or 0.0
                avg_expected_time_underwater = _avg_if_present('simulated_pyramid_time_underwater') or 0.0
                decision_quality_score = _compute_decision_quality_score(
                    _avg_if_present('simulated_pyramid_win'),
                    _avg_if_present('simulated_pyramid_quality'),
                    _avg_if_present('simulated_pyramid_drawdown_penalty'),
                    _avg_if_present('simulated_pyramid_time_underwater'),
                )
                avg_decision_quality_score = decision_quality_score or 0.0

    trade_quality_score = avg_decision_quality_score or proxy_trade_quality_score
    return {
        'avg_entry_quality': round(avg_entry_quality, 4),
        'avg_allowed_layers': round(avg_allowed_layers, 4),
        'regime_gate_allow_ratio': round(allow_ratio, 4),
        'trade_quality_score': trade_quality_score,
        'avg_decision_quality_score': round(avg_decision_quality_score, 4),
        'avg_expected_win_rate': round(avg_expected_win_rate, 4),
        'avg_expected_pyramid_quality': round(avg_expected_pyramid_quality, 4),
        'avg_expected_drawdown_penalty': round(avg_expected_drawdown_penalty, 4),
        'avg_expected_time_underwater': round(avg_expected_time_underwater, 4),
    }


class ModelUnavailableError(RuntimeError):
    def __init__(self, model_name: str, reason: str, detail: str = ""):
        super().__init__(detail or reason)
        self.model_name = model_name
        self.reason = reason
        self.detail = detail or reason


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
    avg_entry_quality: float = 0.0
    avg_allowed_layers: float = 0.0
    trade_quality_score: float = 0.0
    regime_gate_allow_ratio: float = 0.0
    avg_decision_quality_score: float = 0.0
    avg_expected_win_rate: float = 0.0
    avg_expected_pyramid_quality: float = 0.0
    avg_expected_drawdown_penalty: float = 0.0
    avg_expected_time_underwater: float = 0.0
    deployment_profile: str = "standard"
    feature_profile: str = "current_full"
    feature_profile_source: str = "code_default"

@dataclass
class ModelScore:
    """模型的綜合得分"""
    model_name: str
    deployment_profile: str = "standard"
    feature_profile: str = "current_full"
    feature_profile_source: str = "code_default"
    feature_profile_meta: Dict[str, Any] = field(default_factory=dict)
    avg_roi: float = 0.0
    avg_win_rate: float = 0.0
    avg_trades: float = 0.0
    avg_max_drawdown: float = 0.0
    avg_sharpe: float = 0.0
    avg_profit_factor: float = 0.0
    avg_entry_quality: float = 0.0
    avg_allowed_layers: float = 0.0
    avg_trade_quality: float = 0.0
    avg_decision_quality_score: float = 0.0
    avg_expected_win_rate: float = 0.0
    avg_expected_pyramid_quality: float = 0.0
    avg_expected_drawdown_penalty: float = 0.0
    avg_expected_time_underwater: float = 0.0
    regime_stability_score: float = 0.0
    trade_count_score: float = 0.0
    roi_score: float = 0.0
    max_drawdown_score: float = 0.0
    profit_factor_score: float = 0.0
    time_underwater_score: float = 0.0
    decision_quality_component: float = 0.0
    overfit_penalty: float = 0.0
    std_roi: float = 0.0
    train_test_gap: float = 0.0  # 訓練集與測試集的差距（過擬合指標）
    reliability_score: float = 0.0
    return_power_score: float = 0.0
    risk_control_score: float = 0.0
    capital_efficiency_score: float = 0.0
    overall_score: float = 0.0
    composite_score: float = 0.0  # 綜合排名分數
    ranking_eligible: bool = True
    ranking_status: str = "comparable"
    ranking_warning: Optional[str] = None
    placeholder_reason: Optional[str] = None
    folds: List[FoldResult] = field(default_factory=list)
    train_accuracy: float = 0.0  # 訓練集分類準確率
    test_accuracy: float = 0.0   # 測試集分類準確率

class ModelLeaderboard:
    """模型排行榜"""

    SUPPORTED_MODELS = [
        'rule_baseline', 'logistic_regression', 'xgboost',
        'lightgbm', 'catboost', 'random_forest', 'mlp', 'svm', 'ensemble'
    ]
    REFRESH_MODELS = [
        'rule_baseline',
        'logistic_regression',
        'xgboost',
        'lightgbm',
        'catboost',
        'random_forest',
    ]
    DEPLOYMENT_PROFILES: Dict[str, Dict[str, Any]] = {
        'standard': {
            'entry_overrides': {
                'entry_quality_min': 0.55,
                'allowed_regimes': ['all'],
            },
        },
        'high_conviction_bear_top10': {
            'entry_overrides': {
                'confidence_min': 0.52,
                'entry_quality_min': 0.58,
                'top_k_percent': 10.0,
                'allowed_regimes': ['bear'],
            },
        },
        'bear_top5': {
            'entry_overrides': {
                'confidence_min': 0.50,
                'entry_quality_min': 0.57,
                'top_k_percent': 5.0,
                'allowed_regimes': ['bear'],
            },
        },
        'balanced_conviction': {
            'entry_overrides': {
                'confidence_min': 0.50,
                'entry_quality_min': 0.55,
                'top_k_percent': 5.0,
                'allowed_regimes': ['bear', 'chop'],
            },
        },
        'quality_filtered_all_regimes': {
            'entry_overrides': {
                'confidence_min': 0.48,
                'entry_quality_min': 0.56,
                'top_k_percent': 5.0,
                'allowed_regimes': ['all'],
            },
        },
    }

    def __init__(self, data_df: pd.DataFrame, target_col: str = 'simulated_pyramid_win'):
        """
        Args:
            data_df: 必須包含 timestamp, close_price, target label,
                      feat_4h_bias50, feat_4h_rsi14 等欄位
            target_col: Which label column to optimize. Supports
                        label_spot_long_win and simulated_pyramid_win.
        """
        self.data = data_df.copy()
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data = self.data.sort_values('timestamp').reset_index(drop=True)
        self.target_col = target_col
        self.last_model_statuses: Dict[str, Dict[str, Any]] = {}
        self._deployment_profile_override: Optional[str] = None
        self._feature_profile_override: Optional[str] = None
        self._feature_profile_meta_override: Optional[Dict[str, Any]] = None
        self._feature_ablation_payload = train_module._load_json_file(train_module.FEATURE_ABLATION_PATH)
        self._bull_pocket_payload = train_module._load_json_file(train_module.BULL_4H_POCKET_ABLATION_PATH)

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

    def _default_deployment_profile_name(self, model_name: str) -> str:
        if model_name == 'random_forest':
            return 'high_conviction_bear_top10'
        if model_name in {'xgboost', 'catboost', 'lightgbm', 'ensemble'}:
            return 'balanced_conviction'
        if model_name in {'logistic_regression', 'mlp', 'svm'}:
            return 'quality_filtered_all_regimes'
        return 'standard'

    def _deployment_profile_candidates_for_model(self, model_name: str) -> List[str]:
        """Fixed candidate lanes for automatic leaderboard lane selection.

        The leaderboard should compare a small set of deployment lanes rather than
        hard-coding one evidence-driven preset forever.
        """
        if model_name == 'random_forest':
            candidates = [
                'high_conviction_bear_top10',
                'bear_top5',
                'balanced_conviction',
                'standard',
            ]
        elif model_name in {'xgboost', 'catboost', 'lightgbm', 'ensemble'}:
            candidates = [
                'balanced_conviction',
                'high_conviction_bear_top10',
                'bear_top5',
                'standard',
            ]
        elif model_name in {'logistic_regression', 'mlp', 'svm'}:
            candidates = [
                'quality_filtered_all_regimes',
                'balanced_conviction',
                'standard',
            ]
        else:
            candidates = ['standard']

        default_name = self._default_deployment_profile_name(model_name)
        ordered = [default_name] + candidates
        unique: List[str] = []
        for name in ordered:
            if name in self.DEPLOYMENT_PROFILES and name not in unique:
                unique.append(name)
        return unique or ['standard']

    def _deployment_profile_for_model(self, model_name: str) -> Dict[str, Any]:
        """Return the active deployment profile, honoring temporary auto-selection overrides."""
        profile_name = self._deployment_profile_override or self._default_deployment_profile_name(model_name)
        profile = self.DEPLOYMENT_PROFILES.get(profile_name, self.DEPLOYMENT_PROFILES['standard'])
        return {
            'name': profile_name,
            'entry_overrides': dict(profile.get('entry_overrides', {})),
        }

    def _feature_profile_candidates_for_frame(self, feature_cols: List[str]) -> List[Dict[str, Any]]:
        """Formal feature-profile candidates for leaderboard ranking.

        This mirrors training-side shrinkage governance so leaderboard evaluation no
        longer silently assumes the dense full-stack feature set.
        """
        profile_columns = train_module._build_feature_profile_columns(feature_cols)
        candidates: List[Dict[str, Any]] = []
        seen: set[str] = set()

        def add_candidate(name: Optional[str], meta: Optional[Dict[str, Any]] = None) -> None:
            if not name or name in seen:
                return
            cols = profile_columns.get(name) or []
            if not cols:
                return
            candidate_meta = dict(meta or {})
            candidate_meta.setdefault("source", "leaderboard.fixed_feature_candidate")
            candidates.append({
                "name": name,
                "columns": cols,
                "meta": candidate_meta,
            })
            seen.add(name)

        selected_name, _, selected_meta = train_module.select_feature_profile(
            feature_cols,
            target_col=self.target_col,
            ablation_payload=self._feature_ablation_payload,
            bull_pocket_payload=self._bull_pocket_payload,
        )
        add_candidate(selected_name, selected_meta)

        ablation_payload = self._feature_ablation_payload or {}
        if ablation_payload.get("target_col") == self.target_col:
            add_candidate(
                ablation_payload.get("recommended_profile"),
                {
                    "source": "feature_group_ablation.recommended_profile",
                    "generated_at": ablation_payload.get("generated_at"),
                    "candidate_count": len(ablation_payload.get("profiles") or {}),
                },
            )

        for fixed_name in ("core_only", train_module.STRONG_BASELINE_FEATURE_PROFILE, "current_full"):
            add_candidate(fixed_name)

        if not candidates:
            add_candidate("current_full", {"source": "leaderboard.fallback_current_full"})
        return candidates

    def _feature_profile_blocker_assessment(self, meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        meta = dict(meta or {})
        support_rows = meta.get("support_rows")
        exact_live_bucket_rows = meta.get("exact_live_bucket_rows")
        minimum_support_rows = meta.get("minimum_support_rows")
        support_cohort = meta.get("support_cohort")
        source = str(meta.get("source") or "")

        blocker_reason: Optional[str] = None
        exact_bucket_under_minimum = (
            support_cohort
            and exact_live_bucket_rows is not None
            and minimum_support_rows is not None
            and float(exact_live_bucket_rows) < float(minimum_support_rows)
        )
        if exact_bucket_under_minimum:
            blocker_reason = (
                "under_minimum_exact_live_structure_bucket"
                if float(exact_live_bucket_rows) > 0
                else "unsupported_exact_live_structure_bucket"
            )
        elif support_cohort and support_rows is not None and minimum_support_rows is not None and float(support_rows) < float(minimum_support_rows):
            blocker_reason = "insufficient_supported_neighbor_rows"
        elif source.endswith("support_aware_profile") and exact_live_bucket_rows is not None and float(exact_live_bucket_rows) <= 0:
            blocker_reason = "unsupported_exact_live_structure_bucket"

        blocker_applied = blocker_reason is not None
        return {
            "blocker_applied": blocker_applied,
            "blocker_reason": blocker_reason,
            "support_rows": support_rows,
            "exact_live_bucket_rows": exact_live_bucket_rows,
            "support_cohort": support_cohort,
            "minimum_support_rows": minimum_support_rows,
        }

    def _candidate_selection_key(self, score: ModelScore) -> Tuple[float, float, float, float, float, float, float, float]:
        blocker = self._feature_profile_blocker_assessment(score.feature_profile_meta)
        blocker_gate = 0.0 if blocker["blocker_applied"] else 1.0
        exact_rows = float(blocker.get("exact_live_bucket_rows") or 0.0)
        support_rows = float(blocker.get("support_rows") or 0.0)
        return (
            blocker_gate,
            exact_rows,
            support_rows,
            float(score.composite_score),
            float(score.reliability_score),
            float(score.avg_decision_quality_score),
            float(score.avg_win_rate),
            -float(score.std_roi),
        )

    def _score_model_from_folds(
        self,
        model_name: str,
        folds: List[FoldResult],
        all_train_accs: List[float],
        all_test_accs: List[float],
    ) -> ModelScore:
        rois = [f.roi for f in folds]
        wrs = [f.win_rate for f in folds]
        avg_trades = np.mean([f.total_trades for f in folds])
        avg_max_drawdown = np.mean([f.max_drawdown for f in folds])
        avg_profit_factor = np.mean([f.profit_factor for f in folds])
        avg_entry_quality = np.mean([f.avg_entry_quality for f in folds])
        avg_allowed_layers = np.mean([f.avg_allowed_layers for f in folds])
        avg_trade_quality = np.mean([f.trade_quality_score for f in folds])
        avg_decision_quality_score = np.mean([f.avg_decision_quality_score for f in folds])
        avg_expected_win_rate = np.mean([f.avg_expected_win_rate for f in folds])
        avg_expected_pyramid_quality = np.mean([f.avg_expected_pyramid_quality for f in folds])
        avg_expected_drawdown_penalty = np.mean([f.avg_expected_drawdown_penalty for f in folds])
        avg_expected_time_underwater = np.mean([f.avg_expected_time_underwater for f in folds])
        regime_allow_ratios = [f.regime_gate_allow_ratio for f in folds]
        regime_stability_score = _clamp01(1.0 - float(np.std(regime_allow_ratios)) / 0.25)
        trade_count_score = _clamp01(avg_trades / 20.0)
        roi_score = _clamp01(0.5 + float(np.mean(rois)) / 0.20)
        max_drawdown_score = _clamp01(1.0 - avg_max_drawdown / 0.35)
        profit_factor_score = _clamp01((avg_profit_factor - 1.0) / 1.5)
        time_underwater_score = _clamp01(1.0 - avg_expected_time_underwater / 0.60)
        decision_quality_component = avg_decision_quality_score or avg_trade_quality

        scores = ModelScore(
            model_name=model_name,
            deployment_profile=str(getattr(folds[0], 'deployment_profile', 'standard') if folds else 'standard'),
            feature_profile=str(getattr(folds[0], 'feature_profile', 'current_full') if folds else 'current_full'),
            feature_profile_source=str(getattr(folds[0], 'feature_profile_source', 'code_default') if folds else 'code_default'),
            avg_roi=np.mean(rois),
            avg_win_rate=np.mean(wrs),
            avg_trades=avg_trades,
            avg_max_drawdown=avg_max_drawdown,
            avg_profit_factor=avg_profit_factor,
            avg_entry_quality=avg_entry_quality,
            avg_allowed_layers=avg_allowed_layers,
            avg_trade_quality=avg_trade_quality,
            avg_decision_quality_score=avg_decision_quality_score,
            avg_expected_win_rate=avg_expected_win_rate,
            avg_expected_pyramid_quality=avg_expected_pyramid_quality,
            avg_expected_drawdown_penalty=avg_expected_drawdown_penalty,
            avg_expected_time_underwater=avg_expected_time_underwater,
            regime_stability_score=regime_stability_score,
            trade_count_score=trade_count_score,
            roi_score=roi_score,
            max_drawdown_score=max_drawdown_score,
            profit_factor_score=profit_factor_score,
            time_underwater_score=time_underwater_score,
            decision_quality_component=decision_quality_component,
            std_roi=np.std(rois),
            train_accuracy=np.mean(all_train_accs) if all_train_accs else 0,
            test_accuracy=np.mean(all_test_accs) if all_test_accs else 0,
            folds=folds,
        )

        scores.train_test_gap = scores.train_accuracy - scores.test_accuracy
        scores.overfit_penalty = _clamp01(scores.train_test_gap / 0.20)
        win_rate_reference_score = _clamp01((scores.avg_win_rate - 0.45) / 0.20)
        variance_penalty = _clamp01(scores.std_roi / 0.10)

        scores.reliability_score = round(
            0.35 * scores.max_drawdown_score
            + 0.30 * scores.time_underwater_score
            + 0.15 * (1.0 - scores.overfit_penalty)
            + 0.10 * scores.trade_count_score
            + 0.10 * scores.regime_stability_score,
            4,
        )
        scores.return_power_score = round(
            0.50 * scores.roi_score
            + 0.30 * scores.profit_factor_score
            + 0.20 * _clamp01(win_rate_reference_score),
            4,
        )
        scores.risk_control_score = round(
            0.45 * scores.max_drawdown_score
            + 0.30 * scores.time_underwater_score
            + 0.15 * (1.0 - scores.overfit_penalty)
            + 0.10 * (1.0 - variance_penalty),
            4,
        )
        scores.capital_efficiency_score = round(
            0.40 * _clamp01(scores.decision_quality_component)
            + 0.25 * scores.profit_factor_score
            + 0.20 * scores.time_underwater_score
            + 0.15 * _clamp01(scores.avg_allowed_layers / 3.0),
            4,
        )
        scores.overall_score = round(
            0.35 * scores.reliability_score
            + 0.30 * scores.return_power_score
            + 0.20 * scores.risk_control_score
            + 0.15 * scores.capital_efficiency_score,
            4,
        )

        no_trade_placeholder = float(scores.avg_trades or 0.0) <= 0.0
        if no_trade_placeholder:
            scores.ranking_eligible = False
            scores.ranking_status = "no_trade_placeholder"
            scores.placeholder_reason = "no_trades_generated_under_current_deployment_profile"
            scores.ranking_warning = (
                "此模型在當前 deployment profile 下未產生任何交易；"
                "僅可視為 no-trade placeholder，不得當成正常排行榜前段結果。"
            )
            scores.reliability_score = 0.0
            scores.return_power_score = 0.0
            scores.risk_control_score = 0.0
            scores.capital_efficiency_score = 0.0
            scores.overall_score = 0.0

        scores.composite_score = scores.overall_score
        return scores

    def _build_strategy_params(self, model_name: str) -> Dict[str, Any]:
        profile = self._deployment_profile_for_model(model_name)
        entry = {
            'bias50_max': 1.0,
            'nose_max': 0.40,
            'pulse_min': 0,
            'layer2_bias_max': -1.5,
            'layer3_bias_max': -3.5,
            'confidence_min': 0.45,
            'entry_quality_min': 0.55,
            'top_k_percent': 0.0,
            'allowed_regimes': ['all'],
        }
        entry.update(profile.get('entry_overrides', {}))
        return {
            'entry': entry,
            'layers': [0.20, 0.30, 0.50],
            'stop_loss': -0.05,
            'take_profit_bias': 4.0,
            'take_profit_roi': 0.08,
            'deployment_profile': profile['name'],
        }

    def _train_model(self, X_train, y_train, model_name):
        """訓練單一模型"""
        if model_name == 'xgboost':
            try:
                from xgboost import XGBClassifier
            except Exception as exc:
                raise ModelUnavailableError(model_name, 'missing_dependency', str(exc)) from exc
            m = XGBClassifier(
                n_estimators=120, max_depth=3, learning_rate=0.035,
                min_child_weight=10, gamma=0.2,
                colsample_bytree=0.55, subsample=0.6,
                scale_pos_weight=1.0, reg_alpha=0.8, reg_lambda=3.0,
                max_delta_step=1,
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
                    n_estimators=140, max_depth=4, learning_rate=0.04,
                    num_leaves=15, min_child_samples=40,
                    subsample=0.65, colsample_bytree=0.6,
                    reg_alpha=0.8, reg_lambda=3.0,
                    random_state=42, verbose=-1
                )
                m.fit(X_train, y_train)
                return m
            except ImportError as exc:
                raise ModelUnavailableError(model_name, 'missing_dependency', str(exc)) from exc
        elif model_name == 'catboost':
            try:
                from catboost import CatBoostClassifier
                m = CatBoostClassifier(
                    iterations=180, depth=3, learning_rate=0.035,
                    min_data_in_leaf=40, random_strength=1.5,
                    bootstrap_type='Bernoulli', subsample=0.65,
                    l2_leaf_reg=8.0, loss_function='Logloss',
                    random_seed=42, verbose=False
                )
                m.fit(X_train, y_train)
                return m
            except ImportError as exc:
                raise ModelUnavailableError(model_name, 'missing_dependency', str(exc)) from exc
        elif model_name == 'ensemble':
            """Average voting from XGBoost + RF + LR"""
            try:
                from xgboost import XGBClassifier
            except Exception as exc:
                raise ModelUnavailableError(model_name, 'missing_dependency', str(exc)) from exc
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
        profile_columns = train_module._build_feature_profile_columns(feature_cols)
        selected_feature_profile = self._feature_profile_override
        selected_feature_profile_meta = dict(self._feature_profile_meta_override or {})
        if selected_feature_profile:
            selected_feature_cols = profile_columns.get(selected_feature_profile) or feature_cols
        else:
            selected_feature_profile, selected_feature_cols, selected_feature_profile_meta = train_module.select_feature_profile(
                feature_cols,
                target_col=self.target_col,
                ablation_payload=self._feature_ablation_payload,
                bull_pocket_payload=self._bull_pocket_payload,
            )

        if self.target_col not in train_df.columns or self.target_col not in test_df.columns:
            return None

        X_train = train_df[selected_feature_cols].fillna(0)
        y_train = train_df[self.target_col].fillna(0).astype(int)

        X_test = test_df[selected_feature_cols].fillna(0)
        y_test = test_df[self.target_col].fillna(0).astype(int)

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
            if model_name == 'ensemble':
                train_pred = (self._get_confidence(model, X_train, model_name) >= 0.5).astype(int)
                test_pred = (confidence >= 0.5).astype(int)
                train_acc = (train_pred == y_train.values).mean()
                test_acc = (test_pred == y_test.values).mean()
            else:
                if model_name in ['logistic_regression', 'mlp', 'svm']:
                    train_pred = model.predict(model.scaler.transform(X_train))
                    test_pred = model.predict(model.scaler.transform(X_test))
                    train_acc = (train_pred == y_train).mean()
                    test_acc = (test_pred == y_test).mean()
                else:
                    train_acc = (model.predict(X_train) == y_train).mean()
                    test_acc = (model.predict(X_test) == y_test).mean()

        # 回測
        prices = test_df['close_price'].values
        timestamps = test_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').values
        bias50 = test_df['feat_4h_bias50'].fillna(0).values
        nose = test_df['feat_nose'].fillna(0.5).values
        pulse = test_df['feat_pulse'].fillna(0.5).values
        ear = test_df['feat_ear'].fillna(0).values

        bias200 = test_df['feat_4h_bias200'].fillna(0).values if 'feat_4h_bias200' in test_df.columns else bias50.copy()
        regimes = (
            test_df['regime_label'].fillna('unknown').astype(str).str.lower().tolist()
            if 'regime_label' in test_df.columns
            else None
        )
        bb_pct_b_4h = test_df['feat_4h_bb_pct_b'].tolist() if 'feat_4h_bb_pct_b' in test_df.columns else None
        dist_bb_lower_4h = test_df['feat_4h_dist_bb_lower'].tolist() if 'feat_4h_dist_bb_lower' in test_df.columns else None
        dist_swing_low_4h = test_df['feat_4h_dist_swing_low'].tolist() if 'feat_4h_dist_swing_low' in test_df.columns else None
        local_bottom_score = test_df['feat_local_bottom_score'].tolist() if 'feat_local_bottom_score' in test_df.columns else None
        local_top_score = test_df['feat_local_top_score'].tolist() if 'feat_local_top_score' in test_df.columns else None

        params = self._build_strategy_params(model_name)

        result = run_hybrid_backtest(
            prices.tolist(), timestamps.tolist(), bias50.tolist(), bias200.tolist(),
            nose.tolist(), pulse.tolist(), ear.tolist(), confidence.tolist(),
            params,
            regimes=regimes,
            bb_pct_b_4h=bb_pct_b_4h,
            dist_bb_lower_4h=dist_bb_lower_4h,
            dist_swing_low_4h=dist_swing_low_4h,
            local_bottom_score=local_bottom_score,
            local_top_score=local_top_score,
        )
        trade_quality = _summarize_trade_quality(result, test_df)

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
            avg_entry_quality=trade_quality['avg_entry_quality'],
            avg_allowed_layers=trade_quality['avg_allowed_layers'],
            trade_quality_score=trade_quality['trade_quality_score'],
            regime_gate_allow_ratio=trade_quality['regime_gate_allow_ratio'],
            avg_decision_quality_score=trade_quality['avg_decision_quality_score'],
            avg_expected_win_rate=trade_quality['avg_expected_win_rate'],
            avg_expected_pyramid_quality=trade_quality['avg_expected_pyramid_quality'],
            avg_expected_drawdown_penalty=trade_quality['avg_expected_drawdown_penalty'],
            avg_expected_time_underwater=trade_quality['avg_expected_time_underwater'],
            deployment_profile=str(params.get('deployment_profile') or 'standard'),
            feature_profile=str(selected_feature_profile or 'current_full'),
            feature_profile_source=str(selected_feature_profile_meta.get('source') or 'code_default'),
        ), confidence, result, train_acc, test_acc

    def evaluate_model(self, model_name: str) -> Optional[ModelScore]:
        """評估單一模型的 Walk-Forward 表現"""
        splits = self._get_walk_forward_splits()
        candidate_profiles = self._deployment_profile_candidates_for_model(model_name)
        feature_profile_candidates = self._feature_profile_candidates_for_frame(
            [c for c in self.data.columns if c.startswith('feat_')]
        )
        candidate_runs = {
            (deployment_name, feature_candidate['name']): {
                "folds": [],
                "train_accs": [],
                "test_accs": [],
                "feature_profile_meta": dict(feature_candidate.get("meta") or {}),
            }
            for deployment_name in candidate_profiles
            for feature_candidate in feature_profile_candidates
        }
        self.last_model_statuses[model_name] = {"status": "pending", "reason": None, "detail": None}

        try:
            for i, (ts, te, test_s, test_e) in enumerate(splits[:4]):  # 最多跑 4 折避免太慢
                train_df = self.data[(self.data['timestamp'] >= ts) & (self.data['timestamp'] < te)]
                test_df = self.data[(self.data['timestamp'] >= test_s) & (self.data['timestamp'] < test_e)]

                if len(train_df) < MIN_TRAIN_SAMPLES or len(test_df) < 50:
                    continue

                for profile_name in candidate_profiles:
                    for feature_candidate in feature_profile_candidates:
                        feature_profile_name = feature_candidate["name"]
                        self._deployment_profile_override = profile_name
                        self._feature_profile_override = feature_profile_name
                        self._feature_profile_meta_override = dict(feature_candidate.get("meta") or {})
                        result = self._run_single_fold(train_df, test_df, model_name)
                        self._deployment_profile_override = None
                        self._feature_profile_override = None
                        self._feature_profile_meta_override = None
                        if result is None:
                            continue
                        fr, _, _, train_acc, test_acc = result
                        fr.fold = i
                        run = candidate_runs[(profile_name, feature_profile_name)]
                        run["folds"].append(fr)
                        run["train_accs"].append(train_acc)
                        run["test_accs"].append(test_acc)
        except ModelUnavailableError as exc:
            self._deployment_profile_override = None
            self._feature_profile_override = None
            self._feature_profile_meta_override = None
            self.last_model_statuses[model_name] = {
                "status": "unavailable",
                "reason": exc.reason,
                "detail": exc.detail,
            }
            return None
        finally:
            self._deployment_profile_override = None
            self._feature_profile_override = None
            self._feature_profile_meta_override = None

        candidate_scores: List[ModelScore] = []
        for (deployment_name, feature_profile_name), run in candidate_runs.items():
            if not run["folds"]:
                continue
            score = self._score_model_from_folds(
                model_name=model_name,
                folds=run["folds"],
                all_train_accs=run["train_accs"],
                all_test_accs=run["test_accs"],
            )
            score.deployment_profile = deployment_name
            score.feature_profile = feature_profile_name
            score.feature_profile_meta = dict(run.get("feature_profile_meta") or {})
            score.feature_profile_source = str(score.feature_profile_meta.get("source") or getattr(score, "feature_profile_source", "code_default"))
            candidate_scores.append(score)

        if not candidate_scores:
            self.last_model_statuses[model_name] = {
                "status": "insufficient_data",
                "reason": "no_valid_folds",
                "detail": "No folds met minimum train/test sample thresholds",
            }
            return None

        candidate_scores.sort(key=self._candidate_selection_key, reverse=True)
        scores = candidate_scores[0]
        selected_blocker = self._feature_profile_blocker_assessment(scores.feature_profile_meta)
        candidate_diagnostics: List[Dict[str, Any]] = []
        for rank, candidate_score in enumerate(candidate_scores, start=1):
            blocker = self._feature_profile_blocker_assessment(candidate_score.feature_profile_meta)
            candidate_diagnostics.append({
                "rank": rank,
                "model_name": candidate_score.model_name,
                "deployment_profile": candidate_score.deployment_profile,
                "feature_profile": candidate_score.feature_profile,
                "feature_profile_source": candidate_score.feature_profile_source,
                "support_cohort": blocker.get("support_cohort"),
                "support_rows": blocker.get("support_rows"),
                "exact_live_bucket_rows": blocker.get("exact_live_bucket_rows"),
                "minimum_support_rows": blocker.get("minimum_support_rows"),
                "blocker_applied": blocker.get("blocker_applied", False),
                "blocker_reason": blocker.get("blocker_reason"),
                "overall_score": round(float(candidate_score.overall_score), 4),
                "composite_score": round(float(candidate_score.composite_score), 4),
                "avg_decision_quality_score": round(float(candidate_score.avg_decision_quality_score), 4),
                "avg_win_rate": round(float(candidate_score.avg_win_rate), 4),
            })

        self.last_model_statuses[model_name] = {
            "status": "ok",
            "reason": None,
            "detail": None,
            "folds": len(scores.folds),
            "selected_deployment_profile": scores.deployment_profile,
            "selected_feature_profile": scores.feature_profile,
            "selected_feature_profile_source": scores.feature_profile_source,
            "selected_feature_profile_blocker_applied": selected_blocker.get("blocker_applied", False),
            "selected_feature_profile_blocker_reason": selected_blocker.get("blocker_reason"),
            "feature_profile_support_cohort": scores.feature_profile_meta.get("support_cohort"),
            "feature_profile_support_rows": scores.feature_profile_meta.get("support_rows"),
            "feature_profile_exact_live_bucket_rows": scores.feature_profile_meta.get("exact_live_bucket_rows"),
            "deployment_profiles_evaluated": list(dict.fromkeys(score.deployment_profile for score in candidate_scores)),
            "feature_profiles_evaluated": list(dict.fromkeys(score.feature_profile for score in candidate_scores)),
            "feature_profile_candidate_diagnostics": candidate_diagnostics,
        }
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
                status = self.last_model_statuses.get(name, {})
                if status.get("reason") == "missing_dependency":
                    print(f"    ❌ {name}: 缺少依賴 ({status.get('detail')})")
                else:
                    print(f"    ❌ {name}: 資料不足")

        # 排序：按 composite_score 降冪
        results.sort(key=lambda x: x.composite_score, reverse=True)
        return results
