# q15 Bucket Root Cause

- generated_at: **2026-04-20 08:52:33.425639**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2636**
- gap_to_q35_boundary: **0.0864**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`

## Exact live lane
- rows: **2373**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q35': 1139, 'CAUTION|base_caution_regime_or_bias|q65': 434, 'CAUTION|base_caution_regime_or_bias|q15': 289, 'CAUTION|base_caution_regime_or_bias|q00': 285, 'CAUTION|base_caution_regime_or_bias|q85': 226}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** (1139 rows)
- near_boundary_window: `{'lower': 0.2636, 'upper': 0.35}`
- near_boundary_rows: **58**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{'type': None, 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.4319, 'current_normalized': 0.4319, 'needed_raw_delta_to_cross_q35': 0.2541, 'target_bucket_p25': 0.6494, 'target_bucket_median': 0.695, 'needed_raw_delta_to_target_p25': 0.2175, 'needed_raw_delta_to_target_median': 0.2631}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4319 / norm=0.4319 / Δto_cross_q35=0.2541 / target_p25=0.6494 / target_median=0.695
- `feat_4h_dist_bb_lower`: current=1.3619 / norm=0.1702 / Δto_cross_q35=2.0945 / target_p25=2.1292 / target_median=3.2021
- `feat_4h_dist_swing_low`: current=1.8352 / norm=0.1835 / Δto_cross_q35=2.6182 / target_p25=2.0932 / target_median=3.6167

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
