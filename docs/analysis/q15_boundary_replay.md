# q15 Boundary Replay

- generated_at: **2026-04-18 16:33:30.024994**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.2451**
- entry_quality: **0.3434** (trade_floor_gap=-0.2066)
- support_route: **exact_bucket_supported**
- floor_cross_legality: **runtime_blocker_preempts_floor_analysis**

## Boundary replay
- legacy bucket rows: **69**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **59**
- generated_rows_via_boundary_only: **163**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **2.7627**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=656

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.2797 → 0.5882**
- structure_quality: **0.2451 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.3434 → 0.3697**
- trade_floor_gap_after: **-0.1803**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。