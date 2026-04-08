"""
多特徵配置管理器 (Features Engine) v4
- 從 DB 讀取真实特徵值
- 使用 ECDF (full dataset) 正規化 → 分數有差異
- 包含 4H 結構線資訊 (原始值 + 正規化)
- 生成自然語言建議
"""

import json
import math
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from database.models import FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ─── ECDF Anchors (computed from full dataset) ───
# Key: DB column name → [p_lo, p_hi]
# These are loaded from data/ecdf_anchors.json or fall back to hardcoded
_ANCHORS_PATH = Path(__file__).parent.parent / "data" / "ecdf_anchors.json"

def _load_anchors() -> Dict[str, tuple]:
    """Load ECDF anchors from JSON file, fallback to hardcoded."""
    if _ANCHORS_PATH.exists():
        try:
            with open(_ANCHORS_PATH) as f:
                data = json.load(f)
            return {k: (float(v[0]), float(v[1])) for k, v in data.items()}
        except Exception:
            pass
    # Fallback: hardcoded from manual computation
    return {
        'feat_eye': (0.2373, 1.5581),
        'feat_ear': (-0.0242, 0.0229),
        'feat_nose': (0.5009, 0.7781),
        'feat_tongue': (-0.0001, 1.5967),
        'feat_body': (0.0, 0.9617),
        'feat_pulse': (0.1543, 0.8137),
        'feat_aura': (-0.0470, 0.0444),
        'feat_mind': (-0.0840, 0.0796),
        'feat_vix': (-2.0261, 24.1700),
        'feat_dxy': (-2.1528, 100.0530),
        'feat_rsi14': (0.2945, 0.7055),
        'feat_macd_hist': (-0.0024, 0.0023),
        'feat_atr_pct': (0.0100, 0.0121),
        'feat_vwap_dev': (-0.4683, 0.1441),
        'feat_bb_pct_b': (-0.0340, 1.0292),
        'feat_4h_bias50': (-5.5811, 4.5196),
        'feat_4h_bias20': (-3.5934, 3.1118),
        'feat_4h_rsi14': (30.7433, 71.5026),
        'feat_4h_macd_hist': (-1153.6229, 1211.7948),
        'feat_4h_bb_pct_b': (-0.2520, 1.1975),
        'feat_4h_ma_order': (-1.0, 1.0),
        'feat_4h_dist_swing_low': (-2.4801, 100.0),
    }

ECDF_ANCHORS = _load_anchors()

# ─── DB column → frontend key mapping (correct names!) ───
FEATURE_MAP = {
    # 8 Core
    'feat_eye':       'eye',
    'feat_ear':       'ear',
    'feat_nose':      'nose',
    'feat_tongue':    'tongue',
    'feat_body':      'body',
    'feat_pulse':     'pulse',
    'feat_aura':      'aura',
    'feat_mind':      'mind',
    # 2 Macro
    'feat_vix':       'vix',
    'feat_dxy':       'dxy',
    # 5 Technical
    'feat_rsi14':     'rsi14',
    'feat_macd_hist': 'macd_hist',
    'feat_atr_pct':   'atr_pct',
    'feat_vwap_dev':  'vwap_dev',
    'feat_bb_pct_b':  'bb_pct_b',
    # 4H Distance
    'feat_4h_bias50':        '4h_bias50',
    'feat_4h_bias20':        '4h_bias20',
    'feat_4h_rsi14':         '4h_rsi14',
    'feat_4h_macd_hist':     '4h_macd_hist',
    'feat_4h_bb_pct_b':      '4h_bb_pct_b',
    'feat_4h_ma_order':      '4h_ma_order',
    'feat_4h_dist_swing_low': '4h_dist_sl',
}

# ─── Feature engine config (descriptions for UI display) ───
DEFAULT_CONFIG: Dict[str, Any] = {
    # 8 Core
    "eye":   {"name": "Eye",   "emoji": "📊", "description": "24H return / 72H vol ratio (trend strength)",        "modules": {"main": {"name": "72h Vol Ratio",     "source": "Binance",    "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "ear":   {"name": "Ear",   "emoji": "📈", "description": "24H momentum",                          "modules": {"main": {"name": "Momentum",       "source": "K線",    "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "nose":  {"name": "Nose",  "emoji": "📐", "description": "RSI momentum",                    "modules": {"main": {"name": "RSI",         "source": "衍生",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "tongue":{"name": "Tongue","emoji": "🔄", "description": "Mean-reversion deviation",                  "modules": {"main": {"name": "Mean-revert",     "source": "衍生",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "body":  {"name": "Body",  "emoji": "📏", "description": "Volatility z-score",                         "modules": {"main": {"name": "Vol Z-score",     "source": "衍生",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "pulse": {"name": "Pulse", "emoji": "💹", "description": "Volume spike",                   "modules": {"main": {"name": "Vol Spike",     "source": "K線",    "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "aura":  {"name": "Aura",  "emoji": "🔮", "description": "MA deviation",                        "modules": {"main": {"name": "MA Dev",     "source": "複合",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "mind":  {"name": "Mind",  "emoji": "🧮", "description": "Medium-term momentum",                    "modules": {"main": {"name": "144-return",     "source": "Binance", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    # 2 Macro
    "vix":   {"name": "VIX",   "emoji": "📉", "description": "VIX fear gauge",                         "modules": {"main": {"name": "VIX Index",    "source": "Macro",    "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "dxy":   {"name": "DXY",   "emoji": "💵", "description": "Dollar Index (macro strength)",            "modules": {"main": {"name": "DXY",          "source": "Macro",    "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    # 5 Technical
    "rsi14":  {"name": "RSI 14",    "emoji": "📊", "description": "RSI momentum oscillator",              "modules": {"main": {"name": "RSI(14)",    "source": "Technical", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "macd_hist":{"name": "MACD H",  "emoji": "📈", "description": "MACD Histogram (trend momentum)",       "modules": {"main": {"name": "MACD Hist",   "source": "Technical", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "atr_pct":{"name": "ATR %",    "emoji": "📏", "description": "Average True Range % (volatility)",      "modules": {"main": {"name": "ATR Pct",     "source": "Technical", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "vwap_dev":{"name": "VWAP Dev", "emoji": "⚖️", "description": "VWAP deviation (fair value)",            "modules": {"main": {"name": "VWAP Dev",    "source": "Technical", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "bb_pct_b":{"name": "BB %B",    "emoji": "🔵", "description": "Bollinger Band %B",                    "modules": {"main": {"name": "BB %B",       "source": "Technical", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    # 7 4H Structure
    "4h_bias50":     {"name": "4H Bias50",    "emoji": "📐", "description": "4H Price vs MA50 deviation (%)",   "modules": {"main": {"name": "Bias50",      "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_bias20":     {"name": "4H Bias20",    "emoji": "📐", "description": "4H Price vs MA20 deviation (%)",   "modules": {"main": {"name": "Bias20",      "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_rsi14":      {"name": "4H RSI 14",    "emoji": "📈", "description": "4H RSI momentum",                  "modules": {"main": {"name": "RSI(14)",     "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_macd_hist":  {"name": "4H MACD H",    "emoji": "📊", "description": "4H MACD Histogram",               "modules": {"main": {"name": "MACD Hist",   "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_bb_pct_b":   {"name": "4H BB %B",     "emoji": "🔵", "description": "4H Bollinger Band %B",              "modules": {"main": {"name": "BB %B",       "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_ma_order":   {"name": "4H MA Order",  "emoji": "🔄", "description": "4H MA alignment (+1 bull / -1 bear)","modules": {"main": {"name": "MA Order",    "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "4h_dist_sl":    {"name": "4H Swing",     "emoji": "📍", "description": "Distance to 4H swing low (support)","modules": {"main": {"name": "Swing Low",   "source": "4H Structure", "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
}

CONFIG_PATH = Path(__file__).parent.parent / "data" / "features_config.json"


def ecdf_normalize(value: float, p_lo: float, p_hi: float) -> float:
    """Soft ECDF normalization.

    Instead of hard-clipping everything below/above p5/p95 to 0.05/0.95,
    extend the usable range so extreme values still retain some separation.
    This reduces the common "always 5 / 95" saturation problem in the UI.
    """
    span = p_hi - p_lo
    if span < 1e-10:
        return 0.5

    soft_margin = span * 0.5
    soft_lo = p_lo - soft_margin
    soft_hi = p_hi + soft_margin

    if value <= p_lo:
        v = max(soft_lo, value)
        return 0.02 + 0.08 * (v - soft_lo) / max(p_lo - soft_lo, 1e-10)
    if value >= p_hi:
        v = min(soft_hi, value)
        return 0.90 + 0.08 * (v - p_hi) / max(soft_hi - p_hi, 1e-10)
    return 0.10 + 0.80 * (value - p_lo) / span


def normalize_feature(raw_value: Optional[float], db_col: str) -> float:
    """Normalize a single feature to 0..1 using ECDF. Returns 0.5 if None."""
    if raw_value is None:
        return 0.5
    if db_col in ECDF_ANCHORS:
        p_lo, p_hi = ECDF_ANCHORS[db_col]
        return ecdf_normalize(raw_value, p_lo, p_hi)
    return 0.5


def get_raw_and_scores(row) -> Dict[str, Any]:
    """Get both raw 4H values AND normalized scores for all 22 features.
    
    Returns:
        dict with:
          - scores: {key: 0..1 float} for ALL features
          - raw: {key: raw float} for 4H features (for dashboard)
          - raw_all: {key: raw float} for ALL features (for charts)
    """
    scores = {}
    raw_values = {}

    # ─── Core + Macro + Technical: ECDF normalize ──
    for db_col, fe_key in FEATURE_MAP.items():
        val = getattr(row, db_col, None) if hasattr(row, db_col) else None
        scores[fe_key] = normalize_feature(val, db_col)
        raw_values[fe_key] = val  # store raw for API

    return {
        'scores': scores,
        'raw': {k: v for k, v in raw_values.items() if k.startswith('4h_')},
        'raw_all': {k: v for k, v in raw_values.items()},
    }


# ─── FeaturesEngine ───
class FeaturesEngine:
    def __init__(self):
        self.config: Dict[str, Any] = self._load_config()
        self._db = None

    def set_db(self, db):
        self._db = db

    def _load_config(self) -> Dict[str, Any]:
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def save_config(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_latest_scores(self) -> Dict[str, float]:
        """Get normalized scores for ALL 22 features from DB latest row."""
        if self._db is None:
            return {k: 0.5 for k in FEATURE_MAP.values()}
        try:
            row = (
                self._db.query(FeaturesNormalized)
                .order_by(FeaturesNormalized.timestamp.desc())
                .first()
            )
            if row is None:
                return {k: 0.5 for k in FEATURE_MAP.values()}
            result = get_raw_and_scores(row)
            return result['scores']
        except Exception as e:
            logger.error(f"Feature fetch failed: {e}")
            return {k: 0.5 for k in FEATURE_MAP.values()}

    def get_latest_full_data(self) -> Dict[str, Any]:
        """Get scores + raw 4H values for the API."""
        if self._db is None:
            return {'scores': {}, 'raw': {}, 'raw_all': {}}
        try:
            row = (
                self._db.query(FeaturesNormalized)
                .order_by(FeaturesNormalized.timestamp.desc())
                .first()
            )
            if row is None:
                return {'scores': {}, 'raw': {}, 'raw_all': {}}
            # If latest row has null 4H values, find one that has data
            # (happens after restart before 4H warmup completes)
            raw_result = get_raw_and_scores(row)
            if raw_result['raw'] and all(v is None for v in raw_result['raw'].values()):
                row_with_4h = (
                    self._db.query(FeaturesNormalized)
                    .filter(FeaturesNormalized.feat_4h_bias50.isnot(None))
                    .order_by(FeaturesNormalized.timestamp.desc())
                    .first()
                )
                if row_with_4h:
                    return get_raw_and_scores(row_with_4h)
            return raw_result
        except Exception as e:
            logger.error(f"Full data fetch failed: {e}")
            return {'scores': {}, 'raw': {}, 'raw_all': {}}

    def calculate_all_scores(self):
        return self.get_latest_scores()

    def get_config(self) -> Dict[str, Any]:
        """Return config with live DB values merged in."""
        config = json.loads(json.dumps(self.config))  # deep copy
        if self._db is None:
            return config
        try:
            row = (
                self._db.query(FeaturesNormalized)
                .order_by(FeaturesNormalized.timestamp.desc())
                .first()
            )
            if row is None:
                return config
            # If 4H features are null in the latest row, find one with data
            has_4h = getattr(row, 'feat_4h_bias50', None) is not None
            if not has_4h:
                row_with_4h = (
                    self._db.query(FeaturesNormalized)
                    .filter(FeaturesNormalized.feat_4h_bias50.isnot(None))
                    .order_by(FeaturesNormalized.timestamp.desc())
                    .first()
                )
                if row_with_4h:
                    # Merge: scores from latest row, raw values from row with 4H
                    latest_raw = get_raw_and_scores(row)
                    full_raw = get_raw_and_scores(row_with_4h)
                    # Use scores from latest, raw_all from 4H row for 4H keys
                    merged_raw = {**latest_raw.get('raw_all', {}), **{k:v for k,v in full_raw.get('raw_all', {}).items() if v is not None and latest_raw.get('raw_all',{}).get(k) is None}}
                    scores = latest_raw.get('scores', {})
                    # Override 4H scores from the 4H row
                    for k, v in full_raw.get('scores', {}).items():
                        if k.startswith('4h_'):
                            scores[k] = v
                else:
                    raw_result = get_raw_and_scores(row)
                    merged_raw = raw_result.get('raw_all', {})
                    scores = raw_result.get('scores', {})
            else:
                raw_result = get_raw_and_scores(row)
                merged_raw = raw_result.get('raw_all', {})
                scores = raw_result.get('scores', {})

            for fe_key, entry in config.items():
                # Update score
                if fe_key in scores:
                    entry['score'] = scores[fe_key]
                # Update module value with raw DB value
                if fe_key in merged_raw and 'modules' in entry:
                    for mod_key, mod in entry['modules'].items():
                        mod['value'] = merged_raw[fe_key]
        except Exception as e:
            logger.error(f"get_config live merge failed: {e}")
        return config

    def get_features_status(self) -> Dict[str, Any]:
        return self.config

    def update_feature_config(self, feature_key: str, module_key: str, updates: Dict[str, Any]) -> bool:
        if feature_key not in self.config:
            return False
        if module_key not in self.config[feature_key]["modules"]:
            return False
        module = self.config[feature_key]["modules"][module_key]
        if "enabled" in updates:
            module["enabled"] = updates["enabled"]
        if "weight" in updates:
            module["weight"] = max(0.0, min(1.0, updates["weight"]))
        self.save_config()
        return True

    def calculate_recommendation_score(self, scores: Optional[Dict[str, float]] = None) -> int:
        if scores is None:
            scores = self.calculate_all_scores()
        # Model-based: XGBoost learns optimal 4H×sensory fusion weights
        return calculate_model_score(scores)

    def generate_advice(self, scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        if scores is None:
            scores = self.calculate_all_scores()
        rec_score = self.calculate_recommendation_score(scores)
        focus_features = [
            "4h_bias50", "4h_dist_sl", "4h_rsi14", "pulse", "nose", "vix", "dxy", "mind"
        ]
        descriptions = [
            self._desc(feature, scores.get(feature, 0.5))
            for feature in focus_features
            if feature in scores
        ]
        overall = self._overall_advice(rec_score)
        sorted_feats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        names = {
            "eye": "趨勢強度", "ear": "短線動能", "nose": "RSI 極值", "tongue": "均值回歸偏離",
            "body": "波動狀態", "pulse": "量能脈衝", "aura": "均線偏離", "mind": "中期動量",
            "vix": "VIX 風險", "dxy": "美元強弱", "rsi14": "RSI14", "macd_hist": "MACD",
            "atr_pct": "ATR 波幅", "vwap_dev": "VWAP 偏離", "bb_pct_b": "布林帶位置",
            "4h_bias50": "4H MA50 偏離", "4h_bias20": "4H MA20 偏離", "4h_dist_sl": "4H 支撐距離",
            "4h_rsi14": "4H RSI", "4h_macd_hist": "4H MACD", "4h_bb_pct_b": "4H 布林帶位置",
            "4h_ma_order": "4H 均線排列",
        }
        summary = (
            f"{names.get(sorted_feats[0][0], sorted_feats[0][0])}最強（{sorted_feats[0][1]:.0%}），"
            f"{names.get(sorted_feats[-1][0], sorted_feats[-1][0])}最弱（{sorted_feats[-1][1]:.0%}）。"
            f"綜合建議：{overall['text']}"
        )
        return {
            "score": rec_score, "overall": overall,
            "descriptions": descriptions, "summary": summary,
            "scores": scores, "action": overall["action"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _desc(self, feature: str, score: float) -> str:
        templates = {
            "4h_bias50": [
                (0.75, "4H MA50 回檔夠深，進場甜蜜點逐漸浮現"),
                (0.45, "4H 位置中性，仍需等待更好價格或確認"),
                (0.0, "4H 價格仍偏高，追價風險大於優勢"),
            ],
            "4h_dist_sl": [
                (0.75, "距離 4H 支撐很近，適合觀察分批承接機會"),
                (0.45, "離支撐尚有距離，先留意結構是否守穩"),
                (0.0, "距離關鍵支撐太遠，安全邊際不足"),
            ],
            "4h_rsi14": [
                (0.7, "4H 動能維持健康，回檔後仍有延續空間"),
                (0.4, "4H 動能中性，暫時偏向等待市場表態"),
                (0.0, "4H 動能轉弱，應避免過早擴大部位"),
            ],
            "pulse": [
                (0.7, "量能正在放大，價格變化更可能有真實資金支持"),
                (0.4, "量能普通，訊號可信度屬一般水準"),
                (0.0, "量能偏弱，容易出現無量反彈或假突破"),
            ],
            "nose": [
                (0.7, "短線 RSI 偏熱，靠近追價區，應等更好風險報酬"),
                (0.4, "RSI 位於中性帶，適合搭配其他結構訊號一起判讀"),
                (0.0, "RSI 已回到偏冷區，抄底條件開始改善"),
            ],
            "vix": [
                (0.7, "外部風險偏好偏差，全球避險情緒仍在壓抑加密資產"),
                (0.4, "宏觀風險中性，短線仍以幣圈自身節奏為主"),
                (0.0, "外部風險壓力較低，較有利風險資產反彈"),
            ],
            "dxy": [
                (0.7, "美元偏強，流動性壓力較高，現貨操作宜更保守"),
                (0.4, "美元環境中性，暫時不構成主要阻力"),
                (0.0, "美元回落，通常較有利加密資產估值修復"),
            ],
            "mind": [
                (0.7, "中期動量維持正向，代表不是只有短線反彈"),
                (0.4, "中期動量中性，還看不出明確趨勢優勢"),
                (0.0, "中期動量偏弱，反彈持續性需保守看待"),
            ],
        }
        for threshold, text in templates.get(feature, []):
            if score >= threshold:
                return text
        return "目前訊號資訊不足，先維持觀察。"

    def _overall_advice(self, score: int) -> Dict[str, str]:
        # Canonical target is spot-long-win: high score means better long entry quality,
        # not short/做空 confidence. Keep advice aligned with pyramid spot strategy.
        if score > 80:
            return {"text": "🟢 強多訊號 — 可考慮金字塔進場", "action": "strong_buy"}
        if score > 60:
            return {"text": "🟡 偏多格局 — 可等待確認後買入", "action": "buy"}
        if score > 40:
            return {"text": "⚪ 觀望 — 特徵分歧，方向不明", "action": "hold"}
        if score > 20:
            return {"text": "🟠 偏弱格局 — 避免追價，保守減碼", "action": "reduce"}
        return {"text": "🔴 弱勢格局 — 暫停新增部位", "action": "hold_long"}


_engine: Optional[FeaturesEngine] = None

def calculate_model_score(raw_scores: Dict[str, float]) -> int:
    """
    用 XGBoost 模型計算推薦分數 (取代硬編碼 IC 權重)。
    結合 4H 框架 + 感官極端 + 融合特徵 → 模型自己學最佳組合。
    """
    try:
        import pickle, json, math, os
        model_path = Path(__file__).parent.parent / "model/xgb_model.pkl"
        if not model_path.exists():
            # Fallback: weighted formula
            weights = {"4h_bias50": 0.20, "4h_dist_sl": 0.15, "nose": 0.10,
                       "pulse": 0.10, "mind": 0.10, "aura": 0.05, "ema": 0.10,
                       "eye": 0.05, "ear": 0.05, "rsi14": 0.05, "macd_hist": 0.05}
            total = sum(raw_scores.get(k, 0.5) * w for k, w in weights.items())
            return round(max(0, min(100, total * 100)))

        # Load model
        with open(model_path, "rb") as f:
            model_payload = pickle.load(f)

        model = model_payload.get('clf')
        feature_names = model_payload.get('feature_names', [])
        if model is None or not feature_names:
            weights = {"4h_bias50": 0.20, "4h_dist_sl": 0.15, "nose": 0.10,
                       "pulse": 0.10, "mind": 0.10, "aura": 0.05, "ema": 0.10,
                       "eye": 0.05, "ear": 0.05, "rsi14": 0.05, "macd_hist": 0.05}
            total = sum(raw_scores.get(k, 0.5) * w for k, w in weights.items())
            return round(max(0, min(100, total * 100)))

        # Build feature vector - normalize to 0..1
        # 4H features (raw values for the model)
        feat_4h_bias50 = raw_scores.get('4h_bias50', 0)
        feat_4h_bias20 = raw_scores.get('4h_bias20', 0)
        feat_4h_ma_order = raw_scores.get('4h_ma_order', 0)
        feat_4h_rsi14 = raw_scores.get('4h_rsi14', 0.5)  # already 0-1 from ECDF
        feat_4h_macd_hist = raw_scores.get('4h_macd_hist', 0)
        feat_4h_bb_pct_b = raw_scores.get('4h_bb_pct_b', 0.5)
        feat_4h_dist_swing_low = raw_scores.get('4h_dist_sl', 0)

        # 1min sensory
        feat_nose = raw_scores.get('nose', 0.5)
        feat_tongue = raw_scores.get('tongue', 0.5)
        feat_mind = raw_scores.get('mind', 0.5)
        feat_pulse = raw_scores.get('pulse', 0.5)
        feat_eye = raw_scores.get('eye', 0.5)
        feat_ear = raw_scores.get('ear', 0.5)
        feat_body = raw_scores.get('body', 0.5)
        feat_aura = raw_scores.get('aura', 0.5)

        # Macro
        feat_vix = raw_scores.get('vix', 0.5)
        feat_dxy = raw_scores.get('dxy', 0.5)
        feat_rsi14 = raw_scores.get('rsi14', 0.5)
        feat_macd_hist = raw_scores.get('macd_hist', 0.5)
        feat_atr_pct = raw_scores.get('atr_pct', 0.5)
        feat_vwap_dev = raw_scores.get('vwap_dev', 0.5)
        feat_bb_pct_b = raw_scores.get('bb_pct_b', 0.5)

        # Compute fusion features on the fly
        from feature_engine.fusion_features import compute_fusion_features
        fusion = compute_fusion_features(
            feat_4h_bias50=feat_4h_bias50,
            feat_4h_bias20=feat_4h_bias20,
            feat_4h_dist_swing_low=feat_4h_dist_swing_low,
            feat_4h_bb_pct_b=feat_4h_bb_pct_b,
            feat_4h_ma_order=feat_4h_ma_order,
            feat_4h_rsi14=feat_4h_rsi14,
            feat_4h_macd_hist=feat_4h_macd_hist,
            feat_nose=feat_nose,
            feat_tongue=feat_tongue,
            feat_mind=feat_mind,
            feat_pulse=feat_pulse,
            feat_eye=feat_eye,
            feat_ear=feat_ear,
            feat_body=feat_body,
            feat_aura=feat_aura,
        )

        # Build full feature vector
        feature_dict = {
            **{'feat_eye': feat_eye, 'feat_ear': feat_ear, 'feat_nose': feat_nose,
               'feat_tongue': feat_tongue, 'feat_body': feat_body, 'feat_pulse': feat_pulse,
               'feat_aura': feat_aura, 'feat_mind': feat_mind},
            **{'feat_vix': feat_vix, 'feat_dxy': feat_dxy},
            **{'feat_rsi14': feat_rsi14, 'feat_macd_hist': feat_macd_hist,
               'feat_atr_pct': feat_atr_pct, 'feat_vwap_dev': feat_vwap_dev,
               'feat_bb_pct_b': feat_bb_pct_b},
            **{f'feat_4h_bias50': feat_4h_bias50, 'feat_4h_bias20': feat_4h_bias20,
               'feat_4h_rsi14': feat_4h_rsi14 * 100, 'feat_4h_macd_hist': feat_4h_macd_hist,
               'feat_4h_bb_pct_b': feat_4h_bb_pct_b, 'feat_4h_ma_order': feat_4h_ma_order,
               'feat_4h_dist_swing_low': feat_4h_dist_swing_low},
            **{k: v for k, v in fusion.items() if k.startswith('feat_')},
        }

        # Add cross features
        feature_dict['feat_vix_x_eye'] = feature_dict['feat_vix'] * feature_dict['feat_eye']
        feature_dict['feat_vix_x_pulse'] = feature_dict['feat_vix'] * feature_dict['feat_pulse']
        feature_dict['feat_vix_x_mind'] = feature_dict['feat_vix'] * feature_dict['feat_mind']
        feature_dict['feat_mind_x_pulse'] = feature_dict['feat_mind'] * feature_dict['feat_pulse']
        feature_dict['feat_eye_x_ear'] = feature_dict['feat_eye'] * feature_dict['feat_ear']
        feature_dict['feat_nose_x_aura'] = feature_dict['feat_nose'] * feature_dict['feat_aura']
        feature_dict['feat_eye_x_body'] = feature_dict['feat_eye'] * feature_dict.get('feat_body', 0.5)
        feature_dict['feat_ear_x_nose'] = feature_dict['feat_ear'] * feature_dict['feat_nose']
        feature_dict['feat_mind_x_aura'] = feature_dict['feat_mind'] * feature_dict['feat_aura']
        feature_dict['feat_regime_flag'] = 0.0
        feature_dict['feat_mean_rev_proxy'] = feature_dict['feat_mind'] - feature_dict['feat_aura']

        # Align to model's expected feature order
        X_input = []
        for fname in feature_names:
            val = feature_dict.get(fname, 0.0)
            X_input.append(val if val is not None else 0.0)

        import numpy as np
        X_arr = np.array([X_input])

        # Get probability of positive class
        proba = model.predict_proba(X_arr)[0]
        prob_pos = float(proba[-1]) if len(proba) > 1 else 0.5

        # Convert to 0-100 score
        return round(max(0, min(100, prob_pos * 100)))

    except Exception as e:
        logger.warning(f"Model-based score failed ({e}), falling back to weighted formula")
        # Fallback
        weights = {"4h_bias50": 0.20, "4h_dist_sl": 0.15, "nose": 0.10,
                   "pulse": 0.10, "mind": 0.10, "aura": 0.05, "eye": 0.05,
                   "ear": 0.05, "rsi14": 0.05, "macd_hist": 0.05}
        total = sum(raw_scores.get(k, 0.5) * w for k, w in weights.items())
        return round(max(0, min(100, total * 100)))


def get_engine() -> FeaturesEngine:
    global _engine
    if _engine is None:
        _engine = FeaturesEngine()
    return _engine
