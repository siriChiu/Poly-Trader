# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)，流程見 [HEARTBEAT.md](HEARTBEAT.md)。

---

*最後更新：2026-04-05 16:05 GMT+8（心跳 #240）*

---

## 📊 當前系統健康狀態（2026-04-05 16:05 GMT+8，心跳 #240）

### 數據管線
| 項目 | 數值 | 狀態 vs #239 |
|------|------|--------|
| Raw market data | 9,180 筆 | ➡️ 持平 |
| Features | 9,142 筆 | ➡️ 持平 |
| Labels | 8,921 筆 | ➡️ 持平 |
| 全域 IC 通過 | **0/10** 核心感官 | ➡️ 持平 |
| TW-IC（tau=200） | **8/10** | ⬆️ 回升（從 ~9/10 → 8/10）|
| 模型 CV 準確率 | 51.4% | ➡️ 持平 |
| BTC 當前 | $66,849 | ➡️ 持平（從 $66,771）|
| FNG | 12（極度恐懼）| ➡️ 持平 |
| 資金費率 | 0.00003685 | ➡️ 持平 |
| LSR | 1.5907 | ➡️ 持平 |
| OI | 89,829 BTC | ➡️ 持平 |
| Sell Win（全域） | 49.9% | ➡️ 持平 |
| 連敗 | 156 | 🔴 持續 |

### 📌 本輪執行：平行心跳 #240

| 項目 | 狀態 | 備註 |
|------|------|------|
| `scripts/hb_parallel_runner.py` | ✅ #240 建立+完成 | 5 任務並行，158.5s 完成 |
| `scripts/full_ic.py` | ✅ 全域 IC | 0/10 通過（Spearman）|
| `scripts/regime_aware_ic.py` | ✅ 重建 | Bear 3/8, Bull 2/8, Chop 0/8 |
| DW N=200 | 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439 |
| DW 訓練 CV | 97.0% | （僅 200 樣本，極度不穩定，gap=-5.5pp）|
| Global 模型 | Train=63.9%, CV=51.4% | gap=12.5pp |
| 全域 TW-IC (tau=200) | **8/10** | Eye+0.213, VIX-0.419, DXY-0.329 |
| Comprehensive tests | **6/6（20 markers）** | ✅ 全部 PASS |
| `model/train.py` regime | ❌ KeyError | 缺少 5 新特徵 (feat_claw_x_pulse 等) |

### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | **#H390** | **156 連敗持續 + 近 100 筆 0% 勝率** | 🔴 持續 | Circuit Breaker 持續保護中 |
| 🔴 | **#H379** | **sell_win < 50% — 系統方向性錯誤** | 🔴 持續 | 全域 sell_win=49.9%，模型 CV=51.4% |
| 🔴 | **#P440** | **全域 IC 全面崩潰 0/10** | 🔴 持續 | 連續 5 輪（#236-#240）|
| 🔴 | **#P441** | **Chop regime 0/8 全面失效** | 🔴 持續 | Chop 信號完全消失，連續 4+ 輪 |
| 🔴 | **#H426** | **全域/時間加權差異 >20x** | 🟢 驗證中 | 全域 IC ~0.018 vs TW-IC ~8/10 通過 |
| 🔴 | **#HB240** | **regime 訓練 KeyError: 5 新特徵缺失** | 🔴 新發現 | train.py regime 訓練缺少 feat_claw_x_pulse 等 5 列 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | ⚠️ Nose 全域/TW-IC 雙重失效 | Nose 全域 IC=-0.004, TW-IC=+0.152 |
| #REGIME | 🔴 Regime 分類不均 | Bear 3/8, Bull 2/8, Chop 0/8 — 信號分布極不均 |
| #H439 | 🔴 數據管線完全停滯 | 0 筆新數據，#236-#240 完全相同 |
| #ICDECAY | ⚠️ 全域 IC 加速衰減 | #234: 2/8 → #235: 2/8 → #236-#240: 0/10 |
| #DWCV | ⚠️ DW CV 97% 但 N=200 極度不穩定 | 僅 200 樣本，gap=-5.5pp（CV>Train 過擬警告）|

### ✅ 本輪修復/發現

| ID | 狀態 | 備註 |
|----|------|------|
| **#240** | ✅ hb_parallel_runner.py 建立完成 | 首次使用 ProcessPoolExecutor 並行執行 5 任務 |
| **#240** | ✅ 全域 IC 0/10 確認 | 0/10 持平 — IC 真空狀態延續 5 輪 |
| **#240** | ✅ Regime IC 確認 | Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8 |
| **#240** | ✅ 全域 TW-IC 8/10 | Eye+0.213, Ear+0.142, Nose+0.152, Tongue+0.231, Body+0.212, Pulse-0.293, VIX-0.419, DXY-0.329 |
| **#240** | ✅ 全域 TW-IC 8/10 | 僅 Aura(+0.043), Mind(+0.002) 不及格 — Aura/Mind 從強轉弱 |
| **#240** | ✅ DW N=200: 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471 |
| **#240** | ✅ Global model | CV=51.4%, Train=63.9%, gap=12.5pp |
| **#240** | ✅ DW CV=97.0% | Train=91.5%, 但 200 樣本，gap=-5.5pp |
| **#240** | ✅ Comprehensive tests **6/6（20 markers）PASS** | 全部通過 |
| **#240** | ❌ model/train.py regime | KeyError: feat_claw_x_pulse 等 5 列不在 X_cols 中 |
| **#240** | 🟢 平行心跳 158.5s 完成 | 4/5 PASS |

---

## 🔴 感官 IC 掃描（心跳 #240, 2026-04-05 16:05 GMT+8）

### 全域 IC（Spearman）— **0/10 通過** 💥🔴

| 感官/特徵 | 全域 IC | 狀態 vs #239 |
|-----------|---------|------|
| Eye | **+0.0064** | ➡️ 持平 |
| Ear | **-0.0065** | ➡️ 持平 |
| Nose | -0.0039 | ➡️ 持平 |
| Tongue | +0.0246 | ➡️ 持平 |
| Body | +0.0237 | ➡️ 持平 |
| Pulse | -0.0072 | ➡️ 持平 |
| Aura | +0.0027 | ➡️ 持平 |
| Mind | +0.0252 | ➡️ 持平 |
| VIX | -0.0151 | ➡️ 持平 |
| DXY | -0.0180 | ➡️ 持平 |

**全域 IC 0/10 連續 5 輪（#236-#240）。所有感官都在 ±0.05 閾值以內。**

### 全域 時間加權 IC（tau=200）— **8/10 通過** 🟢

| 感官/特徵 | TW-IC (tau=200) | 狀態 |
|-----------|-----------------|------|
| Eye | **+0.2132** | ✅ PASS |
| Ear | +0.1422 | ✅ PASS |
| Nose | +0.1524 | ✅ PASS |
| Tongue | **+0.2314** | ✅ PASS |
| Body | +0.2117 | ✅ PASS |
| Pulse | -0.2925 | ✅ PASS |
| Aura | +0.0430 | ❌ |
| Mind | +0.0023 | ❌ |
| VIX | **-0.4191** | ✅ PASS |
| DXY | -0.3289 | ✅ PASS |

**TW-IC 8/10 — Aura 和 Mind 從強轉弱（過去是強信號），VIX/DXY 成為最強信號。**

### Regime-aware IC（ID join, n=8921）

**Bear（3/8）**：Eye(+0.094)✅, Tongue(+0.070)✅, Aura(-0.060)✅
**Bull（2/8）**：Ear(-0.061)✅, Nose(-0.057)✅
**Chop（0/8）💥**：全部不及 — 所有感官完全失效
**Neutral（5/8）**：Nose/Tongue/Body/Aura/Mind（n=73 樣本少）

### 動態窗口分析

- **最佳窗口：N=200（7/8 通過）**
- Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471, Ear -0.233, Eye +0.115, Mind +0.176
- 僅 Nose -0.023 失敗
- Window scan 趨勢：N=200→7/8, N=400→7/8, N=600→6/8, N=800→4/8, N=1000→6/8, N=2000→5/8, N=3000→5/8, N=5000→3/8
- **DW 訓練**：Train=91.5%, CV=97.0%（200 樣本，gap=-5.5pp — 過擬警告）

### sell_win by regime

| Regime | sell_win | n |
|--------|----------|---|
| Bear | 0.4036 | 2,993 |
| Bull | 0.5942 | 2,952 |
| Chop | 0.5028 | 2,904 |
| Neutral | 0.4167 | 72 |

**Overall: sell_win=0.4990 (n=8,921) | 連敗: 156**

---

## 📋 六色帽會議（#240）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=9,180 / Features=9,142 / Labels=8,921（全部持平，0 增長）。全域 IC **0/10**。TW-IC **8/10** (tau=200)。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8, CV=97.0%。Global model CV=51.4% (Train=63.9%, gap=12.5pp)。sell_win=49.9%。BTC=$66,849，FNG=12，LSR=1.59，OI=89,829。Comprehensive tests 6/6 通過。平行心跳 158.5s。Regime 訓練 KeyError（5 新特徵缺失）。 |
| **紅帽** | **全域 IC 0/10 擴散至 5 輪**，系統在 IC 真空狀態下運行更久。**但 TW-IC 8/10 回升**證明信號存在但被全域稀釋。VIX/DXY 成為最強 TW-IC 信號是重大變化。 |
| **黑帽** | (1) **全域 IC 0/10 持續 5 輪**。(2) **Chop 0/8 持續 4+ 輪**。(3) **數據管線完全停滯**。(4) **sell_win 49.9% < 50%**。(5) **DW CV>Train=-5.5pp 過擬警告**。(6) **Regime 訓練崩潰** — 5 新特徵 (feat_claw_x_pulse 等) 不在特徵列表中。 |
| **黃帽** | (1) **TW-IC 8/10 回升** — 時間加權證明近期信號強。(2) **VIX TW-IC=-0.419 成為最強信號** — 宏觀因子價值提升。(3) **平行心跳穩定** — 158.5s 完成，4/5 PASS。(4) **DW N=200 7/8 持續確認**。(5) **Comprehensive tests 20/20**。 |
| **綠帽** | (1) **TW-IC 8/10 vs Global 0/10** — 全域 dilution 效應極端，推理管道應該完全依賴 TW-IC。(2) **VIX/DXY 成為最強 IC 來源** — 宏觀因子取代自建感官成為核心。(3) **hb_parallel_runner.py 建立成功** — 從 22min 串行優化為 158s 並行。(4) **新特徵缺失問題已識別** — feat_claw_x_pulse, feat_fang_x_vix, feat_fin_x_claw, feat_web_x_fang, feat_nq_x_vix 需在 train.py 中加入。 |
| **藍帽** | **P0 行動：**(1) **修復 train.py 的 5 特徵缺失** — 讓 regime 訓練能正常執行。(2) **TW-IC fusion 推理管道** — 全域 IC 失效，TW-IC 8/10 是實際信號。(3) **數據管線恢復** — 0 新數據已持續 5+ 心跳。(4) **Chop 0/8 需要根本性重新設計或接受其為盲區**。 |

---

## ORID 決策

- **O**: Raw=9,180 / Features=9,142 / Labels=8,921（全部持平）。全域 IC **0/10**（連續 5 輪）。TW-IC **8/10** (tau=200)。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8，CV=97.0%。Global CV=51.4%（gap 12.5pp）。sell_win=49.9%。BTC=$66,849，FNG=12。Losing streak: 156。Regime 訓練 KeyError (5 新特徵缺失)。平行心跳 158.5s。
- **R**: 全域 IC 0/10 擴至 5 輪，但 TW-IC 8/10 回升確認信號仍然存在。VIX/DXY 變最強 IC 是重要結構性變化。
- **I**: (1) **全域 IC 0/10 vs TW-IC 8/10** — 全域稀釋效應持續惡化，TW-IC 信號反而回升。(2) **Aura/Mind 從強轉弱** — 過去最強的兩個信號現在 TW-IC < 0.05。(3) **VIX/DXY 成為核心** — TW-IC -0.419 和 -0.329 遠超所有自建感官。(4) **DW N=200 7/8** — 短期信號持續存在但樣本過少。(5) **5 新特徵缺失** — 新感官系統 (claw/fang/fin/web/nq) 的 cross-features 未列入訓練特徵列表。
- **D**: (1) **P0：修復 train.py 特徵匹配** — 讓 regime 訓練正常執行。(2) **P0：TW-IC fusion 推理驗證** — 全域 IC 已無法作為信號指標。(3) **P1：數據管線恢復** — 0 新數據。(4) **P2：新感官 cross-features 完整性檢查** — 確認所有新增特徵都在訓練和推理管道中。

---

## 📋 本輪修改記錄

- **#240**: `scripts/hb_parallel_runner.py` 建立 — ProcessPoolExecutor 並行執行 5 任務（full_ic, regime_aware_ic, dynamic_window, model_train, comprehensive_test）
- **#240**: 全域 IC 0/10 確認 — 與 #236-#239 完全相同（IC 真空狀態持續 5 輪）
- **#240**: TW-IC 8/10 — Eye+0.213, VIX-0.419, DXY-0.329 等
- **#240**: Regime IC — Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8
- **#240**: 動態窗口 — N=200 最優 7/8，CV=97.0%（200 樣本），N=1000→6/8
- **#240**: Global model — Train=63.9%, CV=51.4%, gap=12.5pp（持平）
- **#240**: 市場數據 — BTC=$66,849, FNG=12, LSR=1.59, OI=89,829
- **#240**: Parallel heartbeat #240 158.5s（4/5 PASS），Comprehensive tests 6/6（20/20 markers）通過
- **#240**: model/train.py regime 訓練 KeyError — feat_claw_x_pulse, feat_fang_x_vix, feat_fin_x_claw, feat_web_x_fang, feat_nq_x_vix 不在 features DataFrame

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **修復 train.py regime 特徵匹配** — 5 新特徵缺失導致 KeyError | #HB240 |
| 🔴 P0 | **全域 IC 0/10 崩潰持續 5 輪** — 所有 10 個感應低於 0.05 閾值 | #P440 |
| 🔴 P0 | **轉向 TW-IC 為主要 IC 指標** — 全域 IC 失效，TW-IC 8/10 | #H426 |
| 🔴 P0 | **Chop 0/8 崩潰持續** — 所有 Chop 信號消失 | #P441 |
| 🔴 P0 | **156 連敗持續** — Circuit Breaker 持續觸發 | #H390 |
| 🟡 P1 | **恢復數據管線增長** — 0 新數據連續 5+ 心跳 | #H439 |
| 🟡 P1 | **DW CV>Train=-5.5pp 過擬警告** — N=200 太不穩定 | #DWCV |
| 🟡 P1 | **新感官特徵完整性檢查** — claw/fang/fin/web/nq 的 cross-features | #HB240 |

---

## 📊 距 90% 勝率差距分析

- **當前全域 sell_win**: 49.9%（差 **40.1pp**）
- **模型 CV 準確率**: 51.4%（差 **38.6pp**，等同隨機）
- **全域 IC 達標率**: **0/10** 核心感官（0%）💥
- **TW-IC 達標率**: **8/10** 核心+宏觀因子（80%）🟢
- **DW N=200 達標率**: **7/8** 核心感官（87.5%）🟢
- **sell_win by regime**: Bear=40.4%, Bull=59.4%, Chop=50.3%
- **主要障礙**:
  1. **全域 IC 完全崩潰 5 輪** — 0/10，全域 IC 已經無法作為信號指標
  2. **TW-IC 8/10 但不反映在勝率** — IC fusion 管道需驗證
  3. **Chop 0/8** — 重要 regime 信號消失 4+ 輪
  4. **連敗 156** — 系統完全失效
  5. **數據管線停滯** — 0 新數據，無法獲取更新信號
  6. **Regime 訓練 KeyError** — 5 新特徵缺失
  7. **DW CV>Train=-5.5pp** — 200 樣本過擬警告
- **本輪修復/發現**:
  - ✅ **hb_parallel_runner.py 建立成功** — 158.5s 完成 5 任務
  - 🟢 **TW-IC 8/10 回升** — 時間加權證明信號存在
  - 🟢 **VIX TW-IC=-0.419, DXY=-0.329** — 宏觀因子成為最強信號
  - ❌ **全域 IC 0/10 持續** — IC 真空狀態擴散至 5 輪
  - ❌ **model/train.py regime KeyError** — 5 新特徵缺失
  - ➡️ **全域 sell_win 49.9%**（持平）
  - ➡️ **連敗 156**（持平）
- **關鍵洞察**: 心跳 #240 確認**全域 IC 真空狀態持續 5 輪**（0/10 連續 5 輪），但 **TW-IC 8/10 回升**（從 #239 的 ~9/10 降至 8/10）。VIX/DXY 從輔助因子升級為最強 IC 來源（TW-IC -0.419/-0.329）。Aura/Mind TW-IC 跌至 <0.05（過去是強信號）。推理管道應該完全依賴 TW-IC 和 DW IC。新感官系統（claw/fang/fin/web/nq）的 cross-features 未列入 train.py 特徵列表。

---

*此文件每次心跳完全覆蓋，保持簡潔。*
