# Poly-Trader Issues 追踪

> **最後更新：2026-04-01 23:36 GMT+8**
> **🔄 心跳 #21：Collector ✅ 運行中(PID 20086)，CV=54.8%，BTC=$68,706.3，Raw=10,946，Features=10,937**

---

## 🔴 危急 — 系統性問題

| ID | 問題 | 影響 | 狀態 |
|----|------|------|------|
| #H33 | 🟡 模型 CV=54.8% 超過基線但仍需提升至 90% | 距目標仍遠 | 🟡 P1 — 繼續優化 |
| #H34 | 感官 IC 普遍負向：eye=-0.343, nose=-0.344, ear=-0.138（負向強！） | 樹模型可自動處理，但需確認是否訊號反轉 | 🟡 P1 — 繼續改進 |
| #H25 | 🔴 Labels 只有 2 類 (0,1)，無 class -1（持平） | 無「觀望」信號 | 🔴 P1 |
| #H31 | 🔴 歷史 raw data polymarket_prob 幾乎全 NULL（非空 ~26/10,946） | Ear/Polymarket 歷史信號缺失 | 🔴 P1 |

## 🟡 高優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H36 | 🟡 Nose/Eye IC 強負向（-0.343/-0.344）可能訊號反轉 | 確認是否需反轉特徵符號（×-1）或重新設計特徵 | 🟡 P1 |
| #H16 | 🟡 Pulse IC 弱 (+0.012，近雜訊) | 替換為 OI 變化率或 BTC/ETH 相對強度 | 🟡 P1 |
| #D01 | 🟡 TypeScript tsc Permission denied | npx tsc 路徑問題 | 🟡 P2 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|-------|------|------|
| #IC4 | 模型動態 IC 加權 | 實現感官動態權重 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
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

## 📊 當前系統健康 (2026-04-01 23:36 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 10,946 筆 | ✅ |
| Features | 10,937 筆 | ✅ |
| Labels | 13,067 筆 (0: 6855, 1: 6212) | ✅ |
| 最新資料時間 | 2026-04-01 15:27 UTC | ✅ |
| BTC 當前 | $68,706.3 | ✅ |
| Polymarket prob (realtime) | 0.3834 | ✅ |
| Polymarket prob (歷史) | 非空 ~26/10,946 | 🔴 |
| **Collector 進程** | **PID 20086 ✅ 運行中** | ✅ |
| 最近收集時間 | 2026-04-01 15:27 UTC | ✅ |
| 所有 Phase 1-7 檔案 | 全部存在 | ✅ |
| 語法檢查 | 全部通過 | ✅ |

### 模型性能（最新）
| 指標 | 值 | 評估 |
|------|------|------|
| Train Accuracy | 73.1% | ✅ 健康 |
| TimeSeries CV | 54.8% ± 5.6% | 🟡 **超越基線 52.5%** |
| Dumb Baseline | 52.5% | — |
| 目標 | 90% | 🔴 仍需大幅改進 |
| 最後訓練 | 2026-04-01 14:05 UTC | ✅ |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **驗證 IC 反轉**：Nose/Eye IC 強負向，需確認 join 邏輯與 label 時序 | #H34/#H36 |
| P1 | **Polymarket 數據回填**：只有 ~26 筆歷史，需修復收集邏輯 | #H31 |
| P1 | **替換 Pulse**：IC=+0.012 近雜訊，改用 OI 變化率或 BTC/ETH 相對強度 | #H16 |
| P1 | **持續收集 realtime 數據**：增加訓練樣本量改善 CV | #H33 |
| P2 | **Labels 3-class**：加入 class -1（持平/觀望信號） | #H25 |
| P2 | **修復 TypeScript 權限** | #D01 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
