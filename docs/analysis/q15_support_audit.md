# q15 Support Audit

- generated_at: **2026-04-18 13:43:25.809469**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bull / None / None**
- current_live_structure_bucket: **None**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (circuit_breaker_blocks_trade)
- execution_guardrail_reason: **circuit_breaker_blocks_trade**

## Scope applicability
- status: **unknown_current_live_bucket**
- active_for_current_live_row: **False**
- current_structure_bucket: **None**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: 無法判定 current live structure bucket，q15 support audit 只能保留為背景治理資訊。

## Support route verdict
- support_governance_route: **no_support_proxy**
- verdict: **insufficient_support_everywhere**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **0**
- supported neighbor rows: **0**
- reason: current q15 live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。
- release_condition: 先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。
- support_progress.status: **no_recent_comparable_history**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **None**
- support_progress.delta_vs_previous: **None**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_progress.reason: 目前找不到同一 q15 bucket 的最近 heartbeat 可比較；先持續累積 exact support。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **None**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 8.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 8.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Next action
- current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。

