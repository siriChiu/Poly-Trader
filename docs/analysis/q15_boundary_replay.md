# q15 Boundary Replay

- generated_at: **2026-04-16 10:49:08.303092**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_not_applicable**
- reason: 目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.2218**
- entry_quality: **0.4227** (trade_floor_gap=-0.1273)
- support_route: **exact_bucket_present_but_below_minimum**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **4**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **187**
- generated_rows_via_boundary_only: **58**
- preexisting_rows_in_replay_bucket: **129**
- generated_row_share: **0.3102**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=364

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.3974 → 0.7745**
- structure_quality: **0.2218 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.4227 → 0.4547**
- trade_floor_gap_after: **-0.0953**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 依 q15 root-cause / support audit 的既有 blocker 繼續治理。
- verify_next: 比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。