# q15 Boundary Replay

- generated_at: **2026-07-28T19:03:45.393650Z**
- feature_timestamp: **2026-07-28 18:41:44.247652**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=runtime_blocker_preempts_bucket_root_cause，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bear / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.1712**
- entry_quality: **0.5709** (trade_floor_gap=0.0209)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **10**
- replay bucket: **CAUTION|base_caution_regime_or_bias|q15**
- replay bucket rows: **85**
- generated_rows_via_boundary_only: **52**
- preexisting_rows_in_replay_bucket: **33**
- generated_row_share: **0.6118**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **CAUTION|base_caution_regime_or_bias|q15** rows=38

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.4074 → None**
- structure_quality: **0.1712 → 0.35**
- bucket_after: **CAUTION|base_caution_regime_or_bias|q15**
- entry_quality: **0.5709 → 0.6157**
- trade_floor_gap_after: **0.0657**
- allowed_layers_after: **1** (entry_quality_C_single_layer)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。