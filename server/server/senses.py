"""
五感配置管理器 (Senses Engine)
- 定義每個感官的子模組
- 計算綜合分數
- 生成自然語言建議
"""

import json
import math
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# ─── 默認感官配置 ───

DEFAULT_SENSE_CONFIG: Dict[str, Any] = {
    "eye": {
        "name": "視覺 Eye",
        "emoji": "👁️",
        "description": "技術面分析",
        "modules": {
            "order_book": {
                "name": "Order Book 深度",
                "source": "Binance Order Book",
                "description": "買賣盤深度比",
                "enabled": True,
                "weight": 0.4,
                "value": None,
            },
            "kline_levels": {
                "name": "K 線高低點",
                "source": "Binance Kline",
                "description": "價格相對支撐/阻力位置",
                "enabled": True,
                "weight": 0.6,
                "value": None,
            },
        },
        "score": 0.5,
    },
    "ear": {
        "name": "聽覺 Ear",
        "emoji": "👂",
        "description": "市場共識",
        "modules": {
            "polymarket": {
                "name": "Polymarket 概率",
                "source": "Polymarket API",
                "description": "預測市場概率",
                "enabled": True,
                "weight": 0.5,
                "value": None,
            },
            "news_sentiment": {
                "name": "新聞情緒",
                "source": "News API",
                "description": "加密貨幣新聞 NLP 情緒分析",
                "enabled": True,
                "weight": 0.5,
                "value": None,
            },
        },
        "score": 0.5,
    },
    "nose": {
        "name": "嗅覺 Nose",
        "emoji": "👃",
        "description": "衍生品市場",
        "modules": {
            "funding_rate": {
                "name": "資金費率",
                "source": "Binance Futures",
                "description": "永續合約資金費率",
                "enabled": True,
                "weight": 0.6,
                "value": None,
            },
            "open_interest": {
                "name": "持倉量",
                "source": "Binance Futures",
                "description": "未平倉合約量變化",
                "enabled": True,
                "weight": 0.4,
                "value": None,
            },
        },
        "score": 0.5,
    },
    "tongue": {
        "name": "味覺 Tongue",
        "emoji": "👅",
        "description": "市場情緒",
        "modules": {
            "fear_greed": {
                "name": "恐懼貪婪指數",
                "source": "Alternative.me",
                "description": "Fear & Greed Index (0~100)",
                "enabled": True,
                "weight": 0.7,
                "value": None,
            },
            "social_media": {
                "name": "社交媒體情緒",
                "source": "Twitter/Reddit",
                "description": "社交平台加密貨幣討論情緒",
                "enabled": True,
                "weight": 0.3,
                "value": None,
            },
        },
        "score": 0.5,
    },
    "body": {
        "name": "觸覺 Body",
        "emoji": "💪",
        "description": "鏈上資金",
        "modules": {
            "stablecoin_mcap": {
                "name": "穩定幣市值",
                "source": "DeFiLlama",
                "description": "主要穩定幣總市值 ROC",
                "enabled": True,
                "weight": 0.5,
                "value": None,
            },
            "liquidation": {
                "name": "清算數據",
                "source": "Coinglass",
                "description": "大額清算方向與金額",
                "enabled": True,
                "weight": 0.5,
                "value": None,
            },
        },
        "score": 0.5,
    },
}

CONFIG_PATH = Path(__file__).parent.parent / "data" / "senses_config.json"


class SensesEngine:
    """五感引擎：管理配置、計算分數、生成建議"""

    def __init__(self):
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """載入配置，若無則使用默認"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULT_SENSE_CONFIG))

    def save_config(self):
        """保存配置到文件"""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def get_senses_status(self) -> Dict[str, Any]:
        """返回五感詳細狀態"""
        return self.config

    def update_sense_config(self, sense_key: str, module_key: str, updates: Dict[str, Any]) -> bool:
        """更新特定感官子模組配置"""
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

    def calculate_sense_score(self, sense_key: str, data: Optional[Dict] = None) -> float:
        """
        計算單個感官的加權分數
        若無真實數據，使用模擬值
        """
        sense = self.config.get(sense_key, {})
        modules = sense.get("modules", {})
        enabled_modules = {k: v for k, v in modules.items() if v.get("enabled", False)}

        if not enabled_modules:
            sense["score"] = 0.5
            return 0.5

        total_weight = sum(m["weight"] for m in enabled_modules.values())
        if total_weight == 0:
            sense["score"] = 0.5
            return 0.5

        score = 0.0
        for key, module in enabled_modules.items():
            value = module.get("value")
            if value is None:
                # 模擬值（實際應從 API 獲取）
                value = random.uniform(0.2, 0.8)
                module["value"] = round(value, 4)
            score += value * (module["weight"] / total_weight)

        score = max(0.0, min(1.0, score))
        sense["score"] = round(score, 4)
        return sense["score"]

    def calculate_all_scores(self, data: Optional[Dict] = None) -> Dict[str, float]:
        """計算所有五感分數"""
        scores = {}
        for sense_key in self.config:
            scores[sense_key] = self.calculate_sense_score(sense_key, data)
        return scores

    def calculate_recommendation_score(self, scores: Optional[Dict[str, float]] = None) -> int:
        """
        綜合五感分數 → 0~100 建議分數
        """
        if scores is None:
            scores = self.calculate_all_scores()

        # 加權平均（每個感官等權重）
        weights = {"eye": 0.25, "ear": 0.20, "nose": 0.20, "tongue": 0.20, "body": 0.15}
        total = 0.0
        for key, weight in weights.items():
            total += scores.get(key, 0.5) * weight

        return round(total * 100)

    def generate_advice(self, scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        根據五感分數組合生成自然語言建議
        """
        if scores is None:
            scores = self.calculate_all_scores()

        rec_score = self.calculate_recommendation_score(scores)

        # 各感官描述
        descriptions = []
        descriptions.append(self._eye_description(scores.get("eye", 0.5)))
        descriptions.append(self._ear_description(scores.get("ear", 0.5)))
        descriptions.append(self._nose_description(scores.get("nose", 0.5)))
        descriptions.append(self._tongue_description(scores.get("tongue", 0.5)))
        descriptions.append(self._body_description(scores.get("body", 0.5)))

        # 綜合建議
        overall = self._overall_advice(rec_score)

        # 找出最強和最弱的感官
        sorted_senses = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        strongest = sorted_senses[0]
        weakest = sorted_senses[-1]

        sense_names = {
            "eye": "技術面", "ear": "市場共識",
            "nose": "衍生品", "tongue": "情緒", "body": "鏈上資金"
        }

        summary = (
            f"{sense_names[strongest[0]]}最強（{strongest[1]:.0%}），"
            f"{sense_names[weakest[0]]}最弱（{weakest[1]:.0%}）。"
            f"綜合建議：{overall['text']}"
        )

        return {
            "score": rec_score,
            "overall": overall,
            "descriptions": descriptions,
            "summary": summary,
            "scores": scores,
            "action": overall["action"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _eye_description(self, score: float) -> str:
        if score > 0.7:
            return "技術面顯示強勢突破 📈"
        elif score > 0.3:
            return "技術面處於整理區間 📊"
        else:
            return "技術面觸及支撐位 📉"

    def _ear_description(self, score: float) -> str:
        if score > 0.6:
            return "市場共識偏多 🟢"
        elif score > 0.4:
            return "市場觀望情緒濃厚 ⚪"
        else:
            return "市場共識偏空 🔴"

    def _nose_description(self, score: float) -> str:
        if score > 0.6:
            return "衍生品市場槓桿偏多 🔼"
        elif score > 0.4:
            return "衍生品市場平穩 ➡️"
        else:
            return "衍生品市場槓桿偏空 🔽"

    def _tongue_description(self, score: float) -> str:
        if score > 0.6:
            return "市場情緒樂觀 😊"
        elif score > 0.4:
            return "市場情緒中性 😐"
        else:
            return "市場情緒極度恐懼 😱"

    def _body_description(self, score: float) -> str:
        if score > 0.6:
            return "鏈上資金持續流入 💰"
        elif score > 0.4:
            return "鏈上資金平穩 ⚖️"
        else:
            return "鏈上資金外流壓力大 📤"

    def _overall_advice(self, score: int) -> Dict[str, str]:
        if score > 80:
            return {
                "text": "🟢 強烈建議買入 — 多數感官一致看多",
                "action": "strong_buy",
                "level": "bullish",
            }
        elif score > 60:
            return {
                "text": "🟡 建議輕倉買入 — 部分感官支持，注意風險",
                "action": "buy",
                "level": "mild_bullish",
            }
        elif score > 40:
            return {
                "text": "⚪ 建議觀望 — 感官分歧，方向不明",
                "action": "hold",
                "level": "neutral",
            }
        elif score > 20:
            return {
                "text": "🟠 建議減倉 — 部分感官偏空",
                "action": "reduce",
                "level": "mild_bearish",
            }
        else:
            return {
                "text": "🔴 建議觀望或做空 — 多數感官偏空",
                "action": "sell",
                "level": "bearish",
            }


# 全局實例
_engine: Optional[SensesEngine] = None


def get_engine() -> SensesEngine:
    global _engine
    if _engine is None:
        _engine = SensesEngine()
    return _engine
