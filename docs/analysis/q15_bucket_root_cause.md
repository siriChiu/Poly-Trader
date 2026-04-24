# q15 Bucket Root Cause

- generated_at: **2026-04-24 11:08:35.169141**
- target_col: **simulated_pyramid_win**
- verdict: **current_row_already_above_q35_boundary**
- candidate_patch_type: **support_accumulation**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bull_high_bias200_overheat_block|q35', 'regime_label': 'bull', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 600, 'bucket_semantic_signature': None}`

## Current live
- live path: **bull / BLOCK / D**
- structure_bucket: `BLOCK|bull_high_bias200_overheat_block|q35`
- structure_quality: **0.4163**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **5 / 50 / 45**

## Exact live lane
- rows: **90**
- bucket_counts: `{'BLOCK|bull_high_bias200_overheat_block|q65': 82, 'BLOCK|bull_high_bias200_overheat_block|q35': 5, 'BLOCK|structure_quality_block|q00': 3}`
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q65** (82 rows)
- near_boundary_window: `{'lower': 0.4163, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live row 已不在 q15/q35 邊界下方，問題改成 exact support 累積，不是 bucket repair。
- candidate_patch: `{'type': 'support_accumulation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5867, 'current_normalized': 0.5867, 'needed_raw_delta_to_cross_q35': 0.0, 'target_bucket_p25': 1.8718, 'target_bucket_median': 1.9105, 'needed_raw_delta_to_target_p25': 0.4133, 'needed_raw_delta_to_target_median': 0.4133}`
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5867 / norm=0.5867 / Δto_cross_q35=0.0 / target_p25=1.8718 / target_median=1.9105
- `feat_4h_dist_bb_lower`: current=1.8331 / norm=0.2291 / Δto_cross_q35=0.0 / target_p25=4.8843 / target_median=4.995
- `feat_4h_dist_swing_low`: current=4.2798 / norm=0.428 / Δto_cross_q35=0.0 / target_p25=5.4449 / target_median=5.5338

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
