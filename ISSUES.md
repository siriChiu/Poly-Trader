# Poly-Trader Issues 追踪

> **最後更新：2026-04-02 01:31 GMT+8**
> **🔄 心跳 #37：Collector ✅ 運行中(PID 20086)，CV=49.7%，BTC=$68,757，Raw=2,208，Features=2,208**
> **✅ 上輪：#H16 feat_body_roc 替換為 MACD_pct（IC: +0.012→-0.072），特徵重算+重訓完成**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=49.6%（數據不足，需持續收集） | 乾淨數據只有 2,208 筆，不足以提升 CV | 🟡 P1 — 持續收集 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 多感官 IC 偏弱（最強 eye=-0.129, 其餘 |IC|<0.1） | 需要更強信號特徵 | 🟡 P1 |
| ~~#H16~~ | ~~Body IC 極弱~~  | **已解決**：MACD_pct (IC=-0.072) | ✅ |
| #H44 | 🟡 feat_pulse / feat_mind 有 9 筆 NULL | 早期數據缺失，不影響近期收集 | 🟡 P2 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|-------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H42** | **feat_eye_dist/feat_pulse 數值在 1e-5 範圍（std≈0，XGBoost 無法分裂）** | **縮放×10000（轉為 bps），重算 2186 筆特徵，重訓模型。Eye IC: -0.044→-0.129, Pulse IC: ≈0→-0.079** | **04-02 00:19** |
| **#H43** | **8,760 筆 1969-era 污染數據混入訓練** | **從 features/labels/raw 全部清除，重訓模型** | **04-02 00:06** |
| #H41 | Collector 未運行 | 已確認 PID 20086 運行中，數據正常收集 | 04-01 23:36 |
| #H40 | senses.py `_get_latest_features()` 缺少 feat_pulse/aura/mind | 補齊 3 個特徵欄位，XGBoost mismatch 修復 | 04-01 23:00 |
| #H39 | feat_mind 最新行 NULL | 已修復，最新行 feat_mind=1.046 ✅ | 04-01 22:14 |
| #H38 | feat_pulse/mind/tongue/body 全為 NULL/常數 | 批次重算，修復 v2 recompute | 04-01 21:53 |
| Predictor mismatch | feature_names mismatch (raw vs feat_*) | 重訓後 model/xgb_model.pkl 已覆蓋為 feat_* | 04-01 22:05 |
| Aura leakage | Nose×Aura 相關 0.91 | Aura 重設為 price vs funding 背離 | 04-01 21:53 |
| model_metrics | 無法追蹤 CV accuracy | 新增 model_metrics 表 + train.py 自動寫入 | 04-01 21:53 |
| #H27 | Tongue FNG 靜態=8.0 | 替換為 volatility_24h | 04-01 (v3) |
| #M13 | feat_tongue_pct 只有 6 unique 值 | v3 preprocessor 修復 | 04-01 (v3) |
| #H33b | 模型標籤映射 bug | labels 已是 0/1，移除 -1→0 映射 | 04-01 21:24 |
| #H33c | train/predictor 特徵不一致 | 統一為 8 特徵 | 04-01 21:24 |
| #H33d | 模型嚴重過擬 (96.9%) | 正則化加強: depth 3, lr 0.03 | 04-01 21:24 |
| #H23 | 資料庫崩潰 | 90 天回填 → 2166 rows | 04-01 17:16 |
| #H24 | Collector 數據卡死 | backlog filled, realtime OK | 04-01 17:16 |
| #M06 | lag 特徵 IC 測試 | ret_1h=0.008, ret_4h=0.003, ret_24h=0.087；不改善 CV，暫緩 | 04-01 |

---

## 📊 當前系統健康 (2026-04-02 01:19 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 2,208 筆 | ✅ |
| Features | 2,208 筆 | ✅ |
| 最新資料時間 | 2026-04-01 17:18 UTC | ✅ |
| BTC 當前 | $68,757 | ✅ |
| **Collector 進程** | **PID 20086 ✅ 運行中** | ✅ |
| 近10分鐘新增 | 2 筆 | ✅ |

### 最新感官讀數 (17:18 UTC)
| 感官 | 值 | 說明 |
|------|-----|------|
| feat_eye_dist | 0.0172 | 技術面（中性偏弱） |
| feat_ear_zscore | 0.0144 | 市場共識（中性） |
| feat_nose_sigmoid | 0.0831 | 資金費率（轉多） |
| feat_tongue_pct | 0.0012 | 情緒（中性偏低） |
| feat_body_roc | 0.2384 | 清算壓力（偏低） |
| feat_pulse | -0.0197 | 脈搏（微弱偏空） |
| feat_aura | 0.3742 | Aura（偏多） |
| feat_mind | -1.4347 | Mind（強烈偏空） |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 75.7% | ✅ 健康（無過擬） |
| TimeSeries CV | 49.6% ± 5.1% | 🟡 略低，需更多數據 |
| 訓練樣本 | 2,208 筆（乾淨） | ⚠️ 持續收集中 |

### 感官 IC（修復 #H42 後，n=2,151）
| 感官 | IC | 評估 |
|------|-----|------|
| eye | -0.129 | 🟡 最強 |
| ear | -0.053 | ⚠️ 弱 |
| nose | -0.105 | 🟡 |
| tongue | -0.098 | 🟡 |
| body | +0.017 | ⚠️ 極弱 |
| pulse | -0.079 | 🟡 |
| aura | -0.025 | ⚠️ 弱 |
| mind | +0.072 | 🟢 |

### 特徵重要性（XGBoost）
| 特徵 | 重要性 |
|------|--------|
| feat_eye_dist | 16.1% |
| feat_body_roc | 15.3% |
| feat_pulse | 13.8% |
| feat_ear_zscore | 12.2% |
| feat_tongue_pct | 11.6% |
| feat_nose_sigmoid | 10.8% |
| feat_aura | 10.1% |
| feat_mind | 10.0% |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **持續累積乾淨數據**：現有 2,208 筆，目標 5,000+ 以提升 CV | #H33 |
| P1 | **Polymarket 數據回填**：只有少量歷史，需修復收集邏輯 | #H31 |
| P1 | **替換 Body 感官**：IC=+0.017 極弱，考慮 OI ROC（已有數據） | #H16 |
| P1 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
