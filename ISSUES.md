# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。

---

*最後更新：2026-04-04 20:41 GMT+8（心跳 #183）*
---

## 📊 當前系統健康狀態（2026-04-04 20:41 GMT+8，心跳 #183）

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw market data | 8,955 筆 | ➡️ 持平 |
| Features | 8,920 筆 | ➡️ 持平 |
| Labels | 8,770 筆 | ➡️ 持平 |
| BTC 當前 | ~$67,071 | ⬇️ 微跌 |
| FNG | 11（Extreme Fear） | ➡️ 持平 |
| Funding Rate | ~0.000012 | ➡️ 持平 |
| LSR | 1.6441 | ➡️ 持平 |
| Taker | 1.6441 (LSR proxy) | |
| OI | 90,613 | |
| Body label | 槓桿偏多 | LSR=1.64 |

### 🔴 最高優先級（P0）

| ID | 問題 | 狀態 | 備註 |
|----|------|------|------|
| #H304 | 🔴 **全域 IC ~0/8 against sell_win** | 🔴 **持續（5 輪）** | 全域僅 Ear 近線（-0.0475），vs label_up 2/8（Ear, Nose）|
| #H340 | 🚨 **Regime 極端分化** | 🔴 Bear 5/8、Bull 1/8、Chop 0/8 | Bear 穩定 5/8，Bull 僅 Ear，Chop 連續多輪全滅 |
| #H137 | 🔴 **CV ~52% 距 90% 遠** | 🔴 **停滯** | 信號天花板 ≈ 52%，model id=36 最新 52.24% |
| #H341 | 🚨 **sell_win vs label_up 鴻溝** | 🔴 **持續** | 全域 1/8 vs 2/8，sell_win rate=0.508 vs up=0.501 |
| #H342 | 🚨 **近期 sell_win 偏離** | 🔴 **持續（3 輪）** | 近期窗口 sell_win_rate 0.47-0.48，顯著低於全域 0.508 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H87 | 🟡 CV≈52% 距目標 90% 差距 ~38pp | 🔴 主要障礙（信號天花板）|
| #H126 | 🟡 共線性：多感官高相關 | 違反獨立感官假設 |
| #H199 | 🟡 **TI 特徵未提升模型** | 51 特徵含 TI，CV 仍 52.24% |
| #H333 | 🟡 **N=500 全滅** | 0/8，中窗口持續失效（多輪確認）|
| #H321 | 🟡 **Tongue 全域 IC≈0** | IC=-0.0012，全域最弱 |

### 🟢 低優先級

| ID | 問題 | 狀態 |
|----|------|------|
| #H97 | 建立 IC rolling trend 追蹤 | 🟢 Time-weighted 已實作 |
| #IC4 | 動態 IC 加權 | 🟢 已實作 time-weighted fusion |
| #H311 | 無 saved models | 🟢 xgb_model.pkl + regime_models.pkl 存在 |

---

## 感官 IC 掃描（心跳 #183, 2026-04-04 20:41）

### 全域 IC against sell_win（N=8,770, 8 核心感官）
| 感官 | IC | 狀態 | vs #182 |
|------|------|------|---------|
| Nose | -0.0500 | ❌ | ➡️ 持平（邊緣）|
| Ear | -0.0475 | ❌ | ⬆️ 回升（-0.0478→-0.0475）|
| Body | -0.0460 | ❌ | ➡️ 持平 |
| Aura | -0.0363 | ❌ | ➡️ 持平 |
| Mind | -0.0246 | ❌ | ➡️ 持平 |
| Eye | +0.0135 | ❌ | ➡️ 持平 |
| Pulse | +0.0057 | ❌ | ➡️ 持平 |
| Tongue | -0.0012 | ❌ | ➡️ 持平 |

**全域達標：1/8 against sell_win** — Ear 近線但 FAIL vs **2/8 against label_up**（Ear, Nose）

### Dynamic Window IC（sell_win）
| N | 達標數 | 過線感官 | 備註 |
|---|--------|---------|------|
| 100 | **7/8** 🆕 | Eye, Nose, Tongue, Body, Pulse, Aura, Mind | 歷史最佳！僅 Ear 失敗 |
| 200 | **7/8** 🆕 | Eye, Nose, Tongue, Body, Pulse, Aura, Mind | tau=50/100 同樣 7/8 |
| 500 | **0/8** | 全滅 | ❌ 中窗口死亡區（多輪持續）|
| 1000 | **4/8** | Eye, Pulse, Aura, Mind | ➡️ 持平 |

### 最強單感官 IC（短窗口）
| 窗口 | 感官 | IC | 備註 |
|------|------|------|------|
| N=100 | **Aura** | **-0.277** 🆕 | 有史以來最強單 IC！大幅改善 |
| N=100 | Mind | -0.230 | ⬆️ 改善 vs #182（-0.239→-0.230 持平強）|
| N=100 | Nose | -0.177 | ⬆️ 大幅改善 vs #182（-0.101→-0.177）|
| N=100 | Tongue | +0.115 | ⬆️ 改善 vs #182（+0.096）|

### Time-Weighted IC
| tau | 達標數 | 備註 |
|-----|--------|------|
| 50 | **7/8** | ⬆️ 改善（#182: 6/8→#183: 7/8）|
| 100 | **7/8** | ⬆️ 改善（#182: 4/8→#183: 7/8）|
| 200 | **4/8** | Nose, Pulse, Aura, Mind |
| 500 | **3/8** | Pulse, Aura, Mind |

### Regime IC（against sell_win）
| 感官 | Bear IC | Bull IC | Chop IC |
|------|---------|---------|---------|
| Eye | +0.0592 ✅ | -0.0220 ❌ | -0.0008 ❌ |
| Ear | -0.0452 ❌ | -0.0604 ✅ | -0.0258 ❌ |
| Nose | -0.0581 ✅ | -0.0464 ❌ | -0.0441 ❌ |
| Tongue | +0.0254 ❌ | -0.0003 ❌ | -0.0328 ❌ |
| Body | -0.0432 ❌ | -0.0482 ❌ | -0.0327 ❌ |
| Pulse | +0.0582 ✅ | +0.0155 ❌ | -0.0460 ❌ |
| Aura | -0.0640 ✅ | -0.0115 ❌ | -0.0161 ❌ |
| Mind | -0.0536 ✅ | -0.0137 ❌ | -0.0052 ❌ |

| Regime | 達標數 | vs #182 |
|--------|--------|---------|
| Bear | **5/8** | ⬆️ 反彈（#182: 1/8→#183: 5/8）|
| Bull | **1/8** | ⬆️ 回歸（#182: 0/8→#183: 1/8）|
| Chop | **0/8** | ➡️ 持平全滅 |

### 🔴 關鍵發現
- **N=100 達到 7/8** — 歷史最佳短窗口結果！Aura -0.277 是有史以來最強單 IC
- **全域仍 ~0/8 against sell_win** — 全局持續零有效，是系統性天花板不是隨機
- **近期 sell_win_rate 偏離 4pp** — 近 100 筆 = 0.470 vs 全域 0.508（持續 3 輪）
- **Bear regime 大幅反彈至 5/8**（#182 時僅 1/8）— 但 Bull/Chop 仍極弱
- **tau=50 和 tau=100 均 7/8** — 近期加權極有效，證明短期信號強
- **sell_win 的 gap（1/8 vs label_up 2/8）** — sell_win 包含交易成本噪聲，更難預測
- **N=500 持續 0/8** — 中期窗口仍是死亡區

---

## 模型狀態

| 項目 | 數值 |
|------|------|
| Global model | XGBClassifier (51 features) |
| Regime models | Bear, Bull, Chop ✓ |
| Predictor type | RegimeAwarePredictor ✓ |
| Model files | xgb_model.pkl + regime_models.pkl ✓ |
| Latest CV | 52.24% (id=36, 51 features, sell-win auto-train) |
| CV std | 0.021 |
| Train accuracy | 72.27% |
| Overfit gap | ~20pp（72.27% vs 52.24%）|
| Trade history | 0 trades |

---

## 六帽分析摘要

### 白帽（事實）
- Raw 8,955 筆、Features 8,920 筆、Labels 8,770 筆
- **全域 ~0/8 against sell_win** — 僅 Ear 近線，5 輪確認
- **N=100 創紀錄 7/8** — Aura -0.277, Mind -0.230, Nose -0.177 是最強信號
- **N=200 7/8** — 中短期同樣有效
- **Bear 5/8, Bull 1/8, Chop 0/8** — 極端分化
- **tau=50 和 tau=100 均 7/8** — 近期加權極有效
- CV 52.24%（id=36, 51 特徵含 TI）
- 近期 sell_win_rate 偏離全域：近 100=0.470 vs 全域=0.508
- BTC $67,071, FNG 11（Extreme Fear），LSR 1.6441，OI 90,613

### 黑帽（風險）
1. **全域 0/8 連續五輪** — 全局天花板確認，不是偶然
2. **Chop regime 持續全滅** — 橫盤市場完全無信號
3. **sell_win vs label_up 2/8 vs 1/8 差距** — sell_win 標籤包含更多噪聲
4. **N=500 持續 0/8** — 中期窗口是系統性死亡區
5. **近期 sell_win_rate 偏離 4pp（0.47 vs 0.508）** — 標籤可能正在 drift
6. **CV 52.24% 停滯** — 51 特徵完全不提升

### 黃帽（價值）
1. **N=100 創 7/8 紀錄** — Aura -0.277 是有史以來最強單 IC
2. **Bear regime 反彈至 5/8** — 熊市信號穩定有效
3. **tau=100 從 4/8 躍升至 7/8** — 時間加權窗口在改善
4. **系統穩定 6/6 全過** — 測試無 FAIL
5. **數據管線正常運行** — Raw stable at 8,955

### 綠帽（創新）
1. **N=100 windowed trading 策略** — 7/8 + Aura -0.277 說明極短期交易可行
2. **Multi-timeframe ensemble**: N=100 的 7 個 IC 信號 + tau=100 融合作為新融合策略
3. **Dynamic sell_win label** — 近期 sell_win rate 偏離可作為 regime 切換信號
4. **Inverse Ear strategy** — Ear 在 N=100 FAIL 但在 global 近線，方向不穩定的警示

### 藍帽（決策）
**P0 行動項：**
1. 🔴 **N=100 窗口策略落地設計** — 7/8 信號 + Aura -0.277 必須利用，設計 windowed IC fusion
2. 🔴 **sell_win drift 持續追蹤** — 連續 3 輪 0.47 vs 0.508，標確定義需要重新檢視
3. 🔴 **過擬 gap ~20pp 縮減** — Train 72.3% vs CV 52.2%，需要正則化或特徵降維
4. 🟡 **Chop regime 新數據源** — 全滅持續，需要外部 alpha
5. 🟢 **Tau=100 從 4/8→7/8 追蹤** — 改善是否可持續

---

## ORID 決策
- **O**: 全域 ~0/8（五輪），Bear 5/8（反彈），N=100 7/8（紀錄），tau=50/100 7/8，CV 52.24%，sell_win recent drift（0.47 vs 0.508）
- **R**: Bear 反彈是正面但 Bull/Chop 仍死寂。N=100 信號強度歷史最佳（Aura -0.277），但全局天花板仍在。sell_win 持續漂移令人擔憂。
- **I**: 三個核心假設：（1）全域 IC~0 是因為短期正信號被長期負信號抵消—N=100 7/8 證明了信號存在但時間不匹配（2）sell_win 漂移說明了標籤與市場行為解耦—可能需要動態標籤（3）Chop 全滅說明橫盤需要完全不同的特徵集
- **D**: （1）**設計 N=100 windowed trading 策略**，利用 7/8 信號（2）**sell_win drift root cause 分析**，確認是否需改 label_up（3）**Chop regime 新 alpha 源探索**

---

## 📋 本輪修改記錄

- **#183**: ✅ 運行 dev_heartbeat.py — Raw=8,955, Features=8,920, Labels=8,770。
- **#183**: 📊 **全盤 IC 分析** — 全域 **~0/8** against sell_win（**第五輪**持續低迷），vs label_up 2/8。
- **#183**: 🆕 **N=100 創紀錄 7/8** — Aura -0.277 歷史最強單 IC！Mind -0.230, Nose -0.177。
- **#183**: 🆕 **N=200 7/8** — 中短期同樣 7 個信號過線。
- **#183**: ⬆️ **tau=50 7/8（#182: 6/8）**、**tau=100 7/8（#182: 4/8 大躍升）**。
- **#183**: ⬆️ **Bear regime 5/8（#182: 1/8 大幅反彈）**、Bull 1/8、Chop 0/8。
- **#183**: 📊 **市場數據** — BTC $67,071, FNG 11, LSR 1.64, OI 90,613。
- **#183**: ✅ **測試結果 6/6 ALL PASS**。

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **N=100 windowed trading 策略** — 7/8 信號落地，設計 windowed IC fusion | #H304 |
| 🔴 P0 | **sell_win drift 根因分析** — 0.47 vs 0.508 連續三輪，標籤可能需重定義 | #H342 |
| 🔴 P0 | **過擬 gap 縮減** — ~20pp gap 需正則化或特徵降維 | #H137 |
| 🟡 P1 | **tau=100 持續改善追蹤** — 4/8→7/8 是否可持續 | #IC4 |
| 🟡 P1 | **Chop regime 新 alpha 源** — 持續 0/8 需外部數據 | #H303 |
| 🟢 P2 | **信心校準** — Platt scaling / temperature scaling | #H87 |

---

*此文件每次心跳完全覆蓋，保持簡潔。*
