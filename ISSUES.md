# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 08:53 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（全量） | **已確認**：僅 Ear IC=-0.051 達標。Bear 4/8, Bull 0/8, Chop 1/8 | 🔴 未突破 |
| #H125 | 🔴 全量 IC 仍低於 0.05 | 衰減模式：N=1000 最佳(4/8)，N=5000 降至 0/8 | 🔴 持續確認 |
| #H130 | 🔴 模型過擬合：gap ~21pp | 全局 gap=21.6pp。Per-regime 模型 gap 僅 2-4pp（大幅改善）| 🟡 改善中 |
| #H137 | 🔴 全局模型 CV 停滯 50.5% | **根本原因**：單特徵 IC ≤0.077。要達 90% 需 IC >0.4 集體。需**新數據源/新特徵**而非調參 | 🔴 CV 天花板 |
| #H140 | 🔴 **CV 天花板 50-52%** | 當前 8 感官 + lag + 交叉特徵組合，CV 無法突破 52%。**唯一出路**：高 IC 新數據源 | 🔴 持續確認 |
| #H141 | 🔴 **Regime 分配錯誤**：features_norm `regime_label` 全 neutral | **H145 fix**: 重新运行 fix_regimes_h141.py。Bear 2897, Bull 2897, Chop 2904, Neutral 72 ✅ | 🟡 已修正（防回歸） |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50-52% 距目標 90% 差距 38-40pp | Per-regime 決策樹：Bear CV 55.6%, Bull 59.0%, Chop 52.6%（vs 全局 51.3%）✅ | 🟡 改善中 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate/fng 幾乎全 NULL（10/8770） | 回填歷史數據 | 🟡 P1 |
| #H301 | 🟡 Bull 僅 1/8（Ear）| Bull 需新數據源（ETF flows, on-chain）| 🟡 P1 |

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
| **#H138-eval** | 動態窗口評估：N=2000 雖有 2/8 但 CV 不穩 | 確認 N=1000 為基準（CV 50.5%±0.5%）✅ | 2026-04-04 07:23 |
| **#H142-fix** | hb105 regime 分配錯誤（全 neutral） | ✅ 確認 regime_aware_ic.py 正確分類 | 2026-04-04 07:44 |
| **#H143-fix1** | train.py 缺少高-IC 交叉特徵 | 新增 feat_eye_x_body, feat_ear_x_nose, feat_mind_x_aura, feat_mean_rev_proxy ✅ | 2026-04-04 08:14 |
| **#H143-fix2** | FeaturesNormalized regime_label 全 neutral | ✅ 重新修正 DB（防 recompute_features 回歸） | 2026-04-04 08:37 |
| **#H145-eval** | Per-regime 模型比全局模型更好 | Bear CV 55.6%, Bull 59.0%, Chop 52.6% vs 全局 51.3% | ✅ 已驗證 |
| **#H145-fix1** | 建立 regime_models.pkl | ✅ 訓練並保存 per-regime DT 模型（8698 samples）| 2026-04-04 08:53 |

---

## 📊 當前系統健康 (2026-04-04 08:53 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,770 筆 | ✅ |
| Features | 8,770 筆 | ✅ |
| Labels | 8,770 筆 (50.1% pos) | ✅ 平衡 |
| Trades | 0 筆 | ⚠️ 模擬中 |
| BTC 當前 | $66,898 | — |
| Funding Rate | 0.000033 | — |
| LSR | 1.726 | ⬆️ 多頭偏多 |

### 感官 IC 掃描（regime_aware_ic.py, N=8778）
| 窗口/Regime | 達標感官數 | 具備 IC |
|------|-----------|---------|
| 全量 (8778) | **1/8** | Ear(-0.051) |
| Bear (2897) | **4/8** | Ear(-0.075), Nose(-0.075), Body(-0.069), Aura(-0.053) |
| Bull (2897) | **0/8** ❌ | (none) |
| Chop (2984) | **1/8** | Aura(-0.056) |

### Per-Regime 模型（決策樹，h=4）
| Regime | Best CV | Gap | 改善 vs 全局 |
|--------|---------|-----|-----------|
| Bear | **55.6%** | 2.7pp | +4.3pp ✅ |
| Bull | **59.0%** | 2.2pp | +7.7pp ✅ |
| Chop | **52.6%** | 3.7pp | +1.3pp |
| Global DT | 51.3% | — | baseline |
| XGBoost | 50.4% | — | baseline |

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| 全局 Train (XGB) | 71.94% | 🟡 overfit |
| 全局 CV (XGB) | 50.36% (±1.46%) | ❌ 硬天花板 |
| 全局 Gap | 21.6pp | 🟡 改善中 |
| Feature Count | 40 (8 base + 24 lags + 8 cross) | — |
| Model | XGBoost, depth=3, reg_alpha=2.0 | ✅ |
| Per-Regime Models | ✅ regime_models.pkl saved | ✅ 新 |
| 測試 | 6/6 PASS | ✅ |

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **Per-regime 預測集成**：更新 predictor.py 使用 regime_models.pkl 路由 | #H145 |
| P0 | **高 IC 新數據源**：VIX、DXY、ETF flows、on-chain（唯一突破 52% CV 的路徑）| #H140 |
| P0 | **防回歸機制**：recompute_features.py 後自動重算 regime labels | #H141 |
| P1 | Bull regime 新數據源：BTC ETF flows、whale wallet tracking | #H301 |
| P1 | 回填 funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85）| #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |
| P3 | 建立每次心跳 IC 歷史趨勢追蹤 | #H97 |

---

## 📋 近期修改記錄

- **#H145-fix1**: 心跳 — 訓練並保存 per-regime 模型 (regime_models.pkl)
- **#H145-eval**: 心跳 — per-regime 模型評估（Bear CV 55.6%, Bull 59.0%, Chop 52.6% vs 全局 51.3%）
- **#H141-fix**: 重新修正 DB regime_label（Bear 2897, Bull 2897, Chop 2904, Neutral 72）
- **#H143**: train.py 新增 4 個交叉特徵 (eye_x_body, ear_x_nose, mind_x_aura, mean_rev_proxy)
- **#H140**: 心跳 — IC 掃描確認 CV 天花板 50-52%（新數據源是唯一出路）
- **#H130-fix**: 全局 gap 降至 21.6pp（depth=3, reg_alpha=2.0）

---

*此文件每次心跳完全覆蓋，保持簡潔。*
