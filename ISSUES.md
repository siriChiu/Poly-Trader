# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 07:09 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（僅 Ear 達標） | **方向正確**：Regime-aware N=1000 訓練 → CV=63.7%（+13.2pp）。Bear 67.1%, Bull 63.8%, Chop 59.6%。仍距 90% 有 26pp 差距 | 🔴 部分改善 |
| #H125 | 🔴 全量 IC 仍低於 0.05（7/8 無效） | N=1000 時 IC≥0.03 有 5/8 達標，窗口化有效但需動態調整 | 🟡 改善中 |
| #H130 | 🔴 模型過擬合：gap ~20pp | Regime-aware N=1000 將 gap 縮至 5-8pp | 🟡 大幅改善 |
| #H137 | 🔴 全局模型 CV 停滯 50.5% | Regime-aware N=1000 CV=63.7%，但 N 衰減嚴重 | 🟡 有方向 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈50-64% 距目標 90% 差距 26-40pp | 根本原因：(1) 特徵 IC 低 (2) Chop regime 無有效感官 (3) 樣本量不足。Regime-aware 已改善至 63.7% | 🟡 P1 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失；Ear 用 Binance long-short 替代 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate/fng 幾乎全 NULL | 回填歷史數據 | 🟡 P1 |
| #H301 | 🟡 Chop 無有效感官（0/8），Bull 僅 2/8 | Chop 需要震盪指標（RSI/Bollinger），Bull 需新數據源（ETF flows, on-chain） | 🟡 P1 |
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
| **#H139-fix1** | dev_heartbeat.py PROJECT_ROOT 計算錯誤（parent.parent→parent） | 改用 Path(__file__).parent ✅ | 2026-04-04 07:08 |
| **#H139-fix2** | check_ic2.py 硬編碼 Windows 路徑 + escape warning | 改用動態路徑 + 移除 `\.` ✅ | 2026-04-04 07:08 |

---

## 📊 當前系統健康 (2026-04-04 07:09 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (8 core + cross-features + lag) | ✅ |
| Labels | 8,770 筆 | ✅ 平衡 (50.8% pos, 49.2% neg) |
| BTC 當前 | $66,812 | ⬇️ 較上次心跳 -$94 |
| FNG | 9（極度恐慌）| ⚠️ 持續極端 |

### 感官 IC（心跳 #139, N=全量 8770, heartbeat_ic_analysis.py）
| 感官 | IC（全量） | IC（Bear） | IC（Chop） | IC（Bull） | 狀態 |
|------|-----------|-----------|-----------|-----------|------|
| Eye | +0.0221 | +0.0376 | +0.0377 | +0.0232 | ❌ |
| Ear | **-0.0516** | **-0.0884** | -0.0295 | **-0.0507** | ✅ Bear+Bull |
| Nose | -0.0483 | **-0.0601** | -0.0417 | -0.0495 | ❌ Bear 邊緣 |
| Tongue | +0.0036 | +0.0409 | -0.0270 | -0.0005 | ❌ |
| Body | +0.0102 | +0.0486 | -0.0045 | -0.0116 | ❌ Bear 邊緣 |
| Pulse | +0.0105 | +0.0305 | -0.0266 | +0.0302 | ❌ |
| Aura | -0.0396 | **-0.0521** | -0.0238 | **-0.0673** | ✅ Bear+Bull |
| Mind | -0.0293 | -0.0572 | -0.0122 | -0.0499 | ❌ Bear 邊緣 |

### Regime-aware 分析（按 DB 時間排序切分）
| Regime | 達標感官（\|IC\|≥0.05） | 數量 |
|--------|-----------|------|
| Bear | Ear(-0.088), Nose(-0.060), Aura(-0.052), Mind(-0.057) | 4/8 ⬆️ 改善 |
| Chop | (none) | 0/8 ❌ |
| Bull | Ear(-0.051), Aura(-0.067) | 2/8 ⬆️ 改善 |

### IC Decay 分析（從 #138 已知）
| N | 達標感官數量 | 具體 |
|---|-------------|------|
| N=500 | 1/8 | Pulse(+0.057) |
| N=1000 | 5/8 | Nose, Body(+0.068), Pulse(+0.126), Aura(-0.104), Mind(-0.105) |
| N=2000 | 2/8 | Pulse(+0.078), Aura(-0.067) |
| N=3000 | 1/8 | Aura(-0.069) |
| N=5000 | 0/8 | 全部無效 |

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| 全局 Train | 71.32% | 🟡 |
| 全局 CV | 50.53% (±0.51%) | ❌ |
| 全局 Train-CV Gap | 20.8pp | 🟡 |
| Regime-aware CV (N=1000) | 63.7% | ✅ 最佳可用 |
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
| P1 | Chop regime 新指標（RSI/Bollinger/ATR震盪） | #H301 |
| P1 | Bull regime 新數據源（ETF flows, on-chain） | #H301 |
| P1 | 回填 volume/funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85）| #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |
| P3 | 建立每次心跳 IC 歷史趨勢追蹤 | #H97 |

---

## 📋 近期修改記錄

- **#139**: 心跳 — 全量 IC analysis（Ear=-0.052, 其餘 <0.05）
- **#139**: Regime-aware IC — Bear 4/8達標(⬆️), Bull 2/8(⬆️), Chop 0/8(❌)
- **#139**: Fix dev_heartbeat.py PROJECT_ROOT（parent.parent→parent）
- **#139**: Fix check_ic2.py 硬編碼 Windows 路徑 + `\.` escape warnings
- **#139**: 測試 6/6 通過
- **#138**: Regime-aware N=1000 訓練 — CV=63.7%（+13.2pp 改善）
- **#133-fix**: 移除 8 constant features

---

*此文件每次心跳完全覆蓋，保持簡潔。*
