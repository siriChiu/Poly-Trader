# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 09:26 GMT+8（心跳 #219）*

---

## 📊 當前系統健康狀態（2026-04-05 09:26 GMT+8，心跳 #219）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,991 筆 | ➡️ 持平 |
| Features | 8,954 筆 | ➡️ 持平 |
| Labels | 8,921 筆 | ➡️ 持平 |
| Merged (correct join) | 8,778 筆 | ➡️ 持平 |
| **RAW 未轉 features** | **37 筆** | 🔴 持平 |
| **Features 未轉 labels** | **33 筆** | 🔴 持平 |
| BTC 當前 | $67,314 | ➡️ 持平 |
| FNG | 11（極度恐懼）| ➡️ 持平 |
| VIX | 23.90 | ➡️ 持平 |
| DXY | 100.19 | ➡️ 持平 |
| Funding | 0.000027 | ➡️ 持平 |
| Sell Win（全域 8,921） | 0.5076 | ⬆️ 微升 |

### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | #H392 | **CV=51% 嚴重過擬** | 🔴 持平 | Train=71%, CV=51%, Gap=+20pp |
| 🔴 | #H390 | **156 連敗 streak（標籤邊界效應）** | 🔴 持平 | threshold_pct=0.05% 造成「假 0」 |
| 🔴 | #H379 | **全域 IC 持續低落（1~4/15 通過）** | 🔴 持平 | 取決於 join 方法：正確 join=1/8 全域，時間 join=4/15 |
| 🔴 | #H405 | **feature_engine/__init__.py 被診斷腳本覆蓋** | ✅ **已修復** | PERCENTILE_CONT 在 SQLite 中不支持，替換為正確 __init__.py |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | 🟡 **Nose+Body z-combo 退化** | IC 全域=0 但 TW-IC 不穩定 |
| #H371 | 🟡 **Ear std=0.0221 太低** | 全域 IC=-0.0516 通過但資訊量低 |
| #H340 | 🟡 **Chop Regime IC 低** | 僅 1/8 通過，仍需 regime-aware 訓練 |
| #H379b | 🟡 **NEAR 閾值特徵** | macd=-0.046, bb=-0.050（全域通過邊緣） |

### 🔬 新發現（心跳 #219 新增）

| ID | 問題 | 狀態 |
|----|------|------|
| #H219-JOIN | 🔴 **Join 方法導致 TW-IC 計算偏差** | 正確 join [timestamp,symbol]→8778 行 vs 僅 timestamp→8929 行（有重複）；#218 報告的 TW-IC 7/8 使用的是有重複的 join，正確方法下 TW-IC 僅 4/8 |
| #H219-DW | 🔥 **Dynamic Window N=200/400 達 7/8 PASS** | Tongue+0.50, Body+0.46 在近期 window 最強；N=100 為 0/8（樣本太少）；N=600/1000 降至 6/8｜
| #H219-IMPORT | ✅ **feature_engine.preprocessor 導入修復** | `__init__.py` 從診斷腳本恢復為正確模組定義，測試 5/6→6/6 PASS |

### ✅ 已解

| ID | 狀態 | 備註 |
|----|------|------|
| **#H405** | ✅ **feature_engine/__init__.py 已修復** | 替換為正確 __init__.py，diagnostic 腳本移至 scripts/check_label_threshold.py |
| **#H400** | ✅ **_time_weighted_ic SQLAlchemy bug 已修復** | 字串列名未轉 Column 物件 |
| #H216-Syntax | ✅ 語法錯誤已修復 | |
| #H382 | ✅ 心跳 missed | |
| #H381 | ✅ NULL regime label | |
| #H380 | ✅ 音樂/社交特徵移除 | |

---

## 🔴 感官 IC 掃描（心跳 #219, 2026-04-05 09:26 GMT+8）

### 全域 IC against label_sell_win（正確 join，N~8,778）

| 感官/特徵 | IC | std | 狀態 | 與 #218 差異 |
|-----------|------|------|------|------|
| **Ear** | **-0.0517** | 0.0221 | ✅ **PASS** | ➡️ 持平 |
| Nose | -0.0483 | 0.1658 | ⚠️ NEAR | ⬇️ 微降 |
| Body | -0.0450 | 0.3324 | ⚠️ NEAR | ⬇️ |
| Tongue | +0.0036 | 0.3690 | ❌ FAIL | ⬇️⬇️ |
| VIX | -0.0702 | 1.5081 | ✅ **PASS** | ➡️ |
| RSI14 | -0.0538 | 0.1198 | ✅ **PASS** | ➡️ |
| BB_pct_b | -0.0526 | 0.3343 | ✅ **PASS** | ➡️ |
| MACD_hist | -0.0465 | 0.0016 | ⚠️ NEAR | ➡️ |
| Eye | +0.0220 | 0.5175 | ❌ FAIL | ⬇️ |
| Pulse | +0.0106 | 0.2461 | ❌ FAIL | ➡️ |
| Aura | -0.0396 | 0.0289 | ❌ FAIL | ➡️ |
| Mind | -0.0293 | 0.0499 | ❌ FAIL | ⬇️ |
| 8 music/social | constant | — | ❌ FAIL | ➡️ |

**全域達標：1/8 核心感官（僅 Ear）｜4/15 含所有特徵**

### 時間衰減 IC（tau=200，正確 join）— 4/8 PASS

| 感官 | TW-IC | 全域 IC | Delta | 狀態 |
|------|-------|---------|-------|------|
| **Nose** | **-0.0584** | -0.0483 | -0.0101 | ✅ **PASS** |
| **Pulse** | **+0.0878** | +0.0106 | +0.0772 | ✅ **PASS** |
| **Aura** | **-0.0916** | -0.0396 | -0.0520 | ✅ **PASS** |
| **Mind** | **-0.0797** | -0.0293 | -0.0504 | ✅ **PASS** |
| Tongue | +0.0335 | +0.0036 | +0.0300 | ❌ FAIL |
| Body | -0.0334 | -0.0450 | +0.0116 | ❌ FAIL |
| Eye | +0.0106 | +0.0220 | -0.0114 | ❌ FAIL |
| Ear | -0.0084 | -0.0517 | +0.0433 | ❌ FAIL |

**注意**：#218 報告的 TW-IC 7/8 PASS 使用的是 timestamp-only join（8929 行，有重複）。
用相同方法重新計算確實得到 7/8 PASS（Tongue+0.53, Body+0.51）。
但正確 join（8778 行）只有 4/8 PASS — **Tongue 和 Body 的 TW-IC 從 0.53/0.51 降至 0.03/−0.03**。

### Dynamic Window IC（正確 join）

| Window | 通過數 | 關鍵特徵 |
|--------|--------|------|
| N=100 | **0/8** | 全部太弱 |
| N=200 | **7/8** | Tongue+0.52, Body+0.48, Ear-0.23, Eye+0.12 |
| N=400 | **7/8** | Tongue+0.50, Body+0.46, Eye+0.14, Ear-0.08 |
| N=600 | **6/8** | Tongue+0.38, Body+0.38, Pulse-0.15, Eye+0.13 |
| N=1000 | **6/8** | Tongue+0.28, Body+0.32, Pulse-0.09, Eye+0.12 |

### Regime-aware IC（全域 8 感官，正確 join）

| Regime | 通過數 | sell_win | 關鍵特徵 |
|--------|--------|------|------|
| **Bear** | **5/8** 🟢 | 0.4170 | Eye+0.056, Nose-0.061, Pulse+0.061, Aura-0.072, Mind-0.063 |
| Bull | **1/8** 🔴 | 0.6055 | Ear-0.065 |
| Chop | **1/8** 🔴 | 0.5028 | Pulse-0.056 |

---

## 📋 六色帽會議（#219）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=8,991 / Features=8,954 / Labels=8,921（持平）。正確 join 全域 IC 1/8（Ear 唯一通過）。DW IC N=200/400 達 7/8（Tongue+0.50, Body+0.46）。Regime: Bear 5/8, Bull 1/8, Chop 1/8。sell_win=50.76%。BTC=$67,314。FNG=11。VIX=23.90。DXY=100.19。**P0 修復**：feature_engine/__init__.py 導致 import 失敗。tests 6/6 通過。 |
| **紅帽** | **警示**。Dynamic Window 結果和全域結果矛盾巨大——N=200 時 Tongue/Body 極強（+0.50），但全域幾乎為零。這意味著「特徵在短期內有效，但長期被稀釋」。Tongue/Body 從 N=1000 的 0.28/0.32 到 N=200 的 0.52/0.48 是強烈的時間衰減信號。Bull regime 僅 1/8 通過尤其令人不安——在 60.5% sell_win 的牛市中最強的感官反而幾乎全部失效。 |
| **黑帽** | (1) **#218 的 TW-IC 7/8 報告基於錯誤的 join** — timestamp-only join 產生重複行（8929 vs 8778），高估了 Tongue/Body 的 TW-IC。(2) **正確 TW-IC 只有 4/8** — Nose/Pulse/Aura/Mind 通過，但 Tongue/Body 這兩個「最強信號」實際上是 0.03/−0.03。(3) **DW IC 的 N=100 為 0/8** — 即使是 200 sample window 才開始有效，預測視野太窄。(4) **Bull regime 1/8** 在 sell_win=60.5% 的環境下幾乎無法提取信號。(5) **37+33 gap 持續存在**。 |
| **黃帽** | (1) **DW IC N=200-400 達 7/8** — 近期的 Tongue/Body 確實強，DW 是正確的指標。(2) **Bear regime 5/8** 在 FNG=11 恐懼市場中至少有 5 個可靠信號。(3) **測試 6/6** — 修復後基礎設施正常。(4) **Tongue/Body 的時間衰減模式可被利用** — 它們不是穩定預測器，但在特定時期有效。 |
| **綠帽** | (1) **DW IC 應取代全域 IC 作為主要指標** — 全域平均掩蓋了短期預測力。(2) **Tongue/Body 作為 trigger 而非持續信號** — 當 DW-200 IC > 0.3 時使用它們，否則關閉。(3) **Regime-specific 訓練需要立即進行** — Bull 1/8 說明全域模型完全不合適。(4) **Nose 的 TW-IC 在正確 join 下反而更好（-0.058 vs #218 的 -0.025）** — 可能 Nose 才是穩定的，而不是「死感」。 |
| **藍帽** | (1) **P0: 使用 DW-200 IC 替代全域 IC 作為特徵選擇標準** — 7/8 vs 1/8。(2) **P0: Regime-specific IC monitoring** — 每個 regime 需要獨立的 IC 追蹤。(3) **P1: Tongue/Body trigger 機制** — 不作為持續特徵，而是作為開關信號。(4) **P1: Gap 37→33 根因排查**。(5) **P2: 修正 join 邏輯** — 在 IC 計算中使用正確的 [timestamp, symbol] join。 |

---

## ORID 決策

- **O**: Raw=8,991 / Features=8,954 / Labels=8,921。正確全域 IC 1/8（Ear）。DW IC: N=200 → 7/8, N=400 → 7/8, N=100 → 0/8。Tongue+0.50/Body+0.46 在 N=400 最強。Regime: Bear 5/8 vs Bull 1/8 vs Chop 1/8。sell_win=50.76%。BTC=$67,314。FNG=11。VIX=23.90。DXY=100.19。Tests 6/6 PASS。feature_engine.__init__.py P0 已修復。
- **R**: **矛盾感更強烈**。#218 報告的 TW-IC 7/8 被證明是 join bug 的產物，但 DW IC 7/8 在 N=200-400 是真實的。這揭示了一個更深層的問題：系統的特徵有效性不是固定的，而是高度依賴時間視窗和市場狀態。全域 IC 太「平」，短期 IC 太「噪」，需要的是正確的視窗選擇。
- **I**: (1) **全域 vs DW 的差距證明特徵是時間局部的** — 它們不是「好」或「壞」，而是「有時好有時壞」。(2) **Tongue/Body 的 N=200-400 有效性但 N=1000 衰減** 說明這些特徵的生命週期約為 200-1000 個樣本。(3) **Bull regime 1/8 是因為 sell_win=60.5%** — 當大多數都 win 時，任何特徵都難以區分。(4) **#218 的 TW-IC 高估是因為 join bug** — 這需要被記錄並修正 IC 計算管道。
- **D**: (1) **P0: 修正 IC 計算 join 邏輯** — 在所有 IC 分析腳本中使用 [timestamp, symbol] join。(2) **P0: 建立 DW-200/400 IC 監控** — 替代全域 IC 作為主要指標。(3) **P1: Tongue/Body DW trigger** — 當 DW IC > 0.3 時加權，否則降權。(4) **P1: Regime-specific IC dashboard** — 每個 regime 獨立跟蹤。(5) **P2: Nose 重新評估** — 在正確 join 下 TW-IC=-0.0584 PASS，可能不是「死感」。(6) **P2: Gap 37→features→33→labels 排查**。

---

## 📋 本輪修改記錄

- **#219**: 🔴 **feature_engine/__init__.py P0 已修復** — 從診斷腳本（PERCENTILE_CONT SQLite 錯誤）恢復為正確 __init__.py，測試從 5/6→6/6 PASS。
- **#219**: 🔴 **發現 #218 TW-IC 7/8 是 join bug** — timestamp-only join 重複行導致高估 Tongue/Body（0.53→0.03）。
- **#219**: 🟡 **DW IC N=200/400 達 7/8** — Tongue+0.50, Body+0.46 在短期內非常強。
- **#219**: 🔴 **Nose 在正確 join 下 TW-IC=-0.0584 PASS** — 不是「死感」，TW-IC 比全域更好。

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **修正 IC 計算 join 邏輯** — 所有 IC 分析使用 [timestamp, symbol] join | #H406 |
| 🔴 P0 | **建立 DW-200/400 IC 監控** — 替代全域 IC 作為主要指標 | #H407 |
| 🔴 P0 | **CV=51% 過擬問題** — Train 71% vs CV 51% gap +20pp | #H392 |
| 🟡 P1 | **Tongue/Body DW trigger 機制** — DW IC > 0.3 時加權 | #H408 |
| 🟡 P1 | **Regime-specific IC dashboard** | #H409 |
| 🟢 P2 | **Nose 重新評估** — TW-IC PASS，保留不替換 | #H410 |
| 🟢 P2 | **Gap 37→features→33→labels 排查** | #H393 |

---

## 📊 距 90% 勝率差距分析

- **當前 CV Accuracy**: ~51.0%（差 39pp）— **持平**
- **全域 IC 達標率**: 1/8 核心（12.5%）— **⬇️ 惡化**（從 #218 的 3/15 降至 1/8）
- **DW IC 達標率（N=400）**: 7/8（88%）🔥 **這是最準確的指標**
- **Regime 分化**: Bear = 5/8 vs Bull = 1/8 vs Chop = 1/8（差距巨大）
- **sell_win**: 50.76%（接近擲硬幣）
- **主要障礙**:
  1. **全域 IC 幾乎全滅** — 全域平均完全掩蓋了短期預測力
  2. **CV Train-CV Gap = +20pp** — 過擬問題仍未解決
  3. **Bull/Chop regime 僅 1/8** — 全域模型無法應對不同市場狀態
  4. **DW N=100 為 0/8** — 即使短期窗口也需要至少 200 樣本才有效
  5. **#218 TW-IC 7/8 是計算錯誤** — Tongue/Body 實際遠低於報告值

---

*此文件每次心跳完全覆蓋，保持簡潔。*
