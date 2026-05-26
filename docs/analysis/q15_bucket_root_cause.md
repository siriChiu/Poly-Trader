# Current-Live Bucket Root Cause

- generated_at: **2026-05-26 13:28:12.189411**
- target_col: **simulated_pyramid_win**
- bucket_scope: **current-live q15 bucket**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.1771**
- gap_to_q35_boundary: **0.1729**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- support rows/minimum/gap: **7 / 50 / 43**

## Exact live lane
- rows: **1514**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q15': 606, 'CAUTION|base_caution_regime_or_bias|q00': 370, 'CAUTION|base_caution_regime_or_bias|q35': 328, 'CAUTION|base_caution_regime_or_bias|q65': 153, 'CAUTION|base_caution_regime_or_bias|q85': 57}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q00** (370 rows)
- near_boundary_window: `{'lower': 0.1771, 'upper': 0.35}`
- near_boundary_rows: **564**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；current-live q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.3481 / norm=0.3481 / Δto_cross_q35=0.5085 / target_p25=0.123 / target_median=0.1617
- `feat_4h_dist_bb_lower`: current=0.6962 / norm=0.087 / Δto_cross_q35=4.1915 / target_p25=0.5669 / target_median=0.6198
- `feat_4h_dist_swing_low`: current=0.9111 / norm=0.0911 / Δto_cross_q35=5.2394 / target_p25=-0.748 / target_median=0.3934

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 current-live bucket verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 current-live support audit。
