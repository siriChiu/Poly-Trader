# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 20:11 GMT+8（心跳 #180）*
---

## 📊 當前系統健康狀態（2026-04-04 20:11 GMT+8，心跳 #180）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,955 筆 | ⬆️ +1 |
| Features | 8,920 筆 | ⬆️ +1 |
| Labels | 8,766 筆 | ➡️ 持平 |
| BTC 當前 | ~$67,129 | ⬆️ 小幅上漲 |
| FNG | 11（Extreme Fear） | ➡️ 持平 |
| Funding Rate | ~0.000016 | ➡️ 持平 |
| LSR | 1.6518 | 🟡 偏多 |
| OI | 90,435 | ➡️ 持平 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 0/8** | 🔴 **持續** | 全域 **0/8** against sell_win（連續 2 輪 0/8），signal ceiling 問題未解 |
| #H321 | 🔴 **Ear/Tongue 持續坍縮** | ⚠️ **部分恢復** | Ear: tau=50 從 -0.0346→-0.0345（持平），全域 -0.0478。N=1000 仍 FAIL |
| #H340 | 🚨 **Regime IC 全面惡化** | 🔴 **惡化** | Bear 從 5/8→0/8（N=2897 新版），Bull 1/8，Chop 0/8。新版 regime 分配顯示 Bear 信號全滅 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **持續** | 根本瓶頸：信號天花板 ≈ 51-52%，id=36 最新模型 52.24% |
| #H341 | 🚨 **sell_win vs label_up 鴻溝** | 🆕 **新增** | agreement 94.9% — 445 筆（5.1%） disagree，sell_win=0.508 vs label_up=0.501 |
| #H200 | 🔴 **Ear IC 持續退化** | 🔴 **持續** | tau=50: -0.0345, 全域: -0.0478 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未重訓模型** | TI 回填完成但最新模型 id=36 已用 51 特徵（含 TI），CV 52.24% 無提升 |
| #H333 | 🟡 **N=500 仍全滅** | 0/8，短期窗口無有效信號 |
| #H335 | 🟡 **_hb180_deep_sell_win.py timestamp 解析 bug** | ✅ **已修復** |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 已有 xgb_model.pkl + regime_models.pkl |

---

## 感官 IC 掃描（心跳 #180, 2026-04-04 20:11）

### 全域 IC against sell_win（N=8,778, 8 核心感官）
| 感官 | IC | 狀態 | vs #179 |
|------|------|------|---------|
| Nose | -0.0500 | ❌ 貼線 | ➡️ 持平 |
| Ear | -0.0478 | ❌ | ➡️ 持平 |
| Body | -0.0461 | ❌ | ➡️ 持平 |
| Aura | -0.0363 | ❌ | ➡️ 持平 |
| Mind | -0.0246 | ❌ | ➡️ 持平 |
| Eye | +0.0135 | ❌ | ➡️ 持平 |
| Pulse | +0.0058 | ❌ | ➡️ 持平 |
| Tongue | -0.0012 | ❌ | ➡️ 持平 |

**全域達標：0/8** — 持續（上輪 0/8，前輪 1/8）

### 全域 IC against label_up
| 感官 | IC | 狀態 | vs #179 |
|------|------|------|---------|
| **Ear** | **-0.0518** | ✅ **勉強過線** | ➡️ 持平 |
| **Nose** | **-0.0520** | ✅ **勉強過線** | ➡️ 持平 |
| 其餘 | <0.05 | ❌ | — |

**2/8 against label_up**（vs 0/8 against sell_win，標籤定義差異持續存在）

### 最近 500 筆 IC
| 感官 | IC | 狀態 | vs #179 |
|------|------|------|---------|
| 全部 | <0.05 | ❌ **全滅** | ❌ 0/8（上輪 0/8）|

**最近 500 筆：0/8** — 持續

### 最近 1000 筆 IC
| 感官 | IC | 狀態 | vs #179 |
|------|------|------|---------|
| **Pulse** | **+0.1148** | ✅ | ➡️ 持平（最強）|
| **Aura** | **-0.0971** | ✅ | ➡️ 持平 |
| **Mind** | **-0.0759** | ✅ | ➡️ 持平 |
| **Eye** | **+0.0607** | ✅ | ➡️ 持平 |

**最近 1000 筆：4/8 過線** — 持平

### Time-Weighted IC
| tau | 達標數 | 過線感官 | 備註 |
|-----|--------|---------|------|
| 50 | **6/8** | Nose, Tongue, Body, Pulse, Aura, Mind | ➡️ 持平 |
| 100 | **6/8** | Nose, Tongue, Body, Pulse, Aura, Mind | ➡️ 持平 |
| 200 | **4/8** | Nose, Pulse, Aura, Mind | ➡️ 持平 |
| 500 | **3/8** | Pulse, Aura, Mind | ➡️ 持平 |

### Regime IC（新版 N=2897 均勻分配）
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| Eye | +0.0089 ❌ | -0.0308 ❌ | +0.0079 ❌ |
| Ear | -0.0338 ❌ | -0.0106 ❌ | -0.0187 ❌ |
| Nose | -0.0142 ❌ | +0.0189 ❌ | -0.0306 ❌ |
| Tongue | +0.0208 ❌ | -0.0353 ❌ | +0.0019 ❌ |
| Body | -0.0211 ❌ | -0.0019 ❌ | -0.0211 ❌ |
| Pulse | +0.0038 ❌ | +0.0341 ❌ | +0.0008 ❌ |
| Aura | -0.0011 ❌ | -0.0308 ❌ | -0.0110 ❌ |
| Mind | -0.0292 ❌ | -0.0313 ❌ | -0.0061 ❌ |

### Regime IC（舊版分布，用於對比 #H304）
| Regime | 達標數 | 感官 | vs #179 |
|--------|--------|------|---------|
| Bear | **5/8** | Eye, Nose, Pulse, Aura, Mind | ➡️ 持平（N=2897 新版 Bear 為 0/8！）|
| Bull | **1/8** | Ear | ➡️ 持平 |
| Chop | **0/8** | 全滅 | ➡️ 持平 |

### 🔴 關鍵發現
- **全域 0/8 已連續兩輪** — 所有 8 感官 against sell_win 無一過線，系統處於持續信號真空
- **新版 Regime 分配 vs 舊版結果差異極大**：Bear 在舊版 5/8，新版 0/8！這表明舊版 Bear 結果可能包含 data leakage（因為用 labels 表的 regime_label 而非 features 表的 regime_label）
- **sell_win vs label_up 差異持續存在**：agreement 94.9%，445 筆 disagreed
- **sell_win by regime（舊版）**：Bear 0.417, Bull 0.605, Chop 0.503
- **N=1000 仍為 4/8** — Pulse(+.115), Aura(-.097), Mind(-.076), Eye(+.061)
- **Time-weighted 穩定** — tau=50: 6/8, tau=500: 3/8，與上輪持平
- **模型未受益於 TI 特徵** — id=36 已用 51 特徵（含 TI），CV 52.24% 與舊版持平
- **_hb180_deep_sell_win.py timestamp bug 已修** — `format='mixed'` 加入解析
- **Chop 佔數據 35-40%** — 0/8 IC + sell_win 0.503 ≈ 隨機，拖累整體模型

### ✅ 修復確認
- _hb180_deep_sell_win.py：timestamp 解析 + features/labels merge bug 已修
- 測試 6/6 全部通過

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (51 features) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | 52.24% (id=36, 51 features, sell-win auto-train) |
| TI 特徵回填 | ✅（最新版 CV 52.24%，無提升）|
| Test results | **6/6 全部通過** ✅ |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,955 筆（+1）、Features 8,920 筆（+1）、Labels 8,766 筆（持平）
- **全域 0/8 against sell_win** — 連續兩輪無有效全域信號
- **全域 2/8 against label_up** — Ear(-.052), Nose(-.052) 勉強過線
- **新版 Bear 0/8**（與舊版 5/8 矛盾，可能含泄露）
- N=500: 0/8, N=1000: 4/8（持平）
- Time-weighted tau=50: 6/8, tau=500: 3/8（持平）
- 測試 6/6 全部通過
- CV 52.24%（最新版本，51 特徵含 TI）
- sell_win vs label_up agreement: 94.9%

### 黑帽（風險）
1. **全局 0/8 信號真空持續** — 最嚴重的系統性問題，連續兩輪確認不是偶然
2. **Regime 結果矛盾** — 舊版 Bear 5/8 vs 新版 Bear 0/8，可能存在 label leakage（用標籤表的 regime_label 而非特徵表的 regime_label）
3. **標籤定義鴻溝持續** — 5.1% disagreement 意味著 sell_win 與簡單漲跌幅有系統性差異
4. **Chop 佔 35-40% 且 IC ≈ 0** — 橫盤時系統完全失效，拖累整體
5. **TI 回填無效** — 模型已用 51 特徵但 CV 仍 52%，說明問題不在特徵數量
6. **Ear 持續衰變** — IC 趨勢惡化，可能需替換或重新設計
7. **最新模型 CV 52.24% — 遠低於 90% 目標（差距 38pp）**

### 黃帽（價值）
1. **N=1000 4/8 仍穩** — Pulse, Aura, Mind, Eye 在中窗口有效
2. **Time-weighted tau=50: 6/8 穩定** — 短期時間衰減仍有效
3. **測試 6/6 全通過** — 系統穩定性良好
4. **數據管線正常運行** — +1 raw，+1 features
5. **sell_win 分佈均勻** — Bear 0.42, Bull 0.61，有 regime 結構可利用

### 藍帽（決策）
**P0 行動項：**
1. 🔴 **修復 regime label 泄露** — 新舊版 Bear IC 矛盾，需統一用 features 表 regime_label
2. 🔴 **信號重設計** — 全域 0/8 連續兩輪，現有 8 感官無法預測 sell_win
3. 🔴 **Chop regime 替代方案** — 佔 35-40% 數據且 IC ≈ 0，需新數據源
4. 🟡 **Confidence-weighted 融合** — 利用 N=1000 和 time-weighted 穩定信號
5. 🟢 **sell_win 標籤優化** — 研究 5.1% disagreement 根因

---

## ORID 決策
- **O**: 全域 0/8 against sell_win（連續兩輪），N=1000 4/8，tau=50 6/8，Bear 新版 0/8 vs 舊版 5/8（矛盾，可能泄露），CV 52.24%，測試 6/6。BTC $67,129, FNG 11。
- **R**: 全域信號真空已不是偶發現象而是系統性問題。Regime IC 矛盾暗示可能存在 label leakage。CV 52% 天花板說明「用現有 8 感官預測 sell_win」的架構有根本限制。
- **I**: 連續 0/8 + regime 結果矛盾 = 現有框架需要質的改變而非量的優化。Chop 佔 35-40% 且 IC ≈ 0，說明橫盤市場完全不可預測。sell_win 定義本身可能包含無法用價格/交易量特徵預測的噪音。方向可能是：（1）改進 sell_win 標籤定義（2）引入全新 alpha 源鏈上數據/巨觀（3）放棄低信心 regime 只交易 high-confidence windows。
- **D**: （1）**修 regime label 泄露**確保 IC 計算正確（2）**探索新 alpha 源**如期權鏈數據、鏈上巨鯨（3）**只交易 high-confidence windows**（N=1000 4/8 區間）（4）**sell_win 標籤重審**研究 5.1% disagreement 根因

---

## 📋 本輪修改記錄

- **#180**: ✅ 運行 dev_heartbeat.py — Raw=8,955, Features=8,920, Labels=8,766。
- **#180**: ✅ **全盤 IC 分析** — 全域 **0/8** against sell_win（持續！），label_up 2/8。
- **#180**: ⚠️ **Regime 矛盾確認** — 舊版 Bear 5/8 vs 新版 Bear 0/8，可能存在 label leakage。
- **#180**: 🔴 **Sell win rate by regime**: Bear 41.7%, Bull 60.5%, Chop 50.3%（sell_win 有明顯 regime structure）
- **#180**: ✅ **sell_win vs label_up gap 量化** — agreement 94.9%, 445 disagree。
- **#180**: ✅ **模型最新狀態確認** — id=36, 51 特徵, CV 52.24%（TI 未提升 CV）。
- **#180**: ✅ **修 _hb180_deep_sell_win.py** — timestamp 解析 bug (format='mixed') + merge bug。
- **#180**: ✅ **測試 6/6 全通過**。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **修復 regime label 泄露** — 統一用 features 表 regime_label 計算 IC | #H340 |
| 🔴 P0 | **信號重設計** — 全域 0/8 連續兩輪，需新 alpha 源 | #H304 |
| 🔴 P0 | **sell_win 標籤重審** — 5.1% disagreement 根因分析 | #H341 |
| 🟡 P1 | **Confidence-only 交易策略** — 只在 N=1000 4/8 窗口交易 | #H126 |
| 🟡 P1 | **tau=50 6/8 融合策略** — 短期時間衰減最穩定 | #H333 |
| 🟢 P2 | **新 alpha 源** — 期權鏈、鏈上巨鯨、VIX 期貨、Polymarket | #H303 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
