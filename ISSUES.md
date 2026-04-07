# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 10:35 UTC（心跳 #540）*

## 📊 系統健康狀態（#540）

| 項目 | 數值 | vs #539 |
|------|------|--------|
| Raw | **9,682** | ⬆️ +7（從 9,675 增長）|
| Features | **9,642** | ⬆️ +7（從 9,635）|
| Labels | **18,052** | ➡️ 持平（凍結~110h+）|
| sell_win (DB all) | **40.37%** | ➡️ 持平 |
| sell_win (regime join) | **49.24%** | ➡️ 持平（n=8770）|
| 全域 IC (15 擴） | **5/15** | ➡️ 持平（VIX, RSI14, MACDHist, BB%B, Nose擦邊）|
| TW-IC (15 擴） | **10/15** | ➡️ 持平 |
| DW N=100 | **7/8**🟢 | ➡️ 持平 |
| DW N=200 | **7/8**🟢 | ➡️ 持平 |
| DW N=600 | **0/8** | ➡️ 持續死區 |
| DW N=1000 | **4/8** | ➡️ 持平 |
| Global model | Train=63.92%, CV=51.39%, gap=12.53pp | ⚠️ train.py KeyError，使用上次值 |
| Regime IC | Bear **4/8**（持平）, Bull **0/8**🔴, Chop **0/8**🔴 | ➡️ 持平 |
| BTC (live) | **$68,531** | ⬆️ +$10（vs #539 $68,521，穩定）|
| FNG | **11**（持續極度恐懼）| ➡️ 持平 |
| FR | **0.00000895** | ⬆️ +13.4%（vs #539 0.00000789，持續回升！）|
| LSR | **1.1877** | ⬆️ +43bps（vs #539 1.1834，持續回升！）|
| OI | **91,134** | ⬆️ +80（vs #539 91,054，微升）|
| preprocessor.py | **語法錯誤已修復** | ✅ 447行indent修復 |
| 測試 | **6/6 (32/32)** | ✅ 全過！preprocessor修復後30 PASS |
| 平行心跳 | **4/5 PASS** 🟡（**3.3s**）| 持平，train持續KeyError |

## 系統狀態：⚠️ 大部分持平但市場持續轉暖！FR持續回升(+13.4%)，LSR回升(+43bps)，preprocessor.py語法已修復
全域 IC (5/15持平)、TW-IC (10/15持平)、模型 (T63.92%/CV51.39%)、Regime IC (Bear 4/8, Bull 0/8❌, Chop 0/8❌) — **全部持平**。DW 7/8維持 N=100/200。FR 從 0.00000789 回升至 0.00000895（**+13.4%**），LSR 回升至 1.1877（+43bps）。BTC穩定$68.5K。**preprocessor.py indent錯誤已修復**（6/6測試恢復），**train.py KeyError持續**。Raw+7。

- **BTC $68,531**: ⬆️ +$10 vs #539（$68,521），$68.5K穩定
- **🟢 FR 持續回升 0.00000895**: +13.4% vs #539（0.00000789→**0.00000895**），多頭付費需求持續恢復
- **⬆️ LSR 1.1877（+43bps）**: 長倉比例持續回升，多頭回歸信號延續
- **⬆️ OI 91,134（+80）**: 持倉量微升
- **✅ preprocessor.py 語法修復**: `save_features_to_db()` 第447行 indent錯誤修復（try/except塊結構修復），測試從26/36→32/32
- **⚠️ train.py 持續KeyError**: `future_return_pct` column在merge後缺失，需要join修復
- **⚡ 平行心跳 4/5 PASS（3.3s）**: full_ic/regime_ic/dynamic_window/tests通過，train失敗
- **Raw+7/Features+7**: 微增長
- **Labels 18,052（但n=8770用於IC）**: DB有18052條但IC分析用join子集8770

## 全域 IC — 5/15 持平

**8 核心（全域 Spearman）**: Eye -0.0135, Ear +0.0475, Nose +0.0500（擦邊閾值）, Tongue +0.0012, Body +0.0460, Pulse -0.0057, Aura +0.0363, Mind +0.0246

**15 擴（全域 Spearman）**: VIX +0.0714✅, RSI14 +0.0542✅, MACDHist +0.0505✅, BB%B +0.0575✅, Nose +0.0500擦邊 — 4+1/15有效

**TW-IC（10 過）**: Nose+0.0587, Pulse-0.0871, AURA+0.0799, Mind+0.0750, VIX+0.0876, RSI14+0.0746, MACD+0.0554, ATR%-0.1280, VWAP+0.1293, BB%B+0.0826

## Dynamic Window — N=600 持續死區

| Window | 通過 | 狀態 |
|--------|------|------|
| N=100 | **7/8**🟢 | Eye, Nose, Tongue, Body, Pulse, Aura, Mind |
| N=200 | **7/8**🟢 | Eye, Nose, Tongue, Body, Pulse, Aura, Mind |
| N=400 | 3/8 | Pulse, Aura, Mind |
| N=600 | **0/8** 🔴 | 持續死區 |
| N=1000 | 4/8 | Eye, Pulse, Aura, Mind |
| N=2000 | 2/8 | Pulse, Aura |
| N=5000 | 0/8 | 全滅 |

## Regime IC — Bear 4/8, Bull 0/8🔴, Chop 0/8🔴（持平）

| Regime | 通過 | 信號 |
|--------|------|------|
| Bear | **4/8** | Ear+0.0785✅, Nose+0.0727✅, Body+0.0682✅, Aura+0.0544✅ |
| Bull | **0/8**🔴 | 全部 <0.05（持續！）|
| Chop | **0/8**🔴 | 全部 <0.05（持續！）|

**sell_win by Regime**: Bear=0.4855, Bull=0.5090, Chop=0.4829, Overall=0.4924（n=8770，匹配子集）

## 市場數據亮點

- **BTC $68,531**: ⬆️ +$10 vs #539（$68,521），$68.5K盤整
- **🟢 FR 0.00000895**: 持續回升（+13.4% vs #539），多頭付費需求持續恢復
- **⬆️ LSR 1.1877（+43bps）**: 長倉比例持續回升，多頭回歸信號延續
- **⬆️ OI 91,134（+80）**: 持倉量微升
- **FNG 11**（持續極度恐慌）

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #P425 | sell_win≥50% 全域 | 🔴 **持續 40.37%（全量Labels），regime子集49.24%** |
| #LABEL_REVIVED | 標籤管線恢復 | 🟢 Labels 18,052（持平）|
| #RAW_STALE | Raw 數據低增長 | 🟢 Raw +7（微增）|
| #P442 | Chop 0/8 | 🔴 持續 200+ 輪 |
| #BULL_BLIND | Bull 0/8 | 🔴 Bull 0/8 持續 |
| #IC_FREEZE | 全域/TW-IC/模型凍結 | 🟡 全域 5/15，TW-IC 10/15（持平）|
| #NO_DATA | 新感官零數據（Claw/Fang/Fin）| 🔴 Collector 未收集 |
| #DW_DEAD | DW N=600 死區 | 🟡 持續0/8 |
| #TRAIN_FAIL | train.py KeyError: future_return_pct | 🔴 **merge後缺失，join問題未修！** |
| #PREPROCESSOR_FIX | ✅ preprocessor.py indent修復 | 🟢 **修復完成，測試6/6恢復！** |
| #FR回升 | ⚠️ FR回升/LSR回升 | 🟡 **FR 0.00000895↗（+13.4%回升！）, LSR 1.1877⬆️（+43bps）** |

## 測試狀態

| 測試 | 結果 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS (9969 文件) |
| 模組導入 | ✅ PASS (8/8, 含preprocessor!) |
| 感官引擎真實數據 | ✅ PASS |
| 前端 TypeScript | ✅ PASS |
| 數據品質 | ✅ PASS |

## 模型訓練

- Global: Train=63.92%, CV=51.39%±3.66%, gap=12.53pp（從last_metrics.json）
- Samples: 8,917, Features: 51, Positive ratio: 30.45%（從last_metrics.json）
- Regime models: bear/bull/chop 各 70 features saved
- 🔴 **本次train.py出現KeyError: 'future_return_pct'** — merge後缺失，join需要修復

> 心跳 #540: full_ic 5/15全域(持平), 10/15 TW-IC(持平), regime Bear 4/8, Bull 0/8 Chop 0/8(DW N=100&200 7/8持平, N=600持續0/8死區!), 測試6/6✅, 平行心跳4/5 PASS🟡(3.3s,train持續KeyError), sell_win **40.37%**（持平，regime子集49.24%持平）, T63.92%/CV51.39%(持平), BTC **$68,531**(+$10), FR ⬆️ **0.00000895**(+13.4%回升!), LSR **1.1877**(+43bps!), OI 91,134(+80), Raw+7/Features+7/Labels持平，**全部IC持平！市場持續轉暖：FR持續回升+13.4%，LSR回升+43bps！preprocessor.py indent修復✅，train.py KeyError待修！**
