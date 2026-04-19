# q15 Bucket Root Cause

- generated_at: **2026-04-19 14:14:04.455344**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q35`
- structure_quality: **0.356**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`

## Exact live lane
- rows: **839**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 649, 'CAUTION|structure_quality_caution|q15': 183, 'CAUTION|base_caution_regime_or_bias|q15': 7}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** (183 rows)
- near_boundary_window: `{'lower': 0.356, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{'type': None, 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5372, 'current_normalized': 0.5372, 'needed_raw_delta_to_cross_q35': 0.0, 'target_bucket_p25': 0.3693, 'target_bucket_median': 0.4022, 'needed_raw_delta_to_target_p25': -0.1679, 'needed_raw_delta_to_target_median': -0.135}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5372 / norm=0.5372 / Δto_cross_q35=0.0 / target_p25=0.3693 / target_median=0.4022
- `feat_4h_dist_bb_lower`: current=1.5799 / norm=0.1975 / Δto_cross_q35=0.0 / target_p25=1.1694 / target_median=1.2669
- `feat_4h_dist_swing_low`: current=3.2779 / norm=0.3278 / Δto_cross_q35=0.0 / target_p25=1.5791 / target_median=3.8325

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
