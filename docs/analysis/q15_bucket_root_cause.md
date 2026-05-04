# Current-Live Bucket Root Cause

- generated_at: **2026-05-04 13:26:55.013445**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bull', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bull / CAUTION / D**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.2117**
- gap_to_q35_boundary: **0.1383**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **820**
- bucket_counts: `{'CAUTION|structure_quality_caution|q35': 687, 'CAUTION|structure_quality_caution|q15': 132, 'CAUTION|base_caution_regime_or_bias|q35': 1}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** (687 rows)
- near_boundary_window: `{'lower': 0.2117, 'upper': 0.35}`
- near_boundary_rows: **128**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.4082, 'current_normalized': 0.4082, 'needed_raw_delta_to_cross_q35': 0.4068, 'target_bucket_p25': 0.5325, 'target_bucket_median': 0.5917, 'needed_raw_delta_to_target_p25': 0.1243, 'needed_raw_delta_to_target_median': 0.1835}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4082 / norm=0.4082 / Δto_cross_q35=0.4068 / target_p25=0.5325 / target_median=0.5917
- `feat_4h_dist_bb_lower`: current=0.8841 / norm=0.1105 / Δto_cross_q35=3.3527 / target_p25=2.5211 / target_median=3.2212
- `feat_4h_dist_swing_low`: current=1.1044 / norm=0.1104 / Δto_cross_q35=4.1909 / target_p25=3.1957 / target_median=3.5041

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
