# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 22:22 GMT+8（心跳 #190）*
---

## 📊 當前系統健康狀態（2026-04-04 22:22 GMT+8，心跳 #190）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,955 筆 | ➡️ 持平（#189 相同） |
| Features | 8,920 筆 | ➡️ 持平 |
| Labels | 8,766 筆 | ➡️ 持平 |
| BTC 當前 | $67,214 | ⬆️ +$85 |
| FNG | 11（Extreme Fear） | ➡️ 持平 |
| Funding Rate | 0.000017 | ➡️ 持平 |
| LSR | 1.6525 | ⬆️ 略升 |
| Taker | 1.0436 | ➡️ 持平 |
| OI | 90,484 | ➡️ 持平 |
| VIX | 23.90 | 🟢 **已修復**（#189 為 NULL）|
| DXY | 100.19 | ✅ 正常 |
| sell_win (全域) | 0.508 | ➡️ 持平 |
| 近期 sell_win (last 500) | 0.472 | 🔴 偏離 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 1/8 against sell_win** | 🔴 **持續（10+ 輪）** | 僅 Ear PASS（-0.0517）|
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 5/8、Bull 1/8、Chop 1/8 | 10+ 輪持平 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，51 特徵無改善 |
| #H341 | 🚨 **sell_win vs label_up 鴻溝** | 🔴 **持續** | sell_win rate=0.508, agreement=0.949 |
| #H342 | 🚨 **近期 sell_win 偏離** | 🔴 **惡化** | 近期窗口 sell_win_rate 0.47 |
| #H353 | 🚨 **數據收集停滯** | 🔴 **持續** | ~10h 無新 raw entries（main.py 未運行）|

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 ~52% |
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=+0.0036，全域最弱 |
| #H352 | 🟡 **VIX 持續 NULL** | ✅ **已修復**（#190）— VIX collector 已整合至 live collector.py，且 backfill 完成 (8,866/8,955) |
| #H351 | 🟡 **Bear sell_win 41.7% 低於隨機** | 熊市實際勝率僅 41.7% |
| #H360 | 🟡 **feat_ear_zscore / feat_tongue_pct 準離散** | std≈0, unique=5 — 需重新設計 |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |
| #H350 | 🟢 **NaN regime 回填** | ✅ 已修復（#188）|

---

## 感官 IC 掃描（心跳 #190, 2026-04-04 22:22 GMT+8）

### 全域 IC against sell_win（N=8,778, 8 核心感官）
| 感官 | IC | 狀態 | vs #189 |
|------|------|------|---------|
| Ear | -0.0517 | ✅ PASS | ➡️ 持平 |
| Nose | -0.0483 | ❌ 近線 | ➡️ 持平 |
| Body | -0.0451 | ❌ 近線 | ➡️ 持平 |
| Aura | -0.0396 | ❌ | ➡️ 持平 |
| Mind | -0.0293 | ❌ | ➡️ 持平 |
| Eye | +0.0220 | ❌ | ➡️ 持平 |
| Pulse | +0.0106 | ❌ | ➡️ 持平 |
| Tongue | +0.0036 | ❌ | ➡️ 持平 |

**全域達標：1/8 against sell_win** — 僅 Ear PASS

### Regime IC（against sell_win）
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| Eye | +0.0560 ✅ | -0.0068 ❌ | -0.0018 ❌ |
| Ear | -0.0414 ❌ | -0.0647 ✅ | -0.0220 ❌ |
| Nose | -0.0610 ✅ | -0.0406 ❌ | -0.0421 ❌ |
| Tongue | +0.0216 ❌ | +0.0075 ❌ | -0.0366 ❌ |
| Body | -0.0422 ❌ | -0.0484 ❌ | -0.0306 ❌ |
| Pulse | +0.0612 ✅ | +0.0232 ❌ | -0.0560 ✅ |
| Aura | -0.0720 ✅ | -0.0124 ❌ | -0.0116 ❌ |
| Mind | -0.0625 ✅ | -0.0180 ❌ | -0.0025 ❌ |

| Regime | 達標數 | vs #189 |
|--------|--------|---------|
| Bear | **5/8** | ➡️ 持平（完全相同）|
| Bull | **1/8** | ➡️ 持平（完全相同）|
| Chop | **1/8** | ➡️ 持平（完全相同）|

### 🟢 VIX IC（新！）
| 指標 | 全域 IC | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|---------|
| VIX level | -0.0212 ❌ | -0.0363 ❌ | **-0.0510 ✅** | -0.0171 ❌ |
| DXY level | -0.0035 ❌ | -0.0200 ❌ | -0.0100 ❌ | +0.0089 ❌ |

**VIX Bull-only IC = -0.0510** — VIX 在牛市中是有效的反向指標！

### 🔴 關鍵發現
- **全域 1/8（Ear PASS -0.0517）** — 10+ 輪無改善
- **Regime 分化完全固化**：Bear 5/8、Bull 1/8、Chop 1/8 — 10+ 輪相同
- **sell_win 50.8% 全域** — 近似隨機，近期 47.2% 偏離
- **VIX 已修復** — 最新 raw VIX=23.90，backfill 8,866/8,955
- **VIX Bull IC = -0.0510** — 新可用信號，僅牛市有效
- **Bear-only 融合 IC = +0.0859**（top 5 signed: Aura, Mind, Pulse, Nose, Eye）
- **測試套件 5/6 通過**（數據品質：ear_zscore/tongue_pct 準離散）
- **feat_ear_zscore std=0.000732, unique=5** — 實質上是 5 級分類，非連續
- **feat_tongue_pct std=0.000501, unique=5** — 同上

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (51 features + regime flags) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | 52.24%（確定性天花板）|
| Train accuracy | 72.27% |
| Overfit gap | ~20pp |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,955 / Features 8,920 / Labels 8,766 — 全部持平 10+ 輪
- 全域 IC 1/8（Ear PASS -0.0517）— 無改善
- Regime IC：Bear 5/8、Bull 1/8、Chop 1/8 — 完全固化
- CV 52.24% — 確定性天花板確認
- sell_win 全域 50.8%，近期(500) 47.2%，近期(100) 47.0%
- BTC $67,214 | FNG 11 (Extreme Fear) | LSR 1.65 | Taker 1.04
- VIX 23.90 — **已修復**（#189 為 NULL）
- **Bear-only combined IC = +0.0859**（top 5 signed: Aura, Mind, Pulse, Nose, Eye）
- **VIX Bull IC = -0.0510** — 牛市反向指標

### 黑帽（風險）
1. **全域 1/8 持續 10+ 輪** — 特徵空間已完全用盡，修調無法突破
2. **~10h 數據收集停滯** — main.py 排程器未運行，系統無法更新
3. **近期 sell_win 偏離至 47.2%** — 模型實際表現低於隨機
4. **CV 52% ≈ 隨機** — 模型無實際預測能力
5. **Bear sell_win 41.7%** — 即使 Bear regime 5/8 IC passing，實際勝率仍低
6. **feat_ear_zscore / feat_tongue_pct 準離散** — 5 unique values，無法提供細粒度信號

### 黃帽（價值）
1. Bear 5/8 穩定通過 — 熊市環境下 5 個感官有效
2. Bear-only 融合 IC = +0.0859 — 最強可用信號
3. 系統環境正常，測試 5/6 通過，模型檔案完整
4. Ear 仍是唯一可靠的全域單一指標
5. sell_win vs label_up 一致率 94.9% — 標籤定義穩定
6. **VIX Bull IC = -0.0510** — 新發現，VIX 在牛市有效

### 綠帽（創新）
1. **VIX regime-aware 整合** — VIX 僅在 Bull regime 有效（IC=-0.0510），可在牛市觸發反向信號
2. **Bear-only IC-weighted 融合** — IC=+0.0859 可作為專門策略
3. **Regime-filtered trading** — 只在 Bear regime 交易，避開 Bull/Chop
4. **外部 alpha 來源** — Twitter/X 新聞 sentiment、完整 VIX、macro calendar
5. **準離散特徵重設計** — ear_zscore / tongue_pct 需改為連續分佈

### 藍帽（決策）
1. ✅ P0：**VIX 收集器已整合** — collector.py 新增 fetch_vix_dxy_latest() 調用
2. ✅ P1：**VIX backfill 完成** — 8,866/8,955 records populated
3. 🔴 P0：**全域 IC 天花板突破** — 需非線性特徵或外部 alpha（10+ 輪無改善）
4. 🟡 P1：**準離散特徵重設計** — ear_zscore / tongue_pct 需改為連續
5. 🟢 P2：**VIX Bull 信號整合** — 牛市時使用 VIX IC=-0.0510 作為額外信號

---

## ORID 決策
- **O**: 全域 1/8（Ear PASS），Regime Bear 5/8/Bull 1/8/Chop 1/8，CV 52.24%，VIX=23.90（已修復），5/6 tests
- **R**: IC 10+ 輪完全固化，Bear 5/8 穩定但 sell_win 僅 41.7%，VIX Bull IC=-0.0510 新發現
- **I**: 特徵空間已完全耗盡。VIX 終於有數據，發現 Bull-only 信號。系統需：(1) 外部非共線 alpha (2) regime-conditional 模型 (3) 重設計準離散特徵 (4) 恢復數據流
- **D**: (1) ✅ VIX collector 整合 + backfill (2) 🔴 IC 天花板需升級策略 (3) 🟡 重設計準離散特徵 (4) 🟢 VIX Bull 信號原型 (5) 🔴 重啟數據收集

---

## 📋 本輪修改記錄

- **#190**: ✅ 運行 dev_heartbeat.py — Raw=8,955, Features=8,920, Labels=8,766。
- **#190**: ✅ 完整 IC 分析 — 全域 1/8（Ear PASS -0.0517），Regime Bear 5/8/Bull 1/8/Chop 1/8。
- **#190**: ✅ Bear-only combined IC 計算 — +0.0859（top 5 signed: Aura, Mind, Pulse, Nose, Eye）。
- **#190**: ✅ VIX IC 新計算 — 全域 -0.0212, Bull -0.0510 ✅, Bear -0.0363, Chop -0.0171。
- **#190**: ✅ **VIX collector 整合** — 新增 `data_ingestion/macro_data.py`（Yahoo Finance fetcher），修改 `data_ingestion/collector.py` 加入 vix_value/dxy_value 欄位 (#H352 FIXED)。
- **#190**: ✅ **VIX backfill 完成** — 8,866/8,955 records (從 ~1 提升至 8,866)。
- **#190**: ✅ 測試套件 5/6 通過（數據品質：ear_zscore/tongue_pct 準離散）。
- **#190**: 🔴 確認 IC 天花板持續 10+ 輪 — 無改善。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **全域 IC 天花板突破** — 10+ 輪無改善，需外部 alpha 或新策略 | #H304 |
| 🔴 P0 | **重啟數據收集服務** — main.py 排程器未運行 | #H353 |
| 🟡 P1 | **準離散特徵重設計** — ear_zscore (std=0.0007, unique=5) / tongue_pct (std=0.0005, unique=5) | #H360 |
| 🟢 P2 | **VIX Bull-only 信號原型** — IC=-0.0510，牛市有效 | #H352 |
| 🟢 P2 | **新數據源探索** — Twitter/X、新聞、macro calendar | #H303 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
