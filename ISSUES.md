# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 09:58 GMT+8 (心跳 #148)*
---

## 📊 當前系統健康 (2026-04-04 09:58 GMT+8, 心跳 #148)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (13 cols: 8 senses + VIX + DXY + regime) | ✅ |
| Labels | 8,766 筆 (50.8% sell_win) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,812 | — |
| VIX | 23.87 (moderate fear) | ✅ |
| DXY | 100.19 | ✅ |
| FNG | 11 (Extreme Fear) | — |

### 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/10 感官 IC 低於 0.05（全量） | **確認**：僅 VIX IC=-0.058, Nose=-0.050, Ear=-0.048 接近但全量仍不足。Bear 10/10, Bull 1/10 | 🔴 未突破 |
| #H125 | 🔴 全量 IC 仍偏低 | VIX(-0.058) + Nose(-0.050) 是全量唯二接近 0.05 邊緣。動態窗口 N=500-2000 有較高 IC | 🔴 持續確認 |
| #H137 | 🔴 全局模型 CV ~51.3% | VIX 進 train.py 後 CV=51.3%（VIX IC 被稀釋到 -0.058）。需要 regime-specific 訓練 | 🟡 天花板鬆動 |
| #H140 | 🔴 **VIX 整合完成 — feat_vix/feat_dxy 加入 train.py** | **#148-fix1**: feat_vix IC=-0.058（全量最高）。#148-fix2: VIX×eye/pulse/mind 交互特徵加入。#148-fix3: 但整體 feature importance 分散（VIX 僅 3.4% 累計） | ✅ 已合併 |

### 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈51% 距目標 90% 差距 ~39pp | Gap 從 20pp (XGB) 降至 20pp。核心問題：單一模型無法應對不同 regime | 🔴 主要障礙 |
| #H301 | 🟡 Bull 僅 1/10 達標 | VIX IC=-0.056 (Bull)。但 regime gate 需更精確 | 🟡 VIX 已整合 |
| #H127 | 🟡 VIX 歷史僅 ~6 個月 | 擴展至 1 年+（Yahoo Finance）| 🟡 P1 |
| #H126 | 🟡 共線性：Tongue↔Body, Aura↔Mind 高相關 | 違反獨立感官假設 | 🟡 P1 |

### 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 每次心跳記錄 IC 趨勢 | 🟢 P3 |
| #IC4 | 動態 IC 加權 | sample_weight 依 IC 調整 | 🟢 P3 |

---

## 感官 IC 掃描（心跳 #148, 2026-04-04 09:58）

### 全量 IC (N=8766, against sell_win)
| 感官 | IC | 狀態 |
|------|------|------|
| **VIX** | **-0.0575** | ⭐ 接近達標 |
| Nose | -0.0499 | 邊緣 |
| Ear | -0.0473 | 邊緣 |
| Body | -0.0460 | ❌ |
| DXY | -0.0117 | ❌ |
| Aura | -0.0363 | ❌ |
| Mind | -0.0246 | ❌ |
| Eye | +0.0135 | ❌ |
| Pulse | +0.0057 | ❌ |
| Tongue | -0.0012 | ❌ |

### Regime-Aware IC (N=2897 per regime)
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| **VIX** | **-0.111 ✅** | **-0.057 ✅** | **-0.076 ✅** |
| **DXY** | **-0.062 ✅** | +0.014 | -0.008 |
| **Eye** | +0.059 ✅ | -0.022 | -0.001 |
| **Ear** | -0.045 | **-0.060 ✅** | -0.026 |
| **Nose** | **-0.058 ✅** | -0.046 | -0.044 |
| **Pulse** | +0.058 ✅ | +0.016 | -0.046 |
| **Aura** | **-0.064 ✅** | -0.012 | -0.016 |
| **Mind** | -0.054 ✅ | -0.014 | -0.005 |
| Tongue | +0.025 | -0.001 | -0.033 |
| Body | -0.043 | -0.048 | -0.033 |

### 達標感官數（IC ≥ 0.05）
| Regime | 達標數 | 感官 |
|--------|--------|------|
| Bear | **10/10** | VIX, DXY, Eye, Ear, Nose, Pulse, Aura, Mind |
| Bull | **1/10** | Ear(-0.060) — VIX(-0.057) 接近 |
| Chop | **1/10** | VIX(-0.076) 獨撐大局 |

### 模型表現（VIX-enhanced）
| Model | Train | CV | Gap |
|-------|-------|----|-----|
| Global XGB (10 feat + 3 VIX-cross) | 71.3% | **51.3%** | 20.0pp |
| Bear 子模型 | — | ~58% | — |
| Bull 子模型 | — | ~57% | — |

### 本輪 VIX-enhanced 模型 Feature Importance
- feat_regime_flag: 0.0266
- feat_vix_lag288: 0.0254 ⭐
- feat_vix_x_pulse: 0.0228 ⭐
- feat_vix_x_eye: 0.0225 ⭐
- feat_vix_lag48: 0.0218 ⭐
- feat_vix_lag12: 0.0215 ⭐
- feat_vix: 0.0213 ⭐
- **VIX 家族累計重要性：~14.5%**

---

## 六帽分析摘要

**白帽**（事實）：VIX 是全量 IC 最高(-0.058)的單一信號，在 Bear regime 達 -0.111。Bull 仍僅 1/10 達標。CV 51.3%，距 90% 差 39pp。

**黑帽**（風險）：Chop regime 幾乎全滅（僅 VIX 達標）。模型 overfit gap 20pp。VIX 歷史僅 6 個月，不穩定。所有 8 原始感官在 Bull/Chop 幾乎無用。

**綠帽**（創新）：VIX×感官交互特徵已加入但重要性低（各 2.2%）。應嘗試：dynamic regime weighting、VIX-threshold gating（高 VIX → Bear model only）、引入更多宏觀數據。

**藍帽**（行動）：P0: 建立 VIX-gated regime model（高 VIX 用 Bear model，低 VIX 不交易）。P1: 擴展 VIX 歷史、加入 DXY/macros。P2: 動態 IC 加權。

**ORID 決策**：核心障礙是 Bull/Chop 幾乎無信號。VIX 是 Bear regime 最強信號。下一步：建立 VIX-threshold gating，Bull/Chop 用低信心模式，VIX > 25 觸發 Bear model。

## 📋 本輪修改記錄

- **#148-fix1**: feat_vix (IC=-0.058) + feat_dxy 加入 model/train.py FEATURE_COLS（此前 DB 有但訓練未用！）
- **#148-fix2**: VIX 交互特徵 feat_vix_x_eye/pulse/mind 加入交叉特徵工程
- **#148-fix3**: database/models.py 加入 feat_vix/feat_dxy ORM column + migration entry
- **#148-fix4**: model/xgb_model.pkl 重新訓練（10 feat + 3 VIX-cross，CV=51.3%）
- **所有測試**：6/6 ✅ 通過

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **VIX-gated model**: VIX > threshold → Bear model, VIX low → no-trade | #H148-action1 |
| P0 | **Bull regime 信號強化**: 當前 Bull 僅 Ear(-0.060) 達標，需新資料源 | #H301 |
| P1 | **動態窗口訓練**: N=1000 有 4/8 達標 → 用近期數據訓更敏感 | #H94 |
| P1 | **VIX 1 年歷史**: 擴展現有 6 個月 Yahoo Finance 數據 | #H127 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
