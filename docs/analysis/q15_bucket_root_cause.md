# Current-Live Bucket Root Cause

- generated_at: **2026-05-24 11:37:11.707733**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q35 bucket**
- verdict: **current_row_already_above_q35_boundary**
- candidate_patch_type: **support_accumulation**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q35', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- structure_quality: **0.5512**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **341**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 147, 'CAUTION|base_caution_regime_or_bias|q35': 80, 'CAUTION|base_caution_regime_or_bias|q00': 63, 'CAUTION|base_caution_regime_or_bias|q65': 32, 'CAUTION|base_caution_regime_or_bias|q85': 19}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** (147 rows)
- near_boundary_window: `{'lower': 0.5512, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live row 已高於 q35 boundary，問題改成 exact support 累積，不是 bucket repair。
- candidate_patch: `{'type': 'support_accumulation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.9551, 'current_normalized': 0.9551, 'needed_raw_delta_to_cross_q35': 0.0, 'target_bucket_p25': 0.0923, 'target_bucket_median': 0.3993, 'needed_raw_delta_to_target_p25': -0.8628, 'needed_raw_delta_to_target_median': -0.5558}`
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.9551 / norm=0.9551 / Δto_cross_q35=0.0 / target_p25=0.0923 / target_median=0.3993
- `feat_4h_dist_bb_lower`: current=2.3561 / norm=0.2945 / Δto_cross_q35=0.0 / target_p25=0.4014 / target_median=0.983
- `feat_4h_dist_swing_low`: current=3.9185 / norm=0.3918 / Δto_cross_q35=0.0 / target_p25=1.6733 / target_median=2.0107

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
