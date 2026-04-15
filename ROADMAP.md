# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 20:41 UTC — Heartbeat #fast（本輪已把 **profile governance contract** 落地到 heartbeat 主路徑。`scripts/hb_leaderboard_candidate_probe.py` 與 `hb_parallel_runner.py` 現在會同步輸出 `governance_contract`，把 `leaderboard_global_winner_vs_train_support_fallback` 明確定義成 **雙角色治理**，不再讓 summary / docs 把它誤讀成 parity drift。）_

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

### 本輪新完成：profile governance 已 machine-read 化
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `governance_contract`，統一輸出：
    - `verdict`
    - `current_closure`
    - `treat_as_parity_blocker`
    - `recommended_action`
    - `global_profile/global_profile_role`
    - `production_profile/production_profile_role`
    - `support_governance_route`
- `scripts/hb_parallel_runner.py`
  - heartbeat summary 現在會持久化 `leaderboard_candidate_diagnostics.governance_contract`
- `tests/test_hb_leaderboard_candidate_probe.py`
  - dual-role / post-threshold stalled 治理 contract regression 已補齊
- `tests/test_hb_parallel_runner.py`
  - heartbeat summary 對 `governance_contract` 的持久化 regression 已補齊

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **40 passed**
- `/home/kazuha/Poly-Trader/venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#fast）：
  - Raw / Features / Labels = **21784 / 13213 / 43574**
  - simulated_pyramid_win = **0.5805**
- label freshness 正常：
  - 240m = **21931 rows / target_rows 13009 / expected_horizon_lag**
  - 1440m = **12558 rows / target_rows 12558 / expected_horizon_lag**
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
  - `q35_scaling_audit.deployment_grade_component_experiment = runtime_patch_crosses_trade_floor`
  - `runtime_entry_quality=0.5675`
  - `runtime_allowed_layers_raw=1`
  - `q35_discriminative_redesign_applied=true`
  - `live_predict_probe.allowed_layers=1`

### q15 / governance / source blockers 現況
- `q15_support_audit`
  - `scope_applicability.status = current_live_not_q15_lane`
  - support route：`exact_bucket_present_but_below_minimum`
- `leaderboard_feature_profile_probe`
  - `leaderboard = core_plus_4h`
  - `train = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - current q35 exact live bucket rows：**15 / 50**
- source blocker
  - `fin_netflow`：**auth_missing / coverage 0.0%**
  - 其他 sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 當前主目標

### 目標 A：把 dual-role profile governance 從「已解釋」推進到「可關閉或可升級」
目前已確認：
- q35 stale runtime blocker 已關閉
- `governance_contract` 已把 profile split 明確定義為 **雙角色治理，不是 parity drift**
- current live q35 exact support 仍只有 **15 / 50**，尚未達關閉 dual-role 的門檻

下一步主目標：
- **持續判斷 dual-role 是否仍為健康治理，或已進入 `post_threshold_governance_contract_needs_leaderboard_sync` 的條件。**

### 目標 B：提升 current live q35 exact support readiness
目前已確認：
- current live row 仍在 `CAUTION|structure_quality_caution|q35`
- `support_governance_route = exact_live_bucket_present_but_below_minimum`
- `live_current_structure_bucket_rows = 15`，距離 `minimum_support_rows = 50` 尚差 **35**

下一步主目標：
- **把 q35 exact support readiness 當成真正的 current-live 治理 blocker，而不是繼續糾纏 profile 語義。**

### 目標 C：維持 q15 standby route 的 truthful governance
目前已確認：
- current live row 不在 q15 lane
- q15 support route 仍是 `exact_bucket_present_but_below_minimum`

下一步主目標：
- **維持 q15 standby route 語義正確；只有 current live row 回到 q15 lane 且 exact support 達標時，才重新升級成 active verify。**

---

## 接下來要做

### 1. 追 q35 current-live exact support
要做：
- 監控 `live_current_structure_bucket_rows` 是否從 **15** 持續增長到 `minimum_support_rows=50`
- 若 exact support 達標，立即判斷 leaderboard 是否仍需保留 global winner，或應升級成 `post_threshold_governance_contract_needs_leaderboard_sync`
- 驗證：
  - `data/leaderboard_feature_profile_probe.json`
  - `data/heartbeat_fast_summary.json`
  - `data/live_predict_probe.json`

### 2. 守住 governance_contract 不回退
要做：
- 每輪 heartbeat 確認 `leaderboard_candidate_diagnostics.governance_contract` 仍存在且與 probe 一致
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
- 再把 profile split 本身當成 parity drift 主 blocker
- 把 q15 standby route 拉回主 closure
- sparse-source auth / archive blocker 主修

原因：
> 本輪已完成 governance contract patch；目前最近的治理缺口是 **q35 exact support readiness**，其次才是 **是否進入 post-threshold leaderboard sync**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q35 exact support readiness** 或 **post-threshold leaderboard sync** 直接相關的 patch / artifact / verify。
2. `leaderboard_feature_profile_probe.alignment.governance_contract` 必須持續存在，且在 support 未翻轉前維持 `treat_as_parity_blocker=false`。
3. `python scripts/hb_parallel_runner.py --fast` 內仍必須 machine-read 顯示：
   - `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55 = true`
   - `q35_scaling_audit.deployment_grade_component_experiment.allowed_layers_gt_0 = true`
   - `live_predict_probe.allowed_layers = 1`
4. q15 audit 若仍 inactive，必須維持 `current_live_not_q15_lane`，不能再被寫成 current-live closure。

---

## Next gate

- **Next focus:**
  1. 追 q35 exact support readiness；
  2. 判斷 dual-role 是否需要升級成 post-threshold leaderboard sync；
  3. 維持 q15 standby route truthfulness。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 exact support** 或 **leaderboard sync** 直接相關的 patch / artifact / verify；
  2. `governance_contract` 必須仍存在且語義正確；
  3. `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55` 與 `allowed_layers_gt_0` 必須持續為 `true`；
  4. `live_predict_probe.allowed_layers = 1` 且 `q35_discriminative_redesign_applied = true`。

- **Fallback if fail:**
  - 若 governance contract 又被誤解為 parity blocker，直接回查 probe / summary 的 contract 持久化；
  - 若 q35 exact support 長期停在 <50，升級成專門的 support-accumulation blocker；
  - 若 current live row 離開 q35，下一輪依 `scope_applicability` 重新選 active lane。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 governance contract 再擴充 machine-read 欄位）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.governance_contract`
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `governance_contract.verdict = dual_role_governance_active` 且 `support_governance_route = exact_live_bucket_present_but_below_minimum`，下一輪**不得再回頭把 profile split 當 parity drift**；必須直接推進 **q35 exact support readiness** 或 **post-threshold leaderboard sync 條件判定**。
