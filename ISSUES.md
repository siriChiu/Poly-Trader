# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 07:23 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（N=全量） | **動態窗口確認**：N=200 最高(5/8, ICs: Nose=-0.094, Tongue=+0.097, Pulse=+0.152, Aura=-0.126, Mind=-0.163)；但 CV 仍僅 51.5%（gap 36.5pp）。**結論**：單靠窗口縮小無法突破 CV 天花板 | 🔴 未突破 |
| #H125 | 🔴 全量 IC 仍低於 0.05 | N=1000→5/8, N=200→5/8（感官不同），N>3000→≤1/8。衰減模式穩定確認 | 🟡 改善中 |
| #H130 | 🔴 模型過擬合：gap ~20pp | 全局 gap=20.8pp 已大幅改善（vs 過擬 33.7pp）。動態窗口 gap=36.5pp（N 太小導致不穩） | 🟡 全局有改善 |
| #H137 | 🔴 全局模型 CV 停滯 50.5% | **根本原因**：單特徵 IC ≤0.15，理論上限 ~53-55%。要達 90% 需 IC >0.4 集體。需**新數據源/新特徵**而非調參 | 🔴 CV 天花板 |
| #H138 | 🔴 **動態窗口確認**：N=200→5/8 但 N=1000 更穩 | N=200 訓練 CV=51.5%±9.2%（不穩）；N=1000 訓練 CV=50.5%±0.5%（穩定）。**推薦：N=1000 作為基準** | ✅ 已評估 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50-52% 距目標 90% 差距 38-40pp | 根本原因確認：(1) 單特徵 IC ≤0.15 (2) Bull/Chop 幾乎無有效感官 (3) 需要新數據源。非調參可解 | 🟡 需新特徵 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate/fng 幾乎全 NULL | 回填歷史數據 | 🟡 P1 |
| #H301 | 🟡 Chop 僅 1/8（Aura），Bull 0/8 | Chop 需要震盪指標（RSI/Bollinger），Bull 需新數據源（ETF flows, on-chain） | 🟡 P1 |
| #H140 | 🔴 **CV 天花板 51-52%** | 當前 8 感官 + lag + 交叉特徵組合，CV 無法突破 52%。**唯一出路**：高 IC 新數據源 | 🔴 新問題 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 被舊數據稀釋 | 改用 N=1000 窗口 | 🟢 已解決（動態窗口確認） |
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
| **#H139-fix1** | dev_heartbeat.py PROJECT_ROOT 計算錯誤 | 改用 Path(__file__).parent ✅ | 2026-04-04 07:08 |
| **#H139-fix2** | check_ic2.py 硬編碼 Windows 路徑 | 改用動態路徑 ✅ | 2026-04-04 07:08 |
| **#H138-eval** | 動態窗口評估：N=200 雖有 5/8 但 CV 不穩 | 確認 N=1000 為基準（CV 50.5%±0.5%）✅ | 2026-04-04 07:23 |

---

## 📊 當前系統健康 (2026-04-04 07:23 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 | ✅ |
| Labels | 8,770 筆 (50.8% pos) | ✅ 平衡 |
| BTC 當前 | $66,867 | ⬇️ 平穩 |
| FNG | 9（極度恐慌）| ⚠️ 持續極端 |
| LSR | 1.74（多頭偏斜）| — |
| OI | 90,245 | — |

### 感官 IC 掃描
| 窗口 | 達標感官數 | 具備 IC |
|------|-----------|---------|
| 全量 (8770) | 1/8 | Ear(-0.052) |
| N=5000 | 0/8 | 全無效 |
| N=3000 | 1/8 | Aura(-0.069) |
| N=2000 | 2/8 | Pulse(+0.078), Aura(-0.067) |
| N=1000 | **5/8** ← **基準** | Nose(-0.051), Body(+0.068), Pulse(+0.126), Aura(-0.104), Mind(-0.105) |
| N=500 | 1/8 | Pulse(+0.057) |
| N=200 | 5/8 | Nose(-0.094), Tongue(+0.097), Pulse(+0.152), Aura(-0.126), Mind(-0.163) |

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| 全局 Train | 71.32% | 🟡 |
| 全局 CV | 50.53% (±0.51%) | ❌ 硬天花板 |
| 全局 gap | 20.8pp | 🟡 改善中 |
| 動態 N=200 Train | 88.0% | 🟡 |
| 動態 N=200 CV | 51.5% (±9.2%) | ❌ 不穩定 |
| 動態 N=200 gap | 36.5pp | 🔴 過擬 |
| Model | XGBoost, depth=3, IC加權 | ✅ |
| 測試 | 6/6 PASS | ✅ |

### Regime-aware IC（波動率分類）
| Regime | 達標感官 | 數量 |
|--------|-----------|------|
| Bear | Ear(-0.075), Nose(-0.075), Aura(-0.053) | 3/8 ⬆️ 最佳 |
| Bull | (none) | 0/8 ❌ |
| Chop | Aura(-0.056) | 1/8 ❌ |

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **高 IC 新數據源**：VIX、DXY、ETF flows、on-chain（唯一突破 52% CV 的路） | #H140 |
| P0 | Chop regime 新指標：RSI、Bollinger Bandwidth、ATR | #H301 |
| P1 | Bull regime 新數據源：BTC ETF flows、whale wallet tracking | #H301 |
| P1 | 回填 funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85）| #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |
| P3 | 建立每次心跳 IC 歷史趨勢追蹤 | #H97 |

---

## 📋 近期修改記錄

- **#140**: 心跳 — 動態窗口評估（N=200 最高但 CV 不穩，N=1000 為基準）
- **#140**: 建立 dynamic_window_train.py（自動掃描 N=200~5000）
- **#140**: CV 天花板確認：51-52%，需新數據源
- **#139**: 全量 IC analysis + Regime-aware IC
- **#133-fix**: 移除 8 constant features
- **#130-fix**: 全局 gap 降至 20.8pp（depth=3, reg_alpha=2.0）

---

*此文件每次心跳完全覆蓋，保持簡潔。*
