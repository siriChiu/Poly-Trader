"""
多感官配置管理器 (Senses Engine) v2
- 定義每個感官的子模組
- 從 DB 讀取真實特徵值計算分數
- 生成自然語言建議
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from database.models import FeaturesNormalized, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 特徵 → 感官映射
FEATURE_TO_SENSE = {
    "feat_eye_dist": "eye",
    "feat_ear_zscore": "ear",
    "feat_nose_sigmoid": "nose",
    "feat_tongue_pct": "tongue",
    "feat_body_roc": "body",
    "feat_pulse": "pulse",
    "feat_aura": "aura",
    "feat_mind": "mind",
}

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
    "eye":   {"name": "視覺 Eye",   "emoji": "👁️", "description": "72h Funding Rate 均值",        "modules": {"main": {"name": "72h Funding 均值",     "source": "Binance Futures",  "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "ear":   {"name": "聽覺 Ear",   "emoji": "👂", "description": "48h 價格動量",                "modules": {"main": {"name": "48h 價格動量",       "source": "Binance K線",     "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "nose":  {"name": "嗅覺 Nose",  "emoji": "👃", "description": "48h 收益率自相關",            "modules": {"main": {"name": "48h 自相關",         "source": "K線衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "tongue":{"name": "味覺 Tongue","emoji": "👅", "description": "24h 波動率",                  "modules": {"main": {"name": "24h 波動率",         "source": "K線衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "body":  {"name": "觸覺 Body",  "emoji": "💪", "description": "24h 價格區間位置",            "modules": {"main": {"name": "24h 區間位置",       "source": "K線衍生",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "pulse": {"name": "脈動 Pulse", "emoji": "💓", "description": "Funding Rate 趨勢",           "modules": {"main": {"name": "Funding 趨勢",       "source": "Binance Futures",  "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "aura":  {"name": "磁場 Aura",  "emoji": "🌀", "description": "波動率×自相關交互",            "modules": {"main": {"name": "波動率×自相關",     "source": "複合特徵",          "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
    "mind":  {"name": "認知 Mind",  "emoji": "🧠", "description": "24h Funding Z-score",         "modules": {"main": {"name": "24h Funding Z",     "source": "Binance Futures",  "enabled": True, "weight": 1.0, "value": None}}, "score": 0.5},
}

CONFIG_PATH = Path(__file__).parent.parent / "data" / "senses_config.json"


def normalize_feature(value: Optional[float], feature_type: str) -> float:
    """ECDF percentile normalization: p5->0.05, p95->0.95, linear in between.
    Anchors computed from 7-day rolling empirical distribution."""
    if value is None:
        return 0.5

    # ECDF anchors (updated from 7-day data)
    anchors = {
        'feat_eye_dist':     (-4.4964,  4.1189),
        'feat_ear_zscore':   (-0.7493,  0.9404),
        'feat_nose_sigmoid': (-0.1820,  0.8945),
        'feat_tongue_pct':   ( 0.0800,  1.3787),
        'feat_body_roc':     (-1.7996,  1.2317),
        'feat_pulse':        ( 0.3932,  0.8486),
        'feat_aura':         ( 0.0383,  1.0000),
        'feat_mind':         (-0.0634,  0.0217),
    }
    p5, p95 = anchors.get(feature_type, (-1.0, 1.0))
    v = max(p5, min(p95, value))
    span = p95 - p5
    if span < 1e-10:
        return 0.5
    return 0.05 + 0.9 * (v - p5) / span


    # ECDF anchors from 7-day empirical data (generated dynamically)
    if feature_type == "feat_eye_dist":
        v = max(-3.9852087611857097, min(4.103286825116237, value))
        span = 8.088495586301947
        return 0.05 + 0.9 * (v - -3.9852087611857097) / span if span > 1e-10 else 0.5

    if feature_type == "feat_ear_zscore":
        v = max(-0.7560784585212744, min(0.948174561035499, value))
        span = 1.7042530195567736
        return 0.05 + 0.9 * (v - -0.7560784585212744) / span if span > 1e-10 else 0.5

    if feature_type == "feat_nose_sigmoid":
        v = max(-0.18195123933674784, min(0.894490833182066, value))
        span = 1.0764420725188137
        return 0.05 + 0.9 * (v - -0.18195123933674784) / span if span > 1e-10 else 0.5

    if feature_type == "feat_tongue_pct":
        v = max(0.08, min(1.3747032542343642, value))
        span = 1.2947032542343642
        return 0.05 + 0.9 * (v - 0.08) / span if span > 1e-10 else 0.5

    if feature_type == "feat_body_roc":
        v = max(-1.8065085905712817, min(1.2404848811671434, value))
        span = 3.046993471738425
        return 0.05 + 0.9 * (v - -1.8065085905712817) / span if span > 1e-10 else 0.5

    if feature_type == "feat_pulse":
        v = max(0.3932000054096227, min(0.8485587989825305, value))
        span = 0.4553587935729078
        return 0.05 + 0.9 * (v - 0.3932000054096227) / span if span > 1e-10 else 0.5

    if feature_type == "feat_aura":
        v = max(0.0383026617403551, min(0.9999927431586128, value))
        span = 0.9616900814182576
        return 0.05 + 0.9 * (v - 0.0383026617403551) / span if span > 1e-10 else 0.5

    if feature_type == "feat_mind":
        v = max(-0.06340077101102537, min(0.02173648399242256, value))
        span = 0.08513725500344793
        return 0.05 + 0.9 * (v - -0.06340077101102537) / span if span > 1e-10 else 0.5

    return 0.5


# ECDF params for reference (7d empirical)
_ECDF_PARAMS = {'feat_eye': {'p5': -3.9852087611857097, 'p50': 0.0, 'p95': 4.103286825116237}, 'feat_ear': {'p5': -0.7560784585212744, 'p50': 0.0007297078224168807, 'p95': 0.948174561035499}, 'feat_nose': {'p5': -0.18195123933674784, 'p50': 0.4311567507828382, 'p95': 0.894490833182066}, 'feat_tongue': {'p5': 0.08, 'p50': 0.6472830310833947, 'p95': 1.3747032542343642}, 'feat_body': {'p5': -1.8065085905712817, 'p50': 0.0, 'p95': 1.2404848811671434}, 'feat_pulse': {'p5': 0.3932000054096227, 'p50': 0.6932674967732069, 'p95': 0.8485587989825305}, 'feat_aura': {'p5': 0.0383026617403551, 'p50': 0.8856753937808264, 'p95': 0.9999927431586128}, 'feat_mind': {'p5': -0.06340077101102537, 'p50': -0.00011024791738978301, 'p95': 0.02173648399242256}}


class SensesEngine:
    def __init__(self):
        self.config: Dict[str, Any] = self._load_config()
        self._db = None

    def set_db(self, db):
        """注入 DB session"""
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

    def _get_latest_features(self) -> Optional[Dict[str, Optional[float]]]:
        """從 DB 讀取最新特徵"""
        if self._db is None:
            return None
        try:
            row = (
                self._db.query(FeaturesNormalized)
                .order_by(FeaturesNormalized.timestamp.desc())
                .first()
            )
            if row is None:
                return None
            return {
                "feat_eye_dist": row.feat_eye_dist,
                "feat_ear_zscore": row.feat_ear_zscore,
                "feat_nose_sigmoid": row.feat_nose_sigmoid,
                "feat_tongue_pct": row.feat_tongue_pct,
                "feat_body_roc": row.feat_body_roc,
                "feat_pulse": row.feat_pulse,
                "feat_aura": row.feat_aura,
                "feat_mind": row.feat_mind,
                "timestamp": row.timestamp,
            }
        except Exception as e:
            logger.error(f"讀取特徵失敗: {e}")
            return None

    def calculate_sense_score(self, sense_key: str, features: Optional[Dict] = None) -> float:
        """計算單個感官分數（從真實特徵值）"""
        sense = self.config.get(sense_key, {})

        # 找到對應的特徵值
        feat_key = {
            "eye": "feat_eye_dist",
            "ear": "feat_ear_zscore",
            "nose": "feat_nose_sigmoid",
            "tongue": "feat_tongue_pct",
            "body": "feat_body_roc",
            "pulse": "feat_pulse",
            "aura": "feat_aura",
            "mind": "feat_mind",
        }.get(sense_key)

        raw_value = features.get(feat_key) if features and feat_key else None
        normalized = normalize_feature(raw_value, feat_key or "")

        # 更新子模組值（所有子模組共享同一個正規化值）
        modules = sense.get("modules", {})
        for mod_key, mod in modules.items():
            if mod.get("enabled", False):
                mod["value"] = round(normalized, 4)

        sense["score"] = round(normalized, 4)
        return sense["score"]

    def calculate_all_scores(self) -> Dict[str, float]:
        """計算所有多感官分數（從 DB 真實數據）"""
        features = self._get_latest_features()
        scores = {}
        for sense_key in self.config:
            scores[sense_key] = self.calculate_sense_score(sense_key, features)
        return scores

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
        # ORID 09:49 — Tongue IC 極低且 FNG 近零變異，暫降權重；Eye IC 反向但有資訊量
        weights = {"eye": 0.15, "ear": 0.10, "nose": 0.15, "tongue": 0.0, "body": 0.10, "pulse": 0.20, "aura": 0.10, "mind": 0.20}
        total = sum(scores.get(k, 0.5) * w for k, w in weights.items())
        return round(total * 100)

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
            f"{names[sorted_senses[0][0]]}最強（{sorted_senses[0][1]:.0%}），"
            f"{names[sorted_senses[-1][0]]}最弱（{sorted_senses[-1][1]:.0%}）。"
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
        if score > 80: return {"text": "🟢 強烈建議買入 — 多數感官一致看多", "action": "strong_buy"}
        if score > 60: return {"text": "🟡 建議輕倉買入 — 部分感官支持，注意風險", "action": "buy"}
        if score > 40: return {"text": "⚪ 建議觀望 — 感官分歧，方向不明", "action": "hold"}
        if score > 20: return {"text": "🟠 建議減倉 — 部分感官偏空", "action": "reduce"}
        return {"text": "🔴 建議觀望或做空 — 多數感官偏空", "action": "sell"}


_engine: Optional[SensesEngine] = None

def get_engine() -> SensesEngine:
    global _engine
    if _engine is None:
        _engine = SensesEngine()
    return _engine
