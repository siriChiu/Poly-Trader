# q15 Bucket Root Cause

- generated_at: **2026-04-20 05:52:01.160266**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **chop / CAUTION / C**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.1541**
- gap_to_q35_boundary: **0.1959**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`

## Exact live lane
- rows: **929**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q35': 492, 'CAUTION|base_caution_regime_or_bias|q85': 189, 'CAUTION|base_caution_regime_or_bias|q15': 170, 'CAUTION|base_caution_regime_or_bias|q65': 78}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** (492 rows)
- near_boundary_window: `{'lower': 0.1541, 'upper': 0.35}`
- near_boundary_rows: **170**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{'type': None, 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.2418, 'current_normalized': 0.2418, 'needed_raw_delta_to_cross_q35': 0.5762, 'target_bucket_p25': 0.541, 'target_bucket_median': 0.6, 'needed_raw_delta_to_target_p25': 0.2992, 'needed_raw_delta_to_target_median': 0.3582}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.2418 / norm=0.2418 / Δto_cross_q35=0.5762 / target_p25=0.541 / target_median=0.6
- `feat_4h_dist_bb_lower`: current=0.7553 / norm=0.0944 / Δto_cross_q35=4.7491 / target_p25=3.3498 / target_median=3.7804
- `feat_4h_dist_swing_low`: current=1.2337 / norm=0.1234 / Δto_cross_q35=5.9364 / target_p25=3.7868 / target_median=4.1046

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
