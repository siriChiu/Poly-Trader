# q15 Support Audit

- generated_at: **2026-04-23 23:55:30.948572**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bull / BLOCK / D**
- current_live_structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_proxy_available**
- verdict: **exact_bucket_missing_proxy_reference_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_bucket_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **143**
- exact-lane proxy rows: **367**
- supported neighbor rows: **0**
- reason: current live exact bucket 仍為 0 rows；即使已有 exact-bucket proxy，也只能作治理參考，不能作 deployment 放行證據。
- release_condition: 先把 current live exact bucket 補到 minimum support，再重查 entry floor；proxy / neighbor 只能保留為比較與校準參考。
- support_progress.status: **stalled_under_minimum**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **True**
- support_progress.reason: current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1478**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.4927**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 24.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 24.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Next action
- current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。

