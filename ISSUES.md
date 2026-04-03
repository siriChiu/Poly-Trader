# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 07:02 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（僅 Ear=-0.0514 達標） | **發現解法**：Regime-aware N=1000 訓練 → CV=63.7%（+13.2pp 改善）。Bear 67.1%, Bull 63.8%, Chop 59.6%。仍距 90% 有 26pp 差距 | 🔴 部分改善 |
| #H125 | 🔴 全量 IC 仍低於 0.05（7/8 無效） | N=1000 時 IC≥0.03 有 5/8 達標，窗口化有效但需動態調整 | 🟡 改善中 |
| #H130 | 🔴 模型過擬合：Train=71.32%, CV=50.53%（-20.8pp gap）| Regime-aware N=1000 已將 gap 縮小：Bear gap=5.7pp, Bull gap=4.3pp, Chop gap=6.4pp | 🟡 大幅改善 |
| #H137 | 🔴 全局模型 CV 停滯 50.5% | **已找到突破**：Regime-aware N=1000 CV=63.7%，但 N 增大後衰減嚴重（N=2000→57.9%）| 🟡 有方向 |
| #H133 | ✅ ~~8/24 features (33%) 為 null/constant~~ | **已修復**：從 FEATURE_COLS 移除 8 個 constant cols，cross-feature 改用 feat_nose_x_aura | 🟢 已修復 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50.5% 距目標 90% 差距 39.5pp | 根本原因：(1) 特徵 IC 低（7/8 < 0.05）(2) regime-mix（Chop 無有效感官）(3) 樣本量不足。**新方案**：regime-aware N=1000 已改善至 63.7%，但仍有 26pp 差距 | 🟡 P1 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 目前用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate 只有 10 筆有效 | volume/funding_rate/FNG 幾乎全 NULL | 🟡 P1 |
| #H301 | 🟡 Bull/Chop 無有效感官 | 牛市需新數據源（ETF flows, on-chain），Chop 需要震盪指標 | 🟡 P1 |
| #H138 | 🔴 **Regime-aware N 衰減**：N=1000→63.7%, N=2000→57.9% | 需要動態窗口：IC 衰減時縮小 N 以維持 signal density | 🔴 新問題 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 被舊數據稀釋 | 改用近期 N=1000 窗口 IC 切換策略 | 🟢 P2 |
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
| **#H135-fix** | model_metrics 表不存在 | 建立 model_metrics 表 ✅ | 2026-04-03 22:39 |
| **#H136-fix** | python3 指向無 pip 的 hermes venv | 改用 /usr/bin/python3.12 並安裝包 ✅ | 2026-04-03 22:39 |
| **#H133-fix** | 8 constant features 佔據 33% feature space | 移除 whisper/tone/chorus/hype/oracle/shock/tide/storm ✅ | 2026-04-04 06:50 |

---

## 📊 當前系統健康 (2026-04-04 07:02 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (8 core + cross-features + lag = 36 total) | ✅ 已清除 constant noise |
| Labels | 8,770 筆 | ✅ 標籤平衡 (50.8% pos, 49.2% neg) |
| BTC 當前 | $66,906 | ✅ |
| FNG | 9（極度恐慌）| ⚠️ |
| LSR | 1.7405（多頭偏多）| 📊 |
| OI | 90,246 BTC | 📊 |
| Taker | 1.0332 | 📊 |
| Funding Rate | 0.00003389（微正）| 📊 |

### 感官 IC（心跳 #138, N=全量 8778, compute_ic.py）
| 感官 | IC（全量） | IC（Bear） | IC（Chop） | IC（Bull） | 狀態 |
|------|-----------|-----------|-----------|-----------|------|
| Eye | +0.0212 | +0.0322 | +0.0383 | -0.0269 | ❌ |
| Ear | **-0.0514** | **-0.0747** | -0.0312 | -0.0353 | ✅ Bear only |
| Nose | -0.0494 | **-0.0746** | -0.0267 | -0.0373 | ❌ Bear only |
| Tongue | +0.0042 | +0.0023 | +0.0238 | -0.0137 | ❌ |
| Body | +0.0088 | -0.0088 | +0.0382 | -0.0041 | ❌ |
| Pulse | +0.0106 | +0.0165 | +0.0150 | +0.0001 | ❌ |
| Aura | -0.0384 | **-0.0534** | **-0.0562** | -0.0103 | ❌ Bear+Chop |
| Mind | -0.0253 | -0.0271 | -0.0181 | -0.0224 | ❌ |

### Regime-aware 分析
| Regime | 達標感官（|IC|≥0.05） | 數量 |
|--------|-----------|------|
| Bear | Ear(-0.075), Nose(-0.075), Aura(-0.053) | 3/8 ⚠️ |
| Chop | Aura(-0.056) | 1/8 ❌ |
| Bull | (none) | 0/8 ❌ |

### 🆕 Regime-Aware 訓練結果（心跳 #138, N=1000）
| Regime | N | 特徵數 | Train | CV (5-fold) | CV std |
|--------|---|--------|-------|-------------|--------|
| Bear | 349 | 8 | 72.78% | 67.08% | ±7.42% |
| Bull | 307 | 4 | 68.08% | 63.83% | ±3.96% |
| Chop | 344 | 6 | 65.99% | 59.58% | ±3.30% |
| **總體** | **1000** | - | - | **~63.7%** | - |

| 窗口大小 | 總體 CV | 改善 vs 全局 | 備註 |
|----------|---------|-------------|------|
| N=1000 | 63.7% | +13.2pp | **最佳配置** ✅ |
| N=1500 | 58.8% | +8.3pp | 衰減中 |
| N=2000 | 57.9% | +7.4pp | 繼續衰減 |
| N=8770 (global) | 50.53% | baseline | 信噪比太低 |

### IC Decay 分析
| N | 達標感官數量 | 具體 |
|---|-------------|------|
| N=500 | 1/8 | Pulse(+0.057) |
| N=1000 | 5/8 | Nose, Body(+0.068), Pulse(+0.126), Aura(-0.104), Mind(-0.105) |
| N=2000 | 2/8 | Pulse(+0.078), Aura(-0.067) |
| N=3000 | 1/8 | Aura(-0.069) |
| N=5000 | 0/8 | 全部無效 |

> **關鍵洞察**: N=1000 時 5/8 有效 → regime-aware N=1000 訓練 CV=63.7%（+13.2pp）。但窗口增大後信噪比急劇下降，需動態調整 N。

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| 全局 Train | 71.32% | 🟡 |
| 全局 CV | 50.53% (±0.51%) | ❌ 仍低 |
| 全局 Train-CV Gap | 20.8pp | 🟡 改善中 |
| Regime-aware CV (N=1000) | 63.7% | ✅ 最佳 |
| Regime-aware Train-CV Gap | ~5-8pp | ✅ 大幅改善 |
| Model | XGBoost, depth=3, IC加權 | ✅ |
| Sell Win Rate | N/A (0 trades) | ❌ |

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | 整合 regime-aware N=1000 到生產訓練管線 | #H122 |
| P0 | 實現動態窗口：IC衰減時縮小N以維持signal density | #H138 |
| P0 | 尋找高IC新特徵（VIX, DXY, ETF flows, on-chain metrics）| #H301 |
| P1 | Bull/Chop regime 新數據源 | #H301 |
| P1 | 回填 volume/funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85）| #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |
| P3 | 建立每次心跳 IC 歷史趨勢追蹤 | #H97 |

---

## 📋 近期修改記錄

- **#138**: 心跳 — 全量 IC analysis + regime-aware IC analysis
- **#138**: Regime-aware N=1000 訓練 — CV=63.7%（+13.2pp 改善）
- **#138**: 窗口分析 N=500/1000/1500/2000/8770 — 確認 N=1000 最佳
- **#138**: 保存結果至 data/heartbeat_138_results.json
- **#138**: 測試 6/6 通過
- **#133-fix**: 移除 8 constant features（whisper/tone/chorus/hype/oracle/shock/tide/storm）
- **#130-fix**: 回滾超參數，過擬合 gap 33.7pp→20.8pp

---

*此文件每次心跳完全覆蓋，保持簡潔。*
