# Current-Live Bucket Root Cause

- generated_at: **2026-05-27 14:12:08.417203**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q00 bucket**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bear_bias200_hard_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'B', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / BLOCK / B**
- structure_bucket: `BLOCK|bear_bias200_hard_block|q00`
- structure_quality: **0.0**
- gap_to_q35_boundary: **0.35**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- support rows/minimum/gap: **0 / 50 / 50**

## Exact live lane
- rows: **12**
- bucket_counts: `{'BLOCK|structure_quality_block|q00': 6, 'BLOCK|bear_bias200_hard_block|q00': 6}`
- dominant_neighbor_bucket: **BLOCK|structure_quality_block|q00** (6 rows)
- near_boundary_window: `{'lower': 0.0, 'upper': 0.35}`
- near_boundary_rows: **12**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q00 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=-0.0385 / norm=0.0 / Δto_cross_q35=1.0385 / target_p25=0.0544 / target_median=0.2565
- `feat_4h_dist_bb_lower`: current=-0.0821 / norm=0.0 / Δto_cross_q35=8.0821 / target_p25=0.1339 / target_median=0.638
- `feat_4h_dist_swing_low`: current=-1.4847 / norm=0.0 / Δto_cross_q35=11.4847 / target_p25=-1.1903 / target_median=-1.1186

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
