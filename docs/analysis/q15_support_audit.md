# q15 Support Audit

- generated_at: **2026-05-13 22:01:26.175866**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- current_live_structure_bucket_rows: **189**
- allowed_layers: **0** (decision_quality_below_trade_floor; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; circuit_breaker_active**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_supported**
- verdict: **exact_bucket_supported**
- deployable: **True**
- governance_reference_only: **False**
- preferred_support_cohort: **exact_live_bucket**
- current bucket gap to minimum: **0**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **838**
- supported neighbor rows: **0**
- reason: current live exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.regression_basis: **current_identity**
- support_progress.current_rows / minimum: **189 / 50**
- support_progress.previous_rows: **189**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.escalate_to_blocker: **False**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q00', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `None`
- support_progress.reason: current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.055**
- best_single_component: **feat_pulse**
- best_single_component_required_score_delta: **0.2716**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 28.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_pulse**
- mode: **None**
- support_ready: **True**
- entry_quality_ge_0_55: **False**
- current_entry_quality: **0.495**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.055**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 28.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **current_bucket_first**
- primary_objective: 先處理當前 live bucket 的 exact-support / runtime gate；q15 lane 只保留 standby repair。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; circuit_breaker_active**
- support rows / minimum / gap: **189 / 50 / 0**
- stagnant_run_count: **2**
- actions: `['verify_floor_and_execution_guardrail']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=CAUTION|base_caution_regime_or_bias|q00, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

