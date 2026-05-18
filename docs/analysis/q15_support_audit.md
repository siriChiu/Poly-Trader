# q15 Support Audit

- generated_at: **2026-05-18 17:15:31.664883**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / CAUTION / C**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_lane_proxy_available**
- verdict: **insufficient_support_everywhere**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **8**
- supported neighbor rows: **0**
- reason: current live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。
- release_condition: 先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / CAUTION / C**
- support_identity.bucket/window/signature: **CAUTION|base_caution_regime_or_bias|q00 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **reference-only; not deployment closure**
- legacy reference heartbeat/rows/minimum: **1202 / 190 / 50**
- legacy semantic verdict: **reference_only_semantic_mismatch_or_missing_fields**; supports_current_identity=**False**; promotable=**False**
- legacy semantic mismatch/missing fields: `['calibration_window', 'entry_quality_label', 'regime_label']` / `[]`
- legacy reference_only_reason: **semantic_evidence_mismatch_or_missing_fields**
- support_progress.reason: current live exact support 目前是 0/50，仍低於 minimum；歷史上同 bucket 曾有 190/50（heartbeat 1202），語義證據已回填但不吻合 current support_identity（mismatched=['calibration_window', 'entry_quality_label', 'regime_label'], missing=[]），只能當 legacy reference，不能宣稱為 same-identity regression。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 8.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.6356**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.0856**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 8.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **current_bucket_first**
- primary_objective: 先處理當前 live bucket 的 exact-support / runtime gate；q15 lane 只保留 standby repair。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **0 / 50 / 50**
- stagnant_run_count: **5**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_legacy_evidence_backfill']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['calibration_window', 'entry_quality_label', 'regime_label']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=CAUTION|base_caution_regime_or_bias|q00, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

