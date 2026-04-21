# q15 Boundary Replay

- generated_at: **2026-04-21 12:55:06.988612**
- target_col: **simulated_pyramid_win**
- verdict: **boundary_replay_requires_exact_support_validation**
- reason: boundary replay 可帶來可見的 exact-lane rebucket rows，但仍需確認這不是把 blocker 假裝成已解。

## Current live row
- signal: **HOLD**
- regime/gate: **bull / CAUTION**
- structure bucket: **CAUTION|structure_quality_caution|q15**
- structure_quality: **0.3445**
- entry_quality: **0.4362** (trade_floor_gap=-0.1138)
- support_route: **exact_bucket_missing_proxy_reference_only**
- floor_cross_legality: **math_cross_possible_but_illegal_without_exact_support**

## Boundary replay
- legacy bucket rows: **0**
- replay bucket: **CAUTION|structure_quality_caution|q35**
- replay bucket rows: **12**
- generated_rows_via_boundary_only: **22**
- preexisting_rows_in_replay_bucket: **0**
- generated_row_share: **1.8333**
- dominant_neighbor_bucket: **CAUTION|structure_quality_caution|q35** rows=661

## feat_4h_bb_pct_b minimal counterfactual
- raw before/after: **0.525 → 0.5412**
- structure_quality: **0.3445 → 0.35**
- bucket_after: **CAUTION|structure_quality_caution|q35**
- entry_quality: **0.4362 → 0.4376**
- trade_floor_gap_after: **-0.1124**
- allowed_layers_after: **0** (entry_quality_below_trade_floor)
- counterfactual verdict: **bucket_proxy_only_not_trade_floor_fix**
- counterfactual reason: 只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。

## Next
- next_action: 保守保留 boundary replay 為候選，但不得跳過 legality / runtime 驗證。
- verify_next: 用 exact-lane replay + runtime guardrail 驗證 rebucket 後的 rows 是否足夠且合法。