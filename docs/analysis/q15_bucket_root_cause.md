# q15 Bucket Root Cause

- generated_at: **2026-04-24 20:15:55.126672**
- target_col: **simulated_pyramid_win**
- verdict: **same_lane_neighbor_bucket_dominates**
- candidate_patch_type: **structure_component_scoring**
- candidate_patch_feature: **feat_4h_bb_pct_b**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`

## Current live
- live path: **chop / CAUTION / D**
- structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- structure_quality: **0.2155**
- gap_to_q35_boundary: **0.1345**
- non_null_4h_feature_count: **10**
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- support rows/minimum/gap: **123 / 50 / 0**

## Exact live lane
- rows: **1894**
- bucket_counts: `{'CAUTION|base_caution_regime_or_bias|q65': 578, 'CAUTION|base_caution_regime_or_bias|q35': 509, 'CAUTION|base_caution_regime_or_bias|q85': 323, 'CAUTION|base_caution_regime_or_bias|q15': 279, 'CAUTION|base_caution_regime_or_bias|q00': 205}`
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** (578 rows)
- near_boundary_window: `{'lower': 0.2155, 'upper': 0.35}`
- near_boundary_rows: **248**

## Decision
- reason: same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，不是 generic breaker / q35 總體治理。
- candidate_patch: `{'type': 'structure_component_scoring', 'feature': 'feat_4h_bb_pct_b', 'current_raw': 0.4024, 'current_normalized': 0.4024, 'needed_raw_delta_to_cross_q35': 0.3956, 'target_bucket_p25': 0.7102, 'target_bucket_median': 0.753, 'needed_raw_delta_to_target_p25': 0.3078, 'needed_raw_delta_to_target_median': 0.3506}`
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。

## Component deltas
- `feat_4h_bb_pct_b`: current=0.4024 / norm=0.4024 / Δto_cross_q35=0.3956 / target_p25=0.7102 / target_median=0.753
- `feat_4h_dist_bb_lower`: current=1.2224 / norm=0.1528 / Δto_cross_q35=3.2606 / target_p25=4.7576 / target_median=5.7345
- `feat_4h_dist_swing_low`: current=0.8569 / norm=0.0857 / Δto_cross_q35=4.0758 / target_p25=8.0553 / target_median=9.09

## Carry-forward
- 先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。
- 若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。
- 若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。
- 若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。
