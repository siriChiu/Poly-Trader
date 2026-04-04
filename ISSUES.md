# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 11:38 GMT+8 (心跳 #151)*
---

## 📊 當前系統健康 (2026-04-04 11:38 GMT+8, 心跳 #151)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,812 筆 | ✅ |
| Features | 8,815 筆 (22 cols + regime) | ✅ |
| Labels | 8,770 筆 (50.8% sell_win) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,837 | — |
| FNG | 11 (Extreme Fear) | — |
| Funding Rate | 0.0000379 (+) | — |
| VIX/DXY | 8,809/8,811 有值 | ✅ 99.9% 已填充 |
| Regime 填充 | Bear 2,927 / Bull 2,912 / Chop 2,904 / Neutral 72 | ✅ 全填充 |

### 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H149-fix1 | 🔴 **訓練/推論特徵不匹配（已修復）** | `load_latest_features()` 缺少 feat_vix、feat_dxy、以及所有 cross-features。#149 全部修復。 | ✅ 已合併 |
| #H122 | 🔴 感官 IC 在 Bull/Chop 幾乎全滅 | Bear 4/8 達標，Bull 2/8，Chop 0/8 | 🔴 持續（Chop 全滅需關注） |
| #H137 | 🔴 全局模型 CV ~51.5% | VIX 進 train.py 後 CV 仍是 51.5%（最新 #23）。需要 regime-specific 訓練 | 🔴 持續 |
| #H150-1 | 🔴 **實時收集 pipeline 缺失 macro 數據** | 最新 45 筆特徵無 regime/VIX/DXY — 已修復（#160） | ✅ 已修復 |

### 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈51% 距目標 90% 差距 ~39pp | 核心問題：單一模型無法應對不同 regime | 🔴 主要障礙 |
| #H301 | 🟡 Chop regime 0/8 達標 | 需新資料源、新特徵工程 | 🔴 Chop 全滅 |
| #H150-2 | 🟡 Venv 已損壞，pip 全局安裝 | 使用 python3.12 + --break-system-packages 已能運行 | 🟡 環境可用 |
| #H127 | 🟡 VIX 歷史僅 ~6 個月 | 擴展至 1 年+（已達 251 筆/1y） | 🟡 已改善 |
| #H126 | 🟡 共線性：Tongue↔Body, Aura↔Mind 高相關 | 違反獨立感官假設 | 🟡 P1 |

### 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 每次心跳記錄 IC 趨勢 | 🟢 P3 |
| #IC4 | 動態 IC 加權 | sample_weight 依 IC 調整 | 🟢 P3 |

---

## 感官 IC 掃描（心跳 #151, 2026-04-04 11:38）

### 全量 IC (N=8,778, against label_up)
| 感官 | IC | 狀態 |
|------|------|------|
| **Nose** | **-0.0520** | ⭐ 達標 |
| **Ear** | **-0.0518** | ⭐ 達標 |
| Body | -0.0495 | 邊緣 |
| Aura | -0.0398 | ❌ |
| Mind | -0.0218 | ❌ |
| Eye | +0.0183 | ❌ |
| Pulse | +0.0056 | ❌ |
| Tongue | +0.0003 | ❌ |

### VIX/DXY IC
| 指標 | Bear | Bull | Chop | Neutral |
|------|------|------|------|---------|
| VIX | **-0.0517 ✅** | **-0.0870 ✅** | -0.0152 ❌ | -0.0755 ✅ |
| DXY | -0.0234 ❌ | -0.0360 ❌ | -0.0041 ❌ | -0.1069 ✅ |

### Regime-Aware IC
| 感官 | Bear IC | Bull IC | Chop IC | Neutral IC |
|------|---------|---------|---------|------------|
| **Eye** | **+0.0673 ✅** | -0.0198 ❌ | +0.0025 ❌ | -0.0217 ❌ |
| **Ear** | -0.0434 ❌ | **-0.0652 ✅** | -0.0347 ❌ | **-0.0548 ✅** |
| **Nose** | **-0.0666 ✅** | -0.0486 ❌ | -0.0375 ❌ | **-0.1135 ✅** |
| Tongue | +0.0176 ❌ | +0.0077 ❌ | -0.0333 ❌ | +0.1178 ✅ |
| **Body** | -0.0455 ❌ | **-0.0510 ✅** | -0.0381 ❌ | -0.2264 ✅ |
| Pulse | +0.0475 ❌ | +0.0204 ❌ | -0.0432 ❌ | +0.0603 ✅ |
| **Aura** | **-0.0691 ✅** | -0.0136 ❌ | -0.0176 ❌ | -0.2297 ✅ |
| **Mind** | **-0.0557 ✅** | -0.0077 ❌ | +0.0038 ❌ | -0.0722 ✅ |

### 達標感官數（IC ≥ 0.05）
| Regime | 達標數 | 感官 |
|--------|--------|------|
| Bear | **4/8** | Eye, Nose, Aura, Mind |
| Bull | **2/8** | Ear, Body |
| Chop | **0/8** | 無（全滅） |
| Neutral | **7/8** | Ear, Nose, Tongue, Body, Pulse, Aura, Mind |

**重要發現**：VIX 在 Bear 和 Bull 都是負 IC 且達標（-0.052, -0.087），是可靠的 macro 信號。DXY 僅在 neutral 時達標。Chop 是所有感官的墓地（0/8）。

### 動態窗口 IC 衰減
| N | 達標數 | 備註 |
|---|--------|------|
| 200 | 5/7 | Pulse +0.17, Nose -0.09, Aura -0.12, Mind -0.15 |
| 500 | 1/7 | Pulse +0.05 |
| 1000 | 3/7 | Pulse +0.13, Aura -0.10, Mind -0.09 |

### 模型表現
| Model | Train | CV | Gap | n_features |
|-------|-------|----|-----|-----------|
| Global XGB (51 feat, VIX) | 72.4% | **51.5%** | 20.9pp | 51 |
| Dynamic N=200 | 87.0% | 51.5% | 35.5pp | 32 |

---

## 六帽分析摘要

**白帽**（事實）：數據量穩定（8,815 raw/features，8,770 labels）。Nose (-0.052) 和 Ear (-0.0518) 是唯二全量 IC 達標的核心感官。**新發現**：VIX IC 在 Bull 為 -0.087（比 Bear -0.052 更強），成為 Bull regime 中最強的 macro 信號。N=200 動態窗口 5/7 通過。**VIX/DXY/Regime 填充率達到 99.9%**。

**黑帽**（風險）：(1) **Chop 市場完全失明（0/8）** — 2,904 筆數據沒有任何感官有預測力。在 choppy 市場系統應該停止交易。(2) VIX 在 Chop 也失效 (-0.015)。(3) DXY 僅在 neutral 時有意義。(4) 短期窗口 (N=200) 有效但 N=500 就崩潰到 1/7 — 信號極度不穩定。(5) CV 仍在 51.5%，幾乎沒有超越隨機。

**綠帽**（創新）：(1) **N=200 動態窗口是最佳配置** — 5/7 通過。這暗示了 regime-specific training with short lookback 是正確方向。(2) N=200 下 Pulse +0.173 是最強單一信號（vol_spike12 在短期極有效）。(3) VIX×Eye/VIX×Mind cross-features 在 Bull regime 應有高 IC（VIX IC=-0.087）。(4) Chop 0/8 是一個明確信號：系統應該在 Chop 時 abstain。

**藍帽**（行動）：P0: (1) 訓練 regime-specific models（Bear: 4/8, Bull: 2/8, Chop: abstain）✅ regime 填充已完成。(2)實現 VIX-gated trading（VIX > 25 使用 Bear model，VIX < 15 使用 Bull model）。P1: (3) 訓練 N=200 rolling model (4) Chop regime abstain threshold。

**ORID 決策**：核心突破是 VIX/DXY/regime 填充完成（99.9%）。VIX 在 Bull regime IC=-0.087 比所有 core sense 都強。Chop 全滅（0/8）確認了需要 regime-aware abstain 機制。下一步：(1)訓練 regime-specific models (2)實現 VIX-gated trading (3)Chop abstain。

## 📋 本輪修改記錄

- **#160-fix**: 修復實時 VIX/DXY 填充 — Yahoo Finance 1y 數據 backfill raw_market_data 和 features_normalized
- **#160-regime**: 計算並填充 45 筆 NULL regime_label → 全部分配 bear/bull/chop
- **#160-labels**: 同步更新 labels 表的 regime_label
- **VIX IC breakthrough**: VIX 在 Bull regime IC=-0.087（比 Bear -0.052 更強），是最強的 macro 信號

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **訓練 regime-specific models**：Bear (4/8), Bull (VIX-gated), Chop (abstain) | #H122 |
| P0 | **VIX-gated model selector**: VIX < 15 → Bull model, VIX > 25 → Bear, otherwise abstain | #H148 |
| P1 | **訓練 N=200 dynamic window model**：利用 5/7 通過的最優窗口 | #H150-action1 |
| P1 | **Chop abstain threshold**: 當 regime=chop 時不交易 | #H301 |
| P1 | **VIX 歷史擴展**: 已擴展到 1y (251 pts) | #H127 ✅ |
| P1 | **Bull regime 信號強化**: 當前 Bull 2/8 達標 (Ear, Body)，需強化 | #H301 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
