# q15 Support Audit

- generated_at: **2026-04-24 18:01:36.281423**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- current_live_structure_bucket_rows: **123**
- allowed_layers: **0** (decision_quality_below_trade_floor)
- execution_guardrail_reason: **decision_quality_below_trade_floor**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_supported**
- verdict: **exact_bucket_supported**
- deployable: **True**
- governance_reference_only: **False**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy rows: **143**
- exact-lane proxy rows: **367**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.regression_basis: **current_identity**
- support_progress.current_rows / minimum: **123 / 50**
- support_progress.previous_rows: **123**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **False**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `{'heartbeat': '20260424a', 'timestamp': '2026-04-23T17:42:41.117933+00:00', 'live_current_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'live_current_structure_bucket_rows': 121, 'minimum_support_rows': 50, 'support_route_verdict': 'exact_bucket_supported', 'support_governance_route': 'exact_live_bucket_supported', 'support_identity': None, 'reference_only_reason': 'missing_or_different_support_identity_or_bucket_semantic_signature'}`
- support_progress.reason: current q15 exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Floor-cross legality
- verdict: **legal_component_experiment_after_support_ready**
- legal_to_relax_runtime_gate: **True**
- remaining_gap_to_floor: **0.15**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.5**
- best_single_component_can_cross_floor: **True**
- reason: 若 exact q15 support 已達標，則 feat_4h_bias50 可作為下一輪優先 component experiment；但仍需通過 runtime guardrail 與回歸驗證。

## Exact-supported component experiment
- verdict: **exact_supported_component_experiment_ready**
- feature: **feat_4h_bias50**
- mode: **single_component_headroom**
- support_ready: **True**
- entry_quality_ge_0_55: **True**
- allowed_layers_gt_0: **True**
- preserves_positive_discrimination: **False** (failed_exact_lane_bucket_dominance)
- reason: exact support 已達標，feat_4h_bias50 可作為保守的 q15 component experiment；但是否保留正向 discrimination，仍需靠 pytest / fast heartbeat / live probe 做回歸驗證。
- verify_next: 用 exact-supported component patch + pytest + fast heartbeat 驗證 allowed_layers / execution_guardrail / live probe 是否仍一致。

## Next action
- exact support 已達標；下一輪可針對最佳 component 做保守 counterfactual 驗證，並以 pytest + fast heartbeat 驗證 runtime guardrail 不回歸。

