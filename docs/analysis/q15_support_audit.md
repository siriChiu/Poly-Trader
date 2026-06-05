# q15 Support Audit

- generated_at: **2026-06-05T12:40:23.029919Z**
- feature_timestamp: **2026-06-05 03:00:00**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **bear / BLOCK / C**
- current_live_structure_bucket: **BLOCK|bias200_below_min|q00**
- current_live_structure_bucket_rows: **131**
- allowed_layers: **0** (decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade)
- execution_guardrail_reason: **decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **BLOCK|bias200_below_min|q00**
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
- exact-lane proxy rows: **10**
- supported neighbor rows: **0**
- reason: current live exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.regression_basis: **current_identity**
- support_progress.current_rows / minimum: **131 / 50**
- support_progress.previous_rows: **131**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **5**
- support_progress.semantic_signature_stalled_support_accumulation: **False**
- support_progress.escalate_to_blocker: **False**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / BLOCK / C**
- support_identity.bucket/window/signature: **BLOCK|bias200_below_min|q00 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: current live exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Equilibrium deadlock assessment
- verdict/state/severity: **not_applicable_current_live_not_target_lane / standby / none**
- confirmed: **False**
- failure_mode: **closed_loop_support_identity_starvation_under_static_gate**
- decision: current live row 不在 q15/current target lane；此 audit 只保留 reference/standby，不把 target-lane support stagnation 誤判為 current-live deadlock。
- forced artifact required/output: **False / data/equilibrium_deadlock_research_action.json**
- forbidden_shortcuts: `['lower_minimum_support_rows', 'treat_proxy_neighbor_or_legacy_rows_as_deployable_support', 'enable_live_buy_or_add_before_exact_support_and_venue_lifecycle_proof']`

## Forced branch decision
- status: **not_required**
- selected_branch: **None**
- decision_clock: **72h_micro_canary_or_single_failed_gate**
- single_failed_gate: **support_gate**
- next_validation_artifact: **data/q15_support_audit.json**
- live_exposure_allowed: **False**
- decision: support deadlock forced branch 尚未觸發；維持一般 support / venue / model gate 驗證。
- branch_matrix: `[('map_signal_redesign_proof', 'delivered_no_current_window_deployable', 'data/q15_map_signal_redesign_proof.json'), ('exact_bucket_row_harvest_proof', 'delivered_support_ready_remaining_gates', 'data/q15_exact_bucket_row_harvest_proof.json'), ('drift_rebaseline_backtest', 'delivered_reference_only', 'data/q15_drift_rebaseline_backtest.json'), ('hard_no_go_single_failed_gate', 'standby', 'data/q15_support_audit.json')]`

## Exact bucket row harvest proof
- artifact: **q15_exact_bucket_row_harvest_proof**
- generated_at: **2026-06-05T03:46:33.530787Z**
- verdict: **exact_bucket_row_harvest_support_ready_remaining_gates**
- current_exact_bucket_rows / minimum: **131 / 50**
- previous_rows: **131**
- delta_vs_previous: **0**
- rows_needed_to_minimum: **0**
- primary_failed_gate: **remaining_live_gates**
- live_exposure_allowed: **False**

## Map/Signal redesign proof
- artifact: **q15_map_signal_redesign_proof**
- generated_at: **2026-06-05T03:46:44.756417Z**
- verdict: **map_signal_redesign_no_current_window_deployable_candidate**
- selected_candidate_id: **dominant_neighbor_exact_lane**
- selected_target_bucket: **BLOCK|bear_bias200_hard_block|q00**
- selected_current_window_rows / all_history_rows: **28 / 174**
- best_reference_candidate_id: **best_historical_exact_lane_bucket**
- primary_failed_gate: **current_live_support_gate**
- live_exposure_allowed: **False**

## Drift rebaseline backtest
- artifact: **q15_drift_rebaseline_backtest**
- generated_at: **2026-06-05T03:46:38.416907Z**
- verdict: **current_identity_support_ready_rebaseline_not_needed**
- selected_candidate_id: **None**
- selected_current_window_rows / all_history_rows: **None / None**
- live_exposure_allowed: **False**

## Floor-cross legality
- verdict: **floor_already_crossed_and_support_ready**
- legal_to_relax_runtime_gate: **True**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 當前 row 已跨過 trade floor，且 exact support 已達標；可進入正常 runtime guardrail 驗證。

## Exact-supported component experiment
- verdict: **exact_supported_component_experiment_ready_but_current_live_not_q15**
- feature: **None**
- mode: **standby_q15_route**
- support_ready: **True**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5788**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.0288**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_applicable_current_live_not_q15_lane)
- reason: current live row 目前停在 BLOCK|bias200_below_min|q00，不在 q15 target lane CAUTION|structure_quality_caution|q15；本 artifact 只能描述非 current-live 的 q15/reference route，不得當成 current-live deployment closure。
- verify_next: 先處理 current-live bucket BLOCK|bias200_below_min|q00 的 exact-support / runtime blocker；只有 live row 回到 q15 lane 且 exact support deployable 時，q15 component experiment 才可進入 deployment verify。

## Active repair plan
- phase: **current_bucket_first**
- primary_objective: 先處理當前 live bucket 的 exact-support / runtime gate；q15 lane 只保留 standby repair。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **HOLD / 0 / decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade**
- support rows / minimum / gap: **131 / 50 / 0**
- stagnant_run_count: **5**
- semantic_signature_delta_vs_previous / stagnant: **0 / 5**
- actions: `['semantic_rebaseline_reference_review', 'verify_floor_and_execution_guardrail']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=BLOCK|bias200_below_min|q00, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

