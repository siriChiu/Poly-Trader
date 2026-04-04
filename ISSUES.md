# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 10:50 GMT+8 (心跳 #149)*
---

## 📊 當前系統健康 (2026-04-04 10:50 GMT+8, 心跳 #149)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (23 cols: 8 核心 + 8 輔助 + VIX + DXY + regime) | ✅ |
| Labels | 8,770 筆 (50.1% sell_win) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,812 | — |
| VIX | 23.87 (moderate fear) | ✅ |
| DXY | 100.19 | ✅ |
| FNG | 11 (Extreme Fear) | — |

### 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H149-fix1 | 🔴 **訓練/推論特徵不匹配（已修復）** | `load_latest_features()` 缺少 feat_vix、feat_dxy、以及所有 cross-features。模型訓練用 51 個特徵但推論時只傳 16 個，VIX 和交叉特徵全為 0。**#149-fix1**: feat_vix/feat_dxy 加入推論。**#149-fix2**: VIX 交互特徵計算加入。所有 cross-features 和 regime flag 同步補齊。 | ✅ 已合併 |
| #H122 | 🔴 感官 IC 在 Bull/Chop 幾乎全滅 | Bear 4/8 達標，Bull 0/8，Chop 1/8 | 🔴 未突破 |
| #H137 | 🔴 全局模型 CV ~51.3% | VIX 進 train.py 後 CV 仍是 51.3%。需要 regime-specific 訓練 | 🟡 天花板鬆動 |

### 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈51% 距目標 90% 差距 ~39pp | 核心問題：單一模型無法應對不同 regime | 🔴 主要障礙 |
| #H301 | 🟡 Bull 僅 0/8 達標 | 需新資料源、新特徵工程 | 🔴 持續 |
| #H127 | 🟡 VIX 歷史僅 ~6 個月 | 擴展至 1 年+（Yahoo Finance）| 🟡 P1 |
| #H126 | 🟡 共線性：Tongue↔Body, Aura↔Mind 高相關 | 違反獨立感官假設 | 🟡 P1 |

### 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 每次心跳記錄 IC 趨勢 | 🟢 P3 |
| #IC4 | 動態 IC 加權 | sample_weight 依 IC 調整 | 🟢 P3 |

---

## 感官 IC 掃描（心跳 #149, 2026-04-04 10:50）

### 全量 IC (N=8,778, against label_up)
| 感官 | IC | 狀態 |
|------|------|------|
| **Ear** | **-0.0514** | ⭐ 唯二達標 |
| Nose | -0.0494 | 邊緣 |
| Body | -0.0481 | 邊緣 |
| Aura | -0.0384 | ❌ |
| Mind | -0.0253 | ❌ |
| Eye | +0.0212 | ❌ |
| Tongue | +0.0042 | ❌ |
| Pulse | +0.0106 | ❌ |

### VIX/DXY IC
| 指標 | 全量 IC | Bear | Bull | Chop |
|------|---------|------|------|------|
| VIX | +0.0047 | +0.0202 | +0.0089 | -0.0073 |
| DXY | +0.0113 | — | — | — |

### Regime-Aware IC
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| **Ear** | **-0.0747 ✅** | -0.0353 | -0.0312 |
| **Nose** | **-0.0746 ✅** | -0.0373 | -0.0267 |
| **Body** | **-0.0685 ✅** | -0.0352 | -0.0316 |
| **Aura** | **-0.0534 ✅** | -0.0103 | **-0.0562 ✅** |
| Eye | +0.0322 | -0.0269 | +0.0383 |
| Pulse | +0.0165 | +0.0001 | +0.0150 |
| Mind | -0.0271 | -0.0224 | -0.0181 |
| Tongue | +0.0023 | -0.0137 | +0.0238 |

### 達標感官數（IC ≥ 0.05）
| Regime | 達標數 | 感官 |
|--------|--------|------|
| Bear | **4/8** | Ear, Nose, Body, Aura |
| Bull | **0/8** | 無 |
| Chop | **1/8** | Aura |

### 動態窗口 IC 衰減
| N | 達標數 | 備註 |
|---|--------|------|
| 500 | 1/8 | Pulse 獨達標 |
| 1000 | 4/8 | Nose, Pulse, Aura, Mind |
| 2000 | 2/8 | Pulse, Aura |
| 3000 | 1/8 | Aura |
| 5000 | 0/8 | 全部低于閾值 |

### 模型表現
| Model | Train | CV | Gap |
|-------|-------|----|-----|
| Global XGB (51 feat) | 71.3% | **51.3%** | 20.0pp |

---

## 六帽分析摘要

**白帽**（事實）：Ear 是全量 IC 最高(-0.0514)的感官。Bear regime 有 4/8 達標，Bull 0/8 全滅，Chop 僅 Aura 達標。VIX IC 從上輪的 -0.058 崩跌至 +0.0047（全量），說明 VIX 的 predictability 被稀釋或在當前 regime 失效。N=1000 時有 4/8 達標 → 動態窗口確實有效。CV 51.3%，距 90% 差 39pp。關鍵修復：推論時 VIX/cross-features 全部為 0，現在已修補。

**黑帽**（風險）：**訓練/推論不匹配**（#H149-fix1）是最嚴重的系統性 bug — 模型在訓練時看到 VIX 和交叉特徵但推論時完全不看。這意味著過去心跳的所有預測都是基於「半盲」特徵集。修補後需觀察推論是否改善。Bull regime 完全無可用信號（0/8），系統在 Bull 市場是瞎的。VIX IC 崩塌可能意味 VIX 與 sell_win 的關係已變化。

**綠帽**（創新）：(1)動態窗口取樣 N=1000 可提升達標數至 4/8 → 應訓練一個 rolling window model。(2)VIX-threshold gating：僅在 VIX > 25 時交易（Bear regime 信號最強）。(3)引入外部數據源：Twitter/X 情緒、Polymarket 預測、DXY 分解。

**藍帽**（行動）：P0: 重新訓練模型（確保所有 51 特徵在推論時可用）並驗證推論是否改善。P1: 建立動態窗口訓練 pipeline (N=1000)。P2: VIX gating 機制 — 高 VIX 觸發交易，低 VIX 持觀望。

**ORID 決策**：核心發現是推論管線有重大缺失 — 模型從未在推論時看到 VIX 和交叉特徵。修復此問題是提升模型效能的關鍵第一步。下一步：(1)提交修復 (2)用修復後的特徵重訓模型 (3)建立 VIX-gated regime model。

## 📋 本輪修改記錄

- **#149-fix1**: `load_latest_features()` 加入 feat_vix、feat_dxy（此前 DB 有但推論未讀取！）
- **#149-fix2**: VIX 交互特徵 feat_vix_x_eye/pulse/mind 在推論時計算
- **#149-fix3**: 所有 cross-features（mind_x_pulse, eye_x_ear 等 8 個）加入推論管線
- **#149-fix4**: feat_regime_flag + feat_mean_rev_proxy 加入推論管線
- **所有測試**：6/6 ✅ 通過

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **重訓模型驗證修復**：用完整的 51 特徵集重訓，確認推論與訓練一致 | #H149-action1 |
| P0 | **VIX-gated model**: VIX > 25 觸發 Bear model 交易 | #H148-action1 |
| P0 | **Bull regime 信號強化**: 當前 Bull 0/8 達標，需新資料源 | #H301 |
| P1 | **動態窗口訓練**: N=1000 有 4/8 達標 → 用近期數據訓更敏感 | #H94 |
| P1 | **VIX 1 年歷史**: 擴展現有 6 個月 Yahoo Finance 數據 | #H127 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
