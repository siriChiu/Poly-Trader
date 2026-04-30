# q15 Support Audit

- generated_at: **2026-04-30 03:02:11.116119**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **bear / BLOCK / C**
- current_live_structure_bucket: **BLOCK|structure_quality_block|q00**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (unsupported_exact_live_structure_bucket)
- execution_guardrail_reason: **unsupported_exact_live_structure_bucket**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **BLOCK|structure_quality_block|q00**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_lane_proxy_available**
- verdict: **insufficient_support_everywhere**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **3**
- supported neighbor rows: **0**
- reason: current live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。
- release_condition: 先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。
- support_progress.status: **no_recent_comparable_history**
- support_progress.regression_basis: **no_same_identity_same_semantic_signature_history**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **None**
- support_progress.delta_vs_previous: **None**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'BLOCK|structure_quality_block|q00', 'regime_label': 'bear', 'regime_gate': 'BLOCK', 'entry_quality_label': 'C', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `None`
- support_progress.reason: 目前找不到同一 current live structure bucket且同 support_identity / semantic signature 的最近 heartbeat 可比較；先持續累積 exact support。

## Floor-cross legality
- verdict: **floor_crossed_but_support_not_ready**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 即使 entry floor 已跨過，exact q15 support 仍未達標，不能把 proxy/neighbor 當 deployment 放行證據。

## Exact-supported component experiment
- verdict: **reference_only_current_live_not_q15_and_support_not_ready**
- feature: **None**
- mode: **reference_only_non_current_live_scope**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- current_entry_quality: **0.6157**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.0657**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_applicable_current_live_not_q15_lane)
- reason: current live row 目前停在 BLOCK|structure_quality_block|q00，不在 q15 target lane CAUTION|structure_quality_caution|q15；本 artifact 只能描述非 current-live 的 q15/reference route，不得當成 current-live deployment closure。
- verify_next: 先處理 current-live bucket BLOCK|structure_quality_block|q00 的 exact-support / runtime blocker；只有 live row 回到 q15 lane 且 exact support deployable 時，q15 component experiment 才可進入 deployment verify。

## Next action
- current live row 目前不在 q15 lane（current=BLOCK|structure_quality_block|q00, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

