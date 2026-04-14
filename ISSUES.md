# ISSUES.md — Current State Only

_最後更新：2026-04-14 18:20 UTC — Heartbeat #739（已把 bull exact-lane toxic sub-bucket 診斷接進 live predictor contract，並落地成「若 current bucket 本身就是 toxic bucket 則直接 veto」的可執行規則；當前 live q35 未被誤傷，但主 blocker 仍是 exact support 未滿）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#738）要求本輪處理
- **Next focus**：
  1. 把 `CAUTION|structure_quality_caution|q15` toxic pocket 升級成 machine-readable veto / rejection rule 候選；
  2. 在 q15 問題拆清後，重新檢查 `proxy_boundary_inconclusive` 是否可定稿；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 必須留下至少一個與 **q15 toxic pocket veto / proxy boundary 定稿** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。
- **Fallback if fail**：
  - 若 q15 veto 還不能穩定區分壞 pocket，下一輪至少把 `q15 / q35` 差異轉成更窄 proxy contract；
  - 若 q35 exact rows 持續卡住，繼續維持 `allowed_layers=0`；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `model/predictor.py` 新增 exact-lane `bucket_diagnostics / toxic_bucket / verdict / reason`，把 q15 toxic pocket 直接帶進 live decision-quality contract；
  - 若 current live structure bucket 本身就是 toxic bucket，現在會升級成 `toxic_sub_bucket_current_bucket` execution veto，直接把 `allowed_layers` 壓到 0；
  - `scripts/hb_predict_probe.py`、`scripts/hb_parallel_runner.py` 已同步輸出上述 machine-readable 欄位；
  - `tests/test_api_feature_history_and_predictor.py`、`tests/test_hb_parallel_runner.py` 已補 regression。
- **本輪觀察導致前提更新**：
  - current live bucket 仍是 **`CAUTION|structure_quality_caution|q35`**，而且 exact rows 已從 **13 → 18**，gap 從 **37 → 32**；
  - exact live lane 已從 **30 → 35 rows**；
  - toxic bucket 仍是 **`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0000）**；
  - `proxy_boundary_verdict` 仍是 **`proxy_boundary_inconclusive`**；
  - 本輪 live probe 的 veto 沒有被觸發，原因不是規則失效，而是 current bucket 不是 toxic q15。
- **本輪明確不做**：
  - 不因 q35 短期表現好就放寬 `allowed_layers=0`；
  - 不把 proxy rows 視為 exact support 已滿；
  - 不把 `fin_netflow` auth blocker 混進 bull lane 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/predictor.py`
    - 新增 exact live lane `exact_lane_bucket_diagnostics`；
    - 新增 `decision_quality_exact_live_lane_bucket_verdict / reason / toxic_bucket / bucket_diagnostics`；
    - 新增 `toxic_sub_bucket_current_bucket` guardrail：只有當 current bucket 本身就是 toxic bucket 時才 veto，避免誤傷 q35。
  - `scripts/hb_predict_probe.py`
    - probe JSON 現在直接序列化 exact-lane toxic sub-bucket diagnostics。
  - `scripts/hb_parallel_runner.py`
    - fast heartbeat summary 現在同步持久化上述 live predictor diagnostics。
  - `tests/test_api_feature_history_and_predictor.py`
    - 新增「q35 不被誤傷」與「toxic current bucket 會被 veto」測試。
  - `tests/test_hb_parallel_runner.py`
    - 新增 heartbeat 讀取新的 live predictor toxic-bucket diagnostics 測試。
  - `ARCHITECTURE.md`
    - 已同步 Heartbeat #739 exact-lane toxic sub-bucket veto contract。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **39 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_predict_probe.py` → live probe 已輸出 `decision_quality_exact_live_lane_bucket_verdict=toxic_sub_bucket_identified`；
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 739` → **通過**，新欄位已進 `data/live_predict_probe.json` 與 `data/heartbeat_739_summary.json`。

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #739：
  - Raw / Features / Labels：**21422 / 12851 / 42960**
  - 本輪增量：**+1 raw / +1 feature / +6 labels**
  - canonical target `simulated_pyramid_win`：**0.5755**
  - 240m labels：**21571 rows / target_rows 12649 / lag_vs_raw 3.3h**
  - 1440m labels：**12304 rows / target_rows 12304 / lag_vs_raw 23.0h**
  - recent raw age：**約 4.3 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**（較 #738 的 27/30 下降 2）
- TW 歷史：**#739=25/30，#738=27/30，#737=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 92.8%**
  - avg_quality：**0.6744**
  - avg_pnl：**+0.0209**
  - avg_drawdown_penalty：**0.0372**
- 判讀：canonical recent window 仍是 supported extreme trend；TW-IC 本輪回落，表示近期訊號仍偏高但不如上一輪穩定。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.3987**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3847 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=35**
  - exact live lane：**35 rows / win_rate 0.6286 / quality 0.3328**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=18 / win_rate 1.0000 / quality 0.7064**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0000 / quality -0.3096）**
  - `decision_quality_exact_live_lane_toxicity_applied`：**false**（因 current bucket 是 q35，不是 toxic q15）
- `docs/analysis/bull_4h_pocket_ablation.md`
  - blocker_state：**`exact_lane_proxy_fallback_only`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**32**（18 / 50）
  - historical exact-bucket proxy：**67 rows / win_rate 0.9552**
  - exact live lane proxy：**330 rows**
  - `proxy_boundary_verdict`：**`proxy_boundary_inconclusive`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
- 判讀：**q15 veto 候選已正式進入 runtime contract，但 live 主 blocker 仍是 q35 exact support 不足，而不是 q35 本身失敗。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 仍是 under-minimum support（18 / 50）
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact current rows：**18**；minimum support：**50**；gap：**32**
- exact live lane：**35 rows / win_rate 0.6286 / quality 0.3328**
- current q35：**18 rows / win_rate 1.0000 / quality 0.7064**
- historical exact-bucket proxy：**67 rows / win_rate 0.9552**

**判讀**
- blocker 仍是 **support 不足**；
- q35 目前表現健康，但還不能解除 runtime blocker。

**下一步方向**
- 持續維持 `allowed_layers=0`；
- 下一輪優先把 proxy contract 定稿，而不是再重複證明 q35 健康。

---

### P1. q15 toxic pocket 已進入 runtime contract，但仍屬「候選 veto」，尚未完成跨 surface 治理定稿
**現象**
- live contract 已輸出：
  - `decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`
  - `decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`
- 若 current bucket 本身是 toxic bucket，predictor 現在會落到 `toxic_sub_bucket_current_bucket` 並 block trade；
- 當前 live current bucket 仍是 q35，因此本輪 `decision_quality_exact_live_lane_toxicity_applied = false`。

**判讀**
- 本輪已完成「找出 toxic pocket」→「把 toxic pocket 轉成可執行 runtime guardrail」的第一步；
- 但這條規則目前只在 predictor contract / probe / heartbeat summary 中定義，尚未完成更上游 governance contract 的定稿收斂。

**下一步方向**
- 把 q15 veto candidate 與 `proxy_boundary_inconclusive` 一起收斂：
  - q15 = 可直接 veto 的 lane-internal pathology；
  - q35 = 仍 blocked 但不是 toxic；
  - proxy = 僅治理參考，不能當成 exact bucket 已支持。

---

### P1. proxy cohort 邊界仍未收斂，verdict 仍是 `proxy_boundary_inconclusive`
**現象**
- recent exact current bucket：**18 rows / win_rate 1.0000**
- historical exact-bucket proxy：**67 rows / win_rate 0.9552**
- broader same-bucket：**20 rows / dominant regime chop 95.6%**
- `proxy_boundary_verdict = proxy_boundary_inconclusive`

**判讀**
- proxy 與 exact current bucket 仍接近，但證據不足以宣告「proxy 可直接當部署依據」；
- 目前更合理的結論是：**proxy 可保留作治理參考，但 exact support 未滿前 runtime 仍 blocked。**

**下一步方向**
- 下一輪把這個結論正式寫成 contract，而不是繼續維持 `inconclusive`。

---

### P1. feature shrinkage 與 support-aware profile 仍分流：global `core_only`，bull-support-aware `core_plus_macro`
**現象**
- feature-group ablation global winner：**`core_only`**
- bull support-aware / train selected：**`core_plus_macro`**
- leaderboard visible winner：**`core_only`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**

**判讀**
- 這仍是刻意雙軌；
- exact bucket 未達 minimum support 前，leaderboard / runtime 都不能把 support-aware profile 包裝成 production winner。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1551)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull lane 根因。

---

## 本輪已清掉的問題

### RESOLVED. q15 toxic pocket 只存在於離線 bull artifact，live predictor 無法 machine-read / runtime 無法轉成可執行 guardrail
**現象（修前）**
- `bull_4h_pocket_ablation.json` 已知道 q15 是 toxic sub-bucket；
- 但 `predictor.py` / `hb_predict_probe.py` / fast heartbeat 還看不到這條規則，無法驗證「q15 會被 veto、q35 不會被誤傷」。

**本輪 patch + 證據**
- `model/predictor.py`
  - 新增 `exact_lane_bucket_diagnostics` 與 `toxic_sub_bucket_current_bucket` guardrail；
- `scripts/hb_predict_probe.py`
  - 新增 exact-lane toxic bucket diagnostics 輸出；
- `scripts/hb_parallel_runner.py`
  - 新增 summary 對應欄位；
- `tests/test_api_feature_history_and_predictor.py`
  - 新增 q35-safe 與 q15-veto regression；
- `tests/test_hb_parallel_runner.py`
  - 新增 live predictor diagnostics regression；
- `ARCHITECTURE.md`
  - 已同步 Heartbeat #739 contract。

**狀態**
- **已修復**；現在 heartbeat 能直接 machine-read：
  - q15 是 toxic sub-bucket；
  - current q35 不是 toxic；
  - 若 current bucket 以後落到 toxic q15，runtime 會直接 veto。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q15 toxic pocket 轉成 live predictor 可執行 guardrail。** ✅
2. **把 toxic pocket diagnostics 接到 probe / fast heartbeat summary。** ✅
3. **重跑 fast heartbeat，確認 current q35 未被誤傷，但 blocker 仍是 exact support 不足。** ✅

### 本輪不做
- 不放寬 live layers；
- 不把 proxy rows 當成 exact support 已滿；
- 不把 `fin_netflow` auth blocker 誤寫成 bull lane 成功敘事；
- 不把 q35 current bucket 誤判成 toxic pocket。

---

## 下一輪 gate

- **Next focus:**
  1. 把 `proxy_boundary_inconclusive` 正式收斂成 contract：proxy 可治理參考，但 exact support 未滿前仍 blocked；
  2. 把 q15 toxic sub-bucket veto candidate 對齊到所有 bull governance surface（artifact / probe / summary / docs）；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **proxy contract 定稿 / q15 veto 跨 surface 對齊** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`allowed_layers`、`decision_quality_exact_live_lane_toxic_bucket` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 proxy contract 仍無法定稿，下一輪至少把 `inconclusive` 收斂成「可用於治理、不可用於部署」的明確 fallback 語義；
  - 若 q35 exact rows 持續卡住，繼續維持 `allowed_layers=0`，不要因 q35 表現漂亮而放寬；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 proxy / veto contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_739_summary.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `current_live_structure_bucket_rows` 是否仍 **< 50**；
     - `decision_quality_exact_live_lane_bucket_verdict` 是否仍為 **`toxic_sub_bucket_identified`**；
     - `decision_quality_exact_live_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `decision_quality_exact_live_lane_toxicity_applied` 是否仍因 current bucket 非 q15 而為 **false**；
     - `proxy_boundary_verdict` 是否仍為 **`proxy_boundary_inconclusive`**；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[*].blocker_reason` 是否仍含 **`under_minimum_exact_live_structure_bucket`**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「q15 已接進 runtime」當成功；必須直接推進 **proxy contract 定稿 / 跨 surface 對齊 / blocker 語義收斂**。
