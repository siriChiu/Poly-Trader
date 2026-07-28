# q15 Support Audit

- generated_at: **2026-07-28T18:43:37.337442Z**
- feature_timestamp: **2026-07-28 18:41:44.247652**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / CAUTION / C**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q15**
- current_live_structure_bucket_rows: **10**
- allowed_layers: **0** (decision_quality_below_trade_floor; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|structure_quality_caution|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **40**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **43**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **10 / 50**
- support_progress.previous_rows: **10**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **2**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / CAUTION / C**
- support_identity.bucket/window/signature: **CAUTION|structure_quality_caution|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: current q15 exact support 目前是 10/50，仍低於 minimum；最近同 bucket 但不同 support_identity 的 reference 是 0/50（heartbeat 48），delta=10，mismatched=['entry_quality_label'], missing=[]。這表示 identity / 語義重切後仍未補到 exact support，不可把比較歷史歸零成進度。

## Equilibrium deadlock assessment
- verdict/state/severity: **equilibrium_deadlock_watch / watch / P1**
- confirmed: **False**
- failure_mode: **closed_loop_support_identity_starvation_under_static_gate**
- decision: 尚未達 confirmed 閾值，但 under-minimum support 已出現零位移或停滯訊號；下一輪需證明 rows 有位移或升級為 forced branch。
- forced artifact required/output: **True / data/equilibrium_deadlock_research_action.json**
- forbidden_shortcuts: `['lower_minimum_support_rows', 'treat_proxy_neighbor_or_legacy_rows_as_deployable_support', 'enable_live_buy_or_add_before_exact_support_and_venue_lifecycle_proof']`

## Forced branch decision
- status: **hard_no_go_recorded**
- selected_branch: **hard_no_go_single_failed_gate**
- decision_clock: **72h_micro_canary_or_single_failed_gate**
- single_failed_gate: **circuit_breaker_gate**
- next_validation_artifact: **data/circuit_breaker_audit.json**
- live_exposure_allowed: **False**
- decision: 熔斷仍是唯一 immediate live gate；本輪以 single failed gate 記錄 no-go，同時要求後續交付 Map/Signal、exact-row harvest 或 drift rebaseline artifact。
- branch_matrix: `[('map_signal_redesign_proof', 'delivered_no_current_window_deployable', 'data/q15_map_signal_redesign_proof.json'), ('exact_bucket_row_harvest_proof', 'blocked_no_positive_delta', 'data/q15_exact_bucket_row_harvest_proof.json'), ('drift_rebaseline_backtest', 'delivered_reference_only', 'data/q15_drift_rebaseline_backtest.json'), ('hard_no_go_single_failed_gate', 'selected', 'data/circuit_breaker_audit.json')]`

## Exact bucket row harvest proof
- artifact: **q15_exact_bucket_row_harvest_proof**
- generated_at: **2026-07-28T18:28:37.675880Z**
- verdict: **exact_bucket_row_harvest_stalled_under_minimum**
- current_exact_bucket_rows / minimum: **10 / 50**
- previous_rows: **10**
- delta_vs_previous: **0**
- rows_needed_to_minimum: **40**
- primary_failed_gate: **support_accumulation_stalled**
- live_exposure_allowed: **False**

## Map/Signal redesign proof
- artifact: **q15_map_signal_redesign_proof**
- generated_at: **2026-07-28T18:28:48.584829Z**
- verdict: **map_signal_redesign_no_current_window_deployable_candidate**
- selected_candidate_id: **dominant_neighbor_exact_lane**
- selected_target_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- selected_current_window_rows / all_history_rows: **0 / 38**
- best_reference_candidate_id: **semantic_entry_quality_family**
- primary_failed_gate: **current_live_support_gate**
- live_exposure_allowed: **False**

## Drift rebaseline backtest
- artifact: **q15_drift_rebaseline_backtest**
- generated_at: **2026-07-28T18:28:43.745304Z**
- verdict: **reference_candidate_found_but_current_window_unproven**
- selected_candidate_id: **semantic_entry_quality_family**
- selected_current_window_rows / all_history_rows: **43 / 57**
- live_exposure_allowed: **False**

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 26.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5709**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.0209**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 26.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **semantic_evidence_backfill_or_exact_accumulation**
- primary_objective: 同 bucket semantic signature 仍停在相同 exact rows；entry-quality 標籤變動不能把 support delta 歸零，下一輪必須交付 Map/Signal redesign 或 exact-bucket row harvest 證據。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; circuit_breaker_active**
- support rows / minimum / gap: **10 / 50 / 40**
- stagnant_run_count: **2**
- semantic_signature_delta_vs_previous / stagnant: **0 / 2**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest', 'equilibrium_deadlock_research_action']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

