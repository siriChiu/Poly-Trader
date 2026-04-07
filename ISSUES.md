# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 18:15 UTC — Heartbeat #568*

## 📊 系統健康狀態 v4.2

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **9,937** | ✅ +18 vs #567 |
| Features | **9,896** | ✅ +18 vs #567 |
| Labels | **18,052** | ⚠️ 持平 |
| sell_win | **40.37%** | ❌ 低於50% |
| 全域 IC | **5/22** | ⚠️ 持平 |
| TW-IC | **13/22** | ⚠️ 持平 |
| 模型數 | **8** | ✅ |
| TS Build | ✅ PASS | ✅ |
| Tests | **3/6** | ❌ server/senses.py 缺失 |

## 📈 心跳 #568 IC 摘要

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
| Nose | +0.0587 | ✅ PASS |
| MACD-Hist | +0.0554 | ✅ PASS |
| 4h_rsi14 | +0.0622 | ✅ PASS（4H特徵）|
| 4h_dist_sl | +0.0620 | ✅ PASS（4H特徵）|
| Pulse | -0.0871 | ✅ PASS |
| 其餘9個 | <0.05 | ❌ |

**TW-IC: 13/22 通過（持平）**

### Dynamic Window（核心8特徵）
- N=100: **7/8**🟢（持平！耳唯一失敗）
- N=200: **7/8**🟢（持平！耳唯一失敗）
- N=400: 3/8（持平）
- N=600: **0/8**💀（持續死區）
- N=1000: 4/8（持平）
- N=2000: 2/8
- N=5000: 0/8

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

## 📊 市場快照（#568 即時）
- BTC: **$69,181**（⬆️ +$237 vs #567 $68,944）
- FNG: **11**（持續極度恐懼）
- FR: **0.00005466**（⬆️ +6.0% vs #567 0.00005157，多頭付費意願持續強勁）
- LSR: **1.2707**（⬆️ +72bps vs #567 1.2635，長倉比例回升）
- OI: **91,356**（⬇️ -99 vs #567 91,455）

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #LABELS_STAGNANT | Labels 18,052 凍結（無增長） | 🔴 持續 |
| #BULL_CHOP_DEAD | Bull 0/8, Chop 0/8（200+輪持續）| 🔴 持續 |
| #SELL_WIN_40 | sell_win=40.37% 遠低於50% | 🔴 持續 |
| #CV_CEILING | CV 51.39% 天花板（6+月無法突破）| 🔴 持續 |
| #SENSORY_MISSING | server/senses.py 缺失（Tests 3/6 fail）| 🔴 新增：重構後改名為 features_engine.py |

## P1

| ID | 問題 | 狀態 |
|----|------|------|
| #DW_DEADZONE | N=600 和 N=5000 持續 0/8 死區 | ⚠️ 持續 |
| #EAR_LOW_VAR | feat_ear std=0.0016, unique=7（準離散特徵）| ⚠️ 持續 |
| #TONGUE_LOW_VAR | feat_tongue std=0.0009, unique=5（準離散特徵）| ⚠️ 持續 |

## ✅ 本次摘要
- 🟢 **數據管線持續增長**：Raw +18, Features +18（vs #567 的 +4 加速！）
- 🟢 **TW-IC 13/22**（持平，4H特徵貢獻3個通過：4h_bias50, 4h_rsi14, 4h_dist_sl）
- 🟢 **全域 IC 5/22**（持平：VIX, BB%B, RSI14, MACD-Hist, Nose）
- 🟢 **DW N=100 7/8 + N=200 7/8 持平**：耳（Ear）在兩個窗口都失敗，其餘7個全過
- 🟢 **FR 升至 0.00005466（+6.0%）**：多頭付費意願持續強勁
- 🟢 **LSR 回升至 1.2707（+72bps）**：長倉比例回升
- 🟢 **BTC $69,181（+$237）**：持續反彈
- 🟢 **平行心跳 4/5 PASS（13.9s）**：full_ic ✅, regime_ic ✅, dynamic_window ✅, train ✅, tests ❌
- 🔴 **Tests 3/6 FAIL**：server/senses.py 已重構為 server/features_engine.py，測試需更新引用
- 🔴 **Bull/Chop 持續 0/8**（200+輪）：系統性問題，需要新數據源
