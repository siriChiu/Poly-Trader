# q15 Bucket Root Cause

- generated_at: **2026-04-23 14:10:43.895945**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / BLOCK / D**
- structure_bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`
- structure_quality: **0.272**
- gap_to_q35_boundary: **0.078**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`

## Exact live lane
- rows: **85**
- bucket_counts: `{'BLOCK|bull_high_bias200_overheat_block|q65': 82, 'BLOCK|structure_quality_block|q00': 3}`
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q65** (82 rows)
- near_boundary_window: `{'lower': 0.272, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{'type': None, 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.3288, 'current_normalized': 0.3288, 'needed_raw_delta_to_cross_q35': 0.2294, 'target_bucket_p25': 1.8718, 'target_bucket_median': 1.9105, 'needed_raw_delta_to_target_p25': 0.6712, 'needed_raw_delta_to_target_median': 0.6712}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3288 / norm=0.3288 / Δto_cross_q35=0.2294 / target_p25=1.8718 / target_median=1.9105
- `feat_4h_dist_bb_lower`: current=1.082 / norm=0.1353 / Δto_cross_q35=1.8909 / target_p25=4.8843 / target_median=4.995
- `feat_4h_dist_swing_low`: current=3.5033 / norm=0.3503 / Δto_cross_q35=2.3636 / target_p25=5.4449 / target_median=5.5338

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
