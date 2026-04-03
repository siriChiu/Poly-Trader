# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-03 22:39 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 7/8 感官 IC 低於 0.05（僅 Ear=-0.052 達標） | **Regime-aware: Bear 4/8 達標（Ear, Nose, Aura, Mind），Bull 2/8，Chop 0/8**。需要：(1) Regime-aware 融合加權 (2) Bull/Chop 新數據源 | 🔴 未改善 |
| #H125 | 🔴 Aura IC=-0.0396 仍低於 0.05 | v12 有 8743 唯一值但整體被稀釋。Bear=-0.052, Bull=-0.067 達標，Chop=-0.024 未達 | 🟡 Bear/Bull 有效 |
| #H130 | 🔴 模型嚴重過擬合：Train=85.06%, CV=51.31%（-33.7pp gap）| **超參數優化導致反效果**：depth 3→5, reg_alpha 2.0→0.5 使 model memorize training data。需降回保守參數：depth=3, reg_alpha=2.0+，加入 dropout/early stopping | 🔴 需回滾參數 |
| #H133 | 🔴 8/24 features (33%) 為 null/constant（whisper/tone/chorus/hype/oracle/shock/tide/storm）| 佔據 feature space 卻全是常數 0。訓練時變成噪音信號。需從 FEATURE_COLS 移除 | 🟡 P1→P0 |
| #H901 | 🔴 volume/funding_rate/FNG 歷史仍幾乎全 NULL | collect_data.py 已修復 import 但數據回補未完成 | 🟡 等待回補 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈51.3% 距目標 90% 差距 38.7pp | 根本原因：(1) 特徵 IC 低 (2) constant 噪音特徵 (3) regime-mix | 🟡 P1 |
| #H31 | 🟡 polymarket_prob 歷史仍全 NULL（0 筆非空） | Ear/Polymarket 信號完全缺失 | 🟡 P1 |
| #H126 | 🟡 高共線性：Tongue↔Body r=0.78, Aura↔Mind r=0.85 | 違反 8 獨立感官假設 | 🟡 P1 |
| #H127 | 🟡 funding_rate 只有 10 筆有效 | volume/funding_rate/FNG 幾乎全 NULL | 🟡 P1 |
| #H301 | 🟡 Bull regime 僅 2/8 達標（Ear, Aura） | 牛市需新數據源（ETF flows, on-chain）| 🟡 P1 |
| #H131 | 🟡 ic_signs.json NaN 修復後已加入 guard | train.py 已加 constant filter + NaN guard | 🟢 已修復 #H132 |

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
| **#H128-fix** | compare_ic.py 語法錯誤 | 加入 `# ` prefix ✅ | 2026-04-04 06:00 |
| **#H129-fix** | deep_ic_analysis.py 語法錯誤 | 修正括號 ✅ | 2026-04-04 06:00 |
| **#H901-fix** | collect_data.py import 路徑錯誤 | 改為 database.models ✅ | 2026-04-04 05:50 |
| **#H132-fix** | ic_signs.json NaN + ConstantInputWarning | NaN→0.0 + constant filter + NaN guard | 2026-04-04 06:30 |
| **#H134-fix** | run_train.py 硬編碼外部工作區路徑 | 改用 Path(__file__).parent.parent ✅ | 2026-04-03 22:39 |
| **#H135-fix** | model_metrics 表不存在 | 建立 model_metrics 表 ✅ | 2026-04-03 22:39 |
| **#H136-fix** | python3 指向無 pip 的 hermes venv | 改用 /usr/bin/python3.12 並安裝包 ✅ | 2026-04-03 22:39 |

---

## 📊 當前系統健康 (2026-04-03 22:39 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 (24 columns: 8 核心 + 8 null/constant + regimes) | ⚠️ 33% 廢特徵 |
| Labels | 8,766 筆 | ✅ 標籤平衡 (50.8% pos, 49.2% neg) |
| BTC 當前 | $66,874 | ✅ |
| FNG | 9（極度恐慌）| ⚠️ |
| LSR | 1.7412（多頭偏多）| 📊 |
| OI | 90,375 BTC | 📊 |
| Funding Rate | 0.00003285（微正）| 📊 |

### 感官 IC（心跳 #110, N=全量 8770）
| 感官 | IC（全量） | IC（Bear） | IC（Chop） | IC（Bull） | 狀態 |
|------|-----------|-----------|-----------|-----------|------|
| Eye | +0.0221 | +0.0376 | +0.0377 | +0.0232 | ❌ |
| Ear | **-0.0516** | **-0.0884** | -0.0295 | **-0.0507** | ✅ 跨 regime 最強 |
| Nose | -0.0483 | **-0.0601** | -0.0417 | -0.0495 | ❌ 接近 |
| Tongue | +0.0036 | +0.0409 | -0.0270 | -0.0005 | ❌ |
| Body | +0.0102 | +0.0486 | -0.0045 | -0.0116 | ❌ |
| Pulse | +0.0105 | +0.0305 | -0.0266 | +0.0302 | ❌ |
| Aura | -0.0396 | **-0.0521** | -0.0238 | **-0.0673** | ❌ Bear/Bull |
| Mind | -0.0293 | **-0.0572** | -0.0122 | -0.0499 | ❌ Bear |

### Regime-aware 分析
| Regime | 達標感官 | 數量 |
|--------|---------|------|
| Bear | Ear(-0.088), Nose(-0.060), Aura(-0.052), Mind(-0.057) | 4/8 ✅ |
| Chop | (none) | 0/8 ❌ |
| Bull | Ear(-0.051), Aura(-0.067) | 2/8 ❌ |

> **關鍵洞察**: Ear 是唯一跨所有 regime 有預測力的感官（反向指標）。Bear regime 最適合交易。整體 7/8 感官無效。

### 模型狀態
| 項目 | 數值 | 狀態 |
|------|------|------|
| Train Accuracy | 85.06%（過擬合）| 🔴 與 CV 差距 33.7pp |
| CV Accuracy | 51.31% (±0.87%) | ❌ 比上輪 56.3% 更糟 |
| Model | XGBoost v5, depth=5, reg_alpha=0.5 | 🔴 參數過激 |
| ic_signs.json | 有效（NaN guard 已加）| ✅ |
| Sell Win Rate | N/A (0 trades) | ❌ |

### 過擬合分析
- 前輪（保守參數）: Train=52.8%, CV=56.3% → **欠擬合**
- 本輪（積極參數）: Train=85.06%, CV=51.31% → **嚴重過擬合**
- 根本原因：(1) 8 個 constant 特徵注入 33% 噪聲 (2) depth 5 + reg_alpha 0.5 使 model memorize (3) 32 lag features + 4 cross features = 36 總特徵，樣本 8770 不足

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
| P0 | 移除 8 個 null/constant features（whisper/tone/chorus/hype/oracle/shock/tide/storm）| #H133 |
| P0 | 回滾超參數：depth=3, reg_alpha=2.0, reg_lambda=6.0, min_child=10 | #H130 |
| P0 | 實作 regime-aware 預測融合（Bear: Ear+Nose+Aura+Mind）| #H122 |
| P1 | Bull/Chop regime 新數據源（ETF flows, on-chain）| #H301 |
| P1 | 回填 volume/funding_rate/FNG 歷史數據 | #H127 |
| P1 | Aura/Mind 正交化（r=0.85） | #H126 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |

---

## 📋 近期修改記錄

- **#107**: 新增 scripts/heartbeat_ic_analysis.py - SQLite 直接 IC 分析
- **#107**: 新增 scripts/get_live_market_data.py - 即時市場數據收集
- **#107**: 關鍵發現 - Ear 穩定達標（全量 IC=-0.052）
- **#109**: 修復 ic_signs.json NaN + train.py 根因修復
- **#110**: 修復 run_train.py 硬編碼路徑 → 使用 Path(__file__).parent.parent
- **#110**: 建立 model_metrics 表（缺失導致 metrics 查詢失敗）
- **#110**: 修復 python 環境：改用 /usr/bin/python3.12（系統包已安裝）+ 安裝 sqlalchemy xgboost scikit-learn
- **#110**: 重新訓練模型，發現過擬合問題（Train 85% vs CV 51%）
- **#110**: 新增 #H136-fix：環境修復

---

*此文件每次心跳完全覆蓋，保持簡潔。*
