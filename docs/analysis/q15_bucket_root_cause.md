# q15 Bucket Root Cause

- generated_at: **2026-04-21 02:57:58.353169**
- target_col: **simulated_pyramid_win**
- verdict: **structure_scoring_gap_not_boundary**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.336**
- gap_to_q35_boundary: **0.014**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade`

## Exact live lane
- rows: **2403**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q35': 1117, 'CAUTION|base_caution_regime_or_bias|q65': 434, 'CAUTION|base_caution_regime_or_bias|q15': 323, 'CAUTION|base_caution_regime_or_bias|q00': 303, 'CAUTION|base_caution_regime_or_bias|q85': 226}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q35** (1117 rows)
- near_boundary_window: `{'lower': 0.336, 'upper': 0.35}`
- near_boundary_rows: **0**

## Decision
- reason: exact live lane 的樣本全部落在鄰近 bucket，且 current_structure_quality 與 q35 邊界之間沒有 exact-lane 緩衝列；這代表單純放寬 q15/q35 boundary 不能生成 exact rows，應優先查結構 component scoring。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.5411, 'current_normalized': 0.5411, 'needed_raw_delta_to_cross_q35': 0.0412, 'target_bucket_p25': 0.654, 'target_bucket_median': 0.695, 'needed_raw_delta_to_target_p25': 0.1129, 'needed_raw_delta_to_target_median': 0.1539}`
- verify_next: 優先用 q15 root-cause artifact 鎖定的 component 做 counterfactual，確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.5411 / norm=0.5411 / Δto_cross_q35=0.0412 / target_p25=0.654 / target_median=0.695
- `feat_4h_dist_bb_lower`: current=1.6785 / norm=0.2098 / Δto_cross_q35=0.3394 / target_p25=2.1292 / target_median=3.3027
- `feat_4h_dist_swing_low`: current=2.5087 / norm=0.2509 / Δto_cross_q35=0.4242 / target_p25=2.0932 / target_median=3.6776

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
