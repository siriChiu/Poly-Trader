# Current-Live Bucket Root Cause

- generated_at: **2026-05-15 19:20:05.794298**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **current_exact_support_under_minimum**
- candidate_patch_type: **support_accumulation_or_semantic_rebaseline**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'D', 'calibration_window': 600, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / BLOCK / D**
- structure_bucket: `BLOCK|structure_quality_block|q00`
- structure_quality: **0.0146**
- gap_to_q35_boundary: **0.3354**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **2 / 50 / 48**

## Exact live lane
- rows: **2**
- bucket_counts: `{'BLOCK|structure_quality_block|q00': 2}`
- dominant_neighbor_bucket: **None** (0 rows)
- near_boundary_window: `{'lower': 0.0146, 'upper': 0.35}`
- near_boundary_rows: **2**

## Decision
- reason: current-live q00 bucket exact support 目前為 2/50，低於 minimum；這是 current exact support under minimum，不是 boundary candidate。
- candidate_patch: `{}`
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。

## Component deltas
- `feat_4h_bb_pct_b`: current=-0.0324 / norm=0.0 / Δto_cross_q35=1.0189 / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=-0.0846 / norm=0.0 / Δto_cross_q35=8.0846 / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=0.4434 / norm=0.0443 / Δto_cross_q35=9.5566 / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
