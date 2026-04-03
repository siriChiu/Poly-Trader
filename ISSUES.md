# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。


> *
---

*最後更新：2026-04-04 06:00 GMT+8*
---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H122 | 🔴 全 8 感官 IC 全部 < 0.05（Eye=+0.022, Ear=-0.035, Nose=-0.046, Tongue=-0.016, Body=-0.010, Pulse=-0.002, Aura=-0.042, Mind=-0.026） | 核心問題：特徵在 N≥5000 時全部失效，但 N=1000 時有 4 個>0.05。**IC 隨樣本增加而衰減**，表明特徵是 regime-dependent 而非普遍有效。需要：(1) regime-aware 加權 (2) 新數據源 (3) 交互項特徵 | 🔴 P0 |
| #H125 | 🔴 Aura 二值化問題已修復（v11→v12）但 IC 仍負（-0.042） | Aura v12 從 fr_abs_norm 替換為 price_sma144_deviation，解決了二值化問題（8758 個唯一值），但 IC 為 -0.042，仍<0.05。需要更強的市場極端程度代理 | 🔴 P0 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈56% 距目標 90% 差距仍大 | 需要特徵/模型雙重突破 | 🟡 P1 |
| #H31 | 🟡 歷史 raw data polymarket_prob 幾乎全 NULL（0 筆非空） | Ear/Polymarket 歷史信號缺失 | 🟡 P1 |
| #H126 | 🟡 感官間高共線性：Tongue↔Body r=0.78, Tongue↔Pulse r=0.76, Aura↔Mind r=0.85 | 違反「8 個獨立感官」假設，需要正交化或替換 | 🟡 P1 |
| #H127 | 🟡 funding_rate 只有 10 筆有效（全部 =2.775e-05） | 多列數據缺失：volume/funding_rate/fear_greed/polymarket 幾乎全 NULL | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 仍被舊數據稀釋 | 已改用近期N=5000 | 🟢 P2 觀察中 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | rolling IC 穩定性追蹤 | 建立每次心跳 IC 歷史趨勢記錄 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H118** | 依賴缺失（venv 損壞） | 重建 venv、pip install ✅ | 2026-04-04 04:11 |
| **#H119-fix** | init_db.py 路徑錯誤 | 加入 sys.path 修正 ✅ | 2026-04-04 04:11 |
| **#H120-fix** | comprehensive_test.py 掃描 venv 導致 FAIL | 排除 venv/site-packages ✅ | 2026-04-04 04:11 |
| **#H123-fix** | comprehensive_test.py PROJECT_ROOT 錯誤（parent.parent） | 修正為 parent ✅ | 2026-04-04 05:00 |
| **#H124-fix** | comprehensive_test.py 語法檢查掃描外來目錄 | 加入 EXCLUDE_DIRS ✅ | 2026-04-04 05:00 |
| **#H128-fix** | scripts/compare_ic.py 語法錯誤（第17行缺少 # 註解） | 加入 `# ` prefix ✅ | 2026-04-04 06:00 |
| **#H129-fix** | scripts/deep_ic_analysis.py 語法錯誤（第87行括號不匹配） | 修正 `/ yi == 0) / n0` → `/ n0` ✅ | 2026-04-04 06:00 |
| **#H122-fix** | Aura 二值化（僅2個值）→ 替換為 price_sma144_deviation | feat_aura 從 8758→8743 個唯一值，但 IC=-0.042 仍低 | 2026-04-04 06:00 |

---

## 📊 當前系統健康 (2026-04-04 06:00 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 8,770 筆 | ✅ |
| Features | 8,770 筆 | ✅ |
| Labels | 8,766 筆 | ✅ 標籤平衡 (50.1% pos, 49.9% neg) |
| BTC 當前 | ~$66,832 | ✅ |
| FNG | 9（極度恐慌）| ⚠️ |
| IC 時間戳匹配 | 8,770/8,770 (100%) | ✅ |

### 感官 IC（心跳 #105, N=5000 近期）
| 感官 | IC (N=5000) | 狀態 | 備註 |
|------|-------------|------|------|
| Eye | +0.022 | ❌ | 最接近閾值 |
| Ear | -0.035 | ❌ | 動量反向 |
| Nose | -0.046 | ❌ | RSI 均值回歸，接近閾值 |
| Tongue | -0.016 | ❌ | |
| Body | -0.010 | ❌ | |
| Pulse | -0.002 | ❌ | 幾乎零 |
| Aura | -0.042 | ❌ | 已重設計 v12，仍低 |
| Mind | -0.025 | ❌ | 長期動量反向 |

### 關鍵發現：IC 衰減分析
| N | 通過閾值感官數 |
|---|--------------|
| 500 | 1/8 (Pulse✅) |
| 1000 | 4/8 (Body✅, Pulse✅, Aura✅, Mind✅) |
| 2000 | 2/8 (Pulse✅, Aura✅) |
| 3000 | 1/8 (Aura✅) |
| 5000 | 0/8 |

> ⚠️ **核心問題**：IC 隨樣本增加而衰減，表明特徵在特定市場狀態（regime）下有效，但整體平均無效。

### 共線性問題
| 配對 | 相關係數 | 問題 |
|------|---------|------|
| Tongue × Body | r=+0.78 | 兩者都是波動率相關特徵 |
| Tongue × Pulse | r=+0.76 | 成交量和波動率高度相關 |
| Aura × Mind | r=+0.85 | 價格偏離 SMA 和動量幾乎相同 |

### 數據缺失問題
| 列 | 非空數 | 總數 | 缺失率 |
|---|-------|-----|-------|
| volume | 10 | 8770 | 99.9% |
| funding_rate | 10 | 8770 | 99.9% |
| fear_greed_index | 10 | 8770 | 99.9% |
| polymarket_prob | 0 | 8770 | 100% |
| stablecoin_mcap | 0 | 8770 | 100% |

### 模型性能
| 指標 | 值 |
|------|-----|
| Train Accuracy | 52.75% |
| TimeSeries CV | 56.30% ± 9.06% |
| n_features | 32（8 base + 24 lag）|

### 測試狀態
| 項目 | 狀態 |
|------|------|
| dev_heartbeat.py | ✅ 全 OK (10 dirs, 14 files, 31 py ok) |
| Python 語法 | ⚠️ compare_ic.py 和 deep_ic_analysis.py 已修復 |
| 檔案結構 | ✅ 21/21 必要文件存在 |
| 模組導入 | ❌ sqlalchemy/pandas 缺失（venv 問題）|

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | 引入新數據源：需要 volume/funding_rate/FNG 的完整歷史 | #H127 |
| P0 | 設計 regime-aware IC：分別計算牛市/熊市/震盪期 IC | #H122 |
| P0 | 尋找非共線特徵替換 Tongue/Body/Aura | #H126 |
| P1 | 回填 Polymarket/Volatility 歷史數據 | #H31 |
| P1 | 修復 venv 依賴（sqlalchemy/pandas） | #H127 |
| P2 | IC 動態加權：依近期 IC 調整 sample_weight | #IC4 |

---

## 📋 近期修改記錄

- **Aura v12**: fr_abs_norm → price_sma144_deviation（解決二值化，IC=-0.042）
- **compare_ic.py**: 第17行缺少 # 註解 → 已修復
- **deep_ic_analysis.py**: 第87行語法錯誤 → 已修復
- **IC 分析**: 深層分析揭示 IC 衰減模式、共線性問題、數據缺失

---
*此文件每次心跳完全覆蓋，保持簡潔。*
