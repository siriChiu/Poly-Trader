# Current-Live Bucket Root Cause

- generated_at: **2026-05-25 23:10:28.471688**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **current_exact_support_under_minimum**
- candidate_patch_type: **support_accumulation_or_semantic_rebaseline**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2462**
- gap_to_q35_boundary: **0.1038**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **7 / 50 / 43**

## Exact live lane
- rows: **1507**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 606, 'CAUTION|base_caution_regime_or_bias|q00': 370, 'CAUTION|base_caution_regime_or_bias|q35': 284, 'CAUTION|base_caution_regime_or_bias|q65': 187, 'CAUTION|base_caution_regime_or_bias|q85': 60}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q00** (370 rows)
- near_boundary_window: `{'lower': 0.2462, 'upper': 0.35}`
- near_boundary_rows: **375**

## Decision
- reason: current-live q15 bucket exact support 目前為 7/50，低於 minimum；這是 current exact support under minimum，不是 boundary candidate。
- candidate_patch: `{}`
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.466 / norm=0.466 / Δto_cross_q35=0.3053 / target_p25=0.123 / target_median=0.1617
- `feat_4h_dist_bb_lower`: current=0.9523 / norm=0.119 / Δto_cross_q35=2.5164 / target_p25=0.5669 / target_median=0.6198
- `feat_4h_dist_swing_low`: current=1.468 / norm=0.1468 / Δto_cross_q35=3.1455 / target_p25=-0.748 / target_median=0.3934

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
