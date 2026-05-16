# Current-Live Bucket Root Cause

- generated_at: **2026-05-16 07:02:28.060099**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / BLOCK / C**
- structure_bucket: `BLOCK|structure_quality_block|q00`
- structure_quality: **0.043**
- gap_to_q35_boundary: **0.307**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `circuit_breaker_active`
- support rows/minimum/gap: **10 / 50 / 40**

## Exact live lane
- rows: **32**
- bucket_counts: `{'BLOCK|structure_quality_block|q00': 32}`
- dominant_neighbor_bucket: **None** (0 rows)
- near_boundary_window: `{'lower': 0.043, 'upper': 0.35}`
- near_boundary_rows: **26**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q00 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.0965 / norm=0.0965 / Δto_cross_q35=0.9029 / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=0.2458 / norm=0.0307 / Δto_cross_q35=7.4424 / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=-0.1728 / norm=0.0 / Δto_cross_q35=9.4758 / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
