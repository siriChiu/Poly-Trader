# q15 Bucket Root Cause

- generated_at: **2026-04-21 03:59:59.464808**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_sensitivity_candidate**
- candidate_patch_type: **bucket_boundary_review**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.3433**
- gap_to_q35_boundary: **0.0067**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`

## Exact live lane
- rows: **1040**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 661, 'CAUTION|structure_quality_caution|q15': 379}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** (661 rows)
- near_boundary_window: `{'lower': 0.3433, 'upper': 0.35}`
- near_boundary_rows: **28**

## Decision
- reason: current_structure_quality 已貼近 q35 邊界，且 exact-lane 存在 near-boundary rows；可把 q15↔q35 分桶公式列入候選，但仍需先做 exact-support legality 驗證。
- candidate_patch: `{'type': 'bucket_boundary_review', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5474, 'current_normalized': 0.5474, 'needed_raw_delta_to_cross_q35': 0.0197, 'target_bucket_p25': 0.4829, 'target_bucket_median': 0.6715, 'needed_raw_delta_to_target_p25': -0.0645, 'needed_raw_delta_to_target_median': 0.1241}`
- verify_next: 以歷史 lane 回放驗證 boundary review 不會把 0-row blocker 假裝成已解。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5474 / norm=0.5474 / Δto_cross_q35=0.0197 / target_p25=0.4829 / target_median=0.6715
- `feat_4h_dist_bb_lower`: current=1.689 / norm=0.2111 / Δto_cross_q35=0.1624 / target_p25=1.5397 / target_median=2.0635
- `feat_4h_dist_swing_low`: current=2.6516 / norm=0.2652 / Δto_cross_q35=0.203 / target_p25=2.0764 / target_median=4.194

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
