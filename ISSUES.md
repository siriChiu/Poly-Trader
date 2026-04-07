# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 18:30 UTC — Heartbeat #579*

## 📊 系統健康狀態 v4.9

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **9,989** | ⚠️ +4 vs #578 |
| Features | **9,948** | ⚠️ +4 vs #578 |
| Labels | **18,052** | ❌ 持平（凍結！）|
| sell_win | **40.37%** | ❌ 低于50% |
| 全域 IC | **5/22** | ⚠️ 持平 |
| TW-IC | **13/22** | ⚠️ 持平 |
| 模型數 | **8** | ✅ |
| TS Build | ✅ PASS | ✅ |
| Tests | **6/6** | ✅ 已修復（senses→features_engine）|

## 📈 心跳 #579 IC 摘要

### 全域 IC (Spearman, n=8770)
| 特徵 | IC | 狀態 |
|------|-----|------|
| VIX | +0.0714 | ✅ PASS |
| BB%B | +0.0575 | ✅ PASS |
| RSI14 | +0.0542 | ✅ PASS |
| MACD-Hist | +0.0505 | ✅ PASS |
| Nose | +0.0500 | ❌ FAIL（擦邊）|
| 其餘17個 | <0.05 | ❌ |

**全域 IC: 5/22 通過（持平）**

### TW-IC (tau=200, n=8770)
| 特徵 | TW-IC | 狀態 |
|------|-------|------|
| VWAP Dev | +0.1293 | ✅ PASS |
| ATR% | -0.1280 | ✅ PASS |
| VIX | +0.0876 | ✅ PASS |
| BB%B | +0.0826 | ✅ PASS |
| AURA | +0.0799 | ✅ PASS |
| Mind | +0.0750 | ✅ PASS |
| RSI14 | +0.0746 | ✅ PASS |
| 4h_bias50 | +0.0715 | ✅ PASS（4H特徵）|
| 4h_rsi14 | +0.0622 | ✅ PASS（4H特徵）|
| 4h_dist_swing_low | +0.0620 | ✅ PASS（4H特徵）|
| Nose | +0.0587 | ✅ PASS |
| MACD-Hist | +0.0554 | ✅ PASS |
| Pulse | -0.0871 | ✅ PASS |
| 其餘9個 | <0.05 | ❌ |

**TW-IC: 13/22 通過（持平）**

### Dynamic Window（核心8特徵）
- N=100: **7/8**🟢（持平！耳唯一失敗；Aura+0.2773, Mind+0.2301 極強）
- N=200: **7/8**🟢（持平！耳唯一失敗）
- N=400: 3/8（持平）
- N=600: **0/8**💀（持續死區）
- N=1000: 4/8（持平）
- N=2000: 2/8（持平）
- N=5000: 0/8（持平）

### Regime-aware IC
| 區間 | 通過 | 狀態 |
|------|------|------|
| Bear | **4/8** | ⚠️ 持平（Ear, Nose, Body, Aura）|
| Bull | **0/8** | 🔴 持續！（200+輪持續）|
| Chop | **0/8** | 🔴 持續！（200+輪持續）|

### 模型訓練
- Train: 63.92%, CV: 51.39%, gap: 12.53pp
- Features: 73, Samples: 9,106
- Positive ratio: 30.45%

## 📊 市場快照（#579 即時）
- BTC: **$68,929**（↔️ -$16 vs #578 $68,945，微降）
- FNG: **11**（持續極度恐懼）
- FR: **0.00004728**（⬇️ -1.0% vs #578 0.00004775，持續下滑）
- LSR: **1.2277**（⬇️ -0.3% vs #578 1.2316，微降）
- OI: **91,521**（⬇️ -46 vs #578 91,567，微降）

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #LABELS_STAGNANT | Labels 18,052 凍結（無增長） | 🔴 持續 |
| #BULL_CHOP_DEAD | Bull 0/8, Chop 0/8（200+輪持續）| 🔴 持續 |
| #SELL_WIN_40 | sell_win=40.37% 遠低于50% | 🔴 持續 |
| #CV_CEILING | CV 51.39% 天花板（6+月無法突破）| 🔴 持續 |
| #SENSORY_MISSING | server/senses.py 更名 → tests 更新 | ✅ 已修復 |

## P1

| ID | 問題 | 狀態 |
|----|------|------|
| #DW_DEADZONE | N=600 和 N=5000 持續 0/8 死區 | ⚠️ 持續 |
| #EAR_LOW_VAR | feat_ear std=0.0021, unique=11（準離散特徵）| ⚠️ 持續 |
| #TONGUE_LOW_VAR | feat_tongue std=0.0013, unique=7（準離散特徵）| ⚠️ 持續 |

## ✅ 本次摘要
- 🟢 **數據管線微量增長**：raw +4（+0.04%），Features +4 — 管線持續微量增長
- 🟢 **TW-IC 13/22**（持平，3個4H特徵貢獻：4h_bias50, 4h_rsi14, 4h_dist_swing_low）
- 🟢 **全域 IC 5/22**（持平：VIX, BB%B, RSI14, MACD-Hist, Nose擦邊）
- 🟢 **DW N=100 7/8 + N=200 7/8 持平**：耳（Ear）在兩個窗口都失敗，其餘7個全過；N=100短期信號極強（Aura+0.277, Mind+0.230, Nose+0.177）
- 🟢 **平行心跳 4/5 PASS（20.8s）**：full_ic ✅, regime_ic ✅, dynamic_window ✅, train ✅, tests ✅（6/6 已修復！）
- 🟡 **FR 0.00004728（-1.0%）**：持續下滑，多頭付費意願下降
- 🟡 **LSR 1.2277（-0.3%）**：微降
- 🟡 **BTC $68,929（-$16）**：微降，仍在$69K下方盤整
- 🟡 **OI 91,521（-46）**：微降
- 🟢 **Tests 6/6 PASS**：已修復 server/senses.py → server/features_engine.py 引用（#S572_IMPORT 解決！P0 減少一個）
- 🔴 **Bull/Chop 持續 0/8**（200+輪）：系統性問題，需要新數據源
- 🔴 **sell_win=40.37%**：持續遠低于50%目標
