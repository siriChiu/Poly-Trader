#!/usr/bin/env python3
"""
Feature ETF Manager — 動態權重 + 淘汰機制

就像 ETF 追蹤指數一樣，這個模組自動：
1. 計算每個特徵的時間加權 IC (TW-IC)
2. 根據 IC 分級分配 ETF 權重
3. 淘汰連續失敗的特徵
4. 追蹤新增特徵的表現

分級標準：
- A+ (|TW-IC| >= 0.15): 3x weight — 高價值核心信號
- A  (|TW-IC| >= 0.10): 2x weight — 強信號
- B  (|TW-IC| >= 0.05): 1x weight — 通過閾值的信號 (baseline)
- C  (|TW-IC| >= 0.02): 0.5x weight — 邊緣信號
- D  (|TW-IC| < 0.02): 0x weight — 淘汰/靜音

淘汰規則：
- 連續 3 個心跳 D 級 → disabled=True
- 新增特徵從 probation 狀態開始，需要 2 個心跳證明
- 已淘汰的特徵每 50 個心跳重新評估一次 IC
"""
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
ETF_REGISTRY_FILE = DATA_DIR / "feature_etf_registry.json"
IC_HISTORY_FILE = DATA_DIR / "feature_etf_ic_history.json"

IC_TIER_THRESHOLDS = {"A+": 0.15, "A_": 0.10, "B_": 0.05, "C_": 0.02}
TIER_WEIGHTS = {"A+": 3.0, "A_": 2.0, "B_": 1.0, "C_": 0.5, "D_": 0.0}
PROBATION_HB_COUNT = 2
DISABLE_THRESHOLD = 3
RE_EVAL_HB_GAP = 50
TAU = 200  # TW-IC decay constant (same as predictor.py)


class FeatureETF:
    """Feature ETF — 管理 20 個特徵的動態權重與淘汰。"""

    def __init__(self):
        self.registry = self._load(ETF_REGISTRY_FILE, {"senses": {}, "hb_number": 0})
        self.ic_history = self._load(IC_HISTORY_FILE, {})

    # ---- helpers ----
    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self, path: Path, default: Dict) -> Dict:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default

    def save(self):
        self._ensure_data_dir()
        ETF_REGISTRY_FILE.write_text(json.dumps(self.registry, indent=2, ensure_ascii=False))
        IC_HISTORY_FILE.write_text(json.dumps(self.ic_history, indent=2, ensure_ascii=False))

    # ---- 等級 ----
    @staticmethod
    def get_tier(abs_ic: float) -> str:
        if abs_ic >= IC_TIER_THRESHOLDS["A+"]:
            return "A+"
        if abs_ic >= IC_TIER_THRESHOLDS["A_"]:
            return "A_"
        if abs_ic >= IC_TIER_THRESHOLDS["B_"]:
            return "B_"
        if abs_ic >= IC_TIER_THRESHOLDS["C_"]:
            return "C_"
        return "D_"

    @staticmethod
    def get_weight(tier: str) -> float:
        return TIER_WEIGHTS.get(tier, 0.0)

    # ---- 特徵註冊 ----
    def register(self, name: str, source: str = "", description: str = "",
                 ic_sign_important: bool = False, is_probation: bool = False):
        if name in self.registry["senses"]:
            return
        self.registry["senses"][name] = {
            "name": name, "source": source, "description": description,
            "tier": "B_", "weight": 1.0, "disabled": False,
            "consecutive_d": 0, "is_probation": is_probation,
            "hb_since_probation": 0,
            "ic_sign_important": ic_sign_important,
            "created_at": datetime.utcnow().isoformat(),
            "last_ic": None, "last_ic_abs": None,
        }

    def update_ic(self, name: str, ic_value: float):
        if name not in self.registry["senses"]:
            self.register(name, description="auto-discovered", is_probation=True)

        sense = self.registry["senses"][name]
        abs_ic = abs(ic_value) if ic_value is not None and np.isfinite(ic_value) else 0.0
        self.ic_history.setdefault(name, []).append(round(ic_value, 6))
        if len(self.ic_history[name]) > 100:
            self.ic_history[name] = self.ic_history[name][-100:]

        tier = self.get_tier(abs_ic)
        sense["last_ic"] = round(ic_value, 6)
        sense["last_ic_abs"] = round(abs_ic, 6)

        if sense.get("is_probation"):
            sense["hb_since_probation"] = sense.get("hb_since_probation", 0) + 1

        if tier == "D_":
            sense["consecutive_d"] = sense.get("consecutive_d", 0) + 1
            if (sense["consecutive_d"] >= DISABLE_THRESHOLD
                    and not sense.get("is_probation")
                    and not sense.get("disabled")):
                sense["disabled"] = True
        else:
            sense["consecutive_d"] = 0
            if (sense.get("is_probation")
                    and sense.get("hb_since_probation", 0) >= PROBATION_HB_COUNT
                    and tier in ("B_", "A_", "A+")):
                sense["is_probation"] = False

        sense["tier"] = tier
        sense["weight"] = self.get_weight(tier)

    def get_active_weights(self) -> Dict[str, float]:
        return {n: s["weight"] for n, s in self.registry["senses"].items()
                if not s.get("disabled") and s.get("tier") != "D_"}

    def get_weighted_scores(self, raw_scores: Dict[str, float]) -> Optional[float]:
        """ETF-weighted composite score from raw feature score dict."""
        weights = self.get_active_weights()
        if not weights:
            return None
        total_w = 0.0
        total_v = 0.0
        for name, wt in weights.items():
            if name in raw_scores:
                raw = raw_scores[name]
                if raw is None or not np.isfinite(raw):
                    raw = 0.5
                total_v += raw * wt
                total_w += wt
        return total_v / total_w if total_w > 0 else None

    def summary_table(self) -> List[Dict]:
        rows = []
        for name, s in self.registry["senses"].items():
            rows.append({
                "name": name,
                "source": s.get("source", ""),
                "tier": s.get("tier", "?"),
                "weight": s.get("weight", 0),
                "disabled": s.get("disabled", False),
                "probation": s.get("is_probation", False),
                "last_ic": s.get("last_ic"),
                "consec_d": s.get("consecutive_d", 0),
            })
        return rows

    def summary_text(self, hb_number: int = None) -> str:
        if hb_number is not None:
            self.registry["hb_number"] = hb_number
        self.save()
        lines = [f"\n  ┌──────── Feature ETF #{self.registry.get('hb_number', '?')} ────────┐"]
        lines.append(f"  │ {'Sense':<20} {'Src':<10} {'IC':>7} {'Tier':<4} {'Wt':>3} {'St'}  │")
        lines.append(f"  ├{'─'*20}┼{'─'*10}┼{'─'*7}┼{'─'*4}┼{'─'*3}┼{'─'*2}┤")
        for r in self.summary_table():
            st = "🔴" if r["disabled"] else ("⏳" if r["probation"] else "✅")
            ic = f"{r['last_ic']:+.4f}" if r['last_ic'] is not None else "  N/A"
            lines.append(f"  │ {r['name']:<20} {r['source']:<10} {ic:>7} {r['tier']:<4} "
                         f"{r['weight']:>3.0f} {st}  │")
        lines.append(f"  └{'─'*58}┘")
        active = sum(1 for r in self.summary_table() if not r["disabled"])
        total = len(self.summary_table())
        lines.append(f"  Active: {active}/{total} senses")
        return "\n".join(lines)
