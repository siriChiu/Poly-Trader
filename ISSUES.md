# ISSUES.md — 問題追蹤

*最後更新：2026-04-07 08:30 UTC（心跳 #580）*

## 📊 系統健康狀態（#580）

| 項目 | 數值 | vs #579 |
|------|------|---------|
| Raw | **9,899** | ➡️ 持平（+0）⚠️ |
| Features | **9,858** | ➡️ 持平（+0）⚠️ |
| Labels | **18,052** | ➡️ 持平 |
| sell_win (DB all) | **40.37%** | ➡️ 持平 |
| sell_win (regime join) | **49.24%** | ➡️ 持平（n=8770）|
| 全域 IC (22 擴） | **5/22** | ➡️ 持平 |
| TW-IC (22 擴） | **13/22** | ➡️ 持平（歷史新高維持）|
| DW N=100 | **7/8**🟢 | ➡️ 持平 |
| DW N=200 | **7/8**🟢 | ➡️ 持平 |
| DW N=400 | **3/8** | ➡️ 持平 |
| DW N=600 | **0/8** 🔴 | ➡️ 持續死區 |
| DW N=1000 | **4/8** | ➡️ 持平 |
| Global model | Train=63.92%, CV=51.39%, gap=12.53pp | ➡️ 持平 |
| Regime IC | Bear **4/8**, Bull **0/8**🔴, Chop **0/8**🔴 | ➡️ 持平 |
| BTC (live) | **$68,797** | ⬆️ +$84（vs #579 $68,713）|
| FNG | **11**（持續極度恐懼）| ➡️ 持平 |
| FR | **0.00004026** | ⬆️ +1.8%（vs #579 0.00003955，續升）|
| LSR | **1.2665** | ⬆️ +51bps（vs #579 1.2614，持續上升！）|
| OI | **91,087** | ⬆️ +40（vs #579 91,047）|
| 測試 | **6/6** ✅ | ⬆️ TypeScript PASS！|
| 平行心跳 | **5/5 PASS** 🟢（**12.9s**）| ⬆️ 全通過！|

## 系統狀態：🟢 全面通過 / BTC回升 / LSR續升 / FR續升 / 測試6/6 / TypeScript已修復

平行心跳 5/5 PASS（12.9s），5項任務全部成功。
測試套件恢復 6/6 PASS（TypeScript 編譯現已通過！）。
⚠️ Raw/Features +0（持平）：數據管線**停止增長**，自 #579 起凍結。
LSR 持續上升至 1.2665（+51bps）：多頭長倉比例持續上升。
FR 續升至 0.00004026（+1.8%）：資金費率持續回升。
BTC 回升至 $68,797（+$84 vs #579）。

- **BTC $68,797**: ⬆️ +$84 vs #579 $68,713，持續回升
- **⬆️ FR 0.00004026（+1.8%）**: 資金費率持續回升，多頭信心增強
- **⬆️ LSR 1.2665（+51bps）**: 長倉比例持續上升，多頭信心增強
- **⬆️ OI 91,087（+40）**: 持倉量微升
- **✅ 5/5 PASS**: 平行心跳全部通過
- **raw +0, features +0**: ⚠️ 數據管線停止增長
- **測試 6/6 ✅**: TypeScript 編譯已修復，全部通過
- **DW 持續**: N=100&200 7/8🟢，N=400 3/8，N=600 持續 0/8 死區
- **訓練**: 73 features, 9106 samples, CV=51.39%（持平）
- **Regime**: Bear 4/8（持續）, Bull 0/8🔴（200+輪持續！）, Chop 0/8🔴（200+輪持續！）

## 全域 IC — 5/22（持平）

**22 擴（全域 Spearman, 含4H/5TI特徵）**: 5/22 passing。
PASS: VIX +0.0714 ✅, RSI14 +0.0542 ✅, MACDHist +0.0505 ✅, BB%B +0.0575 ✅, Nose +0.0500 ✅（擦邊）

**TW-IC（13/22 過, tau=200, 維持新高）**: Nose+0.0587, Pulse-0.0871, AURA+0.0799, Mind+0.0750, VIX+0.0876, RSI14+0.0746, MACD+0.0554, ATR%-0.1280, VWAP+0.1293, BB%B+0.0826, 4h_bias50+0.0715, 4h_rsi14+0.0622, 4h_dist_swing_low+0.0620
FAIL: Eye, Ear, Tongue, Body, DXY (core 8 中有 5 個失效); 4h_bias20, 4h_macd_hist, 4h_bb_pct_b, 4h_ma_order 失敗

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
| Chop | **0/8**🔴 | 全部 <0.05（200+輪持續！）|

**sell_win by Regime**: Bear=0.4855, Bull=0.5090, Chop=0.4829, Overall=0.4924（n=8770）

## 市場數據亮點

- **BTC $68,797**: ⬆️ +$84（+0.12%）vs #579 $68,713，持續回升
- **⬆️ FR 0.00004026**: +1.8%續升，資金費率持續改善
- **⬆️ LSR 1.2665**: 長倉比例持續上升（+51bps），多頭信心持續增強
- **⬆️ OI 91,087（+40）**: 持倉量微升
- **FNG 11**（持續極度恐慌）

## ✅ TypeScript 編譯已修復！

`src/pages/StrategyLab.tsx` 的 JSX 語法錯誤（`>` 符號未轉義）已修復。測試套件現已 **6/6 PASS**（從 5/6 恢復）。Issue #TS_FAIL 已解。

## P0

| ID | 問題 | 狀態 |
|----|------|------|
| #P537 | sell_win≥50% 全域 | 🔴 **持續 40.37%（全量Labels），regime子集49.24%** |
| #RAW_STALE | Raw 數據增長 | ⚠️ **停止增長！**（+0 vs #579，管線再次凍結）|
| #P442 | Chop 0/8 | 🔴 持續 0/8（200+輪）|
| #BULL_BLIND | Bull 0/8 | 🔴 Bull 0/8 持續（200+輪持續！）|
| #FEATURE_MISMATCH | 4H 特徵 | 🟢 **100% 回填完成，7/7 欄位非零** |
| #TS_FAIL | TypeScript 編譯 | 🟢 **已修復 — 6/6 PASS** |
| #NO_DATA | 新感官零數據（Claw/Fang/Fin）| 🔴 Collector 未收集 |
| #DW_DEAD | DW N=600/5000 死區 | 🔴 持續 0/8 |

## ✅ 完成清單 v4.0

- [x] 4H 結構線距離特徵 100% 回填（bias50, bias20, rsi14, macd_hist, bb_pct_b, ma_order, dist_swing_low）
- [x] API `/api/senses` 回傳 22 特徵 + `raw` 欄位
- [x] Web Dashboard 4H 結構線儀表板（牛熊、位置、操作建議）
- [x] ECDF 錨點重新計算（全量資料）
- [x] WebSocket `/ws/live` 支援全部 22 特徵
- [x] 策略實驗室（Strategy Lab）：參數調整 + 回測 + Leaderboard
- [x] `/api/strategies/*` API（run save / leaderboard / get / delete）
- [x] TypeScript 編譯修復

### Phase 14: 策略實驗室（Strategy Lab） — MVP 已完成
- ✅ 規則引擎：金字塔 + SL/TP + 4H 過濾 + 感官條件
- ✅ Web 面板：3 個預設值 + 參數表單 + 執行按鈕
- ✅ Leaderboard：所有已儲存策略依 ROI 排
- ✅ 基準對比：買入持有 vs 盲金字塔 vs 你的策略
- 🔄 下一步：ML 模型模式、混合模式、市場分類回測

## 測試狀態

| 測試 | 結果 |
|------|------|
| 檔案結構 | ✅ PASS |
| 語法檢查 | ✅ PASS (9979 文件) |
| 模組導入 | ✅ PASS (8/8) |
| 感官引擎真實數據 | ✅ PASS |
| 前端 TypeScript | ✅ PASS（已修復！） |
| 數據品質 | ✅ PASS |

## 模型訓練

- Global: Train=63.92%, CV=51.39%±3.66%, gap=12.53pp（持平），**73 features**, 9106 samples
- Positive ratio: 30.45%
- Regime models: bear/bull/chop 各 98 features saved
- ✅ **train.py 成功** — 訓練完整（3 regimes saved）

> Heartbeat #580: full_ic 5/22全域, **13/22 TW-IC 維持新高**（持平！）, regime Bear 4/8, Bull 0/8 Chop 0/8, DW N=100&200 **7/8持平**, N=400 3/8, N=600持續0/8死區, 測試**6/6✅**(TS已修復), 平行心跳**5/5 PASS**🟢(12.9s), sell_win **40.37%**（持平）, T63.92%/CV51.39%(持平), BTC **$68,797**(+$84回升), FR ⬆️ **0.00004026**(+1.8%續升), LSR **1.2665**(+51bps持續上升), OI 91,087(+40), ⚠️**數據管線停止增長：Raw+0, Features+0**！
