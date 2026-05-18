# Current-Live Bucket Root Cause

- generated_at: **2026-05-18 04:05:13.163327**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q00', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q00`
- structure_quality: **0.0642**
- gap_to_q35_boundary: **0.2858**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **62**
- bucket_counts: `{'CAUTION|structure_quality_caution|q15': 62}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** (62 rows)
- near_boundary_window: `{'lower': 0.0642, 'upper': 0.35}`
- near_boundary_rows: **62**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.1439, 'current_normalized': 0.1439, 'needed_raw_delta_to_cross_q35': 0.8406, 'target_bucket_p25': 0.3655, 'target_bucket_median': 0.4095, 'needed_raw_delta_to_target_p25': 0.2216, 'needed_raw_delta_to_target_median': 0.2656}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.1439 / norm=0.1439 / Δto_cross_q35=0.8406 / target_p25=0.3655 / target_median=0.4095
- `feat_4h_dist_bb_lower`: current=0.3696 / norm=0.0462 / Δto_cross_q35=6.9285 / target_p25=0.8971 / target_median=1.0297
- `feat_4h_dist_swing_low`: current=-0.9184 / norm=0.0 / Δto_cross_q35=9.579 / target_p25=-0.7233 / target_median=-0.5398

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
