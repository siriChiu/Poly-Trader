# q15 Support Audit

- generated_at: **2026-05-23 14:31:54.724732**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / BLOCK / C**
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
- support_progress.status: **no_recent_comparable_history**
- support_progress.regression_basis: **no_same_identity_same_semantic_signature_history**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **None**
- support_progress.delta_vs_previous: **None**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / BLOCK / C**
- support_identity.bucket/window/signature: **BLOCK|bear_bias200_hard_block|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **None**
- support_progress.reason: 目前找不到同一 q15 bucket且同 support_identity / semantic signature 的最近 heartbeat 可比較；先持續累積 exact support。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 111 >= 50; Recent 50-sample win rate: 0.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.596**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.046**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 111 >= 50; Recent 50-sample win rate: 0.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **exact_support_accumulation**
- primary_objective: 持續累積 current q15 exact rows 到 deployment-grade minimum。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **0 / 50 / 50**
- stagnant_run_count: **0**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

