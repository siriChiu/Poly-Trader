# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-06 00:25 GMT+8（心跳 #192）*
---

## 📊 當前系統健康狀態（2026-04-06 00:25 GMT+8，心跳 #192）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,956 筆 | ➡️ 持平（+0）|
| Features | 8,921 筆 | ➡️ 持平 |
| Labels | 8,770 筆 | ⬆️ +4 |
| BTC 當前 | $67,136 | ⬆️ +$0 |
| FNG | 11（Extreme Fear）| ➡️ 持平 |
| Funding Rate | 0.000016 | ➡️ 持平 |
| LSR | 1.6525 | ✅ 有數據 |
| Taker | 1.0436 | ✅ 有數據 |
| OI | 90,483 | ✅ 有數據 |
| VIX | 23.90 | ✅ 正常 |
| DXY | 100.19 | ✅ 正常 |
| sell_win (全域) | 0.5076 | ➡️ 持平 |
| 近期 sell_win (last 500) | 0.472 | 🔴 偏離 |
| 近期 sell_win (last 100) | 0.470 | 🔴 偏離 |
| 近期 sell_win (last 50) | 0.360 | 🔴 嚴重偏離 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 3/23，僅 1/8 核心感官** | 🔴 **持續 11+ 輪** | Ear(-0.0516)、RSI14(-0.0536)、BB%p(-0.0523) 全局通過 |
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 8/23、Bull 1/23、Chop 3/23 | 固化 11+ 輪；Bear sell_win=41.7% < 隨機 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，過落差 ~20pp |
| #H342 | 🚨 **近期 sell_win 偏離至 47%** | 🔴 **惡化中** | last 500=0.472, last 100=0.470, last 50=0.360 |
| #H353 | 🚨 **數據收集停滯** | 🔴 **持續** | +0 raw entries 自 #191；排程器仍未運行 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 ~52% |
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=+0.0036，全域最弱（非 placeholder）|
| #H351 | 🟡 **Bear sell_win 41.7% 低於隨機** | 熊市實際勝率僅 41.7%（n=2,897）|
| #H370 | 🟡 **8 個 placeholder 特徵全部 NULL** | whisper/tone/chorus/hype/oracle/shock/tide/storm 全 null（151 null 外的 unique=1）|
| #H371 | 🟡 **Ear 命名 mismatch** | preprocessor 寫 `feat_ear_zscore` → DB column `feat_ear` |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |
| #H350 | 🟢 NaN regime 回填 | ✅ 已修復（#188）|
| #H352 | 🟢 VIX collector 整合 | ✅ 已修復（#190），VIX=23.90 正常 |

---

## 感官 IC 掃描（心跳 #192, 2026-04-06 00:25 GMT+8）

### 全域 IC against sell_win（N=8,770，含 TI 特徵共 23 項）
| 感官/特徵 | IC | std | 狀態 |
|-----------|------|------|------|
| **Ear** | -0.0516 | 0.0221 | ✅ PASS |
| **RSI14** | -0.0536 | 0.1198 | ✅ PASS |
| **BB%p** | -0.0523 | 0.3344 | ✅ PASS |
| Nose | -0.0483 | 0.1658 | ❌ 近線 |
| MACD_hist | -0.0465 | 0.0016 | ❌ 近線 |
| Body | -0.0450 | 0.3325 | ❌ 近線 |
| Aura | -0.0396 | 0.0289 | ❌ |
| VIX | -0.0339 | 5.0419 | ❌ |
| ATR_pct | +0.0313 | 0.0009 | ❌ |
| Mind | -0.0293 | 0.0499 | ❌ |
| Eye | +0.0221 | 0.5176 | ❌ |
| DXY | -0.0184 | 11.1102 | ❌ |
| Pulse | +0.0105 | 0.2461 | ❌ |
| Tongue | +0.0036 | 0.3690 | ❌ |
| VWAP_dev | +0.0005 | 0.2036 | ❌ |
| *whisper/tone/chorus/hype/oracle/shock/tide/storm* | *null/unique=1* | 0 | ❌ **DEAD** |

**全域達標：3/23（Ear, RSI14, BB%p）— 核心 8 感官僅 1/8 通過**

### Regime IC（23 特徵含 TI + placeholder）
| Regime | 達標數 | 通過特徵 | sell_win |
|--------|--------|---------|----------|
| **Bear** | **8/23** | Eye(+0.056), Nose(-0.061), Pulse(+0.061), Aura(-0.072), Mind(-0.063), RSI14(-0.057), MACD(-0.061), ATR(+0.070) | **0.417** 🔴 |
| **Bull** | **1/23** | Ear(-0.065) | **0.606** ✅ |
| **Chop** | **3/23** | Pulse(-0.056), RSI14(-0.056), BB%p(-0.060) | **0.503** ~ |

### 🔑 關鍵發現
- **全域 3/23 通過** — 16/23 特徵完全無效（含 8 個 placeholder + 8 個 IC<0.05 實特徵）
- **Regime 分化持續固化**：Bear 8/23、Bull 1/23、Chop 3/23
- **8 個 placeholder 特徵**（whisper/tone/chorus/hype/oracle/shock/tide/storm）全為 NULL/unique=1/stdev=0
- **Bear sell_win=41.7%** — 模型在熊市預測錯誤率 58.3%（反向準確 58.3%）
- **近期 sell_win 急降至 36%(50)** — 短窗口表現惡化
- **測試套件 6/6 全部通過** — 系統穩定性良好

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (含 TI 特徵) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | ~52%（確定性天花板）|
| Overfit gap | ~20pp |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,956 / Features 8,921 / Labels 8,770（labels +4 自 #191）
- 全域 IC 3/23 通過（Ear, RSI14, BB%p），核心 8 感官僅 1/8
- Regime IC：Bear 8/23 ✅, Bull 1/23 🔴, Chop 3/23
- CV 52% — 確定性天花板持續 11+ 輪
- sell_win 全域 50.8%，近期(500) 47.2%，(100) 47.0%，(50) 36.0%
- BTC $67,136 | FNG 11 (Extreme Fear) | VIX 23.90 | DXY 100.19
- Derivatives：LSR=1.65, Taker=1.04, OI=90,483 — 首次收集到完整衍生品數據
- 測試 6/6 全部通過
- 8 個 placeholder 特徵完全無效（+1 feat_storm 自心跳 #191 的 7 個）

### 黑帽（風險）
1. **20/23 特徵未通過 IC 閾值** — 特徵空間大量低價值信號
2. **Bull regime 僅 1/23 通過** — 牛市幾乎完全無法預測
3. **近期 sell_win 36% (50)** — 短窗口表現急劇惡化
4. **8 個 placeholder 特徵浪費維度** — 新增 feat_storm 同樣為 null
5. **數據收集停頓** — 排程器未運行，系統依賴手動心跳
6. **CV 52% 天花板 11+ 輪無突破** — 特徵共線性、信號天花板、非穩定市場
7. **Bear sell_win=41.7%** — 模型在熊市完全反向預測

### 黃帽（價值）
1. **Bear 8/23 穩定通過** — 熊市仍有 8 個有效特徵
2. **TI 特徵持續有價值** — RSI14(-0.0536)、BB%p(-0.0523) 穩定通過
3. **衍生品數據首次完整收集** — LSR=1.65, Taker=1.04, OI=90,483
4. **測試 6/6 全部通過** — 系統穩定性良好
5. **Bull sell_win=60.6%** — 牛市勝率高於隨機，方向正確

### 綠帽（創新）
1. **反向信号策略** — sell_win 36-47% → 反向操作 53-64% 勝率
2. **Bull-only 交易策略** — Bull regime sell_win=60.6% 為最佳 regime
3. **清除 8 個 placeholder 特徵** — 減少 8 維噪音
4. **Bear 融合 IC 組合** — Aura, Mind, MACD, Nose, Pulse 等 8 特徵融合
5. **近期窗口 IC 追蹤** — N=50 急降至 36% 為早期警告信號

### 藍帽（決策）
1. 🔴 P0：**全域 IC 天花板突破** — 需外部 non-price alpha 或反向策略
2. 🔴 P0：**重啟數據收集服務** — 排程器必須恢復（#H353）
3. 🟡 P1：**清除 8 個 placeholder 特徵** — 減少維度（#H370）
4. 🟡 P1：**Bull-biased 策略** — Bull regime 勝率 60.6% 為目前最佳（替代反向策略）
5. 🟡 P1：**short-window IC monitoring** — N=50 36% 為預警信號，需納入自動觸發
6. 🟢 P2：**衍生品特徵工程** — LSR/Taker/OI 首次收集，尚未用作特徵

---

## ORID 決策
- **O**: 全域 3/23 通過（Ear, RSI14, BB%p），Regime Bear 8/23/Bull 1/23/Chop 3/23，CV ~52%，sell_win 50.8%/47.2%/47.0%/36.0%（50），BTC $67,136，6/6 tests
- **R**: Bear 表現最佳但實際 sell_win=41.7%，Bull 賣出勝率 60.6% 為最優 regime，近期 50-sell_win 急降至 36% 為警報
- **I**: 特徵空間已接近極限。23 維中 20 維無效。需要：(1) 外部 non-price alpha (2) Bull-only 交易或反向策略 (3) 清除 8 個死特徵 (4) 恢復自動數據流 (5) 衍生品特徵工程
- **D**: (1) 🔴 重啟數據收集 (2) 🔴 尋找外部 alpha (3) 🟡 清除 placeholder (4) 🟡 Bull-only 策略原型 (5) 🟡 N=50 預警系統 (6) 🟢 衍生品特徵化

---

## 📋 本輪修改記錄

- **#192**: ✅ 運行 dev_heartbeat.py — Raw=8,956, Features=8,921, Labels=8,770。+4 labels 自 #191（+0 raw 停滯）。
- **#192**: ✅ 完整 IC 分析 23 特徵含 TI + placeholder — 全域 3/23 通過（Ear, RSI14, BB%p）。
- **#192**: ✅ Regime IC 完整 23 特徵 — Bear 8/23, Bull 1/23, Chop 3/23。
- **#192**: ✅ Bear sell_win=41.7%, Bull=60.6%, Chop=50.3% 首次精確報告。
- **#192**: ✅ 首次收集完整衍生品數據 — LSR=1.65, Taker=1.04, OI=90,483。
- **#192**: ✅ sell_win last 50=0.36 為新低，預警信號觸發。
- **#192**: ✅ 確認 8 個 placeholder 特徵全 null（whisper/tone/chorus/hype/oracle/shock/tide/storm）。
- **#192**: ✅ 測試套件 6/6 全部通過。
- **#192**: ⏸️ 未修改代碼 — placeholder 特徵清除需跨 4 文件修改（models.py, predictor.py, engine.py, feature_engine），風險控制。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **全域 IC 天花板突破** — 11+ 輪無改善，需外部 alpha 或反向策略 | #H304 |
| 🔴 P0 | **重啟數據收集服務** — 排程器未運行，+0 raw 自 #191 | #H353 |
| 🟡 P1 | **清除 8 個 placeholder 特徵** — whisper/tone/chorus/hype/oracle/shock/tide/storm | #H370 |
| 🟡 P1 | **Bull-only 策略原型** — Bull sell_win=60.6% 為最佳 | #H342 |
| 🟡 P1 | **N=50 預警系統** — 36% sell_win 需自動觸發檢查 | #H342 |
| 🟢 P2 | **衍生品特徵工程** — LSR/Taker/OI 尚未用作特徵 | #H372 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
