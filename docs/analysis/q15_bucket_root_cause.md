# Current-Live Bucket Root Cause

- generated_at: **2026-05-23 21:09:35.642850**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q35 bucket**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q35', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- structure_quality: **0.4759**
- gap_to_q35_boundary: **0.0**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; circuit_breaker_active`
- support rows/minimum/gap: **14 / 50 / 36**

## Exact live lane
- rows: **355**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 147, 'CAUTION|base_caution_regime_or_bias|q35': 80, 'CAUTION|base_caution_regime_or_bias|q00': 63, 'CAUTION|base_caution_regime_or_bias|q65': 46, 'CAUTION|base_caution_regime_or_bias|q85': 19}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** (147 rows)
- near_boundary_window: `{'lower': 0.4759, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q35 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=1.1247 / norm=1.0 / Δto_cross_q35=-0.1247 / target_p25=0.0923 / target_median=0.3993
- `feat_4h_dist_bb_lower`: current=2.9526 / norm=0.3691 / Δto_cross_q35=0.0 / target_p25=0.4014 / target_median=0.983
- `feat_4h_dist_swing_low`: current=0.4261 / norm=0.0426 / Δto_cross_q35=-0.0 / target_p25=1.6733 / target_median=2.0107

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
