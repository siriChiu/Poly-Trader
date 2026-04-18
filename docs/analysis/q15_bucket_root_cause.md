# q15 Bucket Root Cause

- generated_at: **2026-04-18 12:08:40.638156**
- target_col: **simulated_pyramid_win**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / C**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.2656**
- gap_to_q35_boundary: **0.0844**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Exact live lane
- rows: **51**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 50, 'CAUTION|structure_quality_caution|q35': 1}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** (50 rows)
- near_boundary_window: `{'lower': 0.2656, 'upper': 0.35}`
- near_boundary_rows: **9**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.3079, 'current_normalized': 0.3079, 'needed_raw_delta_to_cross_q35': 0.2482, 'target_bucket_p25': 0.337, 'target_bucket_median': 0.3536, 'needed_raw_delta_to_target_p25': 0.0291, 'needed_raw_delta_to_target_median': 0.0457}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3079 / norm=0.3079 / Δto_cross_q35=0.2482 / target_p25=0.337 / target_median=0.3536
- `feat_4h_dist_bb_lower`: current=0.8826 / norm=0.1103 / Δto_cross_q35=2.0461 / target_p25=1.6837 / target_median=1.8043
- `feat_4h_dist_swing_low`: current=3.7723 / norm=0.3772 / Δto_cross_q35=2.5576 / target_p25=1.7921 / target_median=1.8703

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
