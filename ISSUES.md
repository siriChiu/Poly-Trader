# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 12:08 GMT+8（心跳 #228）*

---

## 📊 當前系統健康狀態（2026-04-05 12:08 GMT+8，心跳 #228）

### 數據管線
| 項目 | 數值 | 狀態 vs #227 |
|------|------|--------|
| Raw market data | 9,029 筆 | ⬆️ +3（#228 持續收集中）|
| Features | 8,991 筆 | ⬆️ +3 |
| Labels | 8,921 筆 | ➡️ 持平 |
| 全域 IC 通過 | 5/15 特徵 | ➡️ 持平（Ear, Body, VIX, DXY, RSI14）|
| 全域 IC 通過（僅 8 核心感官） | 2/8 | ➡️ Ear, Body 通過 |
| TW-IC（tau=200）通過 | 7/8 核心感官 ✅ | ➡️ 僅 Nose 仍 FAIL |
| BTC 當前 | $67,116 | ⬆️ +$10 |
| FNG | 12（極度恐懼）| ➡️ 持平 |
| VIX | ~23.90 | ➡️ 持平 |
| DXY | ~100.19 | ➡️ 持平 |
| Sell Win（全域） | 49.90% | ➡️ 持平 |
| Buy Win（全域） | 49.22% | ➡️ 持平 |
| 連敗 | 156 | ➡️ 持平 |
| 近 100 筆勝率 | 0% | ➡️ 持平 |
| Circuit Breaker | ✅ 觸發中（streak 156 >= 50 + WR 0% < 35%）| ➡️ 持續 |
| Tests | 6/6 PASS | ➡️ 通過 |

### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | **#H390** | **156 連敗持續 + 近 100 筆 0% 勝率** | 🔴 持續 | Circuit Breaker 已實作且已驗證觸發，fusion 路徑也加了 CB 檢查 |
| 🔴 | **#H379** | **sell_win < 50% — 系統方向性錯誤** | 🔴 持續 → 🟡 修復中 | **TW-IC fusion v2 已實作**：排除 Nose（TW-IC -0.028 FAIL），|IC| < 0.05 權重歸零，解決 Tongue(+0.532) 和 Body(+0.505) 被弱信號稀釋問題 |
| 🔴 | **#H440** | **全域與 TW-IC 演算法已修復** | ✅ 已修復 | ic_analysis.py 列名與 TW-IC 計算修正 |
| 🔴 | **#H438** | **全域/局部 IC 符號不一致** | ⚠️ | TW-IC 7/8 pass 但全域僅 2/8 核心通過 — 時間不均勻持續 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | 🟡 Nose IC 邊緣 | TW-IC -0.0279 FAIL → 融合模型中已排除（v2 修復）|
| #H371 | 🟡 Eye IC 邊緣 | TW-IC +0.1368 PASS → 改善中 |
| #H426 | ⚠️ Bull regime 策略反轉 | 已實作 BULL_SIGNAL_INVERT |
| #H340 | 🟡 Chop Regime IC 低 | 待分析 |

### ✅ 已解

| ID | 狀態 | 備註 |
|----|------|------|
| #H440 | ✅ 已修復 | ic_analysis.py 列名+TW-IC 修復 |
| #H436 | ✅ 已修復 | ic_analysis.py DB 表名修復 |
| #H435 | ✅ 已修復 | ic_analysis.py DB 路徑修復 |
| #H425a | ✅ 已應用 | TW-IC 重訓完成 |
| #H420 | ✅ 已修復 | Circuit Breaker 實作完成並驗證 |
| #H419a | ✅ 已修復 | 管線 Gap 恢復 |

---

## 🔴 感官 IC 掃描（心跳 #228, 2026-04-05 12:08 GMT+8）

### 全域 IC（對 label_sell_win）— 5/15 通過

| 感官/特徵 | 全域 IC | 狀態 |
|-----------|---------|------|
| **DXY** | -0.0737 | ✅ PASS |
| **VIX** | -0.0696 | ✅ PASS |
| **Body** | +0.0536 | ✅ PASS |
| **Ear** | -0.0514 | ✅ PASS |
| **RSI14** | -0.0510 | ✅ PASS |
| **BB_pct_b** | -0.0494 | ⚠️ NEAR |
| **MACD_hist** | -0.0463 | ⚠️ NEAR |
| **Tongue** | +0.0444 | ⚠️ NEAR |
| **ATR_pct** | +0.0438 | ⚠️ NEAR |
| **Nose** | -0.0443 | ⚠️ NEAR |
| **Eye** | +0.0422 | ⚠️ NEAR |
| **Aura** | -0.0386 | ❌ FAIL |
| **VWAP_dev** | +0.0323 | ❌ FAIL |
| **Mind** | -0.0281 | ❌ FAIL |
| **Pulse** | -0.0072 | ❌ FAIL |

### 時間衰減 IC（tau=200，加權 Pearson）— 7/8 通過 ✅
- Body: +0.5049 ✅
- Tongue: +0.5316 ✅ **TW-IC 最高！**
- Eye: +0.1368 ✅
- Mind: -0.1996 ✅
- Pulse: -0.2900 ✅
- Aura: -0.1782 ✅
- Ear: -0.0528 ✅
- Nose: -0.0275 ❌ **唯一不合格**

### 連續敗績分析
- 最大連敗：156（持續中）
- 最近 100 筆勝率：0% 🔴🔴🔴
- Circuit Breaker：✅ 觸發中（streak >= 50 AND recent WR < 35% 雙重條件）
- sell_win: 49.90%
- buy_win: 49.22%

---

## 📋 六色帽會議（#228）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=9,029 / Features=8,991 / Labels=8,921。全域 IC 5/15 特徵通過。TW-IC 7/8 核心通過（Body+0.505, Tongue+0.532, Eye+0.137, Pulse-0.290, Mind-0.200, Aura-0.178, Ear-0.053），僅 Nose 不合格（-0.028）。sell_win=49.90%，buy_win=49.22%。連敗 156，近 100 筆 0%。BTC=$67,116, FNG=12。Circuit Breaker 雙重觸發。tests 6/6 全通過。IC sign log 中 Nose TW-IC=-0.0275，仍低於 0.05 閾值。|
| **紅帽** | 數據管線持續運作（Raw 9,026→9,029）是好的。但 156 連敗 + 0% 近 100 筆仍是極端異常 — 在自然機率下幾乎不可能。Tongue+Body 雙超強信號（TW-IC 合計 >1.0）是系統最大的希望，但 v2 fusion 尚未回測驗證。Circuit Breaker 保護了系統不被摧毀 — 這是正確的安全網。|
| **黑帽** | (1) 156 連敗持續 — 即使是隨機擲硬幣也不應該這樣。(2) 全域 sell_win 和 buy_win 雙 <50% 意味著系統方向性錯誤 — 可能整個模型是反向的。(3) TW-IC fusion v2 仍無回測驗證。(4) 8 核心感官中，全域 IC 僅 2 個通過、TW-IC 有 7 個通過 — 這意味著時間加權讓信號看起來比實際更好，可能是過擬合最新數據。(5) 全域 IC 和 TW-IC 的符號差異可能意味著某些感官在長期是正確但在短期是錯誤的，反之亦然。|
| **黃帽** | (1) TW-IC 7/8 通過是迄今最佳成績。(2) Tongue+0.532 和 Body+0.505 是真正的阿爾法。(3) Circuit Breaker 在兩個路徑都保護系統。(4) 數據管線已恢復連續運作。(5) ic_signs.json 已更新且與 TW-IC 一致。(6) heartbeat_collect.py 已現代化。|
| **綠帽** | (1) **反向策略假說**：sell_win=49.90% 和 buy_win=49.22% 兩者都 <50%，但如果系統整體反向操作呢？即 model_predict(sell) → 實際做 buy？(2) **Tongue + Body 融合是唯一阿爾法** — 將其他 6 個感官降權到零，只用這兩個做決策。(3) **FNG=12 極端恐懼** — 歷史底部位，手動做多策略可能是最佳選擇。(4) 考慮用 TW-IC>0.1 的僅 Tongue/Body/Eye 做最小融合。|
| **藍帽** | (1) TW-IC fusion v2 已完成並 commit（#227，82f6ab8）。(2) heartbeat_collect.py 現代化並 commit（#228，988ba85）。(3) **下一步必須：回測驗證 v2 fusion 的 sell_win**。(4) 考慮最小融合（僅 Tongue+Body+Ey e）vs 當前 6 感官融合。(5) **更新 ic_signs.json 以確保 model 使用最新 TW-IC**。|

---

## ORID 決策

- **O**: Raw=9,029（+3）/ Features=8,991 / Labels=8,921。全域 IC 5/15 通過。TW-IC 7/8 核心通過，僅 Nose 失敗（-0.028）。sell_win=49.90%。156 連敗，近 100 筆 0%。Circuit Breaker 雙重觸發。BTC=$67,116, FNG=12。Tests 6/6 PASS。
- **R**: 數據管線穩定恢復是正面。但 156 連敗持續、勝率 <50% 是核心問題 — 系統的方向性錯誤仍未解決。
- **I**: (1) TW-IC fusion v2 是正確的方向但尚未驗證 — Tongue+Body 占 ~55% 權重可能翻轉賣出勝率。(2) 全域與 TW-IC 的巨大差異暗示時間不均勻可能是核心問題。(3) ic_signs.json 中 nose TW-IC=-0.0275 仍 FAIL，融合中已被排除。(4) Circuit Breaker 已保護系統但無法「解決」問題 — 需要模型翻正。
- **D**: (1) ✅ **TW-IC fusion v2 已 commit**。(2) ✅ **heartbeat_collect.py 現代化已 commit**。(3) **P0: 回測驗證 TW-IC fusion v2** — 必須確認 sell_win 提升。(4) **P0: 驗證 ic_signs.json 與 model 的一致性**。(5) **P1: 替換 Nose 感官**。(6) **P1: 探索最小融合（Tongue+Body+Eye only）**。

---

## 📋 本輪修改記錄

- **#228**: 數據收集持續 — Raw +3 rows（9,026→9,029），Features +3（8,988→8,991）
- **#228**: heartbeat_collect.py 現代化 — 改用 poly_trader.db、添加 labels/features/derivatives/FNG 查詢、移除舊的 market.db 依賴
- **#228**: Commit: `988ba85` — "HB #228: Update heartbeat_collect.py — modernize to poly_trader.db, add label counts, derivatives, FNG queries"
- **#228**: Tests 6/6 PASS — 模組導入、語法、數據品質、感官引擎、TypeScript、文件結構全通過
- **#228 發現**: ic_signs.json 中 Nose TW-IC=-0.0275 仍 < 0.05 閾值；TW-IC 7/8 通過維持最佳；全域 IC 與 TW-IC 差距持續

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **回測驗證 TW-IC fusion v2** — 比較 sell_win 改善 | #H379 |
| 🔴 P0 | **驗證 Gateway 是否尊重 should_trade=False** — 確保 Circuit Breaker 真正生效 | #H390 |
| 🔴 P0 | **驗證 ic_signs.json 與 model 一致性** — 確保 predictor 使用最新 IC 符號 | #H438 |
| 🟡 P1 | **替換 Nose 感官** — TW-IC 唯一不合格，全域+雙重都 FAIL | #H391 |
| 🟡 P1 | **最小融合實驗** — 僅用 Tongue+Body+Eye（TW-IC>0.1）融合 | #H340 |
| 🟡 P1 | **Bull regime 方向錯誤修復** — 59.4% 反向 | #H426 |

---

## 📊 距 90% 勝率差距分析

- **當前全域 sell_win**: 49.90%（差 **40.10pp**）
- **當前全域 buy_win**: 49.22%（差 **40.78pp**）
- **全域 IC 達標率**: 5/15 特徵（33.3%），2/8 核心感官
- **TW-IC 達標率**: 7/8 核心感官（87.5%） **⬆️ 維持最佳**
- **主要障礙**:
  1. **全域 sell_win 和 buy_win 雙 < 50%** — 等權融合模型稀釋了 Tongue(+0.532) 和 Body(+0.505) 的強信號
  2. **Nose 雙重失敗** — 全域 -0.044 + TW-IC -0.028，融合 v2 已排除
  3. **缺乏回測驗證** — TW-IC fusion v2 尚未驗證實際勝率提升
  4. **全域 vs TW-IC 巨大差異** — 可能意味著時間不均勻/非平穩性是核心問題
- **本輪最大改善**:
  - ✅ heartbeat_collect.py 現代化
  - ✅ 數據持續收集（+3 raw）
  - ✅ Tests 6/6 PASS
  - ✅ Git commit 完成（988ba85）

**關鍵洞察**: TW-IC fusion v2 將 Tongue 和 Body 的總權重提升到 ~55%（之前被所有感官均分稀釋），這可能翻轉 sell_win 到 50% 以上。但必須通過回測驗證才能確認。Circuit Breaker 現在在 predict() 和 predict_with_ic_fusion() 兩個路徑都保護系統。156 連敗持續意味著即使有 Circuit Breaker 保護，「為什麼模型是錯的」這個問題仍未解決。

---

*此文件每次心跳完全覆蓋，保持簡潔。*
