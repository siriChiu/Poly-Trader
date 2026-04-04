# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 21:42 GMT+8（心跳 #186）*
---

## 📊 當前系統健康狀態（2026-04-04 21:42 GMT+8，心跳 #186）

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

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 1/8 against sell_win** | 🔴 **持續（6+ 輪）** | 僅 Ear PASS（-0.0516）|
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 5/8、Bull 1/8、Chop 1/8 | 持續 |
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
| #H343 | 🟡 **Regime IC 計算偏差** | ✅ 已修復：用真實 regime_label |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |

---

## 感官 IC 掃描（心跳 #186, 2026-04-04 21:42 GMT+8）

### 全域 IC against sell_win（N=8,770, 8 核心感官）
| 感官 | IC | 狀態 | vs #185 |
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

| Regime | 達標數 | vs #185 |
|--------|--------|---------|
| Bear | **5/8** | ➡️ 持平 |
| Bull | **1/8** | ➡️ 持平（僅 Ear）|
| Chop | **1/8** | ➡️ 持平（Pulse）|

### 🔴 關鍵發現
- **全域 IC 1/8**（Ear PASS -0.0516）— 6+ 輪無改善，系統性瓶頸
- **Regime 分化持續**：Bear 5/8 穩定、Bull 1/8 極弱、Chop 1/8 仍不足
- **sell_win 50.8% 全域** — 近似隨機，系統無預測能力
- **CV 52.24%** — 51 特徵天花板
- **venv 正常** — 所有依賴已安裝（ Requirement already satisfied）

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (51 features) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | 52.24%（上次測量）|
| Train accuracy | 72.27% |
| Overfit gap | ~20pp |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,955 筆、Features 8,920 筆、Labels 8,770 筆 — 全部持平
- 全域 IC 1/8（Ear PASS -0.0516）— 6+ 輪無改善
- Regime IC：Bear 5/8、Bull 1/8、Chop 1/8 — 與上次完全相同
- CV 52.24%，sell_win 全域 50.8%
- BTC $67,129, FNG 11（Extreme Fear）— 持平

### 黑帽（風險）
1. 全域 1/8 持續 6+ 輪 — 系統性天花板，短期內無解
2. sell_win 50.8% — 系統無預測能力
3. CV 52% 停滯 — 51 特徵無法突破
4. Bull 僅 1/8 — 牛市無預測能力
5. Overfit 20pp — 泛化能力嚴重不足

### 黃帽（價值）
1. Bear 5/8 穩定 — 熊市策略可行
2. 系統穩定，所有檢查通過
3. IC 計算已修正（真實 regime_label）

### 綠帽（創新）
1. Bear-only 策略 — 僅熊市交易，避開 Bull/Chop 死亡區
2. 新數據源探索 — Twitter/X、新聞、Polymarket、VIX、DXY

### 藍帽（決策）
1. 🔴 P0：全域 IC ~0 根因分析（6+ 輪無改善）— 架構性問題
2. 🔴 P0：CV 52% 天花板 — 需要非線性特徵或外部 alpha
3. 🟡 P1：Chop regime 仍需外部 alpha（1/8 不夠）

---

## ORID 決策
- **O**: 全域 1/8（Ear PASS），Regime Bear 5/8、Bull 1/8、Chop 1/8，CV 52.24%
- **R**: 所有指標 6+ 輪持平，系統處於穩定但低效狀態
- **I**: 全域 IC ~0 是架構性限制 — 需要根本性改變（新數據源、新特徵類型、新標籤定義），而非微調現有 51 特徵
- **D**: (1) 探索新數據源（外部 alpha）(2) 重新審視 sell_win 標籤定義 (3) Bear-only 策略原型

---

## 📋 本輪修改記錄

- **#186**: ✅ 運行 dev_heartbeat.py — Raw=8,955, Features=8,920, Labels=8,770。
- **#186**: 📊 **全域 IC 1/8**（**Ear PASS -0.0516**）— 6+ 輪無改善。
- **#186**: 📊 **Regime IC** — Bear 5/8、Bull 1/8、Chop 1/8 — 持平。
- **#186**: ✅ venv 依賴確認正常（all requirements satisfied）。
- **#186**: ⚠️ **P0 問題持續** — 全域 IC 1/8 及 CV 52% 天花板屬架構性瓶頸。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **全域 IC ~0 根因分析** — 特徵抵消 or 無效？ #H304 |
| 🔴 P0 | **CV 52% 天花板突破** — 51 特徵無法提升，需新方法 | #H137 |
| 🟡 P1 | **Bear-only 策略原型** — 僅用 Bear regime 5/8 信號交易 | #H340 |
| 🟡 P1 | **Chop regime 新 alpha 源** — 1/8 仍不足需外部數據 | #H303 |
| 🟢 P2 | **新數據源探索** — Twitter/X、新聞、VIX、DXY | #H303 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
