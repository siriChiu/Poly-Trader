# q15 Bucket Root Cause

- generated_at: **2026-04-29 22:18:25.944447**
- target_col: **simulated_pyramid_win**
- verdict: **no_exact_live_lane_rows**
- candidate_patch_type: **scope_generation**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / C**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.1507**
- gap_to_q35_boundary: **0.1993**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **0**
- bucket_counts: `{}`
- dominant_neighbor_bucket: **None** (0 rows)
- near_boundary_window: `None`
- near_boundary_rows: **0**

## Decision
- reason: 連 exact live lane 都沒有資料，先補 same regime/gate/entry-quality lane，而不是只修 bucket 邊界。
- candidate_patch: `{'type': 'scope_generation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.3034, 'current_normalized': 0.3034, 'needed_raw_delta_to_cross_q35': 0.5862, 'target_bucket_p25': None, 'target_bucket_median': None, 'needed_raw_delta_to_target_p25': None, 'needed_raw_delta_to_target_median': None}`
- verify_next: 重跑 bull_4h_pocket_ablation.py，確認 exact_scope_rows > 0。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3034 / norm=0.3034 / Δto_cross_q35=0.5862 / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=0.853 / norm=0.1066 / Δto_cross_q35=4.8315 / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=0.3754 / norm=0.0375 / Δto_cross_q35=6.0394 / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
