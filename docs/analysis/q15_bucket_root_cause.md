# Current-Live Bucket Root Cause

- generated_at: **2026-07-28T14:46:10.261078Z**
- feature_timestamp: **2026-07-28 14:33:27.381993**
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
- structure_quality: **0.0091**
- gap_to_q35_boundary: **0.3409**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **327**
- bucket_counts: `{'BLOCK|structure_overextended_block|q85': 233, 'BLOCK|bear_bias200_hard_block|q00': 56, 'BLOCK|bias200_below_min|q15': 21, 'BLOCK|bear_bias200_hard_block|q15': 11, 'BLOCK|structure_quality_block|q00': 4, 'BLOCK|bias200_below_min|q00': 2}`
- dominant_neighbor_bucket: **BLOCK|structure_overextended_block|q85** (233 rows)
- near_boundary_window: `{'lower': 0.0091, 'upper': 0.35}`
- near_boundary_rows: **71**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q00 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.0216 / norm=0.0216 / Δto_cross_q35=0.9784 / target_p25=29.2866 / target_median=30.5119
- `feat_4h_dist_bb_lower`: current=0.0423 / norm=0.0053 / Δto_cross_q35=7.9577 / target_p25=162.6086 / target_median=169.4118
- `feat_4h_dist_swing_low`: current=-0.8626 / norm=0.0 / Δto_cross_q35=10.8626 / target_p25=176.8639 / target_median=184.0365

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
