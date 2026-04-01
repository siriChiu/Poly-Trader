# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 17:33 GMT+8**
> **🚨 關鍵發現：模型嚴重過擬！Walk-Forward 測試僅 53.3%（隨機基線 52.5%），完全無預測力**
> **CV 僅 44.4%（5-fold），Train 96.9% → gap = 52.5pp！**
> **comprehensive_test: 5/6 通過 (TypeScript tsc 權限問題)**

---

## 🔴 🚨 危急 — 系統性問題（本輪確認）

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🔴 模型嚴重過擬：Train 96.9% vs Walk-Forward 53.3% | 預測力 = 隨機，所有交易決策無效 | 🔴 P0 — 必須重構 |
| #H34 | 🔴 全感官 IC < 0.08：Eye IC=0.0209 最高 | 無感官達到 IC > 0.05 可用閾值 | 🔴 P0 — 無有效信號 |
| #H35 | 🔴 Nose/Tongue/Body IC 為負但重要性占比 72% | 模型用反轉雜訊做擬合（非線性扭曲） | 🔴 P0 — 特徵選擇錯誤 |
| #H25 | 🔴 Labels 只有 2 類 (0,1) 無 class -1 | 模型退化為二元分類，無「持平」區間 | 🔴 維持 |
| #H26 | 🔴 Body ROC 粗粒度僅 3 unique 值 | 歷史回填離散化導致 67% = 常數 0.246 | 🔴 需改用連續 ROC |
| #H27 | 🔴 Tongue 僅 6 unique 值 | tongue_sentiment ≈ -0.54 幾乎常數 | 🔴 tongue 卡死 |
| #H29 | 🔴 FNG 完全常數 8.0 (90天內僅6筆=8) | FNG API 僅返回極端恐懼值 | 🔴 FNG API 卡死 |
| #H30 | 🔴 24 筆 labels future_return_pct 為 NULL | 最近 24h 標籤未生成 | 🔴 需修復 label pipeline |
| #H31 | 🔴 Nose funding rate 常數 8.67e-06 | 2160/2166 raw rows funding_rate = NULL or 8.67e-06 | 🔴 funding API 卡死 |
| #H32 | 🔴 Polymarket prob 常數 0.4420 | 僅 6 筆非-NULL（collector 新寫入）| 🔴 polymarket API 卡死 |

## 🔴 高優先級

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H36 | 🔴 Ear IC=0.0466 依賴 price momentum 而非 Polymarket | 回充填充耳用動量代理 → 與 Eye 高度共線 | 🔴 解耦 |
| #H37 | 🔴 2160/2166 raw rows 為 NULL collector 欄位 | 回填只寫 klines，FNG/funding/poly/tongue 全 NULL → 預處理填 default | 🔴 回填不完整 |
| #H16 | 🟡 Eye IC 極弱 IC≈0.02 | 2113 unique 但有變異，預測力不足 | 🟡 需多時間框架增強 |
| #D01 | 🟡 TypeScript 編譯失敗 (tsc Permission denied) | 無法驗證前端 | 🟡 npx/tsc 權限 |

## 🟡 中優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #M06 | 缺少 lag features | 增加 1h/4h/24h 時間滯後特徵 | 🟡 下一步 |
| #H15 | Tongue 應汰換（FNG 靜態） | 找 Twitter/News sentiment API | 🟡 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| #H23 | 🔴 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |
| #H24 | 🔴 Collector 數據卡死 | backlog filled, realtime OK | 04-01 17:16 |
| #H28 ❌ | Ear prob 常數 | **誤判** — Ear 用 price momentum 回填，有 2083 unique | 04-01 17:33 修正 |

---

## 📊 當前系統健康 (2026-04-01 17:33)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2166 筆 (2160 historical + 6 realtime) | ✅ |
| Features | 2166 筆 | ✅ |
| Labels | 2160 筆 (2-class: 0/1), 24 NULL | ⚠️ |
| Model | XGBoost 100 trees, max_depth=4, 149KB | ⚠️ 過擬 |
| BTC 當前 | $68,689.62 | ✅ |
| FNG | 8 (Ext Fear, 2160 NULL + 6=8) | 🔴 |
| Funding Rate | 8.67e-06 (2160 NULL + 6 rows) | 🔴 |

### 感官 IC (vs labels, 2136 valid samples)
| 特徵 | IC_label | IC_return | std | unique | 狀態 |
|------|----------|-----------|-----|--------|------|
| Eye (feat_eye_dist) | **+0.0209** | **+0.0767** | 0.0191 | 2113 | 🟡 略有效 |
| Ear (feat_ear_zscore) | +0.0466 | +0.0485 | 1.0979 | 2083 | ⚠️ 填充代理，弱 |
| Nose (feat_nose_sigmoid) | **-0.0135** | -0.1017 | 0.2221 | 262 | 🔴 無效 |
| Tongue (feat_tongue_pct) | **-0.1289** | -0.1154 | 0.1185 | 30 | 🔴 反向 |
| Body (feat_body_roc) | **-0.0781** | -0.0728 | 0.1843 | 3 | 🔴 常數 |

### 模型性能
| 指標 | 數值 | 評估 |
|------|------|------|
| Train Accuracy | 96.9% | 🔴 過擬 |
| Walk-Forward (70/30) Accuracy | **53.3%** | 🔴 ≈ 隨機 |
| 5-Fold CV Accuracy | **44.4%** | 🔴 比隨機差 |
| Recent 200 Accuracy | 96.5% | 🔴 過擬表現 |
| Dumb Baseline | 52.5% | (always predict majority) |
| Overfit Gap | **43.7pp** | 🔴 極端過擬 |

**結論：模型完全無出樣本預測力。所有感官信號強度不足，模型學到的是訓練集雜訊。**

---

## 📋 下一步 (更新後)

| 優先 | 行動 | Issue | 指令 |
|------|------|-------|------|
| P0 | 接受現實：重構全感官框架 | #H33,H34 | 新數據源 + 新特徵設計 |
| P0 | Nose 替換为 OI/liquidation flow 真實來源 | #H20 | 改用 Binance OI + liquidation |
| P0 | Tongue 汰换 FNG → CryptoPanic/Twitter sentiment | #H27,#H15 | 找新的情緒 API |
| P0 | Body 改用連續 ROC (非離散化) | #H26 | 移除 lambda 離散 |
| P1 | 增加 lag features (3h/6h/24h) | #M06 | preprocessor 加入滯後 |
| P1 | 降低模型複雜度 + 加入正則化 | #H33 | max_depth=3, L1/L2 reg |
| P2 | 引入更多獨立信號源 (鏈上數據、訂單流等) | #H34 | 打破封閉系統 |
| P3 | Eye IC 增強：多時間框架 MA distance | #H16 | 1h/4h/24h 均線距離 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
