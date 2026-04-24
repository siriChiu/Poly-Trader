# q15 Bucket Root Cause

- generated_at: **2026-04-24 08:02:34.143413**
- target_col: **simulated_pyramid_win**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.3156**
- gap_to_q35_boundary: **0.0344**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`

## Exact live lane
- rows: **745**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 690, 'CAUTION|structure_quality_caution|q15': 50, 'CAUTION|base_caution_regime_or_bias|q35': 5}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** (690 rows)
- near_boundary_window: `{'lower': 0.3156, 'upper': 0.35}`
- near_boundary_rows: **36**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.4153, 'current_normalized': 0.4153, 'needed_raw_delta_to_cross_q35': 0.1012, 'target_bucket_p25': 0.5326, 'target_bucket_median': 0.5923, 'needed_raw_delta_to_target_p25': 0.1173, 'needed_raw_delta_to_target_median': 0.177}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4153 / norm=0.4153 / Δto_cross_q35=0.1012 / target_p25=0.5326 / target_median=0.5923
- `feat_4h_dist_bb_lower`: current=1.3106 / norm=0.1638 / Δto_cross_q35=0.8339 / target_p25=2.5227 / target_median=3.2347
- `feat_4h_dist_swing_low`: current=3.6481 / norm=0.3648 / Δto_cross_q35=1.0424 / target_p25=3.1973 / target_median=3.5048

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
