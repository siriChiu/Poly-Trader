# q15 Bucket Root Cause

- generated_at: **2026-04-24 12:54:16.359105**
- target_col: **simulated_pyramid_win**
- verdict: **current_exact_support_under_minimum**
- candidate_patch_type: **support_accumulation_or_semantic_rebaseline**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bull_q15_bias50_overextended_block|q15', 'regime_label': 'bull', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 600, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bull / BLOCK / D**
- structure_bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`
- structure_quality: **0.2916**
- gap_to_q35_boundary: **0.0584**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **29 / 50 / 21**

## Exact live lane
- rows: **90**
- bucket_counts: `{'BLOCK|bull_high_bias200_overheat_block|q65': 82, 'BLOCK|bull_high_bias200_overheat_block|q35': 5, 'BLOCK|structure_quality_block|q00': 3}`
- dominant_neighbor_bucket: **BLOCK|bull_high_bias200_overheat_block|q65** (82 rows)
- near_boundary_window: `{'lower': 0.2916, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: current q15 exact support 目前為 29/50，低於 minimum；這是 current exact support under minimum，不是 boundary candidate。
- candidate_patch: `{}`
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.527 / norm=0.527 / Δto_cross_q35=0.1718 / target_p25=1.8718 / target_median=1.9105
- `feat_4h_dist_bb_lower`: current=1.6161 / norm=0.202 / Δto_cross_q35=1.4158 / target_p25=4.8843 / target_median=4.995
- `feat_4h_dist_swing_low`: current=1.3879 / norm=0.1388 / Δto_cross_q35=1.7697 / target_p25=5.4449 / target_median=5.5338

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
