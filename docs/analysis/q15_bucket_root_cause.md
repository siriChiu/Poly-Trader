# Current-Live Bucket Root Cause

- generated_at: **2026-04-30 06:15:05.806706**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **no_exact_live_lane_rows**
- candidate_patch_type: **scope_generation**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 100, 'bucket_semantic_signature': None}`

## Current live
- live path: **bear / BLOCK / C**
- structure_bucket: `BLOCK|structure_quality_block|q00`
- structure_quality: **0.1287**
- gap_to_q35_boundary: **0.2213**
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
- candidate_patch: `{'type': 'scope_generation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.2818, 'current_normalized': 0.2818, 'needed_raw_delta_to_cross_q35': 0.6509, 'target_bucket_p25': None, 'target_bucket_median': None, 'needed_raw_delta_to_target_p25': None, 'needed_raw_delta_to_target_median': None}`
- verify_next: 重跑 bull_4h_pocket_ablation.py，確認 exact_scope_rows > 0。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.2818 / norm=0.2818 / Δto_cross_q35=0.6509 / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=0.7977 / norm=0.0997 / Δto_cross_q35=5.3648 / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=-0.0948 / norm=0.0 / Δto_cross_q35=6.8009 / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
