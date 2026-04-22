# q15 Support Audit

- generated_at: **2026-04-22 00:38:38.234736**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **HOLD**
- regime / gate / label: **bull / CAUTION / C**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q35**
- current_live_structure_bucket_rows: **73**
- allowed_layers: **0** (decision_quality_below_trade_floor)
- execution_guardrail_reason: **decision_quality_below_trade_floor**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **CAUTION|structure_quality_caution|q35**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_supported**
- verdict: **exact_bucket_supported**
- deployable: **True**
- governance_reference_only: **False**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy rows: **1**
- exact-lane proxy rows: **1**
- supported neighbor rows: **0**
- reason: current live exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.current_rows / minimum: **73 / 50**
- support_progress.previous_rows: **71**
- support_progress.delta_vs_previous: **2**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_progress.reason: current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Floor-cross legality
- verdict: **floor_already_crossed_and_support_ready**
- legal_to_relax_runtime_gate: **True**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 當前 row 已跨過 trade floor，且 exact support 已達標；可進入正常 runtime guardrail 驗證。

## Exact-supported component experiment
- verdict: **no_component_candidate**
- feature: **None**
- mode: **None**
- support_ready: **True**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_no_candidate)
- reason: component_gap_attribution 未提供最佳單點 component，無法形成 exact-supported experiment。
- verify_next: 先修復 live_decision_quality_drilldown 的 component gap attribution，再重跑 q15 audit。

## Next action
- current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。

