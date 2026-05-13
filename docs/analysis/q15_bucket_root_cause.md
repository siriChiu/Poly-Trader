# Current-Live Bucket Root Cause

- generated_at: **2026-05-13 12:20:44.051389**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.1712**
- gap_to_q35_boundary: **0.1788**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- support rows/minimum/gap: **95 / 50 / 0**

## Exact live lane
- rows: **415**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q85': 249, 'CAUTION|base_caution_regime_or_bias|q65': 76, 'CAUTION|base_caution_regime_or_bias|q15': 54, 'CAUTION|base_caution_regime_or_bias|q00': 23, 'CAUTION|base_caution_regime_or_bias|q35': 13}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q85** (249 rows)
- near_boundary_window: `{'lower': 0.1712, 'upper': 0.35}`
- near_boundary_rows: **49**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.3429, 'current_normalized': 0.3429, 'needed_raw_delta_to_cross_q35': 0.5259, 'target_bucket_p25': 0.8983, 'target_bucket_median': 0.9607, 'needed_raw_delta_to_target_p25': 0.5554, 'needed_raw_delta_to_target_median': 0.6178}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3429 / norm=0.3429 / Δto_cross_q35=0.5259 / target_p25=0.8983 / target_median=0.9607
- `feat_4h_dist_bb_lower`: current=0.6615 / norm=0.0827 / Δto_cross_q35=4.3345 / target_p25=8.0552 / target_median=8.3634
- `feat_4h_dist_swing_low`: current=0.8284 / norm=0.0828 / Δto_cross_q35=5.4182 / target_p25=8.8675 / target_median=8.9712

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
