# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 06:50 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（僅 Ear=-0.0516 達標） | **Regime-aware: Bear 3/8 達標（Ear, Nose, Aura），Bull 2/8（Ear, Aura），Chop 1/8（Aura）| 需要：(1) Regime-aware 融合加權 (2) Bull/Chop 新數據源 | 🔴 未改善 |
| #H125 | 🔴 Aura IC=-0.0396 仍低於 0.05 | v12 有 8743 唯一值但整體被稀釋。Bear=-0.053, Bull=-0.010, Chop=-0.056 | 🟡 Chop pass, Bear pass |
| #H130 | 🔴 模型過擬合：Train=71.32%, CV=50.53%（-20.8pp gap）| ✅ 已回滾參數（depth=3, reg_alpha=2.0, reg_lambda=6.0, min_child=10）；已移除 constant features（gap 從 33.7pp→20.8pp，改善 12.9pp）。根因：特徵 IC 太低（7/8 無效），模型無法從低信噪比數據中學習 | 🟡 gap 改善但仍大 |
| #H133 | ✅ ~~8/24 features (33%) 為 null/constant~~ | **已修復**：從 FEATURE_COLS 移除 8 個 constant cols，cross-feature 改用 feat_nose_x_aura | 🟢 已修復 #H133-fix |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50.5% 距目標 90% 差距 39.5pp | 根本原因：(1) 特徵 IC 低（7/8 < 0.05）(2) regime-mix（Chop 無有效感官）(3) 樣本量 8770 可能不足 | 🟡 P1 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 目前用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate 只有 10 筆有效 | volume/funding_rate/FNG 幾乎全 NULL | 🟡 P1 |
| #H301 | 🟡 Bull regime 僅 2/8 達標（Ear=-0.035, below threshold） | 牛市需新數據源（ETF flows, on-chain）| 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 被舊數據稀釋 | 改用近期 N=5000 + regime-aware | 🟢 P2 |
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

## 📊 當前系統健康 (2026-04-04 06:50 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (8 core + 4 cross-features + 28 lag = 40 total) | ✅ 已清除 constant noise |
| Labels | 8,770 筆 | ✅ 標籤平衡 (50.8% pos, 49.2% neg) |
| BTC 當前 | $66,943 | ✅ |
| FNG | 9（極度恐慌）| ⚠️ |
| LSR | 1.7397（多頭偏多）| 📊 |
| OI | 90,360 BTC | 📊 |
| Taker | 1.0332 | 📊 |
| Funding Rate | 0.00003391（微正）| 📊 |

### 感官 IC（心跳 #137, N=全量 8770, regime_aware_ic.py）
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
| Regime | 達標感官 | 數量 |
|--------|---------|------|
| Bear | Ear(-0.075), Nose(-0.075), Aura(-0.053) | 3/8 ⚠️ |
| Chop | Aura(-0.056) | 1/8 ❌ |
| Bull | (none) | 0/8 ❌ |

> **關鍵洞察**: Bear regime 仍有 3 個有效感官（Ear, Nose, Aura），Chop 僅 1 個（Aura），Bull 完全無效。全量 N=8770 時 IC decay 嚴重（1000 樣本時 5/8 有效→5000 時 0/8），顯示早期數據有 signal 但被稀釋。

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| Train Accuracy | 71.32% | 🟡 改善中（85.1%→71.3%）|
| CV Accuracy | 50.53% (±0.51%) | ❌ 仍低（51.3%→50.5% 微降）|
| Train-CV Gap | 20.8pp | 🟡 改善（33.7pp→20.8pp, -12.9pp）|
| Model | XGBoost v5, depth=3, reg_alpha=2.0 | ✅ 參數保守化 |
| Feature Count | 36 (8 base + 24 lag + 4 cross) | ✅ 移除 8 constant |
| Sell Win Rate | N/A (0 trades) | ❌ |

### 過擬合分析（軌跡）
- 保守參數（前前輪）: Train=52.8%, CV=56.3% → **欠擬合**（gap=-3.5pp）
- 積極參數（上輪）: Train=85.1%, CV=51.3% → **嚴重過擬合**（gap=33.7pp）
- **本輪（回滾+清除 constant）**: Train=71.3%, CV=50.5% → **仍過擬合但大幅改善**（gap=20.8pp）
- 根本原因：7/8 感官 IC < 0.05，特徵信噪比太低，模型無法從噪音中區分信號

### 共線性問題
| 配對 | 相關係數 | 問題 |
|------|---------|------|
| Tongue × Body | r=+0.78 | 兩者都是波動率相關 |
| Tongue × Pulse | r=+0.76 | 成交量和波動率相關 |
| Aura × Mind | r=+0.85 | 價格偏離 SMA 和動量幾乎相同 |

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | 實作 regime-aware 預測融合（Bear: Ear+Nose+Aura 加權）| #H122 |
| P0 | IC decay 分析：全量 IC → 近期 N 窗口 IC 切換策略 | #H94 |
| P0 | 尋找高 IC 新特徵（VIX, DXY, ETF flows, on-chain metrics）| #H301 |
| P1 | Bull/Chop regime 新數據源 | #H301 |
| P1 | 回填 volume/funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85） | #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |

---

## 📋 近期修改記錄

- **#133-fix**: 移除 8 constant features（whisper/tone/chorus/hype/oracle/shock/tide/storm）
- **#133-fix**: feat_aura_x_tide → feat_nose_x_aura（tide was constant zero）
- **#130-fix**: 回滾超參數 depth=3, reg_alpha=2.0, reg_lambda=6.0, min_child=10, gamma=0.2
- **#130-fix**: 過擬合 gap 改善 33.7pp → 20.8pp（-12.9pp 改善）
- **#137**: 心跳 — 全量 IC analysis + regime-aware IC analysis (regime_aware_ic.py)
- **#137**: 發現 IC decay：N=1000 時 5/8 有效 → N=5000 時 0/8 有效（早期數據有 signal）

---

*此文件每次心跳完全覆蓋，保持簡潔。*
