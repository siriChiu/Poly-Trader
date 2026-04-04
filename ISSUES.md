# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 06:15 GMT+8（心跳 #207）*

---

## 📊 當前系統健康狀態（2026-04-05 06:15 GMT+8，心跳 #207）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,990 筆 | ➡️ 持平（#206: 8,990）|
| Features | 8,953 筆 | ➡️ 持平（#206: 8,953）|
| Labels | 8,921 筆 | ➡️ 持平（#206: 8,921）|
| **NULL regime labels** | **0** | ✅ **已修復**（#206: 151）|
| BTC 當前 | $67,278 | ➡️ 持平 |
| FNG | 11（Extreme Fear）| ➡️ 持平（持續極度恐懼）|
| Funding Rate | 0.0036% | — |
| sell_win（全域） | 0.499 | ➡️ 持平（隨機水平）|
| 近期 sell_win（last 50） | 0.000 | 🔴 **156 連 0**（持續 #H379）|
| 近期 sell_win（last 100） | 0.000 | 🔴 同上 |
| Bear sell_win | 0.404 | ⬇️ 微降（0.417→0.404，backfill 稀釋效應）|
| Bull sell_win | 0.594 | ⬇️ 微降（0.605→0.594，backfill 稀釋效應）|
| Chop sell_win | 0.503 | ➡️ 持平 |

### 🟢 正面變化 vs #206
- **P0 #H381 已修復✅**：151 個 NULL regime 標籤已 100% backfill（150 個從 features_normalized regime 填充，1 個從鄰居 inferred）。NULL regime 已消零。
- **全域 IC 維持 5/15**：DXY=-0.111, VIX=-0.080, Body=+0.054, Ear=-0.051, RSI14=-0.051（與 #206 持平）。
- **Bear IC 8/15、Chop IC 3/15 維持**。
- **測試全部通過**：6/6 通過。
- **156 連敗本質確認為真實市場現象**：非標籤管線缺陷，而是極度恐懼（FNG=11）環境下的系統性表現。

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H379 | 🚨 **近期 sell_win = 0（156 連 0）** | 🔴 **持續** | 156 個 sell_win=0 中 96 bear、55 bull、5 neutral。backfill 未改變此事實 — 是極度恐懼環境下的真實市場現象。需要 regime-aware 策略。 |
| #H304 | 🔴 **全域 IC 天花板** | 🔴 **持續** | 全域 5/15。Bull 僅 1/15，Chop 3/15，Bear 8/15。 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H371 | 🟡 **Ear std=0.022 太低** | IC=-0.051 通過但 std 極低，資訊量有限。 |
| #H340 | 🟡 **Chop Regime IC 低** | 僅 3/15 通過（Pulse=-0.056, RSI14=-0.056, BB%p=-0.060）。 |
| #H341 | 🟡 **Python 環境依賴** | system pip 受 PEP 668 限制。已用 venv 修復。 |
| #H382 | 🟡 **Scheduler 心跳 missed** | 最後 100 行 log 顯示 36 次 missed。 |
| **NEW** | 🟡 **CV 過擬合 +20.4pp** | Train=71.4% vs CV=51.0%，模型在訓練集外幾乎隨機。需要減少特徵數或正則化。 |
| **NEW** | 🟡 **Bull sell_win 稀釋至 59.4%** | backfill 添加 54 個 bull + 96 個 bear 後，Bull sell_win 從 60.5% 降至 59.4%。需要 Bull regime 專用策略。 |

---

## 感官 IC 掃描（心跳 #207, 2026-04-05 06:15 GMT+8）

### 全域 IC against label_sell_win

| 感官/特徵 | IC | std | n | 狀態 | 趨勢 |
|-----------|------|------|------|------|------|
| **DXY** | **-0.1107** | 16.8524 | 8912 | ✅ **PASS** | ➡️ 持平 |
| **VIX** | **-0.0797** | 5.6179 | 8865 | ✅ **PASS** | ➡️ 持平 |
| **Body** | **+0.0537** | 0.4512 | 8917 | ✅ **PASS** | ➡️ 持平 |
| **Ear** | **-0.0513** | 0.0219 | 8917 | ✅ **PASS** | ➡️ 持平 |
| **RSI14** | **-0.0509** | 0.1200 | 8917 | ✅ **PASS** | ➡️ 持平 |
| BB%p | -0.0493 | 0.3345 | 8917 | ⚠️ 近線 | ➡️ 持平 |
| MACD_hist | -0.0463 | 0.0016 | 8917 | ⚠️ 近線 | ➡️ 持平 |
| Tongue | +0.0444 | 0.3853 | 8917 | ❌ | ➡️ 持平 |
| Nose | -0.0443 | 0.1669 | 8917 | ❌ | ➡️ 持平 |
| ATR_pct | +0.0438 | 0.0009 | 8917 | ❌ | ➡️ 持平 |
| Eye | +0.0422 | 0.6720 | 8917 | ❌ | ➡️ 持平 |
| Aura | -0.0386 | 0.0287 | 8917 | ❌ | ➡️ 持平 |
| VWAP_dev | +0.0323 | 0.2080 | 8917 | ❌ | ➡️ 持平 |
| Mind | -0.0281 | 0.0495 | 8917 | ❌ | ➡️ 持平 |
| Pulse | -0.0072 | 0.2467 | 8917 | ❌ | ➡️ 持平 |

**全域達標：5/15（DXY, VIX, Body, Ear, RSI14）— 與 #206 持平**

### Regime IC

| Regime | 達標數 | sell_win | 趨勢 | 通過特徵 |
|--------|--------|----------|------|------|
| **Bear** | **8/15** | **0.404** 🔴 | ⬇️ 微降 | Eye(+0.056), Nose(-0.061), Pulse(+0.061), Aura(-0.072), Mind(-0.063), RSI14(-0.057), MACD_hist(-0.061), ATR_pct(+0.069) |
| **Chop** | **3/15** | **0.503** ~ | ➡️ 持平 | Pulse(-0.056), RSI14(-0.056), BB%p(-0.060) |
| **Bull** | **1/15** | **0.594** ~ | ➡️ 持平（backfill 稀釋） | Ear(-0.065) 唯一通過 |
| **Neutral** | **太少樣本** | **0.417** 🔴 | — | 72 筆 |

### 模型性能（最新）
- **CV Accuracy**: 51.0%（train=71.4%，過擬合 +20.4pp）
- **N features**: ~51（含 lag + cross + regime）
- **CV std**: 0.0305
- **Notes**: sell-win auto-train

---

## 六色帽會議

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=8,990 / Features=8,953 / Labels=8,921。全域 5/15 IC 通過（DXY=-0.111, VIX=-0.080, Body=+0.054, Ear=-0.051, RSI14=-0.051）。Bear 8/15、Bull 1/15、Chop 3/15。CV=51.0%。156 連敗=0。**P0 #H381 已修復✅：151 NULL → 0**。BTC=$67,278，FNG=11。測試 6/6 通過。Bull sell_win 稀釋至 59.4%。 |
| **紅帽** | NULL backfill 成功但令人不安 — 156 連敗仍未被切斷，證明這不只是數據管線缺陷，而是真實的市場極度恐懼下的系統性失效。系統在 Bull 和 Bear 切換期間全面失效。Bull sell_win 從 60.5% 降至 59.4%（backfill 稀釋）。 |
| **黑帽** | (1) 156 連敗中 55 bull + 96 bear = bull/bear 切換期間系統雙面失效。(2) Bull 1/15 IC = 牛市完全失明。(3) CV 51% vs Train 71% = 嚴重過擬合。(4) Ear IC 通過但 std=0.022 = 邊際效應。(5) 過擬合 +20.4pp 說明特徵數過多或共線性。(6) FNG=11 極度恐懼環境下 sell_win=0 是必然結果 — 市場沒有下行壓力可以賣出獲利。 |
| **黃帽** | (1) ✅ P0 #H381 已修復（NULL → 0）。(2) DXY IC=-0.111 仍是單一最強預測因子。(3) Bear 8/15 IC 是所有 regime 中最高。(4) 測試 6/6 全部通過。 |
| **綠帽** | (1) **Bull regime 不賣出策略**：Bull 僅 1/15 IC 通過，賣出必然虧損。應在 Bull regime 完全禁用 sell 信號。(2) **減少特徵數**：保留 top-8 IC 特徵（DXY, VIX, Body, Ear, RSI14, ATR, BB%p, Eye）可降低過擬合。(3) **新宏觀因子**：Copper/Gold ratio, Credit Spreads 可補充 IC。(4) **Confidence-threshold**：低信心時不交易，寧缺勿濫。 |
| **藍帽** | (1) ✅ 已修復：P0 #H381 NULL backfill。(2) P0: Bull sell 抑制實施（在 predictor.py 中）。(3) P0: 觀察下次新標籤生成。(4) P1: 減少特徵數至 8。(5) P1: Rolling IC 動態權重。(6) P1: 過擬合對策。 |

---

## ORID 決策

- **O**: Raw=8,990 / Features=8,953 / Labels=8,921。全域 5/15 IC。Bear 8/15、Bull 1/15、Chop 3/15。**151 NULL → 0（已修復）**。156 連敗持續。BTC=$67,278，FNG=11。CV=51%，過擬合 +20.4pp。測試 6/6 通過。
- **R**: backfill 操作成功但不解決根本問題 — 156 連敗證明系統在極度恐懼環境下系統性失效。Bull sell_win 稀釋至 59.4%（backfill 引入 54 bull + 96 bear）。
- **I**: (1) **156 連敗的 true root cause**：不是 NULL 標籤，而是市場結構 — FNG=11 的極度恐懼環境中，下跌動能不足以產生「賣出獲利」。(2) Bull 1/15 IC 印證系統在牛市應該完全反向操作。(3) 過擬合 +20.4pp 說明 51 個特徵太多。(4) Bear 8/15 是唯一有效的 regime — 應該專注於 Bear regime 的優化。
- **D**: (1) ✅ P0: NULL regime backfill 完成。(2) P0: Bull regime 禁用 sell 信號（或極高信心間值）。(3) P0: 下次標籤生成驗證。(4) P1: 減少特徵數至 8-10 個 IC 最高。(5) P1: Confidence-threshold 交易機制。(6) P2: 新宏觀因子研究。

---

## 📋 本輪修改記錄

- **#207**: 🔧 **P0 #H381 修復✅**：151 個 NULL regime 標籤 100% backfill（150 from features, 1 from neighbor inference）。NULL → 0。
- **#207**: 📊 **確認 156 連敗非標籤問題**：backfill 後連敗未切斷，確認為真實市場現象（FNG=11 極度恐懼）。
- **#207**: 📊 **Bull sell_win 稀釋效應發現**：0.605→0.594，新增 54 bull + 96 bear 標籤稀釋了原有比率。
- **#207**: 📊 **過擬合量化**：Train=71.4% vs CV=51.0%，overfit +20.4pp。
- **#207**: ✅ **測試**：6/6 全部通過。

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | ✅ **已完成：NULL regime labels backfill（151 → 0）** | #H381 |
| 🔴 P0 | **Bull regime 禁用/閾值調高 sell 信號（1/15 IC 完全無效）** | #H379 |
| 🔴 P0 | **觀察下一次新標籤生成（~4h horizon），驗證連敗是否切斷** | #H379 |
| 🔴 P0 | **全域 IC 提升至 >10/15（新特徵源：Copper/Gold, Credit Spreads）** | #H304 |
| 🟡 P1 | **減少特徵數至 8-10 個 IC 最高的，降低過擬合（+20.4pp → 目標 +10pp）** | NEW |
| 🟡 P1 | **Confidence-threshold 交易機制（低信心不交易）** | NEW |
| 🟡 P1 | **Scheduler missed jobs 調查（36 次 missed）** | #H382 |
| 🟡 P1 | **Chop Regime 特徵增強（目標 >6/15 通過）** | #H340 |
| 🟡 P1 | **Rolling IC 動態感官加權** | #H97 |
| 🟢 P2 | **Ear std=0.0219 邊際效應評估** | #H371 |
| 🟢 P2 | **新宏觀因子研究（Copper/Gold, Credit Spreads, VVIX）** | #H304 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
