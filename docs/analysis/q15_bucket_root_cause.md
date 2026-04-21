# q15 Bucket Root Cause

- generated_at: **2026-04-21 04:23:23.782550**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_sensitivity_candidate**
- candidate_patch_type: **bucket_boundary_review**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.32**
- gap_to_q35_boundary: **0.03**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade`

## Exact live lane
- rows: **2408**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q35': 1117, 'CAUTION|base_caution_regime_or_bias|q65': 434, 'CAUTION|base_caution_regime_or_bias|q15': 327, 'CAUTION|base_caution_regime_or_bias|q00': 304, 'CAUTION|base_caution_regime_or_bias|q85': 226}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** (1117 rows)
- near_boundary_window: `{'lower': 0.32, 'upper': 0.35}`
- near_boundary_rows: **12**

## Decision
- reason: current_structure_quality 已貼近 q35 邊界，且 exact-lane 存在 near-boundary rows；可把 q15↔q35 分桶公式列入候選，但仍需先做 exact-support legality 驗證。
- candidate_patch: `{'type': 'bucket_boundary_review', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5073, 'current_normalized': 0.5073, 'needed_raw_delta_to_cross_q35': 0.0882, 'target_bucket_p25': 0.654, 'target_bucket_median': 0.695, 'needed_raw_delta_to_target_p25': 0.1467, 'needed_raw_delta_to_target_median': 0.1877}`
- verify_next: 以歷史 lane 回放驗證 boundary review 不會把 0-row blocker 假裝成已解。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5073 / norm=0.5073 / Δto_cross_q35=0.0882 / target_p25=0.654 / target_median=0.695
- `feat_4h_dist_bb_lower`: current=1.5737 / norm=0.1967 / Δto_cross_q35=0.7273 / target_p25=2.1292 / target_median=3.3027
- `feat_4h_dist_swing_low`: current=2.5043 / norm=0.2504 / Δto_cross_q35=0.9091 / target_p25=2.0932 / target_median=3.6776

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
