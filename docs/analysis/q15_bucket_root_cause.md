# q15 Bucket Root Cause

- generated_at: **2026-04-20 21:10:05.044722**
- target_col: **simulated_pyramid_win**
- verdict: **current_row_already_above_q35_boundary**
- candidate_patch_type: **support_accumulation**
- candidate_patch_feature: **feat_4h_dist_swing_low**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q35`
- structure_quality: **0.466**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`

## Exact live lane
- rows: **1040**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 661, 'CAUTION|structure_quality_caution|q15': 379}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** (379 rows)
- near_boundary_window: `{'lower': 0.466, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live row 已不在 q15/q35 邊界下方，問題改成 exact support 累積，不是 bucket repair。
- candidate_patch: `{'type': 'support_accumulation', 'feature': 'feat_4h_dist_swing_low', 'current_raw': 3.1644, 'current_normalized': 0.3164, 'needed_raw_delta_to_cross_q35': 0.0, 'target_bucket_p25': 3.0514, 'target_bucket_median': 3.3343, 'needed_raw_delta_to_target_p25': -0.113, 'needed_raw_delta_to_target_median': 0.1699}`
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.7746 / norm=0.7746 / Δto_cross_q35=0.0 / target_p25=0.2255 / target_median=0.3018
- `feat_4h_dist_bb_lower`: current=2.3806 / norm=0.2976 / Δto_cross_q35=0.0 / target_p25=0.6538 / target_median=0.8728
- `feat_4h_dist_swing_low`: current=3.1644 / norm=0.3164 / Δto_cross_q35=0.0 / target_p25=3.0514 / target_median=3.3343

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
