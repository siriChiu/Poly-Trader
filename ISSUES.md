# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 20:50 UTC — Heartbeat #598*

## 📊 系統健康狀態 v4.25

| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw | **10,115** | ✅ +5 vs #597（持續增長） |
| Features | **10,074** | ✅ +5 vs #597 |
| Labels | **27,684** | 🔴 凍結（與 #597 相同） |
| sell_win | **33.21%** | 🔴 持平（vs #597 33.21%） |
| 全域 IC | **5/22** | ➡️ 持平 |
| TW-IC | **13/22** | ➡️ 持平 |
| 模型數 | **8** | ✅ |
| Tests | **6/6** | ✅ 全過 |

## 📈 心跳 #598 IC 摘要

### 全域 IC (Spearman, n=8770)
| 特徵 | IC | 狀態 |
|------|-----|------|
| VIX | +0.0714 | ✅ PASS |
| BB%B | +0.0575 | ✅ PASS |
| RSI14 | +0.0542 | ✅ PASS |
| MACD-Hist | +0.0505 | ✅ PASS |
| Nose | +0.0500 | ❌ FAIL（擦邊持平） |
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
| 4h_bias50 | +0.0715 | ✅ PASS（4H特徵） |
| Nose | +0.0587 | ✅ PASS |
| MACD-Hist | +0.0554 | ✅ PASS |
| 4h_rsi14 | +0.0622 | ✅ PASS（4H特徵） |
| 4h_dist_swing_low | +0.0620 | ✅ PASS（4H特徵） |
| Pulse | -0.0871 | ✅ PASS |
| 其餘9個 | | ❌ |

**TW-IC: 13/22 通過（持平）**

### Dynamic Window（核心8特徵）
- N=100: **7/8**🟢（持平！耳唯一失敗；Aura+0.2773, Mind+0.2301, Nose+0.1766, Body+0.1288 極強）
- N=200: **7/8**🟢（持平！）
- N=400: 3/8（持平）
- N=600: **0/8**💀（持續死區）
- N=1000: 4/8（持平）
- N=2000: 2/8（持平）
- N=5000: 0/8（持平）

### Regime-aware IC
| 區間 | 通過 | 狀態 |
|------|------|------|
| Bear | **4/8** | ⚠️ 持平（Ear, Nose, Body, Aura） |
| Bull | **0/8** | 🔴 持續！（200+輪持續） |
| Chop | **0/8** | 🔴 持續！（200+輪持續） |

**Sell Win by Regime**: Bear 48.55%, Bull 50.90%, Chop 48.29%, Overall 49.24%

### 模型訓練
- Train: 63.92%, CV: 51.39%, gap: 12.53pp
- Features: 73, Samples: 9,106, Positive ratio: 30.45%
- **Regime models**:
  - Bear: CV=60.22%, Train=79.8%, n=2980
  - Bull: CV=73.37%, Train=93.5%, n=2939
  - Chop: CV=65.60%, Train=71.48%, n=3124

## 📊 市場快照（#598 即時）
- BTC: **$68,387**（⬆️ +$28 vs #597 $68,359，微幅反彈）
- 24h Change: **-1.62%**
- FNG: **11**（持續極度恐懼）
- FR: **0.00002992**（⬆️ +4.6% vs #597 0.00002861，空頭壓力微升）
- LSR: **1.3326**（⬆️ +21bps vs #597 1.3305，長倉比例略升）
- OI: **91,037**（⬆️ +48 vs #597 90,989）

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #LABELS_FROZEN | Labels 完全凍結於 27,684（跳增後零增長） | 🔴 持續 |
| #SELL_WIN_33 | sell_win=33.21% 遠低於目標（需≥90%） | 🔴 持續 |
| #BULL_CHOP_DEAD | Bull 0/8, Chop 0/8（200+輪持續零信號）| 🔴 持續 |
| #CV_CEILING | CV 51.39% 天花板（6+月無法突破）| 🔴 持續 |

## P1

| ID | 問題 | 狀態 |
|----|------|------|
| #DW_DEADZONE | N=600 和 N=5000 持續 0/8 死區 | ⚠️ 持續 |
| #EAR_LOW_VAR | feat_ear std=0.0034, unique=14（準離散特徵）| ⚠️ 持續 |
| #TONGUE_LOW_VAR | feat_tongue std=0.0015, unique=7（準離散特徵）| ⚠️ 持續 |
| #LABELS_JUMP | Labels 從 18,052 跳增至 27,684（+53%）原因未明 | ⚠️ 持續 |

## ✅ 本次摘要
- 🟢 **Raw 10,115（+5 vs #597 10,110）**：持續增長
- 🟢 **Features 10,074（+5 vs #597 10,069）**：跟隨 Raw 增長
- 🔴 **Labels 27,684**：完全凍結（與 #597 相同）
- 🔴 **sell_win=33.21%**：持平（vs #597 33.21%），遠低於 90% 目標
- 🟢 **TW-IC 13/22**（持平，3個4H特徵持續貢獻：4h_bias50, 4h_rsi14, 4h_dist_swing_low）
- 🟢 **全域 IC 5/22**（持平：VIX, BB%B, RSI14, MACD-Hist, Nose擦邊）
- 🟢 **DW N=100 7/8 + N=200 7/8 持平**：短窗口持續最強（耳唯一失敗）
- 🟢 **Regime IC 持平**：Bear 4/8（Ear, Nose, Body, Aura），Bull 0/8🔴，Chop 0/8🔴
- 🟢 **平行心跳 5/5 PASS（39.9s）**：full_ic ✅, regime_ic ✅, dynamic_window ✅, train ✅, tests ✅（6/6）— 全面通過！
- 🟢 **Tests 6/6 PASS**：全面通過（9981 Python files syntax OK）
- 🟢 **Global model**: Train=63.92%, CV=51.39%, gap=12.53pp（持平），73 features, 9106 samples
- 🟢 **Regime models**: Bear CV=60.22%, Bull CV=73.37%, Chop CV=65.60%（持平）
- 🟡 **BTC $68,387（+$28）**：微幅反彈，24h -1.62%
- 🟡 **FR 0.00002992（+4.6%）**：空頭付費壓力微升
- 🟡 **LSR 1.3326（+21bps）**：長倉比例略升，多頭優勢持續
- 🟡 **OI 91,037（+48）**：持倉量微增
- 🔴 **Bull/Chop 持續 0/8**（200+輪）：系統性問題，需要新數據源
