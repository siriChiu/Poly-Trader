# q15 Support Audit

- generated_at: **2026-05-27 23:06:57.634994**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / BLOCK / C**
- current_live_structure_bucket: **BLOCK|bear_bias200_hard_block|q00**
- current_live_structure_bucket_rows: **7**
- allowed_layers: **0** (decision_quality_below_trade_floor; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; circuit_breaker_active**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **BLOCK|bear_bias200_hard_block|q00**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **43**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **10**
- supported neighbor rows: **0**
- reason: current live exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **7 / 50**
- support_progress.previous_rows: **7**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **2**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / BLOCK / C**
- support_identity.bucket/window/signature: **BLOCK|bear_bias200_hard_block|q00 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: current live exact support 目前是 7/50，仍低於 minimum；最近同 bucket 但不同 support_identity 的 reference 是 0/50（heartbeat 1542），delta=7，mismatched=['entry_quality_label'], missing=[]。這表示 identity / 語義重切後仍未補到 exact support，不可把比較歷史歸零成進度。

## Equilibrium deadlock assessment
- verdict/state/severity: **not_applicable_current_live_not_target_lane / standby / none**
- confirmed: **False**
- failure_mode: **closed_loop_support_identity_starvation_under_static_gate**
- decision: current live row 不在 q15/current target lane；此 audit 只保留 reference/standby，不把 target-lane support stagnation 誤判為 current-live deadlock。
- forced artifact required/output: **False / data/equilibrium_deadlock_research_action.json**
- forbidden_shortcuts: `['lower_minimum_support_rows', 'treat_proxy_neighbor_or_legacy_rows_as_deployable_support', 'enable_live_buy_or_add_before_exact_support_and_venue_lifecycle_proof']`

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 162 >= 50; Recent 50-sample win rate: 0.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.6359**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.0859**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 162 >= 50; Recent 50-sample win rate: 0.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **current_bucket_first**
- primary_objective: 先處理當前 live bucket 的 exact-support / runtime gate；q15 lane 只保留 standby repair。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; circuit_breaker_active**
- support rows / minimum / gap: **7 / 50 / 43**
- stagnant_run_count: **2**
- semantic_signature_delta_vs_previous / stagnant: **0 / 2**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=BLOCK|bear_bias200_hard_block|q00, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

