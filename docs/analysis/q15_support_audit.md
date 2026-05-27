# q15 Support Audit

- generated_at: **2026-05-27 10:16:56.480788**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / BLOCK / D**
- current_live_structure_bucket: **BLOCK|bear_bias200_hard_block|q15**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **BLOCK|bear_bias200_hard_block|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_lane_proxy_available**
- verdict: **insufficient_support_everywhere**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **10**
- supported neighbor rows: **0**
- reason: current q15 live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。
- release_condition: 先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **3**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **5**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / BLOCK / D**
- support_identity.bucket/window/signature: **BLOCK|bear_bias200_hard_block|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: current q15 exact support 目前是 0/50，仍低於 minimum；最近同 bucket 但不同 support_identity 的 reference 是 0/50（heartbeat 1467），delta=0，mismatched=['entry_quality_label'], missing=[]。這表示 identity / 語義重切後仍未補到 exact support，不可把比較歷史歸零成進度。

## Equilibrium deadlock assessment
- verdict/state/severity: **equilibrium_deadlock_confirmed / confirmed / P0**
- confirmed: **True**
- failure_mode: **closed_loop_support_identity_starvation_under_static_gate**
- decision: 直接判定 current-live exact-support 已進入平衡死循環：同一 support signature 在 minimum 以下重複，delta=0 / stagnant repeats，不能再用 observation-only heartbeat 代表進度。
- forced artifact required/output: **True / data/equilibrium_deadlock_research_action.json**
- forbidden_shortcuts: `['lower_minimum_support_rows', 'treat_proxy_neighbor_or_legacy_rows_as_deployable_support', 'enable_live_buy_or_add_before_exact_support_and_venue_lifecycle_proof']`

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0122**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.0407**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 116 >= 50; Recent 50-sample win rate: 0.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5378**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0122**
- current_entry_quality_ge_0_55: **False**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 116 >= 50; Recent 50-sample win rate: 0.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **equilibrium_deadlock_escape**
- primary_objective: 直接判定 current-live exact-support 已進入平衡死循環；下一輪必須交付 forced research/action artifact（Map/Signal redesign、exact-row harvest 或 drift rebaseline），不能再只做 observation-only heartbeat。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **0 / 50 / 50**
- stagnant_run_count: **3**
- semantic_signature_delta_vs_previous / stagnant: **0 / 5**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest', 'equilibrium_deadlock_research_action']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 直接判定 current-live exact-support gate 進入平衡死循環；下一輪必須交付 data/equilibrium_deadlock_research_action.json 所列的 Map/Signal redesign proof、exact-bucket row harvest proof 或 drift-aware rebaseline backtest。不得再用 observation-only heartbeat、不得降低 support minimum，也不得開啟 live buy/add。

