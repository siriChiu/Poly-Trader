# q15 Boundary Replay

- generated_at: **2026-05-16 06:17:37.036718**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=runtime_blocker_preempts_bucket_root_cause，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bear / BLOCK**
- structure bucket: **BLOCK|structure_quality_block|q00**
- structure_quality: **0.1014**
- entry_quality: **0.5911** (trade_floor_gap=0.0411)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **10**
- replay bucket: **BLOCK|structure_quality_block|q00**
- replay bucket rows: **10**
- generated_rows_via_boundary_only: **19**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=9)
- dominant_neighbor_bucket: **BLOCK|structure_quality_block|q00** rows=0

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.2137 → None**
- structure_quality: **0.1014 → 0.35**
- bucket_after: **BLOCK|structure_quality_block|q00**
- entry_quality: **0.5911 → 0.6533**
- trade_floor_gap_after: **0.1033**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 current-live bucket root-cause artifact。