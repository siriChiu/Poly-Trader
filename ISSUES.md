# ISSUES.md — Current State Only

_最後更新：2026-04-14 18:45 UTC — Heartbeat #740（已把 bull q35 proxy 語義從 `proxy_boundary_inconclusive` 正式收斂為 `proxy_governance_reference_only_exact_support_blocked`，並同步對齊到 bull artifact / leaderboard probe / heartbeat summary / 文件；當前主 blocker 已縮小為 q35 exact support 尚差 8 rows。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#739）要求本輪處理
- **Next focus**：
  1. 把 `proxy_boundary_inconclusive` 收斂成正式 contract；
  2. 把 q15 toxic-sub-bucket veto 對齊到所有 bull governance surface；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 必須留下至少一個與 **proxy contract 定稿 / q15 veto 跨 surface 對齊** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。
- **Fallback if fail**：
  - 若 proxy contract 仍無法定稿，下一輪至少把 `inconclusive` 收斂成「可用於治理、不可用於部署」的明確 fallback 語義；
  - 若 q35 exact rows 持續卡住，繼續維持 `allowed_layers=0`；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/bull_4h_pocket_ablation.py` 已把 bull q35 proxy 語義正式收斂成 **`proxy_governance_reference_only_exact_support_blocked`**；
  - `scripts/hb_leaderboard_candidate_probe.py` 已新增 `proxy_boundary_verdict / reason`、`exact_lane_bucket_verdict`、`exact_lane_toxic_bucket`，probe 不再缺欄；
  - `ARCHITECTURE.md` 已新增 Heartbeat #740 proxy governance contract；
  - `tests/test_bull_4h_pocket_ablation.py`、`tests/test_hb_leaderboard_candidate_probe.py` 已補 regression，並用 `tests/test_hb_parallel_runner.py` 一起驗證摘要路徑未漂移；
  - `python scripts/hb_parallel_runner.py --fast --hb 740` 已重建 artifact / probe / summary。
- **本輪觀察導致前提更新**：
  - current live bucket 仍是 **`CAUTION|structure_quality_caution|q35`**；
  - exact current rows 已從 **18 → 42**，gap 已從 **32 → 8**；
  - exact live lane 已從 **35 → 59 rows**；
  - historical exact-bucket proxy 已從 **67 → 91 rows**；
  - `decision_quality_exact_live_lane_bucket_verdict` 仍是 **`toxic_sub_bucket_identified`**，toxic bucket 仍是 **q15 (4 rows / win_rate 0.0)**；
  - live predictor DQ 已升到 **label=C**、`expected_win_rate=0.7797`、`expected_pyramid_quality=0.4908`，但 `allowed_layers` 仍是 **0**，因 exact support 尚未滿 50。
- **本輪明確不做**：
  - 不因 q35 gap 已縮到 8 就提前解除 runtime blocker；
  - 不把 historical proxy rows 視為 exact support 已滿；
  - 不把 `fin_netflow` auth blocker 混成 bull lane 已改善的證據。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - proxy boundary 判讀新增 `broad_recent500_dominant_regime` fallback，避免 broader regime 證據漏讀；
    - 當 `exact_bucket_present_but_below_minimum` 且 proxy 仍可作 same-bucket 參考時，summary 層正式改寫為 **`proxy_governance_reference_only_exact_support_blocked`**，不再維持模糊 `proxy_boundary_inconclusive`。
  - `scripts/hb_leaderboard_candidate_probe.py`
    - alignment payload 現在同步輸出 `proxy_boundary_verdict / reason`、`exact_lane_bucket_verdict`、`exact_lane_toxic_bucket`。
  - `tests/test_bull_4h_pocket_ablation.py`
    - 補 proxy governance-only regression。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 補 leaderboard probe 對 proxy / toxic bucket 對齊 regression。
  - `ARCHITECTURE.md`
    - 已同步 Heartbeat #740 proxy governance contract。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **18 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 740` → **通過**；
  - 已刷新：
    - `data/heartbeat_740_summary.json`
    - `data/bull_4h_pocket_ablation.json`
    - `docs/analysis/bull_4h_pocket_ablation.md`
    - `data/leaderboard_feature_profile_probe.json`
    - `data/live_predict_probe.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #740：
  - Raw / Features / Labels：**21423 / 12852 / 42985**
  - 本輪增量：**+1 raw / +1 feature / +25 labels**
  - canonical target `simulated_pyramid_win`：**0.5759**
  - 240m labels：**21572 rows / target_rows 12650 / lag_vs_raw 3.3h**
  - 1440m labels：**12328 rows / target_rows 12328 / lag_vs_raw 23.0h**
  - recent raw age：**約 4.4 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**
- TW 歷史：**#740=25/30，#739=25/30，#738=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 83.2%**
  - avg_quality：**0.6853**
  - avg_pnl：**+0.0213**
  - avg_drawdown_penalty：**0.0325**
- 判讀：近期 canonical window 仍是 supported extreme trend；本輪沒有新的 recent-window pathology blocker。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.3309**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3784 (D)**
  - decision-quality label：**C**
  - expected win / quality：**0.7797 / 0.4908**
  - allowed layers：**0 → 0**
  - execution guardrail：**未額外觸發**（`allowed_layers_raw` 本來就是 0）
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=59**
  - exact live lane：**59 rows / win_rate 0.7797 / quality 0.4908**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=42 / win_rate 1.0000 / quality 0.7148**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket.bucket`：**`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0000）**
- `data/bull_4h_pocket_ablation.json`
  - blocker_state：**`exact_lane_proxy_fallback_only`**
  - support_governance_route：**`exact_live_bucket_present_but_below_minimum`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**8**（42 / 50）
  - historical exact-bucket proxy：**91 rows / win_rate 0.9670**
  - exact live lane proxy：**354 rows**
  - `proxy_boundary_verdict`：**`proxy_governance_reference_only_exact_support_blocked`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - blocked candidate：**`core_plus_macro -> under_minimum_exact_live_structure_bucket`**
  - `proxy_boundary_verdict` / `exact_lane_bucket_verdict` 已與 bull artifact 對齊
- 判讀：**本輪真正前進點不是解除 blocker，而是把 blocker 語義正式定稿；目前 blocker 已收斂為「q35 exact support 還差 8 rows」，而不是 proxy 邊界不明。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 仍未達 minimum support，但 gap 已縮到 8
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact current rows：**42**；minimum support：**50**；gap：**8**
- exact live lane：**59 rows / win_rate 0.7797 / quality 0.4908**
- current q35：**42 rows / win_rate 1.0000 / quality 0.7148**
- historical exact-bucket proxy：**91 rows / win_rate 0.9670**

**判讀**
- blocker 仍是 **support 不足**；
- 但 support gap 已明顯收斂，下一輪主要是確認是否跨過 50，而不是再追 proxy 邊界語義。

**下一步方向**
- q35 rows 一旦 **≥ 50**，必須改做「解除 blocker 的驗證流程」，不能直接放行；
- q35 rows 若仍 **< 50**，維持 `allowed_layers=0`。

---

### P1. proxy contract 已定稿，但仍需觀察是否所有 surface 持續零漂移
**現象**
- bull artifact / leaderboard probe / heartbeat summary / docs 現在都已使用：
  - `proxy_boundary_verdict = proxy_governance_reference_only_exact_support_blocked`
- current live bucket 仍是 q35，exact root cause 仍是 under-minimum support。

**判讀**
- 這個 issue 已從「語義未定稿」降級成「後續是否持續零漂移」的治理檢查；
- 只要 q35 尚未滿 50，proxy 就只能治理參考、不能拿來解除 blocker。

**下一步方向**
- 下一輪只驗證這條 contract 是否持續一致，不再把它當成主要未決 blocker；
- 若任一 surface 回退成 `proxy_boundary_inconclusive`，立即升級為 drift regression。

---

### P1. q15 toxic pocket 仍是 bull exact lane 的 lane-internal pathology
**現象**
- `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
- toxic bucket：**`CAUTION|structure_quality_caution|q15`**
- rows：**4**；win_rate：**0.0000**

**判讀**
- q15 仍是 exact lane 內部的明確病灶；
- 目前 current bucket 不是 q15，因此本輪沒有觸發 toxic current-bucket veto，但這條規則必須持續保留。

**下一步方向**
- 若 current bucket 之後落入 q15，runtime 必須直接 veto；
- 若 current bucket 仍是 q35，持續維持「blocked 的原因是 support，不是 q35 自身 toxic」。

---

### P1. feature shrinkage 與 support-aware profile 仍雙軌
**現象**
- global winner：**`core_only`**
- support-aware / train selected：**`core_plus_macro`**
- leaderboard visible winner：**`core_only`**
- blocked candidate：**`core_plus_macro -> under_minimum_exact_live_structure_bucket`**

**判讀**
- 這仍是刻意雙軌；
- 在 q35 exact support 達 minimum 之前，leaderboard / runtime 都不能把 support-aware profile 包裝成 production winner。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1552)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull lane 根因。

---

## 本輪已清掉的問題

### RESOLVED. `proxy_boundary_inconclusive` 語義未定稿，導致 bull blocker 仍停留在模糊敘述
**現象（修前）**
- bull artifact 明知道 q35 exact bucket 已出現、proxy 也足夠接近，但 summary / docs / probe 仍用 `proxy_boundary_inconclusive`；
- 這讓 blocker 語義停在「不知道 proxy 能不能用」，而不是「proxy 只能治理參考，不能 deployment」。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - 正式收斂成 `proxy_governance_reference_only_exact_support_blocked`；
- `scripts/hb_leaderboard_candidate_probe.py`
  - 對齊 `proxy_boundary_verdict / reason` 與 exact-lane toxic bucket；
- `tests/test_bull_4h_pocket_ablation.py`
  - 新增 governance-only regression；
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 新增 probe 對齊 regression；
- `tests/test_hb_parallel_runner.py`
  - 維持 summary 路徑驗證；
- `ARCHITECTURE.md`
  - 已同步 Heartbeat #740 contract；
- `python scripts/hb_parallel_runner.py --fast --hb 740`
  - 已重建 bull artifact / leaderboard probe / heartbeat summary。

**狀態**
- **已修復**；現在系統的明確語義是：
  - proxy = **治理參考**；
  - q35 exact support < 50 = **deployment 仍 blocked**；
  - q15 = **toxic sub-bucket**；
  - `allowed_layers` 仍維持 **0**。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q35 proxy contract 正式定稿成 governance-only。** ✅
2. **把 proxy / toxic-bucket 欄位補進 leaderboard candidate probe，完成跨 surface 對齊。** ✅
3. **重跑 fast heartbeat，確認 q35 gap 已縮到 8，但 blocker 仍未解除。** ✅

### 本輪不做
- 不放寬 live layers；
- 不因 q35 current bucket 健康就跳過 minimum support；
- 不把 proxy rows 視為 exact support 已滿；
- 不把 `fin_netflow` auth blocker 包裝成即將解決。

---

## 下一輪 gate

- **Next focus:**
  1. 追蹤 `CAUTION|structure_quality_caution|q35` exact rows 是否從 **42 → ≥50**；
  2. 若仍 < 50，持續驗證 `proxy_governance_reference_only_exact_support_blocked` 與 `toxic_sub_bucket_identified` 在 artifact / probe / summary / docs 間零漂移；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 exact support 達標驗證** 或 **proxy/t toxic contract 持續零漂移** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 在 artifact / probe / docs / summary 間持續零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論；若 q35 exact rows ≥ 50，必須改做解除 blocker 驗證而非直接部署。

- **Fallback if fail:**
  - 若 q35 exact rows 卡在 42 附近沒有再長，下一輪升級為「support accumulation stalled」調查；
  - 若任一 surface 回退成 `proxy_boundary_inconclusive`，立即視為 governance regression；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_740_summary.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `current_live_structure_bucket_rows` 是否已 **≥ 50**，若否目前是多少；
     - `support_blocker_state` 是否仍是 **`exact_lane_proxy_fallback_only`**；
     - `support_governance_route` 是否仍是 **`exact_live_bucket_present_but_below_minimum`**；
     - `proxy_boundary_verdict` 是否仍是 **`proxy_governance_reference_only_exact_support_blocked`**；
     - `decision_quality_exact_live_lane_bucket_verdict` 是否仍是 **`toxic_sub_bucket_identified`**；
     - `decision_quality_exact_live_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `live_predict_probe.allowed_layers` 是否仍是 **0**。
  3. 若以上條件大多仍成立，下一輪不得再把「proxy contract 已定稿」當成功；必須直接推進 **q35 exact support 達標驗證 / stalled root-cause / blocker 持續治理**。
