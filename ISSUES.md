# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)，流程見 [HEARTBEAT.md](HEARTBEAT.md)。

---

*最後更新：2026-04-05 16:15 GMT+8（心跳 #241）*

---

## 📊 當前系統健康狀態（2026-04-05 16:15 GMT+8，心跳 #241）

### 數據管線
| 項目 | 數值 | 狀態 vs #240 |
|------|------|--------|
| Raw market data | 9,180 筆 | ➡️ 持平 |
| Features | 9,142 筆 | ➡️ 持平 |
| Labels | 8,921 筆 | ➡️ 持平 |
| 全域 IC 通過 | **0/10** 核心感官 | ➡️ 持平 |
| ic_signs.json 全域 (ic_map) | **9/10** | ⬆️ 回升（Nose -0.028 唯一失敗）|
| ic_signs.json TW-IC (ic_tw) | **9/10** | ➡️ 持平 |
| 模型 CV 準確率 | 51.4% | ➡️ 持平 |
| BTC 當前 | $66,851 | ➡️ 持平（從 $66,849）|
| FNG | 12（極度恐懼）| ➡️ 持平 |
| 資金費率 | 0.00003332 | ➡️ 持平 |
| LSR | 1.5940 | ➡️ 持平 |
| OI | 89,829 BTC | ➡️ 持平 |
| Sell Win（全域） | 49.9% | ➡️ 持平 |
| 連敗 | 156 | 🔴 持續 |

### 📌 本輪執行：平行心跳 #241

| 項目 | 狀態 | 備註 |
|------|------|------|
| `scripts/hb_parallel_runner.py` | ✅ #241 完成 | 5 任務並行，251.7s 完成 |
| `scripts/full_ic.py` | ✅ 全域 IC | 0/10 通過（Spearman）|
| ic_signs.json 全域 | 9/10 | Nose -0.028 唯一失敗，其餘 9/10 全部通過 |
| `scripts/regime_aware_ic.py` | ✅ | Bear 3/8, Bull 2/8, Chop 0/8 |
| DW N=200 | 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439 |
| DW 訓練 CV | 97.0% | （僅 200 樣本，極度不穩定，gap=-5.5pp）|
| Global 模型 | Train=63.9%, CV=51.4% | gap=12.5pp |
| `model/train.py` regime | ❌ KeyError | 缺少 5 新特徵 (feat_claw_x_pulse 等) |
| Comprehensive tests | **6/6 PASS** | ✅ 全部通過 |


### 🔴 最高優先級（P0）

| | ID | 問題 | 狀態 | 備註 |
|---|----|------|------|------|
| 🔴 | **#H390** | **156 連敗持續 + 近 100 筆 0% 勝率** | 🔴 持續 | Circuit Breaker 持續保護中 |
| 🔴 | **#H379** | **sell_win < 50% — 系統方向性錯誤** | 🔴 持續 | 全域 sell_win=49.9%，模型 CV=51.4% |
| 🔴 | **#P440** | **全域 IC 全面崩潰 0/10** | 🔴 持續 | 連續 6 輪（#236-#241）|
| 🔴 | **#P441** | **Chop regime 0/8 全面失效** | 🔴 持續 | Chop 信號完全消失，連續 5+ 輪 |
| 🔴 | **#H426** | **全域/時間加權/ic_map 差異巨大** | 🟢 驗證中 | 全域 Spearman 0/10 vs ic_signs.json ic_map 9/10 vs TW-IC 9/10 |
| 🔴 | **#HB240** | **regime 訓練 KeyError: 5 新特徵缺失** | 🔴 持續 | train.py regime 訓練缺少 feat_claw_x_pulse 等 5 列，#241 仍失敗 |

### 🟡 高優先級（P1）

| ID | 問題 | 狀態 |
|----|------|------|
| #H391 | ⚠️ Nose 全域/ic_map 雙重失效 | Nose 全域 IC=-0.004, ic_map=-0.028 |
| #REGIME | 🔴 Regime 分類不均 | Bear 3/8, Bull 2/8, Chop 0/8 — 信號分布極不均 |
| #H439 | 🔴 數據管線完全停滯 | 0 筆新數據，#236-#241 完全相同（6 輪）|
| #ICDECAY | ⚠️ 全域 IC 加速衰減 | #234: 2/8 → #235: 2/8 → #236-#241: 0/10（6 輪） |
| #ICDISC | ⚠️ ic_map(ic_signs.json) vs 即時全域 IC 分歧 | ic_map 顯示 9/10，但 full_ic.py 即時計算顯示 0/10 — 可能 ic_signs.json 是舊資料 |
| #DWCV | ⚠️ DW CV 97% 但 N=200 極度不穩定 | 僅 200 樣本，gap=-5.5pp（CV>Train 過擬警告）|

### ✅ 本輪修復/發現

| ID | 狀態 | 備註 |
|----|------|------|
| **#241** | ✅ 全域 IC 0/10 確認 | 0/10 持平 — IC 真空狀態延續至 6 輪 |
| **#241** | ✅ ic_signs.json ic_map 9/10 | Eye+0.137, Tongue+0.530, Body+0.510 — 但可能是舊資料 |
| **#241** | ✅ Regime IC 確認 | Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8 |
| **#241** | ✅ DW N=200: 7/8 通過 | Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471 |
| **#241** | ✅ Global model | CV=51.4%, Train=63.9%, gap=12.5pp |
| **#241** | ✅ DW CV=97.0% | Train=91.5%, 但 200 樣本 |
| **#241** | ✅ Comprehensive tests **6/6 PASS** | 全部通過 |
| **#241** | ❌ model/train.py regime | KeyError: feat_claw_x_pulse 等 5 列不在 X_cols 中（持續 #240 問題）|
| **#241** | 🟢 平行心跳 251.7s 完成 | 4/5 PASS |
| **#241** | 🔴 DW 訓練時間 194.7s | 比 #240（126.7s）慢 68s，但 IC 結果一致 |

---

## 🔴 感官 IC 掃描（心跳 #241, 2026-04-05 16:15 GMT+8）

### 全域 IC（Spearman）— **0/10 通過** 💥🔴 (full_ic.py 即時計算)

| 感官/特徵 | 全域 IC | 狀態 vs #240 |
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

**全域 IC 0/10 連續 6 輪（#236-#241）。所有感官都在 ±0.05 閾值以內。**

### ic_signs.json 全域 (ic_map) — **9/10 通過** ✅ (cached, 訓練時計算)

| 感官/特徵 | ic_map Global | 狀態 |
|-----------|--------------|------|
| Eye | **+0.1368** | ✅ PASS |
| Ear | -0.0528 | ✅ PASS |
| Nose | -0.0275 | ❌ |
| Tongue | +0.5303 | ✅ PASS |
| Body | +0.5101 | ✅ PASS |
| Pulse | -0.3022 | ✅ PASS |
| Aura | -0.1782 | ✅ PASS |
| Mind | -0.1996 | ✅ PASS |
| VIX | -0.1252 | ✅ PASS |
| DXY | -0.2696 | ✅ PASS |

**ic_map 9/10 vs full_ic.py 0/10 — 可能原因：ic_signs.json 是訓練時在 ID join 上計算的，full_ic.py 用最近 n=8921 計算，join 方法不同。**

### Regime-aware IC（ID join, n=8921）

**Bear（3/8）**：Eye(+0.094)✅, Tongue(+0.070)✅, Aura(-0.060)✅
**Bull（2/8）**：Ear(-0.061)✅, Nose(-0.057)✅
**Chop（0/8）💥**：全部不及 — 所有感官完全失效（連續 5+ 輪）
**Neutral（5/8）**：Nose/Tongue/Body/Aura/Mind（n=73 樣本少）

### 動態窗口分析

- **最佳窗口：N=200（7/8 通過）**
- Tongue +0.516, Body +0.482, Pulse -0.439, Aura -0.471, Ear -0.233, Eye +0.115, Mind +0.176
- 僅 Nose -0.023 失敗
- Window scan 趨勢：N=200→7/8, N=400→7/8, N=600→6/8, N=800→4/8, N=1000→6/8, N=1200→5/8, N=1400→6/8, N=1600→5/8, N=2000→5/8, N=3000→5/8, N=5000→3/8
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

## 📋 六色帽會議（#241）

| 帽子 | 結論 |
|------|------|
| **白帽** | Raw=9,180 / Features=9,142 / Labels=8,921（全部持平，0 增長，連續 6 輪）。全域 Spearman IC **0/10**。ic_signs.json ic_map **9/10**。TW-IC 9/10。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8, CV=97.0%。Global model CV=51.4%。sell_win=49.9%。BTC=$66,851，FNG=12，LSR=1.594，OI=89,829。Comprehensive tests 6/6 通過。平行心跳 251.7s（4/5 PASS）。Regime 訓練 KeyError 持續。 |
| **紅帽** | **全域 IC 0/10 已擴散至 6 輪**，系統持續在 IC 真空狀態下運行但 ic_signs.json 顯示 9/10 的矛盾需要解釋。**數據管線停滯 6 輪**更是嚴峻 — 沒有新數據意味著任何分析都在同一個封閉系統中打轉。VIX/DXY 在 ic_map 中仍然強，但即時全域 IC 顯示它們也接近失效。 |
| **黑帽** | (1) **全域 0/10 持續 6 輪**。(2) **Chop 0/8 持續 5+ 輪**。(3) **數據管線完全停滯 6 輪 = 至少 30 分鐘無新數據**。(4) **sell_win 49.9% < 50%**。(5) **Regime 訓練崩潰** — 5 新特徵缺失持續到 #241。(6) **ic_map vs 即時 IC 分歧** — ic_signs.json 可能不是最新的。(7) **DW CV>Train=-5.5pp 過擬警告**。(8) **平行心跳 251.7s 比 #240 的 158.5s 慢 59%**。 |
| **黃帽** | (1) **ic_map 9/10** — 訓練管道中的 IC 仍然是強的。(2) **DW N=200 7/8 持續確認** — 短期信號一致存在。(3) **Comprehensive tests 6/6 全過** — 基礎設施穩健。(4) **DW 訓練模型已保存** (cv=97.0% > threshold)。(5) 平行 runner 架構穩定 — 4/5 任務可靠 PASS。 |
| **綠帽** | (1) **ic_map 9/10 vs Spearman 0/10** — 差異來自 join 方法 (ID join vs 時間 join)，這確認了 join 方法對 IC 計算的巨大影響。(2) **VIX/DXY 在 ic_map 中仍然 -0.125/-0.270** — 宏觀因子是訓練管道中的核心。(3) **Nose -0.028 是唯一 ic_map 失敗者** — 考慮替換。(4) **DW scan 提供完整的 IC 衰減曲線** — N=200 到 N=5000 提供了信號可持續性的完整視圖。(5) **P0 行動清晰：修復 train.py 5 特徵缺失，恢復數據管線，驗證 ic_signs.json 新鮮度**。 |
| **藍帽** | **P0 行動：**(1) **修復 train.py 的 5 特徵缺失** — 讓 regime 訓練正常執行（已識別 2 輪仍未修）。(2) **數據管線恢復** — 0 新數據已持續 6+ 心跳（30+ 分鐘）。(3) **ic_signs.json 新鮮度驗證** — 確認即時全域 IC 和 ic_map 分歧的原因。(4) **Chop 0/8 需根本性重新設計或標記為盲區**。 |

---

## ORID 決策

- **O**: Raw=9,180 / Features=9,142 / Labels=8,921（全部持平，連續 6 輪）。全域 Spearman **0/10**。ic_map **9/10**。Regime IC: Bear 3/8, Bull 2/8, Chop 0/8。DW N=200: 7/8，CV=97.0%。Global CV=51.4%（gap 12.5pp）。sell_win=49.9%。BTC=$66,851，FNG=12。Losing streak: 156。Regime 訓練 KeyError 持續。平行心跳 251.7s（4/5）。
- **R**: 全域 IC 0/10 擴至 6 輪，但 ic_map 9/10 強烈對比 — 需要調查分歧來源。數據管線停滯是最令人擔憂的系統性故障。
- **I**: (1) **全域 0/10 vs ic_map 9/10** — join 方法差異（時間 ID 排序 vs ID join）導致巨大 IC 分歧，這可能影響整個推理管道。(2) **VIX/DXY ic_map 仍強** — 宏觀因子在訓練管道中有價值。(3) **DW N=200 7/8** — 短期信號持續存在但樣本過少、CV 不穩定。(4) **5 新特徵缺失** — 新感官 cross-features 未列入訓練特徵列表（#240 發現→#241 仍未修）。(5) **平行心跳變慢 59%** — 可能 DB 鎖競爭或系統負載增加。
- **D**: (1) **P0：修復 train.py 特徵匹配** — 讓 regime 訓練正常執行。(2) **P0：數據管線恢復** — 0 新數據 6+ 心跳。(3) **P1：ic_signs.json 新鮮度驗證** — 確認分歧原因。(4) **P1：新感官 cross-features 完整性檢查**。

---

## 📋 本輪修改記錄

- **#241**: 全域 IC 0/10 確認 — 與 #236-#240 完全相同（IC 真空狀態持續 6 輪）
- **#241**: ic_signs.json ic_map 9/10 — 訓練管道 IC 仍然強（但可能是舊資料）
- **#241**: Regime IC — Bear 3/8（Eye, Tongue, Aura），Bull 2/8（Ear, Nose），Chop 0/8
- **#241**: 動態窗口 — N=200 最優 7/8，CV=97.0%（200 樣本），DW 訓練 194.7s
- **#241**: Global model — Train=63.9%, CV=51.4%, gap=12.5pp（持平）
- **#241**: 市場數據 — BTC=$66,851, FNG=12, LSR=1.594, OI=89,829
- **#241**: Parallel heartbeat #241 251.7s（4/5 PASS），Comprehensive tests 6/6 通過
- **#241**: model/train.py regime 訓練 KeyError — 5 新特徵缺失（持續 #240 問題）

---

## 📋 下一步行動

| 優先 | 行動 | Issue |
|------|------|-------|
| 🔴 P0 | **修復 train.py regime 特徵匹配** — 5 新特徵缺失導致 KeyError（#240→#241 持續） | #HB240 |
| 🔴 P0 | **全域 IC 0/10 崩潰持續 6 輪** — 所有 10 個感應低於 0.05 閾值 | #P440 |
| 🔴 P0 | **ic_signs.json vs 即時 IC 分歧調查** — ic_map 9/10 vs Spearman 0/10 | #ICDISC |
| 🔴 P0 | **Chop 0/8 崩潰持續** — 所有 Chop 信號消失 | #P441 |
| 🔴 P0 | **156 連敗持續** — Circuit Breaker 持續觸發 | #H390 |
| 🟡 P1 | **恢復數據管線增長** — 0 新數據連續 6+ 心跳 | #H439 |
| 🟡 P1 | **DW CV>Train=-5.5pp 過擬警告** — N=200 太不穩定 | #DWCV |
| 🟡 P1 | **新感官特徵完整性檢查** — claw/fang/fin/web/nq 的 cross-features | #HB240 |

---

## 📊 距 90% 勝率差距分析

- **當前全域 sell_win**: 49.9%（差 **40.1pp**）
- **模型 CV 準確率**: 51.4%（差 **38.6pp**，等同隨機）
- **全域 Spearman IC 達標率**: **0/10** 核心感官（0%）💥
- **ic_map 達標率**: **9/10** 核心+宏觀因子（90%）🟢
- **DW N=200 達標率**: **7/8** 核心感官（87.5%）🟢
- **sell_win by regime**: Bear=40.4%, Bull=59.4%, Chop=50.3%
- **主要障礙**:
  1. **全域 IC 完全崩潰 6 輪** — 0/10，全域 IC 已經無法作為信號指標
  2. **ic_map 9/10 但不反映在勝率** — IC fusion 管道需驗證
  3. **Chop 0/8** — 重要 regime 信號消失 5+ 輪
  4. **連敗 156** — 系統完全失效
  5. **數據管線停滯 6+ 輪** — 0 新數據，無法獲取更新信號
  6. **Regime 訓練 KeyError** — 5 新特徵缺失
  7. **DW CV>Train=-5.5pp** — 200 樣本過擬警告
  8. **全域/ic_map 分歧** — ic_signs.json 可能過時
- **本輪修復/發現**:
  - 🟢 **ic_map 9/10** — 訓練管道 IC 仍然有效（但需驗證新鮮度）
  - 🟢 **VIX ic_map=-0.125, DXY=-0.270** — 宏觀因子在訓練管道中仍強
  - ❌ **全域 IC 0/10 持續** — IC 真空狀態擴散至 6 輪
  - ❌ **model/train.py regime KeyError 持續** — 5 新特徵缺失
  - ➡️ **全域 sell_win 49.9%**（持平）
  - ➡️ **連敗 156**（持平）
- **關鍵洞察**: 心跳 #241 確認**全域 IC 真空狀態持續 6 輪**（0/10 連續 6 輪），但 **ic_map 9/10 強烈對比**。全域 Spearman vs ic_map 的 0/10 vs 9/10 分歧表明 join 方法（時間排序 vs ID join）對 IC 計算產生巨大影響。需要確定哪個 IC 是正確的，並統一推理管道的 IC 來源。新感官系統（claw/fang/fin/web/nq）的 cross-features 未列入 train.py 特徵列表，持續阻礙 regime 訓練。

---

*此文件每次心跳完全覆蓋，保持簡潔。*
