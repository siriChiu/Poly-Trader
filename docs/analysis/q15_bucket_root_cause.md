# q15 Bucket Root Cause

- generated_at: **2026-04-15 08:22:43.467783**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_sensitivity_candidate**
- candidate_patch_type: **bucket_boundary_review**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.3384**
- gap_to_q35_boundary: **0.0116**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket_blocks_trade`

## Exact live lane
- rows: **421**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 158, 'CAUTION|base_caution_regime_or_bias|q35': 114, 'CAUTION|base_caution_regime_or_bias|q15': 67, 'CAUTION|base_caution_regime_or_bias|q00': 47, 'CAUTION|base_caution_regime_or_bias|q65': 18, 'CAUTION|base_caution_regime_or_bias|q85': 13, 'CAUTION|structure_quality_caution|q15': 4}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** (158 rows)
- near_boundary_window: `{'lower': 0.3384, 'upper': 0.35}`
- near_boundary_rows: **2**

## Decision
- reason: current_structure_quality 已貼近 q35 邊界，且 exact-lane 存在 near-boundary rows；可把 q15↔q35 分桶公式列入候選，但仍需先做 exact-support legality 驗證。
- candidate_patch: `{'type': 'bucket_boundary_review', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.3943, 'current_normalized': 0.3943, 'needed_raw_delta_to_cross_q35': 0.0341, 'target_bucket_p25': 0.7129, 'target_bucket_median': 0.9868, 'needed_raw_delta_to_target_p25': 0.3186, 'needed_raw_delta_to_target_median': 0.5925}`
- verify_next: 以歷史 lane 回放驗證 boundary review 不會把 0-row blocker 假裝成已解。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3943 / norm=0.3943 / Δto_cross_q35=0.0341 / target_p25=0.7129 / target_median=0.9868
- `feat_4h_dist_bb_lower`: current=1.2412 / norm=0.1552 / Δto_cross_q35=0.2812 / target_p25=2.9709 / target_median=3.3455
- `feat_4h_dist_swing_low`: current=4.6416 / norm=0.4642 / Δto_cross_q35=0.3515 / target_p25=3.4987 / target_median=3.7883

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
