# Poly-Trader Issues 追踪

---

## 🟡 中優先級

| ID | 問題描述 | 建議改進 |
|----|----------|----------|
| #009 | 缺少 SHAP 可解釋性圖表 | 集成 shap 庫 |
| #020 | Binance Futures 比率 API 返回空 | 需 API Key |

---

## 🟢 優化方向

| 階段 | 目標 | 狀態 |
|------|------|------|
| Phase 8 | IC 驗證 + 淘汰無效感官 | 🔄 數據累積中 |
| Phase 9 | IC 動態加權模型 | 📋 |
| Phase 10 | 收益歸因系統 | 📋 |
| Phase 11 | 市場環境分類器 | 📋 |

---

## ✅ 已解決

| ID | 問題 | 解決方案 |
|----|------|----------|
| #001 | Eye 返回 None | 已修復 |
| #002 | Ear 解析失敗 | v3: Binance 共識 |
| #003 | Body 字段不匹配 | v3: 清算壓力 |
| #004 | collector 未寫入 | 已修復 |
| #005 | 模型未訓練 | XGBoost 667→480K 筆 |
| #006 | 特徵不匹配 | preprocessor 修復 |
| #007 | 固定止損 | **ATR 追蹤止損** ✅ |
| #010 | 日志編碼 | 不影響功能 |
| #011 | Ear 概率 0.999 | v3: Binance 共識 0.40 |
| #012 | ear_zscore 不足 | 歷史回填 720 筆 |
| #013 | DummyPredictor | XGBoost 載入 |
| #014 | 數據累積慢 | 心跳自動收集 |
| #015 | ear/body 為 0 | 歷史填充 |
| #016 | predictor 未用模型 | xgb_model.pkl 載入 |
| #017 | Body 零變異 | 清算壓力 v3 → 21.5% 重要性 |
| #018 | 測試文件散落 | 移入 tests/ |
| — | Streamlit 延遲 | React + FastAPI |
| — | 無 K 線圖 | TradingView lightweight-charts |

---

## 📊 模型訓練結果（最新）

- 樣本：480,240 筆（47.5% 正樣本）
- **五感均衡**：Body 21.5% > Tongue 20.7% > Ear 19.9% > Nose 19.3% > Eye 18.6%
- 模型：`model/xgb_model.pkl`

---

**最後更新**：2026-03-31 08:20 GMT+8
