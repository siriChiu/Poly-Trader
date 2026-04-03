# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 06:30 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 8/8 感官 IC 低於 0.05（僅 Ear=-0.052 達標） | **Regime-aware 分析顯示 Bear 有 4/8 達標**：Ear=-0.088, Nose=-0.060, Aura=-0.052, Mind=-0.057。但 Chop 0/8、Bull 僅 2/8。需要：(1) 實作 regime 偵測 + 動態加權 (2) Bull regime 新數據源 | 🔴 IC 未提升 |
| #H125 | 🔴 Aura IC=-0.0396 仍低於 0.05 | v12 使用 price_sma144_deviation（8743 唯一值）。Regime-aware: Bear IC=-0.052 ✅, Chop=-0.024 ❌, Bull=-0.067 ✅。整體被 Chop 稀釋 | 🟡 部分解決 |
| #H130 | 🔴 CV 準確率僅 56.3%（距 90% 差距 33.7pp），且訓練準確率僅 52.8% | **已優化超參數**：depth 3→5, n_est 250→300, reg_alpha 2.0→0.5, reg_lambda 6.0→1.0, min_child 10→5。訓練中（n_samples=11112）需驗證新指標 | 🟡 修改已部署，待驗證 |
| #H901 | 🔴 collect_data.py import 錯誤已修復但尚未驗證回補數據完整 | 改為 `from database.models` 並驗證可行。但 volume/funding_rate/fear_greed 列仍幾乎全 NULL | 🟡 等待數據回補 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈56.3% 距目標 90% 差距 33.7pp | 特徵 IC 低是根本原因。Regime-aware 加權可能提升 | 🟡 P1 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate 只有 10 筆有效（全部=2.775e-05） | volume/funding_rate/FNG 幾乎全 NULL | 🟡 P1 |
| #H301 | 🟡 Bull regime 僅 2/8 達標（Ear, Aura） | 牛市需新數據源（ETF flows, on-chain, mining hash rate）| 🟡 P1 |
| #H131 | ✅ ic_signs.json NaN 值已修復 | 40 個 NaN→0.0，JSON 現為有效格式。commit `050a524` | 🟢 已解決 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 被舊數據稀釋 | 改用近期 N=5000 + regime-aware | 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | rolling IC 穩定性追蹤 | 建立每次心跳 IC 歷史趨勢 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H118** | 依賴缺失（venv 損壞） | 重建 venv ✅ | 2026-04-04 04:11 |
| **#H119-fix** | init_db.py 路徑錯誤 | sys.path 修正 ✅ | 2026-04-04 04:11 |
| **#H120-fix** | comprehensive_test.py 掃描 venv | 排除 site-packages ✅ | 2026-04-04 04:11 |
| **#H123-fix** | PROJECT_ROOT 錯誤 | 修正為 parent ✅ | 2026-04-04 05:00 |
| **#H124-fix** | 語法檢查掃描外來目錄 | 加入 EXCLUDE_DIRS ✅ | 2026-04-04 05:00 |
| **#H128-fix** | compare_ic.py 語法錯誤 | 加入 `# ` prefix ✅ | 2026-04-04 06:00 |
| **#H129-fix** | deep_ic_analysis.py 語法錯誤 | 修正括號 ✅ | 2026-04-04 06:00 |
| **#H901-fix** | collect_data.py import 路徑錯誤 | 改為 database.models ✅ | 2026-04-04 05:50 |
| **#H107-fix-1** | venv/bin/activate 缺失 | 直接使用 venv/bin/python 路徑 ✅ | 2026-04-04 06:05 |
| **#H107-fix-2** | 心跳 IC 分析腳本無法連接 DB（無 engine 模組） | 改用直接 SQLite 查詢，不需 SQLAlchemy ✅ | 2026-04-04 06:05 |
| **#H131-fix** | ic_signs.json 含 NaN 值（40 欄位，非有效 JSON） | NaN→0.0，JSON 現在有效。commit 050a524 ✅ | 2026-04-04 06:15 |

---

## 📊 當前系統健康 (2026-04-04 06:30 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 | ✅ |
| Labels | 8,770 筆 | ✅ 標籤平衡 (50.8% pos, 49.2% neg) |
| BTC 當前 | $66,812 | ✅ |
| FNG | 9（極度恐慌）| ⚠️ |
| LSR | 1.7442（多頭偏多）| 📊 |
| OI | 90,332 BTC（~$6.05B）| 📊 |
| Funding Rate | 0.00003000（微正）| 📊 |

### 感官 IC（心跳 #108, N=全量 8770）
| 感官 | IC（全量） | IC（Bear） | IC（Chop） | IC（Bull） | 狀態 |
|------|-----------|-----------|-----------|-----------|------|
| Eye | +0.0221 | +0.0376 | +0.0377 | +0.0232 | ❌ |
| Ear | **-0.0516** | **-0.0884** | -0.0295 | **-0.0507** | ✅ 跨 regime 穩定 |
| Nose | -0.0483 | **-0.0601** | -0.0417 | -0.0495 | ❌ 接近閾值 |
| Tongue | +0.0036 | +0.0409 | -0.0270 | -0.0005 | ❌ |
| Body | +0.0102 | +0.0486 | -0.0045 | -0.0116 | ❌ |
| Pulse | +0.0105 | +0.0305 | -0.0266 | +0.0302 | ❌ |
| Aura | -0.0396 | **-0.0521** | -0.0238 | **-0.0673** | ❌ Bear/Bull 達標 |
| Mind | -0.0293 | **-0.0572** | -0.0122 | -0.0499 | ❌ Bear 達標 |

### Regime-aware 突破
| Regime | 達標感官 | 數量 |
|--------|---------|------|
| Bear | Ear(-0.088), Nose(-0.060), Aura(-0.052), Mind(-0.057) | 4/8 ✅ |
| Chop | (none) | 0/8 ❌ |
| Bull | Ear(-0.051), Aura(-0.067) | 2/8 ❌ |

> **關鍵洞察**: Ear 是唯一跨所有 regime 都有強度的感官。反向指標策略在熊市最有效，熊市的 4 感官加權融合可能帶來實質提升。

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| CV Accuracy | 56.3% (±9.1%) | ❌ 距 90% 差 33.7pp |
| Train Accuracy | 52.8% | ❌ 欠擬合 |
| Model | XGBoost (超參數已優化，待驗證新指標) | 🟡 修改中 |
| ic_signs.json | 40 NaN → 0.0 已修復 | ✅ 有效 JSON |
| Sell Win Rate | N/A (0 trades) | ❌ |

### 共線性問題
| 配對 | 相關係數 | 問題 |
|------|---------|------|
| Tongue × Body | r=+0.78 | 兩者都是波動率相關 |
| Tongue × Pulse | r=+0.76 | 成交量和波動率相關 |
| Aura × Mind | r=+0.85 | 價格偏離 SMA 和動量幾乎相同 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | 實作 regime-aware 預測：用 IC 加權融合（Bear: Ear+Nose+Aura+Mind；Bull: Ear+Aura）| #H122 |
| P0 | 驗證 XGBoost 超參數優化後的 train/CV 指標 | #H130 |
| P1 | Bull regime 新增特徵：ETF flows, on-chain metrics | #H301 |
| P1 | 回填 volume/funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85） | #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |

---

## 📋 近期修改記錄

- **#107**: 新增 scripts/heartbeat_ic_analysis.py - SQLite 直接 IC 分析，不需 SQLAlchemy
- **#107**: 新增 scripts/get_live_market_data.py - 即時市場數據收集
- **#107**: 新增 scripts/check_model_state.py - 模型狀態檢查
- **#107**: 新增 scripts/inspect_tables.py - 資料庫表結構檢查
- **#107**: 關鍵發現 - Ear 穩定達標（全量 IC=-0.052），是唯一跨 regime 有效感官
- **#107**: 關鍵發現 - XGBoost train_acc(52.8%) < cv_acc(56.3%) = 欠擬合信號
- **#108**: ✅ 修復 ic_signs.json - 40 個 NaN 值替換為 0.0，JSON 恢復有效
- **#108**: ✅ 優化 XGBoost 超參數：depth 3→5, reg_alpha 2.0→0.5, reg_lambda 6.0→1.0, min_child 10→5, n_est 250→300

---

*此文件每次心跳完全覆蓋，保持簡潔。*
