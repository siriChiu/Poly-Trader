# q15 Support Audit

- generated_at: **2026-04-16 23:00:23.100224**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **HOLD**
- regime / gate / label: **bull / CAUTION / D**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q15**
- current_live_structure_bucket_rows: **77**
- allowed_layers: **0** (entry_quality_below_trade_floor)
- execution_guardrail_reason: **None**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|structure_quality_caution|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_supported**
- deployable: **True**
- governance_reference_only: **False**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy rows: **1**
- exact-lane proxy rows: **58**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.current_rows / minimum: **77 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **77**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_progress.reason: current q15 exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Floor-cross legality
- verdict: **legal_component_experiment_after_support_ready**
- legal_to_relax_runtime_gate: **True**
- remaining_gap_to_floor: **0.2262**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.754**
- best_single_component_can_cross_floor: **True**
- reason: 若 exact q15 support 已達標，則 feat_4h_bias50 可作為下一輪優先 component experiment；但仍需通過 runtime guardrail 與回歸驗證。

## Exact-supported component experiment
- verdict: **exact_supported_component_experiment_ready**
- feature: **feat_4h_bias50**
- mode: **bias50_floor_counterfactual**
- support_ready: **True**
- entry_quality_ge_0_55: **True**
- allowed_layers_gt_0: **True**
- preserves_positive_discrimination: **None** (not_measured_requires_followup_verify)
- reason: exact support 已達標，feat_4h_bias50 可作為保守的 q15 component experiment；但是否保留正向 discrimination，仍需靠 pytest / fast heartbeat / live probe 做回歸驗證。
- verify_next: 用 exact-supported component patch + pytest + fast heartbeat 驗證 allowed_layers / execution_guardrail / live probe 是否仍一致。

## Next action
- exact support 已達標；下一輪可針對最佳 component 做保守 counterfactual 驗證，並以 pytest + fast heartbeat 驗證 runtime guardrail 不回歸。

