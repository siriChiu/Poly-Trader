# ISSUES.md — Current State Only

_最後更新：2026-04-15 12:56 UTC — Heartbeat #1018（已把 `feat_4h_bias50 + feat_pulse (+ feat_nose)` base-mix experiment 正式納入 q35 audit / fast heartbeat machine-read。結論：**base-mix uplift 明顯優於 `dist_swing_low` 結構 uplift，但最佳情境仍只到 `entry_quality=0.5106`、距 trade floor 還差 `0.0394`，因此 live blocker 已正式升級成 `base-stack redesign`。**）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 做 `feat_4h_bias50 + feat_pulse (+ feat_nose)` 的 base-mix trade-floor closure experiment；
  2. 把 `feat_4h_dist_swing_low` 固定降級成 secondary structure mix；
  3. 維持 profile governance / source blockers / q15 boundary replay 零漂移治理。
- **Success gate**
  1. 留下至少 1 個與 base-mix trade-floor closure 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 base-mix experiment 後 `entry_quality >= 0.55` 與 `allowed_layers > 0` 是否成立；
  3. `q35_scaling_audit.scope_applicability.status` 必須持續正確反映 live-active vs reference-only。
- **Fallback if fail**
  - 若 `bias50 + pulse (+ nose)` 仍無法跨過 floor，下一輪升級為 **base-stack redesign blocker**；
  - 若 q35 applicability 轉成 reference-only，下一輪先處理 current bucket support / component；
  - 若沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

### 本輪承接結果
- **已處理**
  - `scripts/hb_q35_scaling_audit.py`：新增 `base_mix_component_experiment`，用 exact / winner cohort 的 `bias50 + pulse (+ nose)` score 分布做 machine-readable closure experiment。
  - `scripts/hb_parallel_runner.py`：q35 diagnostics / fast heartbeat summary 現在會同步摘取 `base_mix_component_experiment`。
  - `tests/test_hb_parallel_runner.py`：新增 base-mix experiment regression test 與 summary extraction test。
  - `ARCHITECTURE.md`：同步 #1018 q35 base-mix redesign contract。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **64 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1018` → **通過**
- **本輪 machine-read 結論**
  - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.3725`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1775`
  - `joint_component_experiment.best_scenario = exact_lane_p75`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3729`
  - `joint_component_experiment.best_scenario.remaining_gap_to_floor = 0.1771`
  - `base_mix_component_experiment.verdict = base_mix_component_experiment_improves_but_still_below_floor`
  - `base_mix_component_experiment.best_scenario = winner_triplet_p75`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5106`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0394`
  - `live_predict_probe.allowed_layers = 0`
- **本輪明確不做**
  - 不直接 relax runtime gate；
  - 不把 `feat_4h_dist_swing_low` 再包裝成主要 closure；
  - 不讓 profile split / sparse-source blocker 取代 trade-floor 主 blocker。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q35_scaling_audit.py`
    - 新增 `base_component_score_distributions` / `structure_component_score_distributions`。
    - 新增 `base_mix_component_experiment={verdict,machine_read_answer,best_scenario,required_bias50_cap_after_base_mix}`。
    - `recommended_action` 現在會在 base-mix 仍失敗時明確升級成 `base-stack redesign blocker`。
  - `scripts/hb_parallel_runner.py`
    - q35 audit 摘要新增 `base_mix_component_experiment` 萃取，避免下一輪又退回只看 structure uplift。
  - `tests/test_hb_parallel_runner.py`
    - 新增 base-mix experiment regression 與 q35 summary extraction regression。
  - `ARCHITECTURE.md`
    - 新增 #1018 q35 base-mix redesign contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **64 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast --hb 1018`
- **已刷新 artifacts**
  - `data/heartbeat_1018_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/q15_boundary_replay.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1018：
  - Raw / Features / Labels：**21688 / 13117 / 43421**
  - 本輪增量：**+1 raw / +1 feature / +42 labels**
  - canonical target `simulated_pyramid_win`：**0.5795**
  - 240m labels：**21798 rows / target_rows 12876 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12538 rows / target_rows 12538 / lag_vs_raw 約 23.2h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**24/30 pass**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**distribution_pathology**
  - dominant_regime：**bull 98.8%**
  - win_rate：**0.9440**
  - avg_quality：**0.6376**
  - avg_pnl：**+0.0202**
  - avg_drawdown_penalty：**0.0436**
- 判讀：近期 bull 高集中仍需顯式標記，但本輪 live blocker 不是 drift，而是 **trade floor 仍未被 base-mix uplift 跨過**。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**C**
  - `entry_quality = 0.3725`
  - `allowed_layers = 0 → 0`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - **base_quality = 0.3552** / **structure_quality = 0.4246**
  - base components：`bias50=0.2314`, `nose=0.2696`, `pulse=0.2499`, `ear=0.9772`
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `runtime_entry_quality = 0.3725`
  - `runtime_remaining_gap_to_floor = 0.1775`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3729` / `remaining_gap_to_floor = 0.1771`
  - `base_mix_component_experiment.best_scenario = winner_triplet_p75`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5106`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0394`
  - `recommended_action = base-stack redesign blocker`
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `remaining_gap_to_floor = 0.1775`
  - `best_single_component = feat_4h_bias50`
- `data/q15_bucket_root_cause.json`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_dist_swing_low`
- 判讀：**q35 lane 仍 live-active、exact support 已足夠，且 structure uplift 幾乎沒有縮 gap；主 blocker 已正式收斂成 base stack（bias50 + pulse + nose）仍無法合法跨 floor。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `profile_split.verdict = dual_role_required`
- sparse-source blockers
  - `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0% (0/1812)**
  - 其餘 blocked sparse sources：目前主要是 **history gap / snapshot archive**，`nest_pred` 本輪 latest snapshot 已恢復 `ok`
- 判讀：profile split 與 sparse blockers 仍需治理，但優先序仍低於 base-stack redesign。

---

## 目前有效問題

### P1. q35 live lane 已 exact-supported，但 base-mix uplift 最佳情境仍無法跨過 trade floor
**現象**
- `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
- `deployment_grade_component_experiment.runtime_entry_quality = 0.3725`
- `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1775`
- `base_mix_component_experiment.best_scenario = winner_triplet_p75`
- `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5106`
- `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0394`
- `live_predict_probe.allowed_layers = 0`

**判讀**
- `bias50` 公式 review 是有效的，但只把 live row 從 **0.3031 → 0.3725**；
- `dist_swing_low` uplift 只把 gap 再縮 **0.0004**，已被正式排除為主 closure；
- `bias50 + pulse (+ nose)` 已是更強的 closure 路徑，但 **winner_triplet_p75 仍不夠**；
- 下一輪必須把主路徑升級成 **base-stack redesign blocker**，而不是繼續做 component 微調。

---

### P1. `feat_4h_dist_swing_low` 已完成反證：只能作 secondary structure mix，不是主 blocker
**現象**
- `joint_component_experiment.verdict = joint_component_experiment_improves_but_still_below_floor`
- `joint_component_experiment.best_scenario = exact_lane_p75`
- `entry_quality_after = 0.3729`
- `remaining_gap_to_floor = 0.1771`

**判讀**
- 結構 uplift 幾乎不動 floor gap；
- 這題已完成 machine-read 驗證，下一輪不得再回到 `dist_swing_low` 單點 uplift 敘事。

---

### P1. post-threshold profile governance stalled：leaderboard / train / global shrinkage 仍三套語義
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage：`core_only`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- 仍需保留 dual-role governance；
- 但在 base-stack redesign 尚未完成前，不能搶走主修補頻寬。

---

### P1. sparse-source blockers 仍存在，`fin_netflow` 仍是 live auth blocker
**現象**
- `fin_netflow`：`auth_missing`, `coverage=0.0%`
- blocked sparse features：**8 個**
- `nest_pred`：本輪 latest snapshot 已恢復 `ok`，但歷史仍是 snapshot-only gap

**判讀**
- `fin_netflow` 仍是外部憑證 blocker；
- 其他 sparse sources 主要是 history/archive 缺口，不能混寫成 q35 / base-stack root cause。

---

## 本輪已清掉的問題

### RESOLVED. heartbeat 缺少 `bias50 + pulse (+ nose)` base-mix trade-floor closure artifact
**修前**
- q35 audit 只能 machine-read `bias50` 單點與 `dist_swing_low` 聯合 uplift；
- heartbeat 無法正式回答「base stack 最佳情境後還差多少 gap」。

**本輪 patch + 證據**
- `scripts/hb_q35_scaling_audit.py`：新增 `base_mix_component_experiment`
- `scripts/hb_parallel_runner.py`：新增 base-mix summary extraction
- `tests/test_hb_parallel_runner.py`：新增 regression tests
- `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **64 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1018`
  - `base_mix_component_experiment.verdict = base_mix_component_experiment_improves_but_still_below_floor`
  - `best_scenario = winner_triplet_p75`
  - `entry_quality_after = 0.5106`
  - `remaining_gap_to_floor = 0.0394`

**狀態**
- **已修復**：heartbeat 現在能 machine-read 判定 base stack 是否真能跨 floor。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 `bias50 + pulse (+ nose)` closure experiment 做成 machine-readable artifact，正式驗證它是否真能跨過 trade floor。** ✅
2. **正式把 `dist_swing_low` 降級成 secondary structure mix，不再讓它佔用主 closure 頻寬。** ✅
3. **維持 profile split / source blockers / q15 replay 的次級治理定位。** ✅

### 本輪不做
- 不直接 relax runtime gate；
- 不把 `dist_swing_low` 微幅 uplift 誤當主修補解；
- 不讓 profile split / sparse-source blocker 取代 base-stack redesign 成為主焦點。

---

## Next gate

- **Next focus:**
  1. 直接把 **`bias50 + pulse + nose` 升級成 base-stack redesign workstream**：不是再做分位數試算而已，而是要留下新的 base-stack patch / contract / verify；
  2. 維持 `feat_4h_dist_swing_low` 的 secondary structure mix 定位，不再把它當主 closure；
  3. 維持 profile governance / `fin_netflow` auth blocker / sparse-source history blockers 的零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **base-stack redesign** 直接相關的真 patch / artifact / verify；
  2. 必須 machine-read 回答 redesign 後是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`，且不回歸 `q35` applicability / `q15` exact support；
  3. `base_mix_component_experiment` 不得消失，並持續作為主 closure artifact。

- **Fallback if fail:**
  - 若 redesign 後仍無法跨過 floor，下一輪升級為 **bull q35 no-deploy governance blocker**，停止再追這條 lane 的 deployment closure；
  - 若 q35 applicability 轉成 reference-only，下一輪先處理 current bucket support / component 問題；
  - 若 next run 沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 base-stack redesign contract 再被細化）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1018_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `q35_scaling_audit.base_mix_component_experiment.verdict = base_mix_component_experiment_improves_but_still_below_floor`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 `dist_swing_low` 或單點 `bias50` closure 敘事；必須直接處理 **base-stack redesign**。
