# Current-Live Bucket Root Cause

- generated_at: **2026-05-20 22:11:32.960610**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2979**
- gap_to_q35_boundary: **0.0521**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **235**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q65': 67, 'CAUTION|base_caution_regime_or_bias|q00': 63, 'CAUTION|base_caution_regime_or_bias|q15': 54, 'CAUTION|base_caution_regime_or_bias|q85': 35, 'CAUTION|base_caution_regime_or_bias|q35': 16}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** (67 rows)
- near_boundary_window: `{'lower': 0.2979, 'upper': 0.35}`
- near_boundary_rows: **19**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5469, 'current_normalized': 0.5469, 'needed_raw_delta_to_cross_q35': 0.1532, 'target_bucket_p25': 0.7082, 'target_bucket_median': 0.7643, 'needed_raw_delta_to_target_p25': 0.1613, 'needed_raw_delta_to_target_median': 0.2174}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5469 / norm=0.5469 / Δto_cross_q35=0.1532 / target_p25=0.7082 / target_median=0.7643
- `feat_4h_dist_bb_lower`: current=1.3449 / norm=0.1681 / Δto_cross_q35=1.263 / target_p25=5.5052 / target_median=5.8772
- `feat_4h_dist_swing_low`: current=1.7111 / norm=0.1711 / Δto_cross_q35=1.5788 / target_p25=8.7982 / target_median=9.2352

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
