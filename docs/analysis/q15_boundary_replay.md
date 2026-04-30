# q15 Boundary Replay

- generated_at: **2026-04-30 03:02:11.116119**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=no_exact_live_lane_rows，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bear / BLOCK**
- structure bucket: **BLOCK|structure_quality_block|q00**
- structure_quality: **0.1339**
- entry_quality: **0.6157** (trade_floor_gap=0.0657)
- support_route: **insufficient_support_everywhere**
- floor_cross_legality: **floor_crossed_but_support_not_ready**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **BLOCK|structure_quality_block|q00**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- generated_rows_exceed_replay_scope: **False** (excess=0)
- dominant_neighbor_bucket: **BLOCK|structure_quality_block|q00** rows=0

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.2874 → 0.923**
- structure_quality: **0.1339 → 0.35**
- bucket_after: **BLOCK|structure_quality_block|q00**
- entry_quality: **0.6157 → 0.6697**
- trade_floor_gap_after: **0.1197**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 重跑 bull_4h_pocket_ablation.py，確認 exact_scope_rows > 0。