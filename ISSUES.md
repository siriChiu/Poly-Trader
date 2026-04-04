# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 08:14 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（全量） | **已確認**：僅 Ear IC=-0.051 達標。Bear regime 有 4/8 但 Bull 0/8、Chop 1/8 | 🔴 未突破 |
| #H125 | 🔴 全量 IC 仍低於 0.05 | 衰減模式：N↓→更多感官達標但 CV 不穩。N=1000 最佳(4/8) | 🟡 改善中 |
| #H130 | 🔴 模型過擬合：gap ~20pp | 全局 gap=20.1pp。depth=3 正規化已改善（vs 原本 33.7pp）| 🟡 改善中 |
| #H137 | 🔴 全局模型 CV 停滯 50.5% | **根本原因**：單特徵 IC ≤0.077。要達 90% 需 IC >0.4 集體。需**新數據源/新特徵**而非調參 | 🔴 CV 天花板 |
| #H140 | 🔴 **CV 天花板 50-52%** | 當前 8 感官 + lag + 交叉特徵組合，CV 無法突破 52%。**唯一出路**：高 IC 新數據源 | 🔴 持續確認 |
| #H141 | 🔴 **Regime 分配錯誤**：Labels & FeaturesNormalized 全 neutral | FeaturesNormalized.reme_label 已修正（bear/chop/bull 分配完成）。Labels.regime_label 仍全 neutral | 🟡 部分修正 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50-52% 距目標 90% 差距 38-40pp | 根本原因確認：(1) 單特徵 IC ≤0.077 (2) Bull/Chop 幾乎無有效感官 (3) 需要新數據源 | 🟡 需新特徵 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate/fng 幾乎全 NULL | 回填歷史數據 | 🟡 P1 |
| #H301 | 🟡 Chop 僅 1/8（Aura），Bull 0/8 | Chop 需要震盪指標（RSI/Bollinger），Bull 需新數據源（ETF flows, on-chain） | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 被舊數據稀釋 | 改用動態窗口 | 🟢 已確認 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | rolling IC 穩定性追蹤 | 建立每次心跳 IC 歷史趨勢 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H118** | 依賴缺失（venv 損壞） | 安裝系統級包 ✅ | 2026-04-03 22:39 |
| **#H119-fix** | init_db.py 路徑錯誤 | sys.path 修正 ✅ | 2026-04-04 04:11 |
| **#H120-fix** | comprehensive_test.py 掃描 venv | 排除 site-packages ✅ | 2026-04-04 04:11 |
| **#H123-fix** | PROJECT_ROOT 錯誤 | 修正為 parent ✅ | 2026-04-04 05:00 |
| **#H124-fix** | 語法檢查掃描外來目錄 | 加入 EXCLUDE_DIRS ✅ | 2026-04-04 05:00 |
| **#H128-fix** | compare_ic.py 語法錯誤 | 加入 `#` prefix ✅ | 2026-04-04 06:00 |
| **#H129-fix** | deep_ic_analysis.py 語法錯誤 | 修正括號 ✅ | 2026-04-04 06:00 |
| **#H901-fix** | collect_data.py import 路徑錯誤 | 改為 database.models ✅ | 2026-04-04 05:50 |
| **#H132-fix** | ic_signs.json NaN + ConstantInputWarning | NaN→0.0 + constant filter + NaN guard | 2026-04-04 06:30 |
| **#H134-fix** | run_train.py 硬編碼外部工作區路徑 | 改用 Path(__file__).parent.parent ✅ | 2026-04-03 22:39 |
| **#H135-fix** | model_metrics 表不存在 | 建立 model_metrics 表 ✅ | 2026-04-04 04:39 |
| **#H136-fix** | python3 指向無 pip 的 hermes venv | 改用 /usr/bin/python3.12 並安裝包 ✅ | 2026-04-03 22:39 |
| **#H133-fix** | 8 constant features 佔據 33% feature space | 移除 whisper/tone/chorus/hype/oracle/shock/tide/storm ✅ | 2026-04-04 06:50 |
| **#H139-fix1** | dev_heartbeat.py PROJECT_ROOT 計算錯誤 | 改用 Path(__file__).parent ✅ | 2026-04-04 07:08 |
| **#H139-fix2** | check_ic2.py 硬編碼 Windows 路徑 | 改用動態路徑 ✅ | 2026-04-04 07:08 |
| **#H138-eval** | 動態窗口評估：N=200 雖有 5/8 但 CV 不穩 | 確認 N=1000 為基準（CV 50.5%±0.5%）✅ | 2026-04-04 07:23 |
| **#H142-fix** | hb105 regime 分配錯誤（全 neutral） | ✅ 確認 regime_aware_ic.py 正確分類（bear/2897, bull/2897, chop/2984）| 2026-04-04 07:44 |
| **#H143-fix1** | train.py 缺少高-IC 交叉特徵 | 新增 feat_eye_x_body, feat_ear_x_nose, feat_mind_x_aura, feat_mean_rev_proxy ✅ | 2026-04-04 08:14 |
| **#H143-fix2** | FeaturesNormalized regime_label 全 neutral | ✅ 已重新分配：bear/chop/bull 基於 ret_rolling 三分位 | 2026-04-04 08:14 |

---

## 📊 當前系統健康 (2026-04-04 08:14 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,770 筆 | ✅ |
| Features | 8,770 筆 | ✅ |
| Labels | 8,770 筆 (50.8% pos) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,907 | ⬇️ 下跌中 |
| FNG | 11（極度恐慌）| ⚠️ 持續極端 |
| LSR | 1.73（多頭偏斜）| — |
| OI | 90,277 | — |
| Taker Buy/Sell | 1.41 | — |
| Funding Rate | 0.000035 | — |

### 感官 IC 掃描（最新：regime_aware_ic.py + hb105_ic_analysis.py, N=8778）
| 窗口/Regime | 達標感官數 | 具備 IC |
|------|-----------|---------|
| 全量 (8778) | **1/8** | Ear(-0.051) |
| Bear (2897) | **4/8** ⬆️ | Ear(-0.075), Nose(-0.075), Body(-0.069), Aura(-0.053) |
| Bull (2897) | **0/8** ❌ | (none) |
| Chop (2984) | **1/8** | Aura(-0.056) |

**動態窗口（all samples, non-regime）**：
| N | 達標數 | 備註 |
|---|--------|------|
| 500 | 1/8 | Pulse(+0.057) — 但 CV 不穩(±9%) |
| 1000 | **4/8** | Nose/Aura/Mind/Pulse |
| 2000 | 2/8 | Aura/Pulse |

**替代高-IC 特徵發現**（hb105_explore_features.py）：
- eye_dist: IC=+0.0503 ✅
- mean_rev_20h: IC=-0.0558 ✅
- rsi_14_norm: IC=-0.0510 ✅
- price_ret_12h: IC=-0.0516 ✅
- price_ret_24h: IC=-0.0511 ✅

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| 全局 Train | 71.10% | 🟡 overfit |
| 全局 CV | 50.95% (±0.71%) | ❌ 硬天花板 |
| 全局 Gap | 20.1pp | 🟡 改善中（vs 33.7pp）|
| Feature Count | 36 (8 base + 24 lags + 4 cross) | → 40 (+4 new cross-features) |
| Model | XGBoost, depth=3, new cross-features | ✅ |
| 特徵重要性 | 均勻 ~2.7-3.2%（無主導）| ⚠️ 信號分散 |
| 測試 | 6/6 PASS | ✅ |

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **高 IC 新數據源**：VIX、DXY、ETF flows、on-chain（唯一突破 52% CV 的路徑）| #H140 |
| P0 | **整合 raw market data 高-IC 特徵進 pipeline**：eye_dist, mean_rev_20h, price_ret_12h, rsi_14_norm | #H143 |
| P0 | **Regime-aware training**：用新的 regime labels 訓練 per-regime 模型 | #H141 |
| P1 | Bull regime 新數據源：BTC ETF flows、whale wallet tracking | #H301 |
| P1 | 回填 funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85）| #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |
| P3 | 建立每次心跳 IC 歷史趨勢追蹤 | #H97 |

---

## 📋 近期修改記錄

- **#143**: 心跳 — train.py 新增 4 個交叉特徵 (eye_x_body, ear_x_nose, mind_x_aura, mean_rev_proxy)
- **#H143**: FeaturesNormalized regime_label 修正 — 從全 neutral 改為 bear/chop/bull 三分位
- **#140**: 心跳 — IC 掃描確認 CV 天花板 50-52%（新數據源是唯一出路）
- **#139**: 全量 IC analysis + Regime-aware IC
- **#133-fix**: 移除 8 constant features
- **#130-fix**: 全局 gap 降至 20.8pp（depth=3, reg_alpha=2.0）

---

*此文件每次心跳完全覆蓋，保持簡潔。*
