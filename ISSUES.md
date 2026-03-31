# Poly-Trader Issues 追踪

---

## 🔴 高優先級

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H01 | 回測 API 返回 random 模擬數據，不是真實回測 | 回測頁面無參考價值 | 🔄 待修 |
| #H02 | collector 未寫入 Tongue v3 / Body v4 的新欄位（volatility, oi_roc, body_label） | 新數據不完整，模型訓練不準確 | 🔄 待修 |
| #H03 | 前端 Vite 代理到後端 8000 port，但後端需重啟才生效 | 刷新頁面可能暫時看不到更新 | ⚠️ 需用戶重啟 |

---

## 🟡 中優先級

| ID | 問題 | 建議改進 |
|----|------|----------|
| #009 | 缺少 SHAP 可解釋性圖表 | 集成 shap 庫 |
| #M01 | SenseChart 合併 kline 和特徵的 timestamp 對齊不精確（O(n²) 暴力比對） | 改用 hash map 或有序雙指針 |
| #M02 | K 線圖 1W 選項不支援（後端 API limit 最大 1000 點，1W 需 52 點但週期太長） | 移除 1W 或改用 daily candles |
| #M03 | 手機 RWD 未優化（雷達圖在小螢幕可能超出容器） | 添加 responsive size 判斷 |
| #M04 | WebSocket 推送未包含真實五感分數（只推 "connected"） | 加入真實數據推送 |
| #M05 | 綜合分數計算太簡單（5 感等權取平均） | 改用 XGBoost 模型權重 |
| #20 | Binance Futures 比率 API 返回空 | 需 API Key |

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
| #011 | Ear 概率 0.999 | v3: Binance 共識 0.33 |
| #012 | ear_zscore 不足 | 歷史回填 720 筆 |
| #013 | DummyPredictor | XGBoost 載入 |
| #014 | 數據累積慢 | 心跳自動收集 |
| #015 | ear/body 為 0 | 歷史填充 |
| #016 | predictor 未用模型 | xgb_model.pkl 載入 |
| #017 | Body 零變異 | 清算壓力 v3 → 21.5% 重要性 |
| #018 | 測試文件散落 | 移入 tests/ |
| UX1 | 載入中無反饋 | 狀態指示器 + 刷新按鈕 |
| UX2 | Legend 不可控 | legend toggle 正常 |
| UX3 | 交易無反饋 | 二次確認 + 成功提示 |
| UX4 | 分數無變化指示 | Δ 指標 |
| UX5 | 無狀態顯示 | 頂部狀態欄 |
| — | Streamlit 延遲 | React + FastAPI |
| — | 無 K 線圖 | TradingView lightweight-charts |
| — | Ear 模組無效 | Ear v3 Binance 共識 |
| — | 殭屍檔 | 清除 6 個臨時檔 |

---

## 📊 模型訓練結果（最新）

- 樣本：480,240 筆（47.5% 正樣本）
- **五感均衡**：Body 21.5% > Tongue 20.7% > Ear 19.9% > Nose 19.3% > Eye 18.6%
- 模型：`model/xgb_model.pkl`

---

**最後更新**：2026-03-31 18:30 GMT+8
