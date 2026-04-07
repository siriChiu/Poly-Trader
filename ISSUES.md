# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 15:20 UTC（心跳 #573）*

## 📊 系統健康狀態（#573）

| 項目 | 數值 | vs #572 |
|------|------|---------|
| Raw | **9,848** | ⬆️ +8 🟢 |
| Features | **9,808** | ⬆️ +8 🟢 |
| Labels | **18,052** | ➡️ 持平 |
| sell_win (DB all) | **40.37%** | ➡️ 持平 |
| sell_win (regime join) | **49.24%** | ➡️ 持平（n=8770）|
| 全域 IC (22 擴） | **5/22** | ➡️ 持平 |
| TW-IC (22 擴） | **13/22** | ➡️ 持平（歷史新高維持）|
| DW N=100 | **7/8**🟢 | ➡️ 持平 |
| DW N=200 | **7/8**🟢 | ➡️ 持平 |
| DW N=400 | **3/8** | ➡️ 持平 |
| DW N=600 | **0/8** | ➡️ 持續死區 |
| DW N=1000 | **4/8** | ➡️ 持平 |
| Global model | Train=63.92%, CV=51.39%, gap=12.53pp | ➡️ 持平 |
| Regime IC | Bear **4/8**, Bull **0/8**🔴, Chop **0/8**🔴 | ➡️ 持平 |
| BTC (live) | **$68,556** | ⬆️ +$49（vs #572 $68,507）|
| FNG | **11**（持續極度恐懼）| ➡️ 持平 |
| FR | **0.00003672** | ⬆️ +8.7%（vs #572 0.00003379，持續回升！）|
| LSR | **1.2341** | ⬆️ +15bps（vs #572 1.2326，持續回升）|
| OI | **91,194** | ⬆️ +1（vs #572 91,192）|
| 測試 | **5/6** | ➡️ 持平 |
| 平行心跳 | **4/5 PASS** 🟢（**37.2s**）| ✅ 基本通過 |

## 系統狀態：🟡 持平 / 全面穩定 / FR+LSR 雙升 / 數據持續增長 / 測試持續 5/6

FR 持續回升至 0.00003672（+8.7%！）：多頭付費意願持續增強。
LSR 回升至 1.2341（+15bps）：長倉比例持續回升。
Data pipeline 持續增長：Raw +8, Features +8.
測試持續 5/6：感官引擎 `normalize_feature` import 錯誤未解（同 #572）。

- **BTC $68,556**: ⬆️ +$49 vs #572 $68,507，微幅反彈
- **⬆️ FR 持續回升至 0.00003672（+8.7%！）**: 從 #572 的 0.00003379 繼續攀升，多頭需求加速
- **⬆️ LSR 1.2341（+15bps）**: 長倉比例回升，多頭信心增加
- **⬆️ OI 91,194（+1）**: 持倉量持平
- **✅ 4/5 PASS**: 平行心跳基本通過（37.2s）
- **raw +8, features +8**: 🟢 數據管線持續增長
- **測試 5/6**: 感官引擎 import 錯誤持續（`normalize_feature` not found）
- **DW 持續**: N=100&200 7/8🟢，N=400 3/8，N=600 持續 0/8 死區
- **訓練**: 73 features, 9106 samples, CV=51.39%（持平）
- **Regime**: Bear 4/8（持續）, Bull 0/8🔴（200+輪持續！）, Chop 0/8🔴（200+輪持續！）

## 全域 IC — 5/22（持平）

**8 核心（全域 Spearman）**: Eye -0.0135, Ear +0.0475（擦邊）, Nose +0.0500（擦邊）, Tongue +0.0012, Body +0.0460, Pulse -0.0057, Aura +0.0363, Mind +0.0246

**22 擴（全域 Spearman, 含4H/5TI特徵）**: 5/22 passing。
PASS: VIX +0.0714 ✅, RSI14 +0.0542 ✅, MACDHist +0.0505 ✅, BB%B +0.0575 ✅, Nose +0.0500 ✅

**TW-IC（13/22 過, tau=200, 歷史新高維持）**: Nose+0.0587, Pulse-0.0871, AURA+0.0799, Mind+0.0750, VIX+0.0876, RSI14+0.0746, MACD+0.0554, ATR%-0.1280, VWAP+0.1293, BB%B+0.0826, 4h_bias50+0.0715, 4h_rsi14+0.0622, 4h_dist_swing_low+0.0620
FAIL: Eye, Ear, Tongue, Body (core 8 中有 4 個失效); 4h_bias20, 4h_macd_hist, 4h_bb_pct_b, 4h_ma_order 失敗

## Dynamic Window — N=100&200 7/8（持平）

| Window | 通過 | 狀態 |
|--------|------|------|
| N=100 | **7/8**🟢 | eye+0.089, nose+0.177, tongue-0.115, body+0.129, pulse-0.081, aura+0.277, mind+0.230 |
| N=200 | **7/8**🟢 | eye+0.050, nose+0.114, tongue-0.082, body+0.062, pulse-0.131, aura+0.162, mind+0.167 |
| N=400 | **3/8** | Pulse, Aura, Mind |
| N=600 | **0/8** 🔴 | 持續死區 |
| N=1000 | 4/8 | Eye, Pulse, Aura, Mind |
| N=2000 | 2/8 | Pulse, Aura |
| N=5000 | 0/8 | 全滅 |

## Regime IC — Bear 4/8, Bull 0/8🔴, Chop 0/8🔴（持平）

| Regime | 通過 | 信號 |
|--------|------|------|
| Bear | **4/8** | Ear+0.0785✅, Nose+0.0727✅, Body+0.0682✅, Aura+0.0544✅ |
| Bull | **0/8**🔴 | 全部 <0.05（200+輪持續！）|
| Chop | **0/8**🔴 | 全部 <0.05（200+輪持續！|

**sell_win by Regime**: Bear=0.4855, Bull=0.5090, Chop=0.4829, Overall=0.4924（n=8770）

## 市場數據亮點

- **BTC $68,556**: ⬆️ +$49（+0.07%）vs #572 $68,507，微幅反彈
- **⬆️ FR 0.00003672**: 持續回升（+8.7%，加速！）
- **⬆️ LSR 1.2341**: 長倉比例持續回升（+15bps）
- **⬆️ OI 91,194（+1）**: 持倉量持平
- **FNG 11**（持續極度恐慌）

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #P537 | sell_win≥50% 全域 | 🔴 **持續 40.37%（全量Labels），regime子集49.24%** |
| #RAW_STALE | Raw 數據增長 | 🟢 **+8！持續增長中！** |
| #P442 | Chop 0/8 | 🔴 持續 0/8（200+輪）|
| #BULL_BLIND | Bull 0/8 | 🔴 Bull 0/8 持續（200+輪）|
| #IC_FREEZE | 全域/TW-IC/模型凍結 | 🟢 **穩定：全域 5/22，TW-IC 13/22（歷史新高維持）** |
| #NO_DATA | 新感官零數據（Claw/Fang/Fin）| 🔴 Collector 未收集 |
| #DW_DEAD | DW N=600/5000 死區 | 🟡 持續0/8 |
| #FEATURE_MISMATCH | 4H 特徵部分有效 | 🟢 **3/6 通過 TW-IC（bias50+0.0715, rsi14+0.0622, dist_swing_low+0.0620）** |
| #S571_SENSES | server/senses.py 語法錯誤 | 🟢 **已修復（2處缺引號，測試 3/6→5/6）** |
| #S572_IMPORT | 感官引擎 import 錯誤 | 🔴 **`normalize_feature` import error 未解（測試 5/6）** |

## 測試狀態

| 測試 | 結果 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS (9977 文件) |
| 模組導入 | ✅ PASS (8/8) |
| 感官引擎真實數據 | ❌ FAIL（`cannot import name 'normalize_feature' from 'server.senses'`）|
| 前端 TypeScript | ✅ PASS |
| 數據品質 | ✅ PASS |

## 模型訓練

- Global: Train=63.92%, CV=51.39%±3.66%, gap=12.53pp（持平），**73 features**, 9106 samples
- Positive ratio: 30.45%
- Regime models: bear/bull/chop 各 98 features saved
- ✅ **本次train.py成功** — 訓練完整

> Heartbeat #573: full_ic 5/22全域, **13/22 TW-IC 維持歷史新高**（持平！）, regime Bear 4/8, Bull 0/8 Chop 0/8, DW N=100&200 **7/8持平**, N=400 3/8, N=600持續0/8死區, 測試5/6(持平), 平行心跳**4/5 PASS**🟢(37.2s), sell_win **40.37%**（持平）, T63.92%/CV51.39%(持平), BTC **$68,556**(+$49微升), FR ⬆️ **0.00003672**(+8.7%加速回升！), LSR 1.2341(+15bps持續回升), OI 91,194(+1), **數據管線持續增長：Raw+8, Features+8**！測試持續 5/6（`normalize_feature` import 錯誤未解）。
