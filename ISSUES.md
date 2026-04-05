# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 11:36 GMT+8（心跳 #227）*

---

## 📊 當前系統健康狀態（2026-04-05 11:36 GMT+8，心跳 #227）

### 數據管線
| 項目 | 數值 | 狀態 vs #226 |
|------|------|--------|
| Raw market data | 8,996 筆 | ⬆️ +4（#227 數據收集恢復）|
| Features | 8,958 筆 | ⬆️ +3 |
| Labels | 8,921 筆（Merged: 8,921） | ➡️ 持平 |
| 全域 IC 通過 | 5/15 特徵 | ➡️ 持平（Ear, Body, VIX, DXY, RSI14）|
| 全域 IC 通過（僅 8 核心感官） | 2/8 | ➡️ Ear, Body 通過 |
| TW-IC（tau=200）通過 | 7/8 核心感官 ✅ | ➡️ 僅 Nose 仍 FAIL |
| BTC 當前 | $67,106 | ⬆️ +$81 |
| FNG | 12（極度恐懼）| ➡️ 持平 |
| VIX | 23.90 | ➡️ 持平 |
| DXY | 100.19 | ➡️ 持平 |
| Sell Win（全域） | 49.90% | ➡️ 持平 |
| Buy Win（全域） | 49.22% | ➡️ 持平 |
| 連敗 | 156 | ➡️ 持平 |
| 近 100 筆勝率 | 0% | ➡️ 持平 |
| Circuit Breaker | ✅ 觸發中（streak 156 >= 50 + WR 0% < 35%）| ➡️ 持續 |
| Tests | syntax OK | ➡️ 通過 |

### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | **#H390** | **156 連敗持續 + 近 100 筆 0% 勝率** | 🔴 持續 | Circuit Breaker 已實作且已驗證觸發，fusion 路徑也加了 CB 檢查 |
| 🔴 | **#H379** | **sell_win < 50% — 系統方向性錯誤** | 🔴 持續 → 🟡 修復中 | **TW-IC fusion v2 已實作**：排除 Nose（TW-IC -0.0279 FAIL），|IC| < 0.05 權重歸零，解決 Tongue(+0.532) 和 Body(+0.505) 被弱信號稀釋問題 |
| 🔴 | **#H440** | **全域與 TW-IC 演算法已修復** | ✅ 已修復 | ic_analysis.py 列名與 TW-IC 計算修正 |
| 🔴 | **#H438** | **全域/局部 IC 符號不一致** | ⚠️ | TW-IC 7/8 pass 但全域僅 2/8 核心通過 — 時間不均勻持續 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | 🟡 Nose IC 邊緣 | TW-IC -0.0279 FAIL → 融合模型中已排除（v2 修復）|
| #H371 | 🟡 Eye IC 邊緣 | TW-IC +0.1347 PASS → 改善中 |
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

## 🔴 感官 IC 掃描（心跳 #227, 2026-04-05 11:36 GMT+8）

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
- Eye: +0.1347 ✅
- Mind: -0.2021 ✅
- Pulse: -0.2900 ✅
- Aura: -0.1786 ✅
- Ear: -0.0531 ✅
- Nose: -0.0279 ❌ **唯一不合格**

### 連續敗績分析
- 最大連敗：156（持續中）
- 最近 100 筆勝率：0% 🔴🔴🔴
- Circuit Breaker：✅ 觸發中（streak >= 50 AND recent WR < 35% 雙重條件）
- sell_win: 49.90%
- buy_win: 49.22%

---

## 📋 六色帽會議（#227）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=8,996 / Features=8,958 / Labels=8,921 / Merged=8,921。全域 IC 5/15 特徵通過。TW-IC 7/8 核心通過（Body+0.505, Tongue+0.532, Eye+0.135, Pulse-0.290, Mind-0.202, Aura-0.179, Ear-0.053），僅 Nose 不合格（-0.028）。sell_win=49.90%，buy_win=49.22%。連敗 156，近 100 筆 0%。BTC=$67,106, FNG=12, VIX=23.90, DXY=100.19。Circuit Breaker 雙重觸發（streak>=50 + WR<35%）。TW-IC fusion v2 已實作並 commit。 |
| **紅帽** | 數據收集恢復（+4 raw）是正面信號。但 156 連敗 + 0% 近 100 筆仍然是災難級別。TW-IC fusion v2 是正確的改進方向 — 讓 Tongue 和 Body 的超強信號（+0.53 和 +0.50）真正發揮作用，而不是被 Nose(-0.028) 和其他廢信號稀釋。Circuit Breaker 在 fusion 路徑的添加確保即使 fusion 被調用也不會交易。 |
| **黑帽** | (1) 全域 sell_win 和 buy_win 雙 < 50% 持續 — 核心模型仍未翻正。(2) 數據管線停滯 226 輪後才恢復 — 浪費大量時間。(3) TW-IC fusion v2 尚未用回測驗證 — 只是理論改進。(4) Circuit Breaker 阻止了交易，但沒有解決「為什麼模型是錯的」這個根本問題。(5) Nose 全域 IC -0.0443 其實已經接近 0.05 閾值，但 TW-IC 更差（-0.028）— 時間趨勢惡化。 |
| **黃帽** | (1) TW-IC 7/8 核心通過是迄今最佳 IC 成績。(2) Tongue+0.532 和 Body+0.505 是真正的阿爾法信號。(3) Circuit Breaker 雙重檢查（predict + fusion）確保安全。(4) 數據收集恢復，不再停滯。(5) v2 fusion 排除 Nose、零權重低於閾值感官、添加 circuit breaker。 |
| **綠帽** | (1) **Tongue + Body 融合信號可能是翻盤關鍵** — 兩者 TW-IC 加總 > 1.0，極不尋常。(2) **FNG=12 的歷史性恐懼** — 過去類似水平往往是底部，建議手動做多策略。(3) **TW-IC 動態重算機制已存在**（_time_weighted_ic），只需確保 fusion 每次都調用。(4) 考慮將 Pulse/Mind/Aura/Eye/Ear 也加入動態權重融合。 |
| **藍帽** | (1) **TW-IC fusion v2 已完成並 commit** — #H379 部分修復。(2) **Circuit Breaker 在 fusion 路徑已加入** — #H390 部分修復。(3) **下次心跳：需要用 TW-IC v2 做 backtest 驗證** — 確認勝率是否提升。(4) **考慮 Nose 感官替換** — #H391 仍為 P1。 |

---

## ORID 決策

- **O**: Raw=8,996（+4）/ Features=8,958（+3）/ Labels=8,921。全域 IC 5/15 通過。TW-IC 7/8 核心通過，僅 Nose 失敗（-0.028）。sell_win=49.90%。156 連敗，近 100 筆 0%。Circuit Breaker 雙重觸發。BTC=$67,106, FNG=12, VIX=23.90, DXY=100.19。
- **R**: Tongue+0.532 和 Body+0.505 的 TW-IC 異常強大，但全域模型無法利用這些信號因為等權融合被弱信號稀釋。Circuit Breaker 是唯一保護機制。
- **I**: (1) **等權融合是核心錯誤** — Tongue TW-IC 0.532 是 Pulse TW-IC -0.007 的 75 倍強度，但在等權模型中兩者權重相同。(2) **Nose 在全域和 TW-IC 都失敗** — 應該被替換而非修復。(3) **TW-IC fusion v2 解決權重問題** — 排除 Nose，|IC|<0.05 歸零，強信號（Tongue/Body）將主導融合。
- **D**: (1) ✅ **已完成：TW-IC fusion v2** — #H379 部分修復。(2) ✅ **已完成：Circuit Breaker 在 fusion 路徑** — #H390 部分修復。(3) **P1: 回測驗證 TW-IC fusion v2** — 比較 v1 vs v2 的 sell_win。(4) **P1: 替換 Nose 感官** — #H391。(5) **P2: 考慮外部阿爾法源** — Twitter/X 情緒、Polymarket 深度數據。

---

## 📋 本輪修改記錄

- **#227**: 數據收集恢復 — Eye/Nose/Ear/Tongue/Body/Macro 全部成功，Raw +4 rows（8,992→8,996）
- **#227**: TW-IC fusion v2（`model/predictor.py`）— 排除 Nose（TW-IC -0.0279 FAIL）、|TW-IC| < 0.05 權重歸零、circuit breaker 加入 fusion 路徑、追蹤 active/excluded senses
- **#227**: Commit: `82f6ab8` — "HB #227: TW-IC fusion v2 - exclude Nose (TW-IC FAIL), zero-weight below-threshold senses, circuit breaker in fusion path"
- **#227 發現**: Tongue TW-IC +0.5316 和 Body +0.5049 占總 IC 權重的 ~55%，是融合模型的絕對主導因素

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **回測驗證 TW-IC fusion v2** — 比較 sell_win 改善 | #H379 |
| 🔴 P0 | **驗證 Gateway 是否尊重 should_trade=False** — 確保 Circuit Breaker 真正生效 | #H390 |
| 🟡 P1 | **替換 Nose 感官** — TW-IC 唯一不合格，全域+雙重都 FAIL | #H391 |
| 🟡 P1 | **動態 IC 重算** — 每輪心跳更新 TW-IC 權重 | #H340 |
| 🟡 P1 | **Bull regime 方向錯誤修復** — 59.4% 反向 | #H426 |
| 🟢 P2 | **數據管線持續運作** — 確認下次心跳有新數據 | — |
| 🟢 P2 | **FNG 極端策略** — FNG<15 翻多 | — |

---

## 📊 距 90% 勝率差距分析

- **當前全域 sell_win**: 49.90%（差 **40.10pp**）
- **當前全域 buy_win**: 49.22%（差 **40.78pp**）
- **全域 IC 達標率**: 5/15 特徵（33.3%），2/8 核心感官
- **TW-IC 達標率**: 7/8 核心感官（87.5%） **⬆️ 維持最佳**
- **主要障礙**:
  1. **全域 sell_win 和 buy_win 雙 < 50%** — 等權融合模型稀釋了 Tongue(+0.532) 和 Body(+0.505) 的強信號
  2. **Nose 雙重失敗** — 全域 -0.044 + TW-IC -0.028，融合 v2 已排除
  3. **數據管線停滯 226 輪後才恢復** — 浪費大量學習機會
  4. **缺乏回測驗證** — TW-IC fusion v2 尚未驗證實際勝率提升
- **本輪最大改善**: 
  - ✅ TW-IC fusion v2 — 排除 Nose、零權重弱信號、強信號主導
  - ✅ Circuit breaker 在 fusion 路徑加入
  - ✅ 數據收集恢復（+4 raw）
  - ✅ Git commit 完成（82f6ab8）

**關鍵洞察**: TW-IC fusion v2 將 Tongue 和 Body 的總權重提升到 ~55%（之前被所有感官均分稀釋），這可能翻轉 sell_win 到 50% 以上。但必須通過回測驗證才能確認。Circuit Breaker 現在在 predict() 和 predict_with_ic_fusion() 兩個路徑都保護系統。

---

*此文件每次心跳完全覆蓋，保持簡潔。*
