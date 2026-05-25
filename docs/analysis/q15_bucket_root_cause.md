# Current-Live Bucket Root Cause

- generated_at: **2026-05-25 16:19:19.978544**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **boundary_sensitivity_candidate**
- candidate_patch_type: **bucket_boundary_review**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.3355**
- gap_to_q35_boundary: **0.0145**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **1520**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 599, 'CAUTION|base_caution_regime_or_bias|q00': 370, 'CAUTION|base_caution_regime_or_bias|q35': 277, 'CAUTION|base_caution_regime_or_bias|q65': 214, 'CAUTION|base_caution_regime_or_bias|q85': 60}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q00** (370 rows)
- near_boundary_window: `{'lower': 0.3355, 'upper': 0.35}`
- near_boundary_rows: **25**

## Decision
- reason: current_structure_quality 已貼近 q35 邊界，且 exact-lane 存在 near-boundary rows；可把 current bucket↔q35 分桶公式列入候選，但仍需先做 exact-support legality 驗證。
- candidate_patch: `{'type': 'bucket_boundary_review', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.6485, 'current_normalized': 0.6485, 'needed_raw_delta_to_cross_q35': 0.0426, 'target_bucket_p25': 0.123, 'target_bucket_median': 0.1617, 'needed_raw_delta_to_target_p25': -0.5255, 'needed_raw_delta_to_target_median': -0.4868}`
- verify_next: 以歷史 lane 回放驗證 boundary review 不會把 0-row blocker 假裝成已解。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.6485 / norm=0.6485 / Δto_cross_q35=0.0426 / target_p25=0.123 / target_median=0.1617
- `feat_4h_dist_bb_lower`: current=1.3299 / norm=0.1662 / Δto_cross_q35=0.3515 / target_p25=0.5669 / target_median=0.6198
- `feat_4h_dist_swing_low`: current=1.8218 / norm=0.1822 / Δto_cross_q35=0.4394 / target_p25=-0.748 / target_median=0.3934

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
