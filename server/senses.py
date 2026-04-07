"""
多感官配置管理器 (Senses Engine) v3
- 8 Core Senses (ECDF normalized)
- 22+ 完整特徵 (含 4H, Macro, Technical)
- 從 DB 讀取真實特徵值計算分數
- 生成自然語言建議
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from database.models import FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ─── 8 Core 特徵映射 ───
CORE_FEATURE_MAP = {
    "feat_eye_dist": "eye",
    "feat_ear_zscore": "ear",
    "feat_nose_sigmoid": "nose",
    "feat_tongue_pct": "tongue",
    "feat_body_roc": "body",
    "feat_pulse": "pulse",
    "feat_aura": "aura",
    "feat_mind": "mind",
}

# ECDF p5/p95 錨點 (7-day empirical, updated regularly)
ECDF_ANCHORS = {
    'feat_eye_dist':    (-4.50,  +4.12),
    'feat_ear_zscore':  (-0.75,  +0.94),
    'feat_nose_sigmoid':  (-0.18,  +0.89),
    'feat_tongue_pct':  (+0.08,  +1.38),
    'feat_body_roc':    (-1.80,  +1.23),
    'feat_pulse':       (+0.39,  +0.85),
    'feat_aura':        (+0.04,  +1.00),
    'feat_mind':        (-0.06,  +0.02),
}

# ─── 4H 特徵範圍 (用 95th percentile 經驗值) ───
FOURH_RANGES = {
    # (min, max) for min-max normalization → 0..1
    '4h_bias50':       (-5,  +10),
    '4h_bias':          (-5,  +10),
    '4h_rsi14':         (30,  70),
    '4h_macd_hist':    (-2000, +2000),
    '4h_bb_pct_b':      (0, 1),
    '4h_dist_swing_low': (-50, +30),
    '4h_ma_order':      (-1, 1),
}


def ecdf_normalize(value: float, p5: float, p95: float) -> float:
    """線性 ECDF: p5→0.05, p95→0.95"""
    v = max(p5, min(p95, value))
    span = p95 - p5
    if span < 1e-10:
        return 0.5
    return 0.05 + 0.9 * (v - p5) / span


def minmax_normalize(value: float, lo: float, hi: float) -> float:
    """Min-max 正規化到 0..1"""
    span = hi - lo
    if span < 1e-10:
        return 0.5
    return min(max((value - lo) / span, 0), 1)


def sigmoid_clip(value: float, scale: float = 1.0) -> float:
    """Sigmoid + clip 到 0..1"""
    if scale == 0:
        return 0.5
    return 1.0 / (1.0 + math.exp(-value / scale))


def normalize_feature(value, col_name: str) -> float:
    """Normalize a single feature value to 0..1 using ECDF anchors. Returns 0.5 if value is None."""
    if value is None:
        return 0.5
    if col_name in ECDF_ANCHORS:
        p5, p95 = ECDF_ANCHORS[col_name]
        return ecdf_normalize(value, p5, p95)
    return 0.5


def normalize_all_features(row) -> Dict[str, float]:
    """Normalize a FeaturesNormalized row → dict of frontend keys with 0..1 scores."""
    scores = {}

    # ─── Core 8: ECDF ───
    core_db_cols = {
        'feat_eye': 'feat_eye_dist',
        'feat_ear': 'feat_ear_zscore',
        'feat_nose': 'feat_nose_sigmoid',
        'feat_tongue': 'feat_tongue_pct',
        'feat_body': 'feat_body_roc',
        'feat_pulse': 'feat_pulse',
        'feat_aura': 'feat_aura',
        'feat_mind': 'feat_mind',
    }
    for name, db_col in core_db_cols.items():
        raw = getattr(row, db_col, None) if db_col != db_col else getattr(row, 'feat_eye' if name == 'eye' else 'feat_' + name, None)
        if raw is not None and db_col in ECDF_ANCHORS:
            p5, p95 = ECDF_ANCHORS[db_col]
            scores[name] = round(ecdf_normalize(raw, p5, p95), 4)
        else:
            scores[name] = 0.5

    # ─── Macro: VIX, DXY ───
    for name in ['vix', 'dxy']:
        raw = getattr(row, f'feat_{name}', None)
        if raw is not None:
            if name == 'vix':
                scores[name] = round(minmax_normalize(raw, 10, 50), 4)
            elif name == 'dxy':
                scores[name] = round(minmax_normalize(raw, 95, 110), 4)
        else:
            scores[name] = 0.5

    # ─── Technical Indicators ───
    # RSI14 (already 0..1 in DB)
    raw = getattr(row, 'feat_rsi14', None)
    scores['rsi14'] = round(raw, 4) if raw is not None else 0.5

    # MACD Hist (use sigmoid with scale)
    raw = getattr(row, 'feat_macd_hist', None)
    scores['macd_hist'] = round(sigmoid_clip(raw, 0.01), 4) if raw is not None else 0.5

    # ATR %
    raw = getattr(row, 'feat_atr_pct', None)
    scores['atr_pct'] = round(minmax_normalize(raw or 0, 0.005, 0.03), 4)

    # VWAP Dev
    raw = getattr(row, 'feat_vwap_dev', None)
    scores['vwap_dev'] = round(sigmoid_clip(raw or 0, 0.2), 4)

    # BB %B (already 0..1)
    raw = getattr(row, 'feat_bb_pct_b', None)
    scores['bb_pct_b'] = round(raw, 4) if raw is not None else 0.5

    # ─── 4H Features ───
    # bias50: -5% to +10%
    raw = getattr(row, 'feat_4h_bias50', None)
    scores['4h_bias50'] = round(minmax_normalize(raw or 0, -5, 10), 4)

    # bias20
    raw = getattr(row, 'feat_4h_bias20', None)
    scores['4h_bias20'] = round(minmax_normalize(raw or 0, -5, 10), 4)

    # rsi14 (4H)
    raw = getattr(row, 'feat_4h_rsi14', None)
    scores['4h_rsi14'] = round(minmax_normalize(raw or 50, 30, 70), 4)

    # macd_hist (4H)
    raw = getattr(row, 'feat_4h_macd_hist', None)
    scores['4h_macd_hist'] = round(sigmoid_clip(raw or 0, 500), 4)

    # bb_pct_b (4H)
    raw = getattr(row, 'feat_4h_bb_pct_b', None)
    scores['4h_bb_pct_b'] = round(raw, 4) if raw is not None else 0.5

    # ma_order: -1 to +1
    raw = getattr(row, 'feat_4h_ma_order', None)
    scores['4h_ma_order'] = round((raw + 1) / 2, 4) if raw is not None else 0.5

    # dist_swing_low
    raw = getattr(row, 'feat_4h_dist_swing_low', None)
    scores['4h_dist_sl'] = round(minmax_normalize(raw or 0, -50, 30), 4)

    # P0/P1 features (many are 0/null, give 0.5 if not available)
    for name in ['nq_return_1h', 'nq_return_24h', 'claw', 'claw_intensity',
                 'fang_pcr', 'fang_skew', 'fin_netflow', 'web_whale',
                 'scales_ssr', 'nest_pred', 'whisper', 'tone', 'chorus',
                 'hype', 'oracle', 'shock', 'tide', 'storm']:
        raw = getattr(row, f'feat_{name}', None)
        if raw is not None and abs(raw) > 1e-10:
            scores[name] = round(sigmoid_clip(raw, max(abs(raw) * 2, 1.0)), 4)
        else:
            scores[name] = 0.5

    return scores


# ─── Legacy senses engine (for backward compat) ───

SENSE_NAMES = {
    "eye": "視覺 Eye",
    "ear": "聽覺 Ear",
    "nose": "嗅覺 Nose",
    "tongue": "味覺 Tongue",
    "body": "觸覺 Body",
    "pulse": "脈動 Pulse",
    "aura": "磁場 Aura",
    "mind": "認知 Mind",
}

SENSE_EMOJIS = {
    "eye": "👁️", "ear": "👂", "nose": "👃", "tongue": "👅", "body": "💪",
    "pulse": "💓", "aura": "🌀", "mind": "🧠",
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "eye":   {"name": "視覺 Eye",   "emoji": "👁️", "description": "24H return / 72H vol ratio",        "modules": {"main": {"name": "72h Vol Ratio",     "source": "Binance",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "ear":   {"name": "聽覺 Ear",   "emoji": "👂", "description": "24H momentum",                "modules": {"main": {"name": "Momentum",       "source": "K線",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "nose":  {"name": "嗅覺 Nose",  "emoji": "👃", "description": "RSI momentum",            "modules": {"main": {"name": "RSI",         "source": "衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "tongue":{"name": "味覺 Tongue","emoji": "👅", "description": "Mean-reversion deviation",                  "modules": {"main": {"name": "Mean-revert",         "source": "衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "body":  {"name": "觸覺 Body",  "emoji": "💪", "description": "Volatility z-score",            "modules": {"main": {"name": "Vol Z-score",       "source": "衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "pulse": {"name": "脈動 Pulse", "emoji": "💓", "description": "Volume spike",           "modules": {"main": {"name": "Vol Spike",       "source": "K線",  "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "aura":  {"name": "磁場 Aura",  "emoji": "🌈", "description": "MA deviation",            "modules": {"main": {"name": "MA Dev",     "source": "複合",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "mind":  {"name": "認知 Mind",  "emoji": "🧠", "description": "Medium-term momentum",         "modules": {"main": {"name": "144-return",     "source": "Binance",  "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
}

CONFIG_PATH = Path(__file__).parent.parent / "data" / "senses_config.json"


class SensesEngine:
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
        """Get normalized scores for ALL features. Used by API /senses."""
        if self._db is None:
            return {k: 0.5 for k in ['eye','ear','nose','tongue','body','pulse','aura','mind']}
        try:
            row = (
                self._db.query(FeaturesNormalized)
                .order_by(FeaturesNormalized.timestamp.desc())
                .first()
            )
            if row is None:
                return {k: 0.5 for k in ['eye','ear','nose','tongue','body','pulse','aura','mind']}
            return normalize_all_features(row)
        except Exception as e:
            logger.error(f"Feature fetch failed: {e}")
            return {k: 0.5 for k in ['eye','ear','nose','tongue','body','pulse','aura','mind']}

    def calculate_all_scores(self) -> Dict[str, float]:
        """Calculate all scores — core 8 + all extra features."""
        return self.get_latest_scores()

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def get_senses_status(self) -> Dict[str, Any]:
        return self.config

    def update_sense_config(self, sense_key: str, module_key: str, updates: Dict[str, Any]) -> bool:
        if sense_key not in self.config:
            return False
        if module_key not in self.config[sense_key]["modules"]:
            return False
        module = self.config[sense_key]["modules"][module_key]
        if "enabled" in updates:
            module["enabled"] = updates["enabled"]
        if "weight" in updates:
            module["weight"] = max(0.0, min(1.0, updates["weight"]))
        self.save_config()
        return True

    def calculate_recommendation_score(self, scores: Optional[Dict[str, float]] = None) -> int:
        if scores is None:
            scores = self.calculate_all_scores()
        # IC-based weights
        weights = {"eye": 0.15, "ear": 0.10, "nose": 0.15, "tongue": 0.0, "body": 0.10, "pulse": 0.20, "aura": 0.10, "mind": 0.20}
        total = sum(scores.get(k, 0.5) * w for k, w in weights.items())
        x = (total * 100 - 50) / 15
        amplified = 50 + 50 * (1 / (1 + math.exp(-1.5 * x)) - 0.5) * 2
        return round(max(0, min(100, amplified)))

    def generate_advice(self, scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        if scores is None:
            scores = self.calculate_all_scores()
        rec_score = self.calculate_recommendation_score(scores)
        descriptions = [
            self._desc("eye", scores.get("eye", 0.5)),
            self._desc("ear", scores.get("ear", 0.5)),
            self._desc("nose", scores.get("nose", 0.5)),
            self._desc("tongue", scores.get("tongue", 0.5)),
            self._desc("body", scores.get("body", 0.5)),
        ]
        overall = self._overall_advice(rec_score)
        sorted_senses = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        names = {"eye": "技術面", "ear": "市場共識", "nose": "衍生品", "tongue": "情緒", "body": "鏈上資金", "pulse": "脈動", "aura": "磁場", "mind": "認知"}
        summary = (
            f"{names.get(sorted_senses[0][0], sorted_senses[0][0])}最強（{sorted_senses[0][1]:.0%}），"
            f"{names.get(sorted_senses[-1][0], sorted_senses[-1][0])}最弱（{sorted_senses[-1][1]:.0%}）。"
            f"綜合建議：{overall['text']}"
        )
        return {
            "score": rec_score, "overall": overall,
            "descriptions": descriptions, "summary": summary,
            "scores": scores, "action": overall["action"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _desc(self, sense: str, score: float) -> str:
        templates = {
            "eye": [(0.7, "技術面顯示強勢突破 📈"), (0.3, "技術面處於整理區間 📊"), (0, "技術面觸及支撐位 📉")],
            "ear": [(0.6, "市場共識偏多 🟢"), (0.4, "市場觀望情緒濃厚 ⚪"), (0, "市場共識偏空 🔴")],
            "nose": [(0.6, "衍生品市場槓桿偏多 🔼"), (0.4, "衍生品市場平穩 ➡️"), (0, "衍生品市場槓桿偏空 🔽")],
            "tongue": [(0.6, "市場情緒樂觀 😊"), (0.4, "市場情緒中性 😐"), (0, "市場情緒極度恐懼 😱")],
            "body": [(0.6, "鏈上資金持續流入 💰"), (0.4, "鏈上資金平穩 ⚖️"), (0, "鏈上資金外流壓力大 📤")],
        }
        for threshold, text in templates.get(sense, []):
            if score > threshold:
                return text
        return "數據不足 ❓"

    def _overall_advice(self, score: int) -> Dict[str, str]:
        if score > 80: return {"text": "🔴 強烈建議做空 — 多數感官確認下跌趨勢", "action": "strong_sell"}
        if score > 60: return {"text": "🟠 建議做空 — 部分感官支持下跌", "action": "sell"}
        if score > 40: return {"text": "⚪ 建議觀望 — 感官分歧，方向不明", "action": "hold"}
        if score > 20: return {"text": "🟡 偏多格局 — 下跌動能不足", "action": "hold_long"}
        return {"text": "🟢 多頭格局 — 價格可能上升", "action": "hold"}


_engine: Optional[SensesEngine] = None

def get_engine() -> SensesEngine:
    global _engine
    if _engine is None:
        _engine = SensesEngine()
    return _engine
