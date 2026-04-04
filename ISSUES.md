# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-05 23:15 GMT+8（心跳 #191）*
---

## 📊 當前系統健康狀態（2026-04-05 23:15 GMT+8，心跳 #191）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,956 筆 | ⬆️ +1（+0.4h 新資料）|
| Features | 8,921 筆 | ⬆️ +1 |
| Labels | 8,766 筆 | ➡️ 持平 |
| BTC 當前 | $67,136 | ⬇️ -$78 |
| FNG | 11（Extreme Fear）| ➡️ 持平 |
| Funding Rate | 0.000016 | ➡️ 持平 |
| LSR | —（未收集）| — |
| Taker | —（未收集）| — |
| OI | —（未收集）| — |
| VIX | 23.90 | ✅ 正常 |
| DXY | 100.19 | ✅ 正常 |
| sell_win (全域) | 0.508 | ➡️ 持平 |
| 近期 sell_win (last 500) | 0.472 | 🔴 偏離 |
| 近期 sell_win (last 100) | 0.470 | 🔴 偏離 |
| 最新 raw timestamp | 14:56 UTC | 🟡 ~8h 前（心跳運行後收集停頓）|

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC 3/21，僅 1/8 核心感官** | 🔴 **持續 10+ 輪** | Ear(-0.0516)、RSI14(-0.0536)、BB%p(-0.0523) 全局通過 |
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 8/13、Bull 1/13、Chop 3/13 | 固化 10+ 輪 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，過落差 ~20pp |
| #H342 | 🚨 **近期 sell_win 偏離至 47%** | 🔴 **持續** | last 500=0.472, last 100=0.470，低於隨機 |
| #H353 | 🚨 **數據收集停滯** | 🔴 **持續** | ~1.5h 無新 raw entries（心跳執行間）；main.py 排程器未運行 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 ~52% |
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=+0.0036，全域最弱 |
| #H351 | 🟡 **Bear sell_win 41.7% 低於隨機** | 熊市實際勝率僅 41.7% |
| #H360 | 🟡 **feat_ear std=0.0008, unique≈5** | 測試報告為準離散，但實際 DB 8,896 unique → **已改善** |
| #H370 | 🟡 **7 個 placeholder 特徵全部為 0** | whisper/tone/chorus/hype/oracle/shock/tide/std/unique=1 |
| #H371 | 🟡 **Ear 命名 mismatch** | preprocessor 寫 `feat_ear_zscore` → DB column `feat_ear`（透過 property 映射 OK，但 IC 腳本讀取列名不一致）|

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |
| #H350 | 🟢 NaN regime 回填 | ✅ 已修復（#188）|
| #H352 | 🟢 VIX collector 整合 | ✅ 已修復（#190），VIX=23.90 正常 |

---

## 感官 IC 掃描（心跳 #191, 2026-04-05 23:15 GMT+8）

### 全域 IC against sell_win（N=8,770, 含 TI 特徵共 13 項）
| 感官/特徵 | IC | std | 狀態 |
|-----------|------|------|------|
| **Ear** | -0.0516 | 0.0221 | ✅ PASS |
| **RSI14** | -0.0536 | 0.1198 | ✅ PASS |
| **BB%p** | -0.0523 | 0.3344 | ✅ PASS |
| Nose | -0.0483 | 0.1658 | ❌ 近線 |
| MACD_hist | -0.0465 | 0.0016 | ❌ 近線 |
| Body | -0.0450 | 0.3325 | ❌ 近線 |
| ATR_pct | +0.0313 | 0.0009 | ❌ |
| Aura | -0.0396 | 0.0289 | ❌ |
| Mind | -0.0293 | 0.0499 | ❌ |
| Eye | +0.0220 | 0.5176 | ❌ |
| Pulse | +0.0105 | 0.2460 | ❌ |
| Tongue | +0.0036 | 0.3690 | ❌ |
| VWAP_dev | +0.0005 | 0.2036 | ❌ |

**全域達標：3/13（包含 TI），僅 1/8 核心感官通過**

### Regime IC（13 特徵含 TI）
| Regime | 達標數 | 通過特徵 |
|--------|--------|---------|
| **Bear** | **8/13** | Eye(+0.056), Nose(-0.061), Pulse(+0.061), Aura(-0.072), Mind(-0.063), RSI14(-0.057), MACD(-0.061), ATR(+0.070) |
| **Bull** | **1/13** | Ear(-0.065) |
| **Chop** | **3/13** | Pulse(-0.056), RSI14(-0.056), BB%p(-0.060) |

### 🟢 VIX IC
| 指標 | 全域 IC | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|---------|
| VIX level | -0.0339 | -0.0232 | -0.0387 | -0.0036 |

VIX 全域未達標（|-0.0339| < 0.05），但在 Bull regime 接近閾值。

### 🔑 關鍵發現
- **全域 3/13（Ear, RSI14, BB%p 通過）** — 新增 TI 特徵提供了 2 個額外通過信號
- **Regime 分化持續固化**：Bear 8/13、Bull 1/13、Chop 3/13
- **7 個 placeholder 特徵全部 null**（whisper/tone/chorus/hype/oracle/shock/tide）— 死weight
- **Bear-only 融合 IC = +0.0859**（top 5 signed: Aura, Mind, Pulse, Nose, Eye）— 最強融合信號
- **sell_win 全域 50.8%，近期(500) 47.2%，近期(100) 47.0%** — 模型近期表現更差
- **測試套件 6/6 全部通過**（改善自 #190 的 5/6）

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (含 5 TI 特徵) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | ~52%（確定性天花板）|
| Overfit gap | ~20pp |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,956 / Features 8,921 / Labels 8,766 — 緩慢增長（+1 raw 自 #190）
- 全域 IC 3/13 通過（+2 TI 特徵），但核心 8 感官仍僅 1/8
- Regime IC：Bear 8/13 ✅, Bull 1/13 🔴, Chop 3/13
- CV 52% — 確定性天花板持續
- sell_win 全域 50.8%，近期(500) 47.2% — 低於隨機
- VIX 23.90, DXY 100.19, FNG 11 (Extreme Fear)
- 測試 6/6 全部通過（所有驗證通過！）
- 7 個 placeholder 特徵完全無效（IC=0, std=0, unique=1）

### 黑帽（風險）
1. **8/13 features 未能通過 IC 閾值** — 特徵空間仍有大量低價值信號
2. **Bull regime 僅 1/13 通過** — 牛市幾乎完全無法預測
3. **近期 sell_win 47% 低於隨機** — 模型反向有 predictive value（47% = 53% 反向準確率）
4. **7 個 placeholder 特徵浪費維度** — whisper/tone/chorus/hype/oracle/shock/tide 全部 std=0
5. **數據收集停頓** — 排程器未運行，系統依賴手動心跳
6. **CV 52% 天花板 10+ 輪無突破** — 特徵共線性、信號天花板、非穩定市場

### 黃帽（價值）
1. **Bear 8/13 穩定通過** — 8 個特徵在熊市有效，8/13 為迄今最佳
2. **TI 特徵新增價值** — RSI14(-0.0536)、BB%p(-0.0523) 通過全局閾值
3. **Bear 融合 IC=+0.0859** — 融合信號比任何單一特徵都強
4. **測試 6/6 全部通過** — 系統穩定性良好
5. **VIX 數據恢復** — 23.90 正常收集，Bull IC=-0.0387
6. **VIX/DXY columns 已添加至 raw_market_data** — 基礎設施改善

### 綠帽（創新）
1. **反向信号策略** — sell_win 47% → 反向操作 53% 勝率，可作為 baseline
2. **Bear-only 交易策略** — 僅在 Bear regime 交易，使用 8/13 有效特徵融合
3. **清除 placeholder 特徵** — 移除 7 個死特徵節省維度，降低噪音
4. **Regime-gated ensemble** — 不同 regime 使用不同子集（Bear: 8特徵, Chop: 3特徵, Bull: 1特徵+VIX）
5. **近期窗口 IC** — N=500 有 10/21 通過，N=1000 有 5/21 — 非穩定市場需要短窗口權重

### 藍帽（決策）
1. 🔴 P0：**全域 IC 天花板突破** — 需外部 non-price alpha 或 new feature engineering 策略
2. 🔴 P0：**重啟數據收集服務** — main.py 排程器必須恢復
3. 🟡 P1：**清除 7 個 placeholder 特徵** — 減少維度，節省計算
4. 🟡 P1：**反向策略原型** — sell_win < 50% → 反向預測
5. 🟢 P2：**VIX 在 Bull/Chop  regime 整合** — 作為額外信號

---

## ORID 決策
- **O**: 全域 3/13（Ear, RSI14, BB%p PASS），Regime Bear 8/13/Bull 1/13/Chop 3/13，CV ~52%，sell_win 50.8%/47.2%(500)/47.0%(100)，VIX=23.90，6/6 tests
- **R**: Bear 表現最佳但近期勝率下降，Bull 幾乎完全無法預測，系統穩定但預測能力不足
- **I**: 特徵空間已接近極限。價格-derived 特徵已完全利用。需要：(1) 外部 non-price alpha (2) 反向策略利用 47% sell_win (3) 清除死特徵 (4) 恢復自動數據流
- **D**: (1) 🔴 重啟數據收集 (2) 🟡 清除 placeholder 特徵 (3) 🟡 探索反向策略 (4) 🔴 尋找外部 alpha 來源 (5) 🟢 VIX/DXY 持續監控

---

## 📋 本輪修改記錄

- **#191**: ✅ 運行 dev_heartbeat.py — Raw=8,956, Features=8,921, Labels=8,766。+1 raw 自 #190。
- **#191**: ✅ 完整 IC 分析 13 特徵含 TI — 全域 3/13 通過（Ear, RSI14, BB%p）。
- **#191**: ✅ Regime IC — Bear 8/13（+3 自 #190 的 5/8，計入 TI 特徵），Bull 1/13，Chop 3/13。
- **#191**: ✅ Bear-only 融合 IC = +0.0859（top 5 signed）。
- **#191**: ✅ 測試套件 6/6 全部通過（改善自 5/6）。
- **#191**: ✅ VIX IC：全域 -0.0339, Bear -0.0232, Bull -0.0387, Chop -0.0036。
- **#191**: 🔴 確認 7 個 placeholder 特徵全為 null（whisper/tone/chorus/hype/oracle/shock/tide）。
- **#191**: 🟡 確認近期 sell_win 47.0-47.2% — 低於隨機，但可作為反向策略基礎。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **全域 IC 天花板突破** — 10+ 輪無改善，需外部 alpha 或反向策略 | #H304 |
| 🔴 P0 | **重啟數據收集服務** — main.py 排程器未運行 | #H353 |
| 🟡 P1 | **清除 7 個 placeholder 特徵** — whisper/tone/chorus/hype/oracle/shock/tide | #H370 |
| 🟡 P1 | **反向策略原型** — sell_win 47% → 反向 53% | #H342 |
| 🟢 P2 | **VIX/DXY 持續監控** — Bull IC=-0.0387 接近閾值 | #H352 |
| 🟢 P2 | **新數據源探索** — Twitter/X、新聞、macro calendar | #H303 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
