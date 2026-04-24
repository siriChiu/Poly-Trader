# q15 Boundary Replay

- generated_at: **2026-04-24 21:04:05.212904**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=same_lane_neighbor_bucket_dominates，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.2327**
- entry_quality: **0.3632** (trade_floor_gap=-0.1868)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **legal_component_experiment_after_support_ready**

## Boundary replay
- legacy bucket rows: **122**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q65**
- replay bucket rows: **1**
- generated_rows_via_boundary_only: **241**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=240)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** rows=578

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.4316 → 0.7766**
- structure_quality: **0.2327 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q65**
- entry_quality: **0.3632 → 0.3925**
- trade_floor_gap_after: **-0.1575**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。