# q15 Boundary Replay

- generated_at: **2026-04-29 04:02:11.780400**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=runtime_blocker_preempts_bucket_root_cause，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bear / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.2966**
- entry_quality: **0.4702** (trade_floor_gap=-0.0798)
- support_route: **insufficient_support_everywhere**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=0

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.6581 → None**
- structure_quality: **0.2966 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.4702 → 0.4836**
- trade_floor_gap_after: **-0.0664**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。