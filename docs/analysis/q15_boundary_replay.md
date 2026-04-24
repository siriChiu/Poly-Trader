# q15 Boundary Replay

- generated_at: **2026-04-24 23:03:33.226843**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=runtime_blocker_preempts_bucket_root_cause，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **chop / CAUTION**
- structure bucket: **CAUTION|base_caution_regime_or_bias|q15**
- structure_quality: **0.1587**
- entry_quality: **0.435** (trade_floor_gap=-0.115)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **101**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q65**
- replay bucket rows: **1**
- generated_rows_via_boundary_only: **277**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=276)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q65** rows=578

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3054 → None**
- structure_quality: **0.1587 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q65**
- entry_quality: **0.435 → 0.4829**
- trade_floor_gap_after: **-0.0671**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。