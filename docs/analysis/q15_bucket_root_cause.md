# q15 Bucket Root Cause

- generated_at: **2026-04-25 19:55:52.566953**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2038**
- gap_to_q35_boundary: **0.1462**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- support rows/minimum/gap: **14 / 50 / 36**

## Exact live lane
- rows: **1821**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q65': 577, 'CAUTION|base_caution_regime_or_bias|q35': 423, 'CAUTION|base_caution_regime_or_bias|q85': 323, 'CAUTION|base_caution_regime_or_bias|q15': 293, 'CAUTION|base_caution_regime_or_bias|q00': 205}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** (577 rows)
- near_boundary_window: `{'lower': 0.2038, 'upper': 0.35}`
- near_boundary_rows: **262**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.407 / norm=0.407 / Δto_cross_q35=0.43 / target_p25=0.7102 / target_median=0.753
- `feat_4h_dist_bb_lower`: current=1.2085 / norm=0.1511 / Δto_cross_q35=3.5442 / target_p25=4.7435 / target_median=5.7346
- `feat_4h_dist_swing_low`: current=0.4707 / norm=0.0471 / Δto_cross_q35=4.4303 / target_p25=8.0592 / target_median=9.0904

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
