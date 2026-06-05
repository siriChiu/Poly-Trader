# q15 Boundary Replay

- generated_at: **2026-06-05T03:46:47.222148Z**
- feature_timestamp: **2026-06-05 03:00:00**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable_for_current_context**
- artifact_context_freshness: **current_context** (`[]`)
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|bias200_below_min|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 200, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- reason: q15 root-cause verdict=same_lane_neighbor_bucket_dominates，不是 boundary_sensitivity_candidate；boundary replay 本輪不適用，舊 boundary counterfactual 不可當 current truth。

## Current live row
- signal: **HOLD**
- regime/gate: **bear / BLOCK**
- structure bucket: **BLOCK|bias200_below_min|q00**
- structure_quality: **0.0593**
- entry_quality: **0.5788** (trade_floor_gap=0.0288)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **floor_already_crossed_and_support_ready**

## Boundary replay
- legacy bucket rows: **131**
- replay bucket: **BLOCK|bear_bias200_hard_block|q00**
- replay bucket rows: **28**
- generated_rows_via_boundary_only: **293**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.0**
- generated_rows_exceed_replay_scope: **True** (excess=265)
- dominant_neighbor_bucket: **BLOCK|bear_bias200_hard_block|q00** rows=174

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **-0.0299 → 0.855**
- structure_quality: **0.0593 → 0.35**
- bucket_after: **BLOCK|bear_bias200_hard_block|q00**
- entry_quality: **0.5788 → 0.6515**
- trade_floor_gap_after: **0.1015**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **counterfactual_not_evaluated**
- counterfactual reason: boundary replay 不適用於目前 RCA verdict，因此不消費舊 q15 counterfactual。

## Next
- next_action: 維持 boundary replay 為 non-applicable，直到 RCA 重新輸出 boundary_sensitivity_candidate。
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。