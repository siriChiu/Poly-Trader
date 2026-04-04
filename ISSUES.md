# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 00:10 GMT+8（心跳 #193）*
---

## 📊 當前系統健康狀態（2026-04-05 00:10 GMT+8，心跳 #193）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,956 筆 | 🔴 +0（停滯 2+ 輪）|
| Features | 8,921 筆 | ➡️ 持平 |
| Labels | 8,766 筆 | ⬇️ -4（重新計數確認）|
| BTC 當前 | $67,343 | ⬆️ +$207 |
| Price Change | +0.77% | ⬆️ 回升中 |
| FNG | 11（Extreme Fear）| ➡️ 持平（極端恐懼）|
| Funding Rate | 0.000016 | ➡️ 持平 |
| LSR | 1.6076 | ✅ 有數據 |
| Taker | 1.6076 | ⬆️ 買盤優勢 |
| OI | 91,731 | ⬆️ +1,248 |
| VIX | 23.90 | ✅ 正常 |
| DXY | 100.19 | ✅ 正常 |
| sell_win (全域) | 0.5076 | ➡️ 持平 |
| 近期 sell_win (last 500) | 0.472 | 🔴 偏離 |
| 近期 sell_win (last 100) | 0.470 | 🔴 偏離 |
| 近期 sell_win (last 50) | 0.360 | 🔴 嚴重偏離 |
| Bear sell_win | 0.417 | 🔴 反向預測 |
| Bull sell_win | 0.606 | ✅ 最佳 regime |
| Chop sell_win | 0.503 | ➡️ 隨機 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 3/23，僅 1/8 核心感官** | 🔴 **持續 11+ 輪** | Ear(-0.052), RSI14(-0.054), BB%p(-0.052) 全局通過 |
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 8/23、Bull 1/23、Chop 3/23 | 固化 11+ 輪；Bear sell_win=41.7% < 隨機 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，過落差 ~20pp |
| #H342 | 🚨 **近期 sell_win 偏離至 47%** | 🔴 **惡化中** | last 500=0.472, last 100=0.470, last 50=0.360 |
| #H353 | 🔴 **數據收集停滯 →✅ 已部分修復** | 🟡 **改善中** | 安裝 apscheduler，main.py 排程器已啟動（PID 399202），待驗證 5min 數據入庫 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 ~52% |
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=+0.0036，全域最弱（非 placeholder）|
| #H351 | 🟡 **Bear sell_win 41.7% 低於隨機** | 熊市實際勝率僅 41.7%（n=2,897）|
| #H370 | 🟡 **8 個 placeholder 特徵全部 NULL** | whisper/tone/chorus/hype/oracle/shock/tide/storm 全 null（151 null 外的 unique=1）|
| #H371 | 🟡 **Ear 命名 mismatch** | preprocessor 寫 `feat_ear` → alias `feat_ear_zscore` 已補，server routes 仍用 `feat_ear_zscore` |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |
| #H350 | 🟢 NaN regime 回填 | ✅ 已修復（#188）|
| #H352 | 🟢 VIX collector 整合 | ✅ 已修復（#190），VIX=23.90 正常 |

---

## 感官 IC 掃描（心跳 #193, 2026-04-05 00:10 GMT+8）

### 全域 IC against sell_win（N=8,766，含 TI 特徵共 23 項）
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
| **Bear** | **8/23** | ATR(+0.07), Aura(-0.07), Eye(+0.06), MACD(-0.06), Mind(-0.06), Nose(-0.06), Pulse(+0.06), RSI14(-0.06) | **0.417** 🔴 |
| **Bull** | **1/23** | Ear(-0.065) | **0.606** ✅ |
| **Chop** | **3/23** | BB%p(-0.060), Pulse(-0.056), RSI14(-0.056) | **0.503** ~ |

### 🔑 關鍵發現
- **全域 3/23 通過** — 20/23 特徵完全無效（含 8 個 placeholder + 12 個 IC<0.05 實特徵）
- **Regime 分化持續固化**：Bear 8/23、Bull 1/23、Chop 3/23（與 #192 相同）
- **8 個 placeholder 特徵**（whisper/tone/chorus/hype/oracle/shock/tide/storm）全為 NULL/unique=1/stdev=0
- **Bear sell_win=41.7%** — 模型在熊市預測錯誤率 58.3%（反向準確 58.3%）
- **Bull sell_win=60.6%** — 最佳 regime，唯一高於隨機
- **近期 sell_win 急降至 36%(50)** — 短窗口表現惡化
- **BTC +0.77%** — 價格溫和回升，但 FNG 仍在極端恐懼 11
- **排程器已啟動** — apscheduler 安裝完成，main.py 背景運行（PID 399202）
- **測試套件 6/6 全部通過** — 系統穩定性良好

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (含 TI 特徵) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | ~52%（確定性天花板，11+ 輪無突破）|
| Overfit gap | ~20pp |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,956 / Features 8,921 / Labels 8,766（labels 持平，重新計數確認）
- 全域 IC 3/23 通過（Ear, RSI14, BB%p），核心 8 感官僅 1/8
- Regime IC：Bear 8/23 ✅, Bull 1/23 🔴, Chop 3/23
- CV 52% — 確定性天花板持續 11+ 輪
- sell_win 全域 50.8%，近期(500) 47.2%，(100) 47.0%，(50) 36.0%
- Bear 41.7%, Bull 60.6%, Chop 50.3% — 熊市模型完全反向
- BTC $67,343(+0.77%) | FNG 11 (Extreme Fear) | VIX 23.90 | DXY 100.19
- Derivatives：LSR=1.61, Taker=1.61, OI=91,731 — 買盤持續優勢
- 排程器：apscheduler 安裝 ✅，main.py 啟動 ✅（PID 399202）
- 測試 6/6 全部通過

### 黑帽（風險）
1. **20/23 特徵未通過 IC 閾值** — 特徵空間大量低價值信號，11+ 輪無改善
2. **Bull regime 僅 1/23 通過** — 牛市幾乎完全無法預測
3. **近期 sell_win 36% (50)** — 短窗口表現急劇惡化
4. **8 個 placeholder 特徵浪費維度** — 新增 feat_storm 同樣為 null
5. **數據收集剛修復** — 排程器剛啟動，需等待 5+ 分鐘驗證數據入庫
6. **CV 52% 天花板 11+ 輪無突破** — 特徵共線性、信號天花板、非穩定市場
7. **Bear sell_win=41.7%** — 模型在熊市完全反向預測，實際是反向指標

### 黃帽（價值）
1. **Bear 8/23 穩定通過** — 熊市仍有 8 個有效特徵（反向策略基礎）
2. **TI 特徵持續有價值** — RSI14(-0.0536)、BB%p(-0.0523)、MACD_hist(-0.0465) 穩定
3. **Bull sell_win=60.6%** — 牛市勝率 60.6% 為目前最佳 regime
4. **排程器已修復** — apscheduler 安裝，main.py 背景運行中
5. **測試 6/6 全部通過** — 系統穩定性良好
6. **衍生品數據持續收集** — LSR/TSR/OI 完整

### 綠帽（創新）
1. **Bear 反向策略** — sell_win 41.7% → 反向操作 58.3% 勝率（8 個有效特徵）
2. **Bull-only 交易策略** — Bull regime sell_win=60.6% + regime-aware selection
3. **清除 8 個 placeholder 特徵** — 減少 8 維噪音，可能提升 CV
4. **混合策略** — Bull regime 正向 + Bear regime 反向 + Chop 觀望
5. **Neural regime-aware model** — 考慮用神經網絡取代 XGBoost 的 regime selection
6. **External alpha sources** — Polymarket、Twitter/X、新聞情緒尚未真正利用

### 藍帽（決策）
1. 🔴 P0：**驗證排程器數據收集** — 5min 後檢查 raw 是否增長
2. 🔴 P0：**全域 IC 天花板突破** — 11+ 輪無改善，需外部 alpha 或反向策略
3. 🟡 P1：**清除 8 個 placeholder 特徵** — 減少 8 維噪音（#H370）
4. 🟡 P1：**Bear 反向 + Bull 正向混合策略原型**
5. 🟡 P1：**N=50 預警系統** — 36% sell_win 需自動觸發檢查
6. 🟡 P1：**Ear std=0.022 太低** — Ear 幾乎常數，IC -0.052 可能是數據偽影
7. 🟢 P2：**衍生品特徵工程** — LSR/Taker/OI 尚未用作特徵

---

## ORID 決策
- **O**: 全域 3/23 通過（Ear, RSI14, BB%p），Regime Bear 8/23/Bull 1/23/Chop 3/23，CV ~52%，sell_win 50.8%/47.2%/47.0%/36.0%（50），BTC $67,343(+0.77%)，6/6 tests，排程器已啟動
- **R**: 排程器修復是重大進展；Bear sell_win=41.7% 反向準確 58.3% 是可利用的信號；Bull 60.6% 為唯一正向 regime；近期 50-sell_win=36% 持續惡化
- **I**: 系統已進入「信號天花板」狀態。23 維中 20 維無效，且 11+ 輪無改善。需要：(1) 驗證排程器正常運行 (2) 反向策略 prototype (3) Bull-only 交易 (4) 清除 placeholder (5) 外部 alpha 引入
- **D**: (1) 🔴 驗證排程器數據入庫 (2) 🔴 測試 Bear 反向策略原型 (3) 🔴 尋找外部 alpha (4) 🟡 清除 placeholder 特徵 (5) 🟡 Bull-only 策略 (6) 🟢 衍生品特徵化

---

## 📋 本輪修改記錄

- **#193**: ✅ 運行 dev_heartbeat.py — Raw=8,956（+0 停滯）, Features=8,921, Labels=8,766。
- **#193**: ✅ 完整 IC 分析 23 特徵含 TI + placeholder — 全域 3/23 通過（Ear, RSI14, BB%p），結果與 #192 一致。
- **#193**: ✅ Regime IC 確認固化 — Bear 8/23, Bull 1/23, Chop 3/23。
- **#193**: ✅ 衍生品數據 — LSR=1.61, Taker=1.61, OI=91,731（買盤優勢持續）。
- **#193**: ✅ BTC $67,343 (+0.77%) | FNG 11 (Extreme Fear) | VIX 23.90 | DXY 100.19。
- **#193**: 🔧 **🔴 P0 修復：安裝 apscheduler 並啟動 main.py 排程器**（PID 399202）— 數據收集停滯問題（#H353）已部分修復，待驗證 5min 數據入庫。
- **#193**: ✅ 測試套件 6/6 全部通過。
- **#193**: ⏸️ 未修改特徵代碼 — placeholder 清除、策略重構需跨多文件修改，需更謹慎處理。

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **驗證排程器數據入庫** — 5min 後檢查 raw > 8,956 | #H353 |
| 🔴 P0 | **全域 IC 天花板突破** — 11+ 輪無改善，需外部 alpha 或反向策略 | #H304 |
| 🔴 P0 | **Bear 反向策略原型** — 利用 8 個有效 Bear 特徵反向交易 | #H340 |
| 🟡 P1 | **清除 8 個 placeholder 特徵** — whisper/tone/chorus/hype/oracle/shock/tide/storm | #H370 |
| 🟡 P1 | **Bull-only 策略原型** — Bull sell_win=60.6% 為最佳 regime | #H342 |
| 🟡 P1 | **N=50 預警系統** — 36% sell_win 需自動觸發檢查 | #H342 |
| 🟡 P1 | **Ear std=0.022 調查** — 幾乎常數，IC 可能是數據偽影 | #H371 |
| 🟢 P2 | **衍生品特徵工程** — LSR/Taker/OI 尚未用作特徵 | #H372 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
