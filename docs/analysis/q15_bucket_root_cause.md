# Current-Live Bucket Root Cause

- generated_at: **2026-05-04 23:56:23.006167**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **structure_scoring_gap_not_boundary**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bull_q15_bias50_overextended_block|q15', 'regime_label': 'bull', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bull / BLOCK / D**
- structure_bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`
- structure_quality: **0.3483**
- gap_to_q35_boundary: **0.0017**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **185**
- bucket_counts: `{'BLOCK|bull_high_bias200_overheat_block|q35': 100, 'BLOCK|bull_high_bias200_overheat_block|q65': 82, 'BLOCK|structure_quality_block|q00': 3}`
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q35** (100 rows)
- near_boundary_window: `{'lower': 0.3483, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: exact live lane 的樣本全部落在鄰近 bucket，且 current_structure_quality 與 q35 邊界之間沒有 exact-lane 緩衝列；這代表單純放寬 current bucket / q35 boundary 不能生成 exact rows，應優先查結構 component scoring。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.6476, 'current_normalized': 0.6476, 'needed_raw_delta_to_cross_q35': 0.005, 'target_bucket_p25': 0.5222, 'target_bucket_median': 0.5942, 'needed_raw_delta_to_target_p25': -0.1254, 'needed_raw_delta_to_target_median': -0.0534}`
- verify_next: 優先用 current-live bucket root-cause artifact 鎖定的 component 做 counterfactual，確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.6476 / norm=0.6476 / Δto_cross_q35=0.005 / target_p25=0.5222 / target_median=0.5942
- `feat_4h_dist_bb_lower`: current=1.3215 / norm=0.1652 / Δto_cross_q35=0.0412 / target_p25=1.6782 / target_median=1.8567
- `feat_4h_dist_swing_low`: current=2.2316 / norm=0.2232 / Δto_cross_q35=0.0515 / target_p25=2.5377 / target_median=4.1238

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
