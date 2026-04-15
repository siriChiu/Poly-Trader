# ISSUES.md — Current State Only

_最後更新：2026-04-15 11:55 UTC — Heartbeat #1016（本輪把 q35 exact-lane formula review 從只覆蓋 p25..p90，擴到 **min..p25 core-normal 支持區**；live `feat_4h_bias50` 不再被 legacy 線性公式硬壓成 0 分，`entry_quality` 由 **0.4192 → 0.4919**，trade-floor gap 由 **0.1308 → 0.0581**。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 做 `feat_4h_bias50` exact-supported q35 lane component experiment / formula review；
  2. 驗證 profile governance 在 exact-supported lane 下如何收斂；
  3. 維持 q15 boundary replay / source auth blocker / breaker false-positive 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 bias50 component experiment / floor-gap closure 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 bias50 experiment 是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`；
  3. `q35_scaling_audit.scope_applicability.status` 必須持續正確反映 live-active vs reference-only。
- **Fallback if fail**
  - 若 bias50 experiment 仍無法跨過 floor，下一輪改查 pulse / base mix 聯合路徑；
  - 若 q35 applicability 又變 reference-only，下一輪先處理 current bucket 的 support / component 問題；
  - 若 next run 沒有 bias50 component artifact，升級為 trade-floor blocker。

### 本輪承接結果
- **已處理**
  - `model/q35_bias50_calibration.py`：新增 `exact_lane_core_band_below_p25` 分支，讓 exact-lane `min..p25` 的 core-normal 支持區在 `bias50_formula_may_be_too_harsh` 情境下可得到保守非零 score，不再被 legacy 線性公式壓成 0。
  - `tests/test_api_feature_history_and_predictor.py`：新增 regression test，鎖住 `min..p25` 低側支持區的 calibration 行為。
  - `ARCHITECTURE.md`：同步 q35/q15 calibration contract，明確記錄低側 core-normal 支持區也必須被 exact-lane formula review 覆蓋。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **37 passed**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **25 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1016` → **通過**
- **本輪 machine-read 結論**
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
  - `q35_scaling_audit.deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `q35_scaling_audit.deployment_grade_component_experiment.runtime_entry_quality = 0.4919`
  - `q35_scaling_audit.deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.0581`
  - `live_predict_probe.allowed_layers = 0`
- **本輪明確不做**
  - 不直接 relax runtime gate；
  - 不回頭把 q15 boundary replay 升回主修補路徑；
  - 不把 `fin_netflow` auth blocker 混寫成 bias50 / q35 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/q35_bias50_calibration.py`
    - 新增 `exact_lane_core_band_below_p25` 校準分支。
    - 只在 `overall_verdict=bias50_formula_may_be_too_harsh` + `status=formula_review_required` + bull q35 current lane 成立時啟用。
    - 目的：修掉「exact-supported 低側 core-normal bias50 仍被算成 0 分」這個假 blocker。
  - `tests/test_api_feature_history_and_predictor.py`
    - 新增 `test_piecewise_q35_bias50_calibration_supports_exact_lane_core_normal_below_p25_formula_review`。
  - `ARCHITECTURE.md`
    - 新增 #1016 contract：low-side core-normal band 也必須被 exact-lane formula review 覆蓋。
- **Tests（已通過）**
  - `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **37 passed**
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **25 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast --hb 1016`
- **已刷新 artifacts**
  - `data/heartbeat_1016_summary.json`
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
- Heartbeat #1016：
  - Raw / Features / Labels：**21686 / 13115 / 43366**
  - 本輪增量：**+1 raw / +1 feature / +0 label**
  - canonical target `simulated_pyramid_win`：**0.5787**
  - 240m labels：**21745 rows / target_rows 12823 / lag_vs_raw 約 3.5h**
  - 1440m labels：**12536 rows / target_rows 12536 / lag_vs_raw 約 23.3h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**22/30 pass**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 98.0%**
  - win_rate：**0.9520**
  - avg_quality：**0.6449**
  - avg_pnl：**+0.0204**
  - avg_drawdown_penalty：**0.0417**
- 判讀：canonical lane 仍健康；當前主 blocker 是 **entry-quality 尚未跨過 trade floor**，不是 drift。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - `entry_quality = 0.4919`
  - `allowed_layers = 0 → 0`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `feat_4h_bias50.normalized_score = 0.2335`（本輪 patch 後不再是 0）
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
  - `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `baseline_entry_quality = 0.4192`
  - `runtime_entry_quality = 0.4919`
  - `runtime_remaining_gap_to_floor = 0.0581`
  - `required_bias50_cap_for_floor = 0.1937`
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `remaining_gap_to_floor = 0.0581`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.1937`
- `data/q15_bucket_root_cause.json`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_dist_swing_low`
- `data/q15_boundary_replay.json`
  - `verdict = boundary_replay_not_applicable`
- 判讀：**q35 formula 假 blocker 已縮小，但還沒跨 floor；q15 boundary 仍不是主路徑。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `profile_split.verdict = dual_role_required`
- `fin_netflow`
  - coverage：**0.0%**
  - latest status：**auth_missing**
  - archive_window_coverage：**0.0% (0/1810)**
- 判讀：profile split 仍未收斂，但優先序低於 trade-floor closure；`fin_netflow` 仍是獨立外部 auth blocker。

---

## 目前有效問題

### P1. exact-supported q35 live lane 仍低於 trade floor；bias50 patch 已有效但不足以放行
**現象**
- `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
- `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
- `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
- `entry_quality: 0.4192 → 0.4919`
- `remaining_gap_to_floor: 0.1308 → 0.0581`
- `allowed_layers = 0`
- `best_single_component_required_score_delta = 0.1937`

**判讀**
- 本輪已證明 root cause 之一是 bias50 legacy 線性公式過嚴；
- 但單點 bias50 修補仍不足以讓 current q35 live lane 跨過 `0.55` trade floor；
- 下一輪需升級成 **bias50 + 結構 component 聯合修補**，優先看 `feat_4h_dist_swing_low` / 結構 mix，而不是再只做 generic q35 敘事。

---

### P1. post-threshold profile governance stalled：leaderboard / train / global shrinkage 仍三套語義
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage：`core_only`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- exact-supported live lane 已恢復，但 production profile 與 global shrinkage winner 仍未完成角色邊界收斂；
- 仍需保留 dual-role governance，但優先序低於 trade-floor closure。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `coverage = 0.0%`
- `latest status = auth_missing`
- `archive_window_coverage = 0.0% (0/1810)`

**判讀**
- 仍是外部憑證 blocker；
- 不可與 q35 / bias50 / profile split 混寫。

---

## 本輪已清掉的問題

### RESOLVED. exact-lane core-normal 低側支持區會被 legacy bias50 線性公式誤殺成 0 分
**修前**
- `bias50_formula_may_be_too_harsh` 已被 q35 audit 識別；
- 但 `compute_piecewise_bias50_score()` 只覆蓋 `p25..p90`，沒有覆蓋 `min..p25`；
- 結果 exact-supported q35 row 即使落在 core-normal 低側支持區，也仍然拿到 `normalized_score=0.0`。

**本輪 patch + 證據**
- `model/q35_bias50_calibration.py`：新增 `segment=exact_lane_core_band_below_p25`
- `tests/test_api_feature_history_and_predictor.py`：新增 regression test
- `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **37 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1016`
  - `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `entry_quality: 0.4192 → 0.4919`
  - `trade-floor gap: 0.1308 → 0.0581`
  - `feat_4h_bias50.normalized_score = 0.2335`

**狀態**
- **已修復**：current q35 exact-supported row 不再因 low-side core-normal bias50 落點而被 legacy 公式硬壓成 0 分。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **修掉 q35 exact-lane formula review 的 low-side blind spot，讓 exact-supported core-normal bias50 row 不再被誤殺。** ✅
2. **用 fast heartbeat 驗證 patch 是否真的縮小 floor gap，而不是只改文件。** ✅
3. **維持 profile split / fin_netflow auth blocker / q15 boundary replay 的次級治理定位。** ✅

### 本輪不做
- 不直接 relax runtime gate；
- 不把 q15 boundary replay 升回主修補路徑；
- 不把 source auth blocker 重新包裝成 q35 問題。

---

## Next gate

- **Next focus:**
  1. 對 `feat_4h_bias50 + feat_4h_dist_swing_low` 做 **exact-supported q35 lane 聯合 component experiment**，直接驗證 `entry_quality` 能否跨過 `0.55`、`allowed_layers` 能否 > 0；
  2. 在 exact-supported lane 下，釐清 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_only` 的 production vs shrinkage 角色邊界；
  3. 維持 `q15_boundary_replay / fin_netflow auth blocker / breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **trade-floor closure** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：聯合 component experiment 後 `entry_quality` 是否 ≥ `0.55`、`allowed_layers` 是否 > 0；
  3. `q35_scaling_audit.scope_applicability.status`、`q15_support_audit.support_route.verdict`、`q15_boundary_replay.verdict` 不得漂移。

- **Fallback if fail:**
  - 若 `bias50 + feat_4h_dist_swing_low` 仍無法跨過 floor，下一輪升級成 **base mix + structure mix 聯合問題**，把 `feat_nose / feat_pulse` 一起納入；
  - 若 q35 applicability 又回 reference-only，下一輪先處理 current bucket 的 support / component 問題，不得硬套 q35 結論；
  - 若沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若聯合 component contract 被正式採納）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1016_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
     - `q35_scaling_audit.deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 q15 boundary / generic q35 敘事；必須直接做 **bias50 + feat_4h_dist_swing_low 聯合 trade-floor closure / profile governance 收斂**。
