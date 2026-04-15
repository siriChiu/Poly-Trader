# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 21:16 UTC — Heartbeat #fast（本輪已把 **q35 exact support readiness** 升級成 machine-read `support_progress` contract。probe / heartbeat summary 現在不只知道 current bucket rows，還能直接表達是仍在累積、缺少可比歷史，或已進入 stalled 候選 blocker。）_

本文件只保留**目前已落地能力、當前主目標、下一步 gate**，不保留歷史 roadmap 敘事。

---

## 已完成

### Canonical heartbeat / diagnostics
- fast heartbeat 持續刷新：
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/q15_boundary_replay.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/heartbeat_fast_summary.json`

### 本輪新完成：q35 exact support progression 已 machine-read 化
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `support_progress`
  - `governance_contract` 同步攜帶 support progression 內容
- `scripts/hb_parallel_runner.py`
  - `run_leaderboard_candidate_probe()` 傳入 `HB_RUN_LABEL`
  - heartbeat summary 持久化 `support_progress / minimum_support_rows / live_current_structure_bucket_gap_to_minimum`
- `tests/test_hb_leaderboard_candidate_probe.py`
  - stalled exact-support regression 已補齊
- `tests/test_hb_parallel_runner.py`
  - heartbeat summary 對 `support_progress` 的持久化 regression 已補齊

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **41 passed**
- `/home/kazuha/Poly-Trader/venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#fast）：
  - Raw / Features / Labels = **21786 / 13215 / 43578**
  - simulated_pyramid_win = **0.5806**
- label freshness 正常：
  - 240m = **21933 rows / target_rows 13011 / expected_horizon_lag**
  - 1440m = **12560 rows / target_rows 12560 / expected_horizon_lag**
- raw freshness：**約 0.5 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / drift / live runtime
- Global IC：**18/30**
- TW-IC：**26/30**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 100.0%**
  - window win_rate：**0.8920**
- fast heartbeat current live q35 path：
  - lane：**bull / CAUTION / q35**
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `deployment_grade_component_experiment = runtime_patch_crosses_trade_floor`
  - `runtime_entry_quality = 0.5507`
  - `runtime_allowed_layers_raw = 1`
  - `q35_discriminative_redesign_applied = true`
  - `live_predict_probe.allowed_layers = 1`

### q35 / q15 / governance 現況
- `leaderboard_feature_profile_probe`
  - `leaderboard = core_plus_4h`
  - `train = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - current q35 exact live bucket rows：**13 / 50**
  - `support_progress.status = no_recent_comparable_history`
  - `support_progress.gap_to_minimum = 37`
- `q15_support_audit`
  - `scope_applicability.status = current_live_not_q15_lane`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `floor_cross_legality.verdict = floor_crossed_but_support_not_ready`

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0%**
- 其他 sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 當前主目標

### 目標 A：把 q35 exact support readiness 從「人工觀察」推進到「可 machine-read 管理」
目前已確認：
- q35 runtime path 已維持 `entry_quality=0.5507 / allowed_layers=1`
- exact support 仍只有 **13 / 50**，本輪比上輪 **15 / 50** 更弱
- `support_progress` 已落地，後續 heartbeat 可以直接辨識是 `accumulating / no_recent_comparable_history / stalled_under_minimum`

下一步主目標：
- **讓 q35 exact support readiness 成為 heartbeat 的單一 machine-read 管理路徑，並在 support 真正停滯時自動升級 blocker。**

### 目標 B：維持 dual-role governance 正確，但不再把它當主 blocker
目前已確認：
- `governance_contract` 仍明確指出這是 **雙角色治理，不是 parity drift**
- 真正卡住的是 current live q35 exact support，不是 profile 語義

下一步主目標：
- **在 support 未翻轉前，維持 `treat_as_parity_blocker=false`，把治理焦點放在 q35 exact support gap。**

### 目標 C：維持 q15 standby route 的 truthful governance
目前已確認：
- current live row 不在 q15 lane
- q15 support route 仍是 `exact_bucket_present_but_below_minimum`
- floor 雖跨過，但 support 尚未 ready

下一步主目標：
- **維持 q15 standby route 語義正確；只有 current live row 回到 q15 lane 且 exact support 達標時，才重新升級成 active verify。**

---

## 接下來要做

### 1. 追 q35 current-live exact support
要做：
- 監控 `live_current_structure_bucket_rows` 是否從 **13** 持續增長到 `minimum_support_rows=50`
- 每輪直接讀 `support_progress.status / delta_vs_previous / stagnant_run_count`
- 若後續出現 `stalled_under_minimum` 且連續 heartbeat 無成長，升級成 `#PROFILE_GOVERNANCE_STALLED`
- 驗證：
  - `data/leaderboard_feature_profile_probe.json`
  - `data/heartbeat_fast_summary.json`
  - `data/live_predict_probe.json`

### 2. 守住 governance contract 與 support_progress 不回退
要做：
- 每輪 heartbeat 確認 `leaderboard_candidate_diagnostics.governance_contract` 與 `support_progress` 仍存在且與 probe 一致
- 若 contract 消失、漏寫、或重新把 dual-role 誤標成 parity blocker，視為 regression
- 驗證：
  - `python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q`
  - `python scripts/hb_parallel_runner.py --fast`

### 3. 維持 q15 standby route truthful governance
要做：
- 持續使用 `q15_support_audit.scope_applicability` 作單一真相來源
- 若 current live row 仍是 q35，文件 / heartbeat 不得再把 q15 standby route 寫成主 closure
- 只在 q15 exact rows 達標後，才重新升級 q15 component path

---

## 暫不優先

以下本輪後仍不排最前面：
- 把 profile split 本身重新當作 parity drift 主 blocker
- 把 q15 standby route 拉回主 closure
- sparse-source auth / archive blocker 主修

原因：
> 本輪已完成 support progression contract；目前最近的治理缺口是 **q35 exact support readiness**，其次才是 **support 是否 stalled 需要升級 blocker**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q35 exact support readiness** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify。
2. `leaderboard_feature_profile_probe.alignment.governance_contract` 必須持續存在，且在 support 未翻轉前維持 `treat_as_parity_blocker=false`。
3. `support_progress` 必須持續存在，並能 machine-read 表達 current rows / gap / stagnation 狀態。
4. `python scripts/hb_parallel_runner.py --fast` 內仍必須 machine-read 顯示：
   - `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55 = true`
   - `q35_scaling_audit.deployment_grade_component_experiment.allowed_layers_gt_0 = true`
   - `live_predict_probe.allowed_layers = 1`
5. q15 audit 若仍 inactive，必須維持 `current_live_not_q15_lane`，不能再被寫成 current-live closure。

---

## Next gate

- **Next focus:**
  1. 追 q35 exact support readiness（13/50 → 50/50）；
  2. 觀察 `support_progress` 是否轉成 `accumulating` 或 `stalled_under_minimum`；
  3. 維持 q15 standby route truthfulness。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 exact support** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify；
  2. `governance_contract` 與 `support_progress` 必須仍存在且語義正確；
  3. `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55` 與 `allowed_layers_gt_0` 必須持續為 `true`；
  4. `live_predict_probe.allowed_layers = 1` 且 `q35_discriminative_redesign_applied = true`。

- **Fallback if fail:**
  - 若 governance contract 或 support_progress 又消失，回查 probe / summary persistence；
  - 若 q35 exact support 在可比 heartbeat 仍長期停在 `<50` 且 `support_progress.stalled_under_minimum=true`，升級成 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 current live row 離開 q35，下一輪依 `scope_applicability` 重新選 active lane。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 `support_progress` contract 再擴充欄位）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.governance_contract` 與 `leaderboard_candidate_diagnostics.support_progress`
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `support_governance_route = exact_live_bucket_present_but_below_minimum`：
     - `support_progress.status = accumulating` → 繼續追 exact support 累積；
     - `support_progress.status = stalled_under_minimum` → 升級 `#PROFILE_GOVERNANCE_STALLED` 評估；
     - `support_progress.status = no_recent_comparable_history` → 再留至少一輪 machine-read history，不得回頭把 profile split 當 parity drift。
