"""
特徵有效性驗證器
定期檢查每個特徵的 IC（信息係數），標記無效特徵並觸發六帽會議。
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from database.models import FeaturesNormalized, RawMarketData, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 有效性閾值
IC_WARNING_THRESHOLD = 0.03   # IC 低於此值 → ⚠️ 需關注
IC_CRITICAL_THRESHOLD = 0.01  # IC 低於此值 → 🔴 需汰換
NULL_RATIO_THRESHOLD = 0.5    # 超過 50% 為空 → ⚠️ 數據來源不穩
MIN_SAMPLES_FOR_VALIDATION = 20  # 至少 20 筆才啟動驗證

FEATURE_COLS = [
    "feat_eye_dist",
    "feat_ear_zscore",
    "feat_nose_sigmoid",
    "feat_tongue_pct",
    "feat_body_roc",
]

SENSE_NAMES = {
    "feat_eye_dist": "Eye (眼·技術面)",
    "feat_ear_zscore": "Ear (耳·市場共識)",
    "feat_nose_sigmoid": "Nose (鼻·衍生品)",
    "feat_tongue_pct": "Tongue (舌·情緒)",
    "feat_body_roc": "Body (身·鏈上資金)",
}


def compute_null_ratios(session: Session) -> Dict[str, float]:
    """計算每個特徵的空值比例。"""
    rows = session.query(FeaturesNormalized).all()
    if not rows:
        return {col: 1.0 for col in FEATURE_COLS}

    n = len(rows)
    ratios = {}
    for col in FEATURE_COLS:
        null_count = sum(1 for r in rows if getattr(r, col) is None)
        ratios[col] = null_count / n
    return ratios


def compute_ic(
    session: Session, symbol: str = "BTCUSDT"
) -> Dict[str, float]:
    """
    計算每個特徵與未來收益率的 Spearman 相關係數（IC）。
    使用 raw_market_data 的 close_price 作為價格來源。
    """
    from scipy import stats
    import pandas as pd

    # 取特徵
    feat_rows = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    if len(feat_rows) < MIN_SAMPLES_FOR_VALIDATION:
        logger.info(f"樣本不足 ({len(feat_rows)} < {MIN_SAMPLES_FOR_VALIDATION})，跳過 IC 計算")
        return {}

    # 取價格
    raw_rows = (
        session.query(RawMarketData)
        .filter(RawMarketData.symbol == symbol, RawMarketData.close_price.isnot(None))
        .order_by(RawMarketData.timestamp)
        .all()
    )
    if len(raw_rows) < 2:
        logger.warning("價格數據不足，無法計算 IC")
        return {}

    import numpy as np

    # 構建特徵 DataFrame
    feat_data = []
    for r in feat_rows:
        feat_data.append({
            "timestamp": r.timestamp,
            **{col: getattr(r, col) for col in FEATURE_COLS},
        })
    feat_df = pd.DataFrame(feat_data).set_index("timestamp").sort_index()

    # 構建價格 Series
    price_series = pd.Series(
        {r.timestamp: r.close_price for r in raw_rows}
    ).sort_index()

    # 計算未來收益率（下一個價格點的收益率）
    price_returns = price_series.pct_change().shift(-1)

    # 合併
    merged = feat_df.join(price_returns.rename("future_return"), how="inner")
    merged.dropna(subset=["future_return"], inplace=True)

    # 計算 IC
    ic = {}
    for col in FEATURE_COLS:
        valid = merged[[col, "future_return"]].dropna()
        if len(valid) < 5:
            ic[col] = 0.0
            continue
        corr, _ = stats.spearmanr(valid[col], valid["future_return"])
        ic[col] = float(corr) if not pd.isna(corr) else 0.0

    return ic


def validate_senses(
    session: Session, symbol: str = "BTCUSDT"
) -> Dict:
    """
    完整的特徵有效性驗證。
    Returns: {
        "status": "ok" | "warning" | "critical",
        "issues": [list of issue strings],
        "details": {col: {ic, null_ratio, status}},
        "needs_hat_meeting": bool
    }
    """
    null_ratios = compute_null_ratios(session)
    ic_values = compute_ic(session, symbol)

    details = {}
    issues = []
    needs_hat_meeting = False

    for col in FEATURE_COLS:
        name = SENSE_NAMES.get(col, col)
        null_r = null_ratios.get(col, 1.0)
        ic = ic_values.get(col, None)

        status = "ok"

        # 檢查空值比例
        if null_r > NULL_RATIO_THRESHOLD:
            status = "warning"
            issue = f"⚠️ {name}: 空值比例 {null_r:.0%}，數據來源不穩定"
            issues.append(issue)

        # 檢查 IC
        if ic is not None:
            if abs(ic) < IC_CRITICAL_THRESHOLD:
                status = "critical"
                issue = f"🔴 {name}: IC={ic:.4f}，幾乎無預測力，需汰換或重新設計"
                issues.append(issue)
                needs_hat_meeting = True
            elif abs(ic) < IC_WARNING_THRESHOLD:
                if status != "critical":
                    status = "warning"
                issue = f"⚠️ {name}: IC={ic:.4f}，預測力偏弱，需優化"
                issues.append(issue)

        details[col] = {
            "name": name,
            "ic": ic,
            "null_ratio": null_r,
            "status": status,
        }

    # 整體狀態
    if any(d["status"] == "critical" for d in details.values()):
        overall = "critical"
        needs_hat_meeting = True
    elif any(d["status"] == "warning" for d in details.values()):
        overall = "warning"
    else:
        overall = "ok"

    return {
        "status": overall,
        "issues": issues,
        "details": details,
        "needs_hat_meeting": needs_hat_meeting,
        "sample_count": session.query(FeaturesNormalized).count(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def format_validation_report(result: Dict) -> str:
    """格式化驗證報告為可讀文本。"""
    lines = [
        f"=== 特徵有效性驗證報告 ({result['timestamp']}) ===",
        f"樣本數: {result['sample_count']}",
        f"整體狀態: {result['status'].upper()}",
        "",
    ]

    for col, detail in result["details"].items():
        ic_str = f"{detail['ic']:.4f}" if detail["ic"] is not None else "N/A"
        null_str = f"{detail['null_ratio']:.0%}"
        icon = {"ok": "✅", "warning": "⚠️", "critical": "🔴"}.get(detail["status"], "❓")
        lines.append(
            f"  {icon} {detail['name']}: IC={ic_str}, 空值率={null_str}"
        )

    if result["issues"]:
        lines.append("")
        lines.append("發現的問題:")
        for issue in result["issues"]:
            lines.append(f"  {issue}")

    return "\n".join(lines)
