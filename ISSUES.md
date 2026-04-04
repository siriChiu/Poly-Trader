# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 11:56 GMT+8 (心跳 #152)*
---

## 📊 當前系統健康 (2026-04-04 11:56 GMT+8, 心跳 #152)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,829 筆 | ✅ |
| Features | 8,829 筆 (22 cols + regime) | ✅ |
| Labels | 8,770 筆 (50.8% sell_win) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,847 | — |
| FNG | 11 (Extreme Fear) | — |
| Funding Rate | +0.00004 | — |
| Regime 填充 | Bear 2,897 / Bull 2,897 / Chop 2,904 / Neutral 80 | ✅ 全填充 |

### 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H149-fix1 | 🔴 **訓練/推論特徵不匹配（已修復）** | `load_latest_features()` 缺少 feat_vix、feat_dxy、以及所有 cross-features。#149 全部修復。 | ✅ 已合併 |
| #H122 | 🔴 感官 IC 在 Bull/Chop 幾乎全滅 | Bear 5/8 達標（改善！），Bull 2/8，Chop 0/8 | 🔴 持續（Bear 進步 2 感官） |
| #H137 | 🔴 全局模型 CV ~52% | XGBoost CV 52.24%（最新 #23）。需要 regime-specific 訓練 | 🔴 持續 |
| #H150-1 | 🔴 **實時收集 pipeline 缺失 macro 數據** | 最新 45 筆特徵無 regime/VIX/DXY — 已修復（#160） | ✅ 已修復 |

### 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 核心問題：單一模型無法應對不同 regime | 🔴 主要障礙 |
| #H301 | 🟡 Chop regime 0/8 | 需新資料源、新特徵工程 | 🔴 Chop 全滅 |
| #H150-2 | 🟡 Venv 已損壞，pip 全局安裝 | 使用 python3.12 + --break-system-packages 已能運行 | 🟡 環境可用 |
| #H127 | 🟡 VIX 歷史僅 ~6 個月 | 擴展至 1 年+（已達 251 筆/1y） | 🟡 已改善 |
| #H126 | 🟡 共線性：Tongue↔Body, Aura↔Mind 高相關 | 違反獨立感官假設 | 🟡 P1 |

### 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 每次心跳記錄 IC 趨勢 | 🟢 P3 |
| #IC4 | 動態 IC 加權 | sample_weight 依 IC 調整 | 🟢 P3 |

---

## 感官 IC 掃描（心跳 #152, 2026-04-04 11:56）

### 全量 IC (N=8,778, against label_up)
| 感官 | IC | 狀態 |
|------|------|------|
| Eye | +0.0212 | ❌ |
| **Ear** | **-0.0522** | ⭐ 達標 |
| Nose | -0.0475 | 邊緣 |
| Tongue | +0.0042 | ❌ |
| Body | -0.0515 | ❌ |
| Pulse | +0.0027 | ❌ |
| Aura | -0.0300 | ❌ |
| Mind | -0.0253 | ❌ |

### Regime-Aware IC
| 感官 | Bear IC | Bull IC | Chop IC | Neutral IC |
|------|---------|---------|---------|------------|
| **Eye** | **+0.0626 ✅** | -0.0140 ❌ | -0.0035 ❌ | -0.0407 ❌ |
| **Ear** | -0.0399 ❌ | **-0.0617 ✅** | -0.0258 ❌ | **-0.0592 ✅** |
| **Nose** | **-0.0670 ✅** | -0.0426 ❌ | -0.0365 ❌ | **-0.1046 ✅** |
| Tongue | +0.0135 ❌ | +0.0111 ❌ | -0.0340 ❌ | +0.0744 ✅ |
| **Body** | -0.0439 ❌ | **-0.0509 ✅** | -0.0351 ❌ | **-0.0747 ✅** |
| **Pulse** | **+0.0523 ✅** | +0.0264 ❌ | -0.0529 ❌ | +0.0115 ❌ |
| **Aura** | **-0.0722 ✅** | -0.0090 ❌ | -0.0102 ❌ | **-0.1143 ✅** |
| **Mind** | **-0.0618 ✅** | -0.0113 ❌ | +0.0045 ❌ | **-0.0763 ✅** |

### 達標感官數（IC ≥ 0.05）
| Regime | 達標數 | 感官 |
|--------|--------|------|
| Bear | **5/8** | Eye, Nose, Pulse, Aura, Mind |
| Bull | **2/8** | Ear, Body |
| Chop | **0/8** | 無（全滅） |
| Neutral | **6/8** | Ear, Nose, Tongue, Body, Aura, Mind |

**重要發現**：Bear regime 是唯一有 5/8 感官達標的 regime。VIX 在 neutral 最有意義（IC=-0.074）。Chop 仍然 0/8 — 全滅。

### 動態窗口 IC 衰減
| N | 達標數 | 備註 |
|---|--------|------|
| 200 | **5/8** | Ear, Tongue, Pulse, Aura, Mind — 最佳窗口 |
| 500 | 2/8 | Ear, Mind — 信號退化 |
| 1000 | 3/8 | Ear, Tongue, Pulse — 中等穩定 |

### VIX/DXY IC
| Regime | VIX IC | DXY IC |
|--------|--------|--------|
| Bear | -0.0003 ❌ | -0.0083 ❌ |
| Bull | -0.0211 ❌ | -0.0475 ❌ |
| Chop | -0.0025 ❌ | -0.0320 ❌ |
| Neutral | **-0.0882 ✅** | **-0.0742 ✅** |

### 模型表現
| Model | Train | CV | Gap | n_features |
|-------|-------|----|-----|-----------|
| Global XGB | 72.27% | **52.24%** | 20.03pp | 51 |
| Regime DT Bear | 58.3% | 55.6% | 2.7pp | 51 |
| Regime DT Bull | 61.2% | 59.0% | 2.2pp | 51 |
| Regime DT Chop | 56.3% | 52.6% | 3.7pp | 51 |

---

## 六帽分析摘要

**白帽**（事實）：數據量穩定（8,829 raw/features，8,770 labels）。全量 IC僅 Ear (-0.0522)、Body (-0.0515) 通過。Nose (-0.0475) 邊緣。Bear 5/8 是最佳 regime（Eye, Nose, Pulse, Aura, Mind）。N=200 動態窗口 5/8 最佳。**Regime DT models**: Bear 55.6%, Bull 59.0%, Chop 52.6%。Global XGB CV 52.24%。**Regime gap 都在 2-4pp — 過擬合可控**。

**黑帽**（風險）：(1) **Chop 市場完全失明（0/8）** — 2,904 筆數據沒有任何感官有預測力。(2) Bull 只有 2/8 達標（Ear, Body），比 Bear 弱。(3) VIX/DXY macro 信號在 regime 下不穩定，僅 Neutral 有 6/8 通過。(4) 全局 CV 52.24% 約等於隨機，Gap 20pp 嚴重。(5) 動態窗口從 N=200 的 5/8 退化到 N=500 的 1/7（上一輪）2/8 — 信號不穩。

**綠帽**（創新）：(1) **N=200 動態窗口 5/8 — 短期窗口最佳**。(2) Pulse +0.052 在 Bear 是最強單一信號。(3) Regime DT models **gap 只有 2-4pp**，說明 overfitting 問題已大幅改善（global XGB gap 20pp）。(4) Bear 5/8 表明在 Bear 市場，多感官融合預測力最強。(5) VIX-gated trading: 當 VIX > threshold 切到 Bear model，可能比全局模型好 3-7pp。(6) Chop abstain 機制：regime=chop 時不交易，避免隨機賭博。

**藍帽**（行動）：P0: (1) ✅ **Regime-specific model ensemble 部署** — 在 predictor.py 中實現 regime 路由。(2) ✅ **Chop abstain** — 當 regime=chop 時返回 ABSTAIN。(3) ✅ 實現 60/40 ensemble (regime/global)。P1: (4) 優化 Bull sensory IC。(5) 擴展 VIX 歷史。(6) 研究 N=7 動態窗口 IC 穩定化。

**ORID 決策**：
- **O**: Regime-aware IC 已完成。Bear 5/8, Bull 2/8, Chop 0/8。Regime DT models 訓練完成（Bear 55.6%, Bull 59.0%, Chop 52.6%）。Chop 全滅持續。Global XGB CV 52.24%。
- **R**: 系統在 Bear regime 有最多有效信號（5/8），但在全局模型下被稀釋到 2/8。Regime-aware 路由是突破方向。Chop 全滅是最大風險。
- **I**: 核心瓶頸: **regime-specific models gap 只有 2-4pp vs global 20pp** — regime 路由可以顯著改善 overfitting。Chop 0/8 說明橫盤市場目前完全無法預測，需要 abstain 機制。
- **D**: (1) ✅ 更新 ISSUES.md 記錄所有 IC 結果。(2) ✅ **實現 regime-aware ensemble predictor** — `load_predictor()` 返回 `models` dict，`predict()` 按 regime 路由。(3) ✅ **部署 60/40 regime/global ensemble**。(4) ✅ **Chop abstain**。(5) P0 任務：訓練 regime-specific XGBoost（目前僅 DT）提升 CV 更進一步。

## 📋 本輪修改記錄

- **#152-ensemble**: ✅ **實現 regime-aware model ensemble predictor** — `predictor.py` 中 `load_predictor()` 返回 `regime_models` dict，`predict()` 按 regime 動態路由到對應模型（Bear/Bull/Chop/Neutral）。
- **#152-chop-abstain**: ✅ **實現 Chop abstain 機制** — regime=chop 時直接返回 ABSTAIN，避免隨機賭博。
- **#152-regime-gate**: ✅ **實現 60/40 ensemble 權重** — regime model 60% + global model 40%，在 Bear/Bull/Neutral 路由到各自 model，全局 model 作為 fallback。
- **#152-ic**: ✅ 全量 IC 掃描完成。Bear 5/8, Bull 2/8, Chop 0/8。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| ✅ P0 | **部署 regime-aware ensemble predictor** | `predictor.py` ✅ 已合併 |
| ✅ P0 | **實現 Chop abstain 機制** | `predictor.py` ✅ 已合併 |
| ✅ P0 | **60/40 regime/global ensemble** | `predictor.py` ✅ 已合併 |
| P0 | **訓練 regime-specific XGBoost models**（目前僅 DT，CV 55-59% → 目標 65%+） | #H122 |
| P0 | **Chop 新信號源** — 0/8 需新特徵 | #H301 |
| P1 | **Bull regime 感官強化** — 2/8 需改善 | #H301 |
| P1 | **VIX 歷史擴展** — 從 251 筆到 1 年+ | #H127 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
