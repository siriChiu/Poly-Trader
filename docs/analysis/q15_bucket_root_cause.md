# Current-Live Bucket Root Cause

- generated_at: **2026-05-17 14:02:35.701094**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **insufficient_scope_data**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / C**
- structure_bucket: `CAUTION|structure_quality_caution|q15`
- structure_quality: **0.2293**
- gap_to_q35_boundary: **0.1207**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **41**
- bucket_counts: `{'CAUTION|structure_quality_caution|q15': 41}`
- dominant_neighbor_bucket: **None** (0 rows)
- near_boundary_window: `{'lower': 0.2293, 'upper': 0.35}`
- near_boundary_rows: **20**

## Decision
- reason: 目前資料不足，尚無法判定 current-live q15 bucket 0-row 的最小可修補原因。
- candidate_patch: `{}`
- verify_next: 先確保 live probe / support artifacts 完整，再重跑 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4676 / norm=0.4676 / Δto_cross_q35=0.355 / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=1.1769 / norm=0.1471 / Δto_cross_q35=2.9261 / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=0.6601 / norm=0.066 / Δto_cross_q35=3.6576 / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
