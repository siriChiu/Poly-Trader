# Current-Live Bucket Root Cause

- generated_at: **2026-05-24 00:12:29.917754**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q35 bucket**
- verdict: **current_row_already_above_q35_boundary**
- candidate_patch_type: **support_accumulation**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q35', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- structure_quality: **0.4938**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **46**
- bucket_counts: `{'CAUTION|structure_quality_caution|q15': 37, 'CAUTION|structure_quality_caution|q35': 3, 'CAUTION|base_caution_regime_or_bias|q15': 3, 'CAUTION|base_caution_regime_or_bias|q00': 3}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** (37 rows)
- near_boundary_window: `{'lower': 0.4938, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live row 已高於 q35 boundary，問題改成 exact support 累積，不是 bucket repair。
- candidate_patch: `{'type': 'support_accumulation', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.8741, 'current_normalized': 0.8741, 'needed_raw_delta_to_cross_q35': 0.0, 'target_bucket_p25': 0.4215, 'target_bucket_median': 0.4913, 'needed_raw_delta_to_target_p25': -0.4526, 'needed_raw_delta_to_target_median': -0.3828}`
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.8741 / norm=0.8741 / Δto_cross_q35=0.0 / target_p25=0.4215 / target_median=0.4913
- `feat_4h_dist_bb_lower`: current=2.2508 / norm=0.2813 / Δto_cross_q35=0.0 / target_p25=1.1059 / target_median=1.21
- `feat_4h_dist_swing_low`: current=3.1434 / norm=0.3143 / Δto_cross_q35=0.0 / target_p25=-0.8429 / target_median=-0.2443

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
