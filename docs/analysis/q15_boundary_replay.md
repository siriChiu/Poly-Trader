# q15 Boundary Replay

- generated_at: **2026-04-21 14:29:45.146309**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q35**
- structure_quality: **0.3835**
- entry_quality: **0.469** (trade_floor_gap=-0.081)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **12**
- replay bucket: **CAUTION|structure_quality_caution|q15**
- replay bucket rows: **0**
- generated_rows_via_boundary_only: **0**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **None**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q15** rows=379

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.5924 → 0.5924**
- structure_quality: **0.3835 → 0.3835**
- bucket_after: **CAUTION|structure_quality_caution|q15**
- entry_quality: **0.469 → 0.469**
- trade_floor_gap_after: **-0.081**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。