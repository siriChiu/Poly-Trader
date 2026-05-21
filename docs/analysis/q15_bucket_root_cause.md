# Current-Live Bucket Root Cause

- generated_at: **2026-05-21 09:13:41.088023**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q35 bucket**
- verdict: **current_exact_support_under_minimum**
- candidate_patch_type: **support_accumulation_or_semantic_rebaseline**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q35', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- structure_quality: **0.356**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **13 / 50 / 37**

## Exact live lane
- rows: **242**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q65': 65, 'CAUTION|base_caution_regime_or_bias|q00': 63, 'CAUTION|base_caution_regime_or_bias|q15': 57, 'CAUTION|base_caution_regime_or_bias|q35': 30, 'CAUTION|base_caution_regime_or_bias|q85': 27}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** (65 rows)
- near_boundary_window: `{'lower': 0.356, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: current-live q35 bucket exact support 目前為 13/50，低於 minimum；這是 current exact support under minimum，不是 boundary candidate。
- candidate_patch: `{}`
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.6232 / norm=0.6232 / Δto_cross_q35=0.0 / target_p25=0.7067 / target_median=0.7672
- `feat_4h_dist_bb_lower`: current=1.5483 / norm=0.1935 / Δto_cross_q35=0.0 / target_p25=5.4686 / target_median=5.7696
- `feat_4h_dist_swing_low`: current=2.4305 / norm=0.243 / Δto_cross_q35=0.0 / target_p25=8.8715 / target_median=9.2932

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
