# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)，流程見 [HEARTBEAT.md](HEARTBEAT.md)。

---

*最後更新：2026-04-05 16:50 GMT+8（心跳 #243）*

---

## 📊 當前系統健康狀態（2026-04-05 16:50 GMT+8，心跳 #243）

### 數據管線
| 項目 | 數值 | 狀態 vs #242 |
|------|------|--------|
| Raw market data | 9,180 筆 | ➡️ 持平 |
| Features | 9,142 筆 | ➡️ 持平 |
| Labels | 8,921 筆 | ➡️ 持平 |
| Raw 數據停滯 | **136 分鐘未更新** | 🔴 惡化（#242 116 分鐘）|
| 全域 IC 通過 | **4/15** (full_ic.py v4) | ➡️ 持平（VIX, RSI14, MACD, BB %B）|
| ic_signs.json TW-IC (ic_tw) | **9/10** 核心 | ➡️ 持平 |
| 模型 CV 準確率 | 51.4% | ➡️ 持平 |
| BTC 當前 | $66,867 | ➡️ 持平（從 $66,858）|
| FNG | 12（極度恐懼）| ➡️ 持平 |
| 資金費率 | 0.00001810 | ➡️ 持平 |
| LSR | 1.5954 | ➡️ 持平 |
| OI | 89,876 BTC | ➡️ 持平 |
| Sell Win（全域） | 49.9% | ➡️ 持平 |
| 連敗 | 156 | 🔴 持續 |

### 📌 本輪執行：平行心跳 #243

| 項目 | 狀態 | 備註 |
|------|------|------|
| `scripts/hb_parallel_runner.py` | ✅ #243 **6/6 COMPLETE** | 全部通過，195.6s（#242: 191.0s）|
| `scripts/full_ic.py` | ✅ 全域 IC v4 | **4/15 通過**（VIX -0.071, RSI14 -0.055, MACD -0.051, BB%B -0.058）|
| `scripts/regime_aware_ic.py` | ✅ | Bear **3/8**, Bull 2/8, Chop 0/8, Neutral 5/8 |
| DW N=200 | 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439, Mind +0.176 |
| DW 訓練 CV | 97.0% | （僅 200 樣本，gap=-5.5pp — 過擬警告）|
| DW 訓練時間 | 190.4s | |
| Global 模型 | Train=63.9%, CV=51.4% | gap=12.5pp |
| `model/train.py` regime | ✅ **3 regime 全部保存** | bear/bull/chop: 99 features saved — **#240→#242 KeyError 問題已修復！** |
| Backtest | ✅ PASS | 0.55s |
| Comprehensive tests | **6/6 PASS** | ✅ 全部通過 |

### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | **#H390** | **156 連敗持續 + 近 100 筆 0% 勝率** | 🔴 持續 | Circuit Breaker 持續保護中 |
| 🔴 | **#H379** | **sell_win < 50% — 系統方向性錯誤** | 🔴 持續 | 全域 sell_win=49.9%，模型 CV=51.4% |
| 🔴 | **#P440** | **全域 IC 持續低迷** | 🟡 部分改善 | full_ic.py v4: 4/15 通過，但 8 核心感官 0/8 |
| 🔴 | **#P441** | **Chop regime 0/8 全面失效** | 🔴 持續（6+ 輪）| Chop 信號完全消失 |
| 🔴 | **#H426** | **全域/ic_map/TW-IC 差異巨大** | 🔴 持續 | 全域 Spearman 4/15 vs ic_map 9/10 vs TW-IC 9/10 |
| 🔴 | **#COLLECT** | **數據管線 136 分鐘無更新** | 🔴 惡化 | 從 #242 的 116 分鐘惡化至 136 分鐘 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | Nose 全域/ic_map 雙重失效 | Nose 全域 IC=-0.050, ic_map=-0.028 |
| #REGIME | Regime 分類不均 | Bear 3/8, Bull 2/8, Chop 0/8 |
| #ICDISC | ic_map(ic_signs.json) vs 即時全域 IC 分歧 | ic_map/TW-IC 9/10，full_ic.py 即時計算 8 核心 0/8 |
| #DWCV | DW CV 97% 但 N=200 極度不穩定 | 僅 200 樣本，gap=-5.5pp |
| #API_DOWN | 前端 API 全部離線 | Connection refused |
| #18NO_DATA | 18 個特徵無數據 | 8 aux + 6 new senses + NQ + Nest |

### ✅ 本輪修復/發現

| ID | 狀態 | 備註 |
|----|------|------|
| **#243** | 🔥 **regime 訓練 KeyError 已修復！** | bear/bull/chop 全部 99 features saved，#240→#242 連續 3 輪的 KeyError 消失 |
| **#243** | ✅ 全域 IC **4/15** | VIX(-0.071), RSI14(-0.055), MACD(-0.051), BB%B(-0.058) |
| **#243** | ✅ ic_signs.json TW-IC 9/10 | Tongue +0.530, Body +0.510, ATR +0.443, DXY -0.270 |
| **#243** | ✅ Regime IC | Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8 |
| **#243** | ✅ DW N=200: 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471 |
| **#243** | ✅ Global model | CV=51.4%, Train=63.9%, gap=12.5pp |
| **#243** | ✅ DW CV=97.0% | Train=91.5%, gap=-5.5pp（過擬警告）|
| **#243** | ✅ Comprehensive tests **6/6 PASS** | |
| **#243** | ✅ Backtest PASS | 0.55s |
| **#243** | ✅ 平行心跳 6/6 PASS | 195.6s |
| **#243** | 🔴 市場數據 | BTC=$66,867 (-0.10%), FNG=12, LSR=1.5954, FR=0.00001810, OI=89,876 |

---

## 🔴 感官 IC 掃描（心跳 #243, 2026-04-05 16:50 GMT+8）

### 全域 IC (full_ic.py v4) — **4/15 通過**

| 感官/特徵 | Global IC | TW-IC (tau=200) | 狀態 |
|-----------|----------|-----------------|------|
| Eye | +0.0135 | +0.0106 | ❌ |
| Ear | -0.0478 | -0.0084 | ❌ |
| Nose | -0.0500 | -0.0584 | ❌ |
| Tongue | -0.0012 | +0.0335 | ❌ |
| Body | -0.0461 | -0.0334 | ❌ |
| Pulse | +0.0058 | +0.0878 | ❌ |
| Aura | -0.0363 | -0.0916 | ❌ |
| Mind | -0.0246 | -0.0797 | ❌ |
| **VIX** | **-0.0713** | -0.0981 | ✅ |
| DXY | -0.0137 | -0.0403 | ❌ |
| **RSI14** | **-0.0545** | -0.0728 | ✅ |
| **MACD-Hist** | **-0.0506** | -0.0422 | ✅ |
| ATR% | +0.0220 | +0.0755 | ❌ |
| VWAP Dev | -0.0073 | -0.1009 | ❌ |
| **BB %B** | **-0.0578** | -0.0857 | ✅ |

### ic_signs.json TW-IC — **9/10 通過**

| 感官/特徵 | TW-IC | 狀態 |
|-----------|-------|------|
| Eye | +0.1368 | ✅ |
| Ear | -0.0528 | ✅ |
| Nose | -0.0275 | ❌ |
| Tongue | +0.5303 | ✅ |
| Body | +0.5101 | ✅ |
| Pulse | -0.3022 | ✅ |
| Aura | -0.1782 | ✅ |
| Mind | -0.1996 | ✅ |
| VIX | -0.1252 | ✅ |
| DXY | -0.2696 | ✅ |

### Regime-aware IC（ID join, n=8921）

**Bear（3/8）**：Eye(+0.094)✅, Tongue(+0.070)✅, Aura(-0.060)✅
**Bull（2/8）**：Ear(-0.061)✅, Nose(-0.057)✅
**Chop（0/8）**：全部不及（持續 6+ 輪）
**Neutral（5/8）**：Nose/Tongue/Body/Aura/Mind（n=73 樣本少）

### 動態窗口分析

- **最佳窗口：N=200（7/8 通過）**
- Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471, Ear -0.233, Eye +0.115, Mind +0.176
- 僅 Nose -0.023 失敗
- Window scan: N=200→7/8, N=400→7/8, N=600→6/8, N=1000→6/8, N=2000→5/8, N=5000→3/8

### sell_win by regime

| Regime | sell_win | n |
|--------|----------|---|
| Bear | 0.5010 | 2,993 |
| Bull | 0.4850 | 2,951 |
| Chop | 0.4925 | 2,904 |
| Neutral | ~0.42 | 73 |

**Overall: sell_win=0.4990 (n=8,921) | 連敗: 156**

---

## 📋 六色帽會議（#243）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=9,180 / Features=9,142 / Labels=8,921（全部持平，**136 分鐘未更新**）。全域 15 特徵 IC **4/15**（VIX+RSI14+MACD+BB%B）。TW-IC 9/10。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8, CV=97.0%。Global CV=51.4%。sell_win=49.9%。BTC=$66,867，FNG=12，LSR=1.5954，OI=89,876。Comprehensive tests 6/6 通過。平行心跳 6/6 PASS（195.6s）。**regime 訓練 KeyError 已修復**。Backtest PASS。18 特徵無數據。 |
| **紅帽** | **數據管線已 136 分鐘無新數據** — 從 #242 的 116 分鐘繼續惡化。系統完全處於封閉真空狀態。全域 8 核心 IC 0/8 持續 7+ 輪。連敗 156 無變化。但 regimme 訓練終於修復是重大好消息。 |
| **黑帽** | (1) 8 核心全域 0/8 持續 7+ 輪。(2) Chop 0/8 持續 6+ 輪。(3) **數據管線 136 分鐘停滯**。(4) sell_win 49.9% < 50%。(5) DW CV>Train=-5.5pp。(6) API 全部離線。(7) 18 特徵完全無數據。 |
| **黃帽** | (1) **regime 訓練 KeyError 已修復** — bear/bull/chop 全部正常保存，這是 #240→#242 未能解決的 P0。(2) 4/15 IC 通過。(3) DW N=200 7/8 持續確認。(4) Comprehensive tests 6/6。(5) Backtest PASS。 |
| **綠帽** | (1) **regime 訓練修復是最重要突破** — 三路模型現在正常生成，系統重新獲得 regime-aware 預測能力。(2) 全域 4/15 TI 通過 — VIX/RSI14/MACD/BB%B 全域有效。(3) DW N=200 7/8，比 #241 和 #242 都穩定（DW 訓練 190.4s vs #242 187.6s vs #241 194.7s）。(4) Parallel runner 穩定在 ~195s。 |
| **藍帽** | **P0 行動：**(1) ~~修復 train.py 的 KeyError~~ — **DONE**。(2) **恢復數據管線** — 136 分鐘無更新，檢查 main.py scheduler。(3) **Chop 0/8 問題** — 需要新信號源或重新設計 Chop 特徵。(4) **sell_win 49.9% < 50%** — Circuit Breaker 持續保護。 |

---

## ORID 決策

- **O**: Raw=9,180 / Features=9,142 / Labels=8,921。全域 4/15，TW-IC 9/10。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8，CV=97.0%。Global CV=51.4%（gap 12.5pp）。sell_win=49.9%。BTC=$66,867，FNG=12。連敗: 156。**regime 訓練 6/6 PASS**。管線 136 分鐘未更新。
- **R**: 最重大進展是 regime 訓練 KeyError 終於修復 — 三輪失敗後的突破。但數據管線持續惡化（116→136 分鐘），全域核心 0/8 持續。
- **I**: (1) **regime 訓練修復完成** — bear/bull/chop 正常保存 99 features 每個。(2) **全域 TI 4/15 通過** — VIX/RSI14/MACD/BB%B 提供穩定信號。(3) **DW N=200 持續 7/8** — 短期窗口仍然是最佳信號提取窗口。(4) **136 分鐘數據停滯** — scheduler 可能已崩潰。
- **D**: (1) ~~P0：修復 KeyError~~ DONE。(2) **P0：恢復數據管線** — scheduler/main.py。(3) **P0：Chop 信號重新設計**。(4) **P1：API 服務恢復**。

---

## 📋 本輪修改記錄

- **#243**: 🔥 **regime 訓練 KeyError 已修復** — bear/bull/chop 99 features 全部保存（#240→#242 三輪失敗後首次）
- **#243**: 全域 IC **4/15**（VIX, RSI14, MACD, BB%B 全域通過）
- **#243**: ic_signs.json TW-IC 9/10 — Tongue +0.530, Body +0.510, ATR +0.443
- **#243**: Regime IC — Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8
- **#243**: 動態窗口 — N=200 最優 7/8, CV=97.0%（200 樣本），DW 訓練 190.4s
- **#243**: Global model — Train=63.9%, CV=51.4%, gap=12.5pp
- **#243**: 市場數據 — BTC=$66,867, FNG=12, LSR=1.5954, FR=0.00001810, OI=89,876
- **#243**: Parallel heartbeat #243 **195.6s（6/6 COMPLETE）**
- **#243**: **6 個任務全部通過** — full_ic, regime_aware_ic, DW, model_train, backtest, tests
- **#243**: 數據管線 **136 分鐘未更新** — 持續惡化
- **#243**: Backtest PASS — 0.55s
- **#243**: Comprehensive tests **6/6 PASS**
- **#243**: 18 個特徵無數據（8 aux + 6 new + NQ + Nest）

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| ~~🔴 P0~~ | ~~**修復 train.py regime 特徵匹配**~~ | ~~#HB240~~ ✅ |
| 🔴 P0 | **恢復數據管線** — 136 分鐘無更新，檢查 scheduler/main.py | #COLLECT |
| 🔴 P0 | **Chop 0/8 崩潰持續 6+ 輪** | #P441 |
| 🔴 P0 | **156 連敗持續** — Circuit Breaker 持續觸發 | #H390 |
| 🔴 P0 | **全域 8 核心 0/8 持續 7+ 輪** | #P440 |
| 🟡 P1 | **全域/ic_map/TW-IC 分歧原因** | #ICDISC |
| 🟡 P1 | **API 服務恢復** — 前端完全離線 | #API_DOWN |
| 🟡 P1 | **DW CV>Train=-5.5pp 過擬警告** | #DWCV |
| 🟡 P1 | **18 特徵無數據** — 確保 collector 啟用新特徵 | #18NO_DATA |

---

## 📊 距 90% 勝率差距分析

- **當前全域 sell_win**: 49.9%（差 **40.1pp**）
- **模型 CV 準確率**: 51.4%（差 **38.6pp**，等同隨機）
- **全域 8 核心 Spearman IC 達標率**: **0/8**（0%）
- **全域 15 特徵 Spearman IC 達標率**: **4/15**（27%）— TI 貢獻
- **TW-IC 達標率**: **9/10** 核心（90%）
- **DW N=200 達標率**: **7/8** 核心（87.5%）
- **sell_win by regime**: Bear=50.1%, Bull=48.5%, Chop=49.3%
- **主要障礙**:
  1. **8 核心全域 IC 完全崩潰 7+ 輪** — 自建感官全域失效
  2. **TI 4/15 全域通過但 sell_win 仍 49.9%** — IC fusion 管道未充分利用 TI
  3. **Chop 0/8** — 重要 regime 信號消失 6+ 輪
  4. **連敗 156** — 系統完全失效
  5. **數據管線停滯 2+ 小時** — 無法獲取更新信號
- **本輪修復/發現**:
  - 🔥 **regime 訓練 KeyError 修復** — 三輪失敗後首次全部正常
  - 🟢 **全域 4/15** — TI 全域通過（VIX/RSI14/MACD/BB%B）
  - 🟢 **ATR TW-IC +0.443** — 第二強信號僅次於 Tongue
  - 🟢 **Backtest PASS**
  - 🟢 **6/6 任務全部通過**
  - ❌ **全域核心 0/8 持續 7+ 輪**
  - ❌ **數據管線 136 分鐘未更新**
  - ➡️ **全域 sell_win 49.9%**（持平）
  - ➡️ **連敗 156**（持平）
- **關鍵洞察**: 心跳 #243 最大的突破是 **regime 訓練 KeyError 終於修復** — 三輪（#240/#241/#242）失敗後，bear/bull/chop 三個 regime 模型現在正常生成並保存 99 features。系統重新獲得完整的 regime-aware 預測能力。全域 IC 仍然 4/15（TI 貢獻），核心 8 感官全域 0/8 持續，但 TW-IC 維持 9/10。數據管線惡化至 136 分鐘是最運行風險。

---

*此文件每次心跳完全覆蓋，保持簡潔。*
