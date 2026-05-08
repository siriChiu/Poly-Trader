# q15 Support Audit

- generated_at: **2026-05-08 09:15:53.044736**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_proxy_available**
- verdict: **exact_bucket_missing_proxy_reference_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_bucket_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **132**
- exact-lane proxy rows: **820**
- supported neighbor rows: **688**
- reason: current q15 exact bucket 仍為 0 rows；即使已有 exact-bucket proxy，也只能作治理參考，不能作 deployment 放行證據。
- release_condition: 先把 current q15 exact bucket 補到 minimum support，再重查 entry floor；proxy / neighbor 只能保留為比較與校準參考。
- support_progress.status: **regressed_under_minimum**
- support_progress.regression_basis: **same_identity_same_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **55**
- support_progress.delta_vs_previous: **-55**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **True**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `{'heartbeat': '1094', 'timestamp': '2026-04-28T02:23:38.954280+00:00', 'live_current_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'live_current_structure_bucket_rows': 122, 'minimum_support_rows': 50, 'support_route_verdict': 'exact_bucket_supported', 'support_governance_route': 'exact_live_bucket_supported', 'support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'support_identity_backfilled': False, 'semantic_identity_evidence': {'source': 'explicit_support_identity', 'explicit_support_identity_present': True, 'explicit_bucket_semantic_signature_present': True, 'backfilled_bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2', 'backfilled_support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'candidate_support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'source_fields_complete': True, 'matched_fields': ['target_col', 'horizon_minutes', 'current_live_structure_bucket', 'regime_label', 'regime_gate', 'entry_quality_label', 'bucket_semantic_signature'], 'mismatched_fields': ['calibration_window'], 'missing_fields': [], 'supports_current_identity': False, 'promotable_to_same_identity_history': False, 'verdict': 'reference_only_semantic_mismatch_or_missing_fields'}, 'reference_only_reason': 'semantic_evidence_mismatch_or_missing_fields'}`
- support_progress.reason: current q15 exact support 自最近一次已就緒 55/50（heartbeat 1103） 回落；需優先檢查 current bucket / support artifact 是否退化。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1194**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.398**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 22.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- current_entry_quality: **0.4306**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.1194**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 22.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **semantic_evidence_backfill_or_exact_accumulation**
- primary_objective: 把舊版 supported reference 轉成可審計語義證據；不能補齊 identity 前，就主動累積新版 exact rows。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **0 / 50 / 50**
- stagnant_run_count: **0**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_legacy_evidence_backfill']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['calibration_window']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

