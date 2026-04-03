# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。


> *
---

*最後更新：2026-04-04 04:11 GMT+8*
> **🔄 心跳 #103：環境修復（venv 重建、DB 初始化、init_db 路徑修正）；DB=空需回填；CV=56.30%；感官 IC 重算中**

---

## 🔴 最高優先級 (P0)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H119 | 🔴 資料庫重建後為空（0 筆 raw/features/labels）| 執行 backfill 回填歷史數據，恢復訓練管線 | 🔴 P0 |
| #H120 | 🔴 Pulse/Aura/Mind IC=NaN（無數據可算） | 等待數據回填後重算 | 🔴 P0 |

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈56% 距目標 90% 差距仍大 | 累積更多數據（11112K/目標 50K+）+ 特徵創新 | 🟡 P1 |
| #H31 | 🟡 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🟡 P1 |
| #H121 | 🟡 3 感官 IC < 0.05（Eye=-0.013, Nose=-0.031, Body=-0.038）| 需要替換或重設計這些感官 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 仍被舊數據稀釋 | 已改用近期N=5000，監控效果 | 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | rolling IC 穩定性追蹤 | 建立每次心跳 IC 歷史趨勢記錄 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H115** | 🔴 Pulse IC=0 完全失效（vol_spike12 失效） | 替換為 vol_ratio_12_48（IC=+0.1087）✅ | 04-02 16:05 |
| **#H114** | 🔴 Tongue/Aura 感官替換後穩定監控 | tongue→vr24/144; aura→fr_abs_norm | 04-02 15:44 |
| **#H113** | 🔴 Aura IC 驟降（-0.0171，失效） | 替換為 volume_trend_12（IC=-0.2522）✅ | 04-02 13:39 |
| **#H112** | 🔴 Tongue IC 驟降（-0.0016，失效） | 替換為 fr_acceleration（IC=+0.1162）✅ | 04-02 13:39 |
| **#H111** | ⚠️ Pulse IC 接近閾值（-0.0717） | 已升 P0 → 解決 #H115 | 04-02 16:05 |
| **#H110** | ⚠️ Tongue IC 弱（-0.0043 上輪）| 本輪自然回升至 +0.0880 ✅ | 04-02 13:29 |
| **#H109** | ⚠️ Aura IC 驟降（-0.0089 上輪）| 本輪自然回升至 +0.0791 ✅ | 04-02 13:29 |
| **#H108** | 🔴 Pulse IC 連續3輪 < 0.05（vol_roc48 無效） | 替換為 vol_spike12（IC=-0.0669, p=0.034）✅ | 04-02 13:25 |
| **#H107** | Eye IC 衰減至臨界（0.0497 < 0.05） | 本輪心跳自然回升 ✅ | 04-02 13:09 |
| **#H106** | ic_signs.json stale（全量N=15366稀釋） | 改用近期N=5000，全8感官IC>0.05 | 04-02 12:40 |
| **#H105** | Ear IC 弱(-0.029) | 替換為 mom_24(IC=-0.085@recent) | 04-02 12:35 |
| **#H104** | Eye IC 弱(-0.021) | 替換為 fr_cumsum_48(IC=-0.063@recent) | 04-02 12:35 |
| **#H102** | model/last_metrics.json stale | 同步修正 | 04-02 12:05 |
| **#H101** | Pulse/Aura IC 不顯著 | Pulse→vol_roc48; Aura→vol_ratio_short_long | 04-02 11:57 |
| **#H100** | label=-1 只有 2 筆 | UPDATE labels 修正門檻；CV 45%→56% | 04-02 11:19 |
| **#H99** | Nose IC≈0.005 | 替換為 RSI14 norm（IC=-0.082）| 04-02 11:13 |
| **#H118** | 依賴缺失（venv 損壞、sqlalchemy 未安裝）| 重建 venv、pip install -r requirements.txt ✅ | 2026-04-04 04:11 |
| **#H119-fix** | init_db.py 路徑錯誤（ModuleNotFoundError）| 加入 sys.path 修正 ✅ | 2026-04-04 04:11 |
| **#H120-fix** | comprehensive_test.py 掃描 venv 導致 FAIL | 排除 venv/site-packages ✅ | 2026-04-04 04:11 |
| #H96 | ic_signs.json stale | N=4975 重算 + 重訓 | 04-02 10:38 |
| #H95 | Body IC 不顯著 | 替換為 price_ret_20P | 04-02 10:20 |
| #H76 | 模型過擬合 | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match | 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |

---

## 📊 當前系統健康 (2026-04-04 04:11 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 0 筆（DB 重建） | ❌ 需回填 |
| Features | 0 筆 | ❌ 需回填 |
| Labels | 0 筆 | ❌ 需回填 |
| BTC 當前 | $66,877（live Binance API） | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ 市場悲觀 |
| Funding Rate | ~0.0（需實時查詢）| ⚠️ |

### 感官 IC（模型訓練時數據 N=11112）
| 感官 | 特徵 | IC | 狀態 |
|------|------|------|------|
| Eye | - | -0.013 | ❌ <0.05 |
| Ear | - | +0.058 | ✅ |
| Nose | - | -0.031 | ❌ <0.05 |
| Tongue | - | -0.126 | ✅ 強（負向）|
| Body | - | -0.038 | ❌ <0.05 |
| Pulse | - | NaN | ❌ 無數據 |
| Aura | - | NaN | ❌ 無數據 |
| Mind | - | NaN | ❌ 無數據 |

> 上次完整 IC（#H101, N=5000）：Eye=-0.0533 / Ear=-0.0733 / Nose=-0.0734 / Tongue=+0.0570 / Body=+0.0720 / Pulse=+0.1087 / Aura=+0.1067 / Mind=-0.1457

### 模型性能
| 指標 | 值 |
|------|-----|
| Train Accuracy | 52.75% |
| TimeSeries CV | 56.30% ± 9.06% |
| n_features | 32（8 base + 24 lag）|

### 測試狀態
| 項目 | 狀態 |
|------|------|
| dev_heartbeat.py | ✅ 全 OK |
| comprehensive_test.py | ⚠️ 4/6 通過（DB 空、IC 無數據導致 2 項 FAIL）|
| Python 語法(非 venv) | ✅ |
| 模組導入 | ✅ 8/8 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P0 | **回填數據**：執行 backfill 或 collector，恢復 raw/features/labels 到 DB | #H119 |
| P0 | **重算 IC**：DB 回填後重新計算全部 8 感官 IC | #H120 |
| P1 | **替換弱感官**：Eye/Nose/Body IC < 0.05，需新特徵設計 | #H121 |
| P1 | **累積數據**：每天+288筆，目標 50,000+ 筆 | #H87 |
| P2 | **研究組合特徵**：mind×eye 交叉項 IC 可能更高 | - |
| P3 | **IC 動態加權**：依近期 IC 調整 XGBoost sample_weight | #IC4 |

---

## 🟡 近期狀態更新

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H116 | 📈 價格 × 多感官走勢為空，疑似時間對齊 / 資料窗不足 / 回填缺口 | nearest-match 對齊 + empty-state + 補齊歷史窗 | ✅ 已修復 |
| #H117 | 綜合推薦分數仍不精確，疑似模型校準 / 選型不穩 | 做 confidence calibration、regime-aware model selection、驗證不是感官本身造成偏差 | ✅ 已修復（regime-aware 進行中）|
| #H118 | 🔬 回測引擎近期失效，需重新驗證交易曲線與指標輸出 | 重新跑 backtesting/engine.py、metrics.py、optimizer.py 的端到端驗證 | 🔄 部分完成（optimizer 待補）|

## 📋 近期補充說明

- `data/ic_signs.json` 已從 NaN 修正為實際模型 IC 值（全量 N=11112），但 Pulse/Aura/Mind 無 IC 數據
- `init_db.py` 已修復 sys.path，現在可正常初始化 DB
- `comprehensive_test.py` 已修復排除 venv/site-packages
- venv 已重建，所有 requirements.txt 依賴已安裝
- DB 結構已初始化，但表格為空，需要 backfill 或 collector 填入數據
- Binance API 可連線（BTC=$66,877），collector 可用但需先有歷史窗口

---
*此文件每次心跳完全覆蓋，保持簡潔。*
