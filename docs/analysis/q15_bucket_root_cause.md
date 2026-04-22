# q15 Bucket Root Cause

- generated_at: **2026-04-22 05:25:40.012967**
- target_col: **simulated_pyramid_win**
- verdict: **current_row_already_above_q35_boundary**
- candidate_patch_type: **support_accumulation**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / BLOCK / D**
- structure_bucket: `BLOCK|bull_high_bias200_overheat_block|q65`
- structure_quality: **0.6934**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`

## Exact live lane
- rows: **367**
- bucket_counts: `{'BLOCK|bull_high_bias200_overheat_block|q35': 143, 'BLOCK|bull_high_bias200_overheat_block|q65': 116, 'BLOCK|structure_quality_block|q00': 108}`
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q35** (143 rows)
- near_boundary_window: `{'lower': 0.6934, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live row 已不在 q15/q35 邊界下方，問題改成 exact support 累積，不是 bucket repair。
- candidate_patch: `{'type': 'support_accumulation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 1.1712, 'current_normalized': 1.0, 'needed_raw_delta_to_cross_q35': -0.1712, 'target_bucket_p25': 0.8459, 'target_bucket_median': 0.8907, 'needed_raw_delta_to_target_p25': -0.3253, 'needed_raw_delta_to_target_median': -0.2805}`
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。

## Component deltas
- `feat_4h_bb_pct_b`: current=1.1712 / norm=1.0 / Δto_cross_q35=-0.1712 / target_p25=0.8459 / target_median=0.8907
- `feat_4h_dist_bb_lower`: current=3.85 / norm=0.4813 / Δto_cross_q35=0.0 / target_p25=2.8454 / target_median=2.9917
- `feat_4h_dist_swing_low`: current=5.8974 / norm=0.5897 / Δto_cross_q35=0.0 / target_p25=5.0245 / target_median=5.1317

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
