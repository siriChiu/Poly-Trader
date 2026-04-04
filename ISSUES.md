# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 21:12 GMT+8（心跳 #185）*
---

## 📊 當前系統健康狀態（2026-04-04 21:12 GMT+8，心跳 #185）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,955 筆 | ➡️ 持平 |
| Features | 8,920 筆 | ➡️ 持平 |
| Labels | 8,770 筆 | ➡️ 持平 |
| BTC 當前 | ~$67,129 | ➡️ 持平 |
| FNG | 11（Extreme Fear） | ➡️ 持平 |
| Funding Rate | ~0.000016 | ➡️ 持平 |
| sell_win rate | 0.508（全域）| ➡️ 持平 |
| sell_win recent100 | 0.470 | ⬇️ 偏離全域 |
| sell_win recent500 | 0.472 | ⬇️ 偏離全域 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 1/8 against sell_win** | 🔴 **持續（5+ 輪）** | 僅 Ear PASS（-0.0516）|
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 5/8、Bull 1/8、Chop 1/8 | Chop 從 0→1（修復 regime 分類後）|
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，51 特徵無改善 |
| #H341 | 🚨 **sell_win vs label_up 鴻溝** | 🔴 **持續** | sell_win rate=0.508 |
| #H342 | 🚨 **近期 sell_win 偏離** | 🔴 **持續** | 近期窗口 sell_win_rate 0.47-0.48 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 ~52% |
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=+0.0036，全域最弱 |
| #H343 | 🟡 **Regime IC 計算偏差** | 修復：用真實 regime_label 取代 timestamp thirds |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |

---

## 感官 IC 掃描（心跳 #185, 2026-04-04 21:12 GMT+8）

### 全域 IC against sell_win（N=8,770, 8 核心感官）
| 感官 | IC | 狀態 | vs #184 |
|------|------|------|---------|
| Ear | -0.0516 | ✅ PASS | ➡️ 持平 |
| Nose | -0.0483 | ❌ 近線 | ➡️ 持平 |
| Body | -0.0450 | ❌ 近線 | ➡️ 持平 |
| Aura | -0.0396 | ❌ | ➡️ 持平 |
| Mind | -0.0293 | ❌ | ➡️ 持平 |
| Eye | +0.0221 | ❌ | ➡️ 持平 |
| Pulse | +0.0105 | ❌ | ➡️ 持平 |
| Tongue | +0.0036 | ❌ | ➡️ 持平 |

**全域達標：1/8 against sell_win** — 僅 Ear PASS

### Dynamic Window IC（sell_win，實際 SQL 計算）
| N | 達標數 | 過線感官 | 備註 |
|---|--------|---------|------|
| 100 | **7/8** | Eye, Ear, Pulse, Aura, Mind, Body, MACD | Eye -0.1012, Mind -0.2663 最強 |
| 500 | **6/8** | Eye, Ear, Tongue, Pulse, Aura, Mind | 實際 6/8（之前 heartbeat_ic 誤報 0/8）|

### 最強單感官 IC（短窗口 N=100）
| 窗口 | 感官 | IC | 備註 |
|------|------|------|------|
| N=100 | **Mind** | **-0.2663** | 全域最強 |
| N=100 | Body | -0.1797 | 強 |
| N=100 | Eye | -0.1012 | 有效 |
| N=100 | Pulse | -0.1115 | 有效 |
| N=100 | Aura | -0.1893 | 強 |
| N=100 | Ear | -0.0853 | 有效 |
| N=100 | MACD | +0.0589 | TI 有效 |
| N=100 | VWAP | -0.1362 | TI 有效 |

### Regime IC（against sell_win，真實 regime_label）
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| Eye | +0.0560 ✅ | -0.0068 ❌ | -0.0018 ❌ |
| Ear | -0.0414 ❌ | -0.0647 ✅ | -0.0220 ❌ |
| Nose | -0.0610 ✅ | -0.0406 ❌ | -0.0421 ❌ |
| Tongue | +0.0216 ❌ | +0.0075 ❌ | -0.0366 ❌ |
| Body | -0.0422 ❌ | -0.0484 ❌ | -0.0306 ❌ |
| Pulse | +0.0612 ✅ | +0.0232 ❌ | -0.0560 ✅ |
| Aura | -0.0720 ✅ | -0.0124 ❌ | -0.0116 ❌ |
| Mind | -0.0625 ✅ | -0.0180 ❌ | -0.0025 ❌ |

| Regime | 達標數 | vs #184 |
|--------|--------|---------|
| Bear | **5/8** | ➡️（Eye, Nose, Pulse, Aura, Mind）|
| Bull | **1/8** | ➡️（僅 Ear）— 之前 timestamp thirds 方法誤判 Bull 有 1/8（Aura），修正後只有 Ear |
| Chop | **1/8** | ⬆️（0→1，Pulse PASS）— 之前 timestamp thirds 報告 0/8 是因分組不準 |

### 🔴 關鍵發現
- **全域 IC 1/8**（Ear PASS -0.0516）— 5+ 輪無改善，系統性瓶頸
- **N=100 維持 7/8** — 極短期信號持續存在，Mind -0.2663 最強
- **N=500 實際 6/8** — 之前 heartbeat_ic 報告不準確，修正後動態窗口依然有效
- **Regime 真實分化**：Bear 5/8 穩定、Bull 1/8 極弱、Chop 從 0/8 修正為 1/8
- **sell_win 50.8% 全域、近期 47%** — 近似隨機，系統無預測能力
- **CV 52.24%** — 51 特徵天花板，模型過拟合 20pp

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (51 features) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | 52.24% |
| Train accuracy | 72.27% |
| Overfit gap | ~20pp（72.27% vs 52.24%）|
| Trade history | 0 trades |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,955 筆、Features 8,920 筆、Labels 8,770 筆
- 全域 IC 1/8（Ear PASS -0.0516）— 5+ 輪無改善
- N=100 7/8，Mind -0.2663 最強單 IC
- 真實 Regime IC：Bear 5/8、Bull 1/8、Chop 1/8（修正 timestamp thirds 錯誤）
- CV 52.24%，sell_win 全域 50.8%，近期 47%
- BTC $67,129, FNG 11（Extreme Fear）

### 黑帽（風險）
1. 全域 1/8 持續 5+ 輪 — 系統性天花板
2. sell_win 50.8% 全域、近期 47% — 系統近似隨機
3. CV 52% 停滯 — 51 特徵無法突破
4. Bull 僅 1/8 — 牛市無預測能力
5. 過拟合 20pp — 泛化能力不足

### 黃帽（價值）
1. N=100 7/8 — 極短期信號存在，可設計窗口交易
2. Bear 5/8 穩定 — 熊市策略可行
3. Chop 從 0→1 — 真實 regime 分析改善了 Pulse 檢測
4. 系統穩定，所有檢查通過

### 綠帽（創新）
1. N=100 windowed trading — Mind (-0.2663) + Body (-0.1797) + Aura (-0.1893) ensemble
2. Bear-only strategy — 僅熊市交易，避開 Bull/Chop 死亡區
3. Regime-aware 特徵 — 不同 regime 用不同感官子集

### 藍帽（決策）
1. 🔴 P0：全域 IC ~0 根因分析（5+ 輪無改善）
2. 🔴 P0：CV 52% 天花板需新方法（非線性、特徵工程、外部數據）
3. 🟡 P1：N=100 windowed trading 策略設計
4. 🟡 P1：Chop regime 仍需外部 alpha（1/8 不夠）

---

## ORID 決策
- **O**: 全域 1/8（Ear PASS），N=100 7/8（Mind -0.2663 最強），真實 Regime Bear 5/8、Bull 1/8、Chop 1/8，CV 52.24%
- **R**: 短期信號強但全域消散，sell_win 50.8% 近似隨機，時間尺度 mismatch 是架構性限制
- **I**: (1) 信號在長窗口被抵消說明特徵互相抵消或標籤定義不匹配 (2) 真實 regime 分類比 timestamp thirds 更準確 (3) 51 特徵無法突破 52% CV 說明需要非線性特徵或外部 alpha
- **D**: (1) 修復 regime IC 計算（用真實 regime_label）✅ 本輪已修 (2) 設計 N=100 windowed trading 策略 (3) 探索非線性特徵工程打破 CV 52% 天花板

---

## 📋 本輪修改記錄

- **#185**: ✅ 運行 dev_heartbeat.py — Raw=8,955, Features=8,920, Labels=8,770。
- **#185**: 📊 **全域 IC 1/8**（**Ear PASS -0.0516**）— 5+ 輪無改善。
- **#185**: 📊 **Dynamic Window** — N=100 7/8（Mind -0.2663 最強），N=500 實際 6/8。
- **#185**: 📊 **真實 Regime IC** — Bear 5/8、Bull 1/8（Ear）、Chop 1/8（Pulse）。
- **#185**: 🔧 **修復 regime IC 計算** — heartbeat_ic_analysis.py 改用真實 regime_label 列取代 timestamp thirds 錯誤分組。
- **#185**: ✅ **測試結果** — dev_heartbeat.py 全通過，IC 腳本修正後正常運行。
- **#185**: ⚠️ **P0 問題持續** — 全域 IC 1/8 及 CV 52% 天花板屬架構性瓶頸。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **全域 IC ~0 根因分析** — 特徵抵消 or 無效？ #H304 |
| 🔴 P0 | **CV 52% 天花板突破** — 51 特徵無法提升，需新方法 | #H137 |
| 🟡 P1 | **N=100 windowed trading 策略** — 7/8 信號落地設計 | #H304 |
| 🟡 P1 | **Chop regime 新 alpha 源** — 1/8 仍不足需外部數據 | #H303 |
| 🟢 P2 | **信心校準** — Platt scaling / temperature scaling | #H87 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
