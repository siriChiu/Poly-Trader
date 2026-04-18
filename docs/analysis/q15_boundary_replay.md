# q15 Boundary Replay

- generated_at: **2026-04-18 15:02:26.615581**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bull / None**
- structure bucket: **None**
- structure_quality: **None**
- entry_quality: **None** (trade_floor_gap=None)
- support_route: **insufficient_support_everywhere**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **None**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **None** rows=0

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **None → None**
- structure_quality: **None → None**
- bucket_after: **None**
- entry_quality: **None → None**
- trade_floor_gap_after: **None**
- allowed_layers_after: **0** (None)
- counterfactual verdict: **counterfactual_unavailable**
- counterfactual reason: 缺少 feat_4h_bb_pct_b 當前值或 needed_raw_delta_to_cross_q35，無法做最小反事實。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。