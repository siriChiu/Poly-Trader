# q15 Bucket Root Cause

- generated_at: **2026-04-21 19:01:19.097308**
- target_col: **simulated_pyramid_win**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.2832**
- gap_to_q35_boundary: **0.0668**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`

## Exact live lane
- rows: **1056**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 677, 'CAUTION|structure_quality_caution|q15': 379}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** (677 rows)
- near_boundary_window: `{'lower': 0.2832, 'upper': 0.35}`
- near_boundary_rows: **115**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.4191, 'current_normalized': 0.4191, 'needed_raw_delta_to_cross_q35': 0.1965, 'target_bucket_p25': 0.4847, 'target_bucket_median': 0.6744, 'needed_raw_delta_to_target_p25': 0.0656, 'needed_raw_delta_to_target_median': 0.2553}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4191 / norm=0.4191 / Δto_cross_q35=0.1965 / target_p25=0.4847 / target_median=0.6744
- `feat_4h_dist_bb_lower`: current=1.3081 / norm=0.1635 / Δto_cross_q35=1.6194 / target_p25=1.5457 / target_median=2.0685
- `feat_4h_dist_swing_low`: current=2.6279 / norm=0.2628 / Δto_cross_q35=2.0242 / target_p25=2.0796 / target_median=3.9587

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
