# Current-Live Bucket Root Cause

- generated_at: **2026-06-05T03:46:18.436695Z**
- feature_timestamp: **2026-06-05 03:00:00**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bias200_below_min|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / BLOCK / C**
- structure_bucket: `BLOCK|bias200_below_min|q00`
- structure_quality: **0.0593**
- gap_to_q35_boundary: **0.2907**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade`
- support rows/minimum/gap: **131 / 50 / 0**

## Exact live lane
- rows: **473**
- bucket_counts: `{'BLOCK|bear_bias200_hard_block|q00': 174, 'BLOCK|bias200_below_min|q00': 139, 'BLOCK|structure_quality_block|q00': 93, 'BLOCK|bias200_below_min|q15': 44, 'BLOCK|bear_bias200_hard_block|q15': 23}`
- dominant_neighbor_bucket: **BLOCK|bear_bias200_hard_block|q00** (174 rows)
- near_boundary_window: `{'lower': 0.0593, 'upper': 0.35}`
- near_boundary_rows: **293**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': -0.0299, 'current_normalized': 0.0, 'needed_raw_delta_to_cross_q35': 0.8849, 'target_bucket_p25': -0.0101, 'target_bucket_median': 0.0393, 'needed_raw_delta_to_target_p25': 0.0299, 'needed_raw_delta_to_target_median': 0.0692}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=-0.0299 / norm=0.0 / Δto_cross_q35=0.8849 / target_p25=-0.0101 / target_median=0.0393
- `feat_4h_dist_bb_lower`: current=-0.0984 / norm=0.0 / Δto_cross_q35=7.1457 / target_p25=-0.0222 / target_median=0.0977
- `feat_4h_dist_swing_low`: current=1.7959 / norm=0.1796 / Δto_cross_q35=8.2041 / target_p25=-2.6255 / target_median=-1.7578

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
