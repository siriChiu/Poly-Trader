# Current-Live Bucket Root Cause

- generated_at: **2026-05-19 12:09:47.261317**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **bear / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2205**
- gap_to_q35_boundary: **0.1295**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`
- support rows/minimum/gap: **2 / 50 / 48**

## Exact live lane
- rows: **136**
- bucket_counts: `{'CAUTION|structure_quality_caution|q15': 109, 'CAUTION|base_caution_regime_or_bias|q00': 25, 'CAUTION|base_caution_regime_or_bias|q15': 2}`
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** (109 rows)
- near_boundary_window: `{'lower': 0.2205, 'upper': 0.35}`
- near_boundary_rows: **54**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4272 / norm=0.4272 / Δto_cross_q35=0.3809 / target_p25=0.3928 / target_median=0.4551
- `feat_4h_dist_bb_lower`: current=1.0917 / norm=0.1365 / Δto_cross_q35=3.1394 / target_p25=0.9986 / target_median=1.1465
- `feat_4h_dist_swing_low`: current=0.9159 / norm=0.0916 / Δto_cross_q35=3.9242 / target_p25=-0.566 / target_median=0.5205

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
