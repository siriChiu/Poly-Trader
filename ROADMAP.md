# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 17:42 UTC — Heartbeat #1023（本輪已把 **q35 audit / runner baseline-vs-runtime drift** 收斂成正式 contract：runner 先刷新 live probe，再由 q35 audit 明確區分 **baseline / calibration / deployed runtime**。因此下一輪主路徑不再是「修 q35 drift」，而是：**利用剛達標的 q15 exact support，驗證 component deployment 是否能在保留 discrimination 的前提下把 current live lane 推過 floor。**）_

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
  - numbered summary：`data/heartbeat_1023_summary.json`

### 本輪新完成：q35 audit/runtime baseline-vs-deployed 語義對齊
- `scripts/hb_parallel_runner.py`
  - 先跑 `hb_predict_probe.py`，再跑 `hb_q35_scaling_audit.py`
  - heartbeat summary 現在持久化：`baseline_current_live`、`calibration_runtime_current`、`current_live`（deployed runtime）、`runtime_source`、`q35_discriminative_redesign_applied`
- `scripts/hb_q35_scaling_audit.py`
  - q35 audit 現在顯式輸出：
    - `baseline_current_live`
    - `calibration_runtime_current`
    - `deployed_runtime_current`
    - `deployment_grade_component_experiment.runtime_source`
    - `deployment_grade_component_experiment.q35_discriminative_redesign_applied`
- `tests/test_hb_parallel_runner.py`
  - 已補 order / schema regression

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py -q` → **75 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1023` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1023）：
  - Raw / Features / Labels = **21775 / 13204 / 43496**
  - simulated_pyramid_win = **0.5793**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.3h**
- raw freshness：**約 0.5 分鐘**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**27/30**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 100.0%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - structure_bucket：**CAUTION|structure_quality_caution|q35**
  - entry_quality：**0.4115**
  - entry_quality_label：**D**
  - allowed layers：**0 → 0**
  - decision-quality scope：**regime_label+regime_gate+entry_quality_label**

### q35 / q15 / governance 現況
- `q35_scaling_audit`
  - `baseline_current_live.entry_quality = 0.3411`
  - `calibration_runtime_current.entry_quality = 0.4115`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.4115`
  - `deployment_grade_component_experiment.runtime_source = live_predict_probe`
  - `deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
  - **治理結論**：q35 drift 已解；現在看到的就是 current live row 真實狀態，而不是 artifact 對齊問題
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `component_experiment.verdict = exact_supported_component_experiment_ready`
  - `machine_read_answer = {support_ready=true, entry_quality_ge_0_55=true, allowed_layers_gt_0=true, preserves_positive_discrimination_status=not_measured_requires_followup_verify}`
  - **治理結論**：support blocker 已解除，但 deployment verify 還差 discrimination check
- `leaderboard_feature_profile_probe`
  - `leaderboard_selected_profile = core_plus_macro`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `global_recommended_profile = core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `live_current_structure_bucket_rows = 50`
  - **治理結論**：已過 threshold，問題從 support shortage 轉成 post-threshold profile governance

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0%**
- 其餘 sparse sources：**history gap / archive blocker**

---

## 當前主目標

### 目標 A：把 q15 exact-supported component experiment 從 machine-read ready 推到 deployment-grade verify
目前已確認：
- q15 exact bucket rows **已達 50**；
- `support_ready=true`、`entry_quality_ge_0_55=true`、`allowed_layers_gt_0=true` 已成立；
- 但 `preserves_positive_discrimination_status` 仍是 **`not_measured_requires_followup_verify`**。

下一步主目標：
- **把 q15 exact-supported component deployment 做成真正可驗證 patch，並補上 discrimination verify。**

### 目標 B：把 q35 問題收斂成真實 live floor gap，而不是 surface drift
目前已確認：
- q35 drift 已解；
- current q35 live row 真實數字是 **0.4115 / 0 layers**；
- q35 formula review 雖改善 baseline，但仍未單獨把 current row 推過 floor。

下一步主目標：
- **讓 q35 / q15 路徑共同回答：current live lane 還差哪個 component、哪個 verify。**

### 目標 C：收斂 post-threshold profile governance
目前已確認：
- leaderboard / train / global 三條 profile 語義仍分裂；
- 但 exact support 已恢復，這已不再是「support 未達標」問題。

下一步主目標：
- **等 q15 deployment verify 完成後，再把 post-threshold profile governance 收斂成單一可解讀 contract。**

---

## 接下來要做

### 1. 驗證 q15 exact-supported component deployment
要做：
- 在 q15 exact-supported 前提下，實作 / 驗證 `feat_4h_bias50` component deployment patch；
- machine-read 補齊：
  - `preserves_positive_discrimination = true`
  - `entry_quality_ge_0_55 = true`
  - `allowed_layers_gt_0 = true`
- 驗證：
  - `live_predict_probe`
  - `live_decision_quality_drilldown`
  - `q15_support_audit`
  - fast heartbeat summary

### 2. 把 q35 current live lane 與 q15 verify 串成同一條 deployment 敘事
要做：
- 保持 q35 audit 的 baseline/calibration/deployed 三軌輸出；
- 不再把 q35 drift 當 blocker；
- 用 q35 audit + q15 audit 一起回答 current live lane 還差什麼。

### 3. 收斂 post-threshold profile governance
要做：
- 等 q15 exact-supported verify 完成後，再處理：
  - leaderboard selected profile
  - train selected profile
  - global shrinkage winner
- 目標是把 `post_threshold_profile_governance_stalled` 收斂成 machine-read 可執行結論。

---

## 暫不優先

以下本輪後仍不排最前面：
- 再修一次 q35 audit/runtime drift
- 稀疏來源 auth / archive blocker 主修
- 先做 profile governance 大重構

原因：
> 本輪已經把 q35 surface drift 修掉；真正新的閉環機會是 **q15 exact-supported component deployment verify**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q15 exact-supported component deployment verify** 直接相關的 patch / run / verify。
2. machine-read surface 必須清楚回答：
   - `support_ready = true`
   - `entry_quality_ge_0_55 = true`
   - `allowed_layers_gt_0 = true`
   - `preserves_positive_discrimination = true`
3. q35 audit / q15 support audit / live predictor / heartbeat summary 對同一條 current live row 必須給出一致可解讀的 deployment 結論。
4. 若 q15 verify 成功，下一輪再收斂 profile governance；若失敗，必須明確降級成 research-only / no-deploy。

---

## Next gate

- **Next focus:**
  1. 驗證 q15 exact-supported component deployment；
  2. 保持 q35 drift 已解狀態，改追 current live floor gap；
  3. 之後再收斂 post-threshold profile governance。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 exact-supported component verify** 直接相關的 patch / artifact / verify；
  2. `q15_support_audit.component_experiment.machine_read_answer.preserves_positive_discrimination` 必須不再是 `not_measured_requires_followup_verify`；
  3. `live_predict_probe` / `live_decision_quality_drilldown` / `q15_support_audit` / `heartbeat summary` 必須對同一條 live row 給出一致結論。

- **Fallback if fail:**
  - 若 q15 verify 失敗或失去 discrimination，下一輪降回 `reference_only_exact_support_verified_but_not_deployable`；
  - 若 current live row 離開 q35/q15 path，下一輪切回 support accumulation / bucket governance；
  - 若 next run 沒有新 patch，只剩報告，升級成 governance blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 deployment contract 再擴大）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1023_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.deployment_grade_component_experiment.runtime_source = live_predict_probe`
     - `q15_support_audit.component_experiment.verdict = exact_supported_component_experiment_ready`
     - `q15_support_audit.component_experiment.machine_read_answer.support_ready = true`
     則下一輪不得再把主焦點放在 q35 drift；必須直接做 **q15 exact-supported component deployment verify + discrimination check**。
