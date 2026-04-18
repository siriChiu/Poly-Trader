# q15 Boundary Replay

- generated_at: **2026-04-18 18:49:43.144791**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bull / BLOCK**
- structure bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- structure_quality: **0.1765**
- entry_quality: **0.3612** (trade_floor_gap=-0.1888)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **41**
- replay bucket: **BLOCK|structure_quality_block|q00**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **BLOCK|structure_quality_block|q00** rows=106

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.1594 → 0.6697**
- structure_quality: **0.1765 → 0.35**
- bucket_after: **BLOCK|structure_quality_block|q00**
- entry_quality: **0.3612 → 0.4045**
- trade_floor_gap_after: **-0.1455**
- allowed_layers_after: **0** (regime_gate_block)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。