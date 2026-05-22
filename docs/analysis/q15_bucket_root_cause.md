# Current-Live Bucket Root Cause

- generated_at: **2026-05-22 16:11:08.540506**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **current_exact_support_under_minimum**
- candidate_patch_type: **support_accumulation_or_semantic_rebaseline**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q00', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q00`
- structure_quality: **0.1097**
- gap_to_q35_boundary: **0.2403**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- support rows/minimum/gap: **1 / 50 / 49**

## Exact live lane
- rows: **274**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 122, 'CAUTION|structure_quality_caution|q15': 109, 'CAUTION|base_caution_regime_or_bias|q00': 40, 'CAUTION|base_caution_regime_or_bias|q35': 3}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** (122 rows)
- near_boundary_window: `{'lower': 0.1097, 'upper': 0.35}`
- near_boundary_rows: **246**

## Decision
- reason: current-live q00 bucket exact support 目前為 1/50，低於 minimum；這是 current exact support under minimum，不是 boundary candidate。
- candidate_patch: `{}`
- verify_next: 維持 minimum_support_rows=50 與 current-live guardrail，累積同 support_identity 的 exact rows；若只有 legacy / different semantic signature 支撐，文案必須標成 semantic rebaseline reference。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.2437 / norm=0.2437 / Δto_cross_q35=0.7068 / target_p25=0.4297 / target_median=0.4979
- `feat_4h_dist_bb_lower`: current=0.5867 / norm=0.0733 / Δto_cross_q35=5.8255 / target_p25=1.1002 / target_median=1.2832
- `feat_4h_dist_swing_low`: current=0.0805 / norm=0.008 / Δto_cross_q35=7.2818 / target_p25=-0.7104 / target_median=0.9474

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
