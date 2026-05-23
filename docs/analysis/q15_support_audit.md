# q15 Support Audit

- generated_at: **2026-05-23 20:09:22.255203**
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
- verdict: **exact_bucket_missing_exact_lane_proxy_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **216**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 缺樣本，只剩 same-lane proxy；這仍不足以解除 runtime blocker。
- release_condition: 必須先生成 current q15 exact bucket 真樣本，proxy 不可直接轉成 deployment allowance。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **5**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / BLOCK / D**
- support_identity.bucket/window/signature: **BLOCK|bear_bias200_hard_block|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: current q15 exact support 目前是 0/50，仍低於 minimum；最近同 bucket 但不同 support_identity 的 reference 是 0/50（heartbeat 1467），delta=0，mismatched=['entry_quality_label'], missing=[]。這表示 identity / 語義重切後仍未補到 exact support，不可把比較歷史歸零成進度。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0279**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.093**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 12.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5221**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0279**
- current_entry_quality_ge_0_55: **False**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 12.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **semantic_evidence_backfill_or_exact_accumulation**
- primary_objective: 同 bucket semantic signature 仍停在相同 exact rows；entry-quality 標籤變動不能把 support delta 歸零，下一輪必須交付 Map/Signal redesign 或 exact-bucket row harvest 證據。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **0 / 50 / 50**
- stagnant_run_count: **2**
- semantic_signature_delta_vs_previous / stagnant: **0 / 5**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

