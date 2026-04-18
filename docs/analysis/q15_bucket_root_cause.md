# q15 Bucket Root Cause

- generated_at: **2026-04-18 13:43:25.809469**
- target_col: **simulated_pyramid_win**
- verdict: **runtime_blocker_preempts_bucket_root_cause**
- candidate_patch_type: **None**
- candidate_patch_feature: **None**

## Current live
- live path: **bull /  / **
- structure_bucket: `None`
- structure_quality: **None**
- gap_to_q35_boundary: **None**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `circuit_breaker_blocks_trade`

## Exact live lane
- rows: **0**
- bucket_counts: `{}`
- dominant_neighbor_bucket: **None** (0 rows)
- near_boundary_window: `None`
- near_boundary_rows: **0**

## Decision
- reason: 目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。
- candidate_patch: `{}`
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。

## Component deltas
- `feat_4h_bb_pct_b`: current=None / norm=None / Δto_cross_q35=None / target_p25=None / target_median=None
- `feat_4h_dist_bb_lower`: current=None / norm=None / Δto_cross_q35=None / target_p25=None / target_median=None
- `feat_4h_dist_swing_low`: current=None / norm=None / Δto_cross_q35=None / target_p25=None / target_median=None

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
