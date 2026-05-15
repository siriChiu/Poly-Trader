# q15 Support Audit

- generated_at: **2026-05-15 12:04:37.909407**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- current_live_structure_bucket_rows: **173**
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
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **860**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。
- release_condition: 保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。
- support_progress.status: **exact_supported**
- support_progress.regression_basis: **current_identity**
- support_progress.current_rows / minimum: **173 / 50**
- support_progress.previous_rows: **173**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **False**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 1000, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `{'heartbeat': '1188', 'timestamp': '2026-05-13T12:21:50.323469+00:00', 'live_current_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'live_current_structure_bucket_rows': 95, 'minimum_support_rows': 50, 'support_route_verdict': 'exact_bucket_supported', 'support_governance_route': 'exact_live_bucket_supported', 'support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'support_identity_backfilled': False, 'semantic_identity_evidence': {'source': 'explicit_support_identity', 'explicit_support_identity_present': True, 'explicit_bucket_semantic_signature_present': True, 'backfilled_bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2', 'backfilled_support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'candidate_support_identity': {'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q15', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}, 'source_fields_complete': True, 'matched_fields': ['target_col', 'horizon_minutes', 'current_live_structure_bucket', 'regime_label', 'regime_gate', 'entry_quality_label', 'bucket_semantic_signature'], 'mismatched_fields': ['calibration_window'], 'missing_fields': [], 'supports_current_identity': False, 'promotable_to_same_identity_history': False, 'verdict': 'reference_only_semantic_mismatch_or_missing_fields'}, 'reference_only_reason': 'semantic_evidence_mismatch_or_missing_fields'}`
- support_progress.reason: current q15 exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。

## Floor-cross legality
- verdict: **legal_component_experiment_after_support_ready**
- legal_to_relax_runtime_gate: **True**
- remaining_gap_to_floor: **0.0776**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.2587**
- best_single_component_can_cross_floor: **True**
- reason: 若 exact q15 support 已達標，則 feat_4h_bias50 可作為下一輪優先 component experiment；但仍需通過 runtime guardrail 與回歸驗證。

## Exact-supported component experiment
- verdict: **exact_supported_component_experiment_blocked_by_discrimination**
- feature: **feat_4h_bias50**
- mode: **single_component_headroom**
- support_ready: **True**
- entry_quality_ge_0_55: **True**
- current_entry_quality: **0.4724**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0776**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **False** (failed_exact_lane_bucket_dominance)
- reason: exact support 已達標，且 feat_4h_bias50 在數學上可補足 floor gap；但 current q15 bucket 對 sibling buckets 未保留正向 win/pnl/quality discrimination，不得把 component experiment 標記為 deployment-ready。
- verify_next: 先重設 / 重訓 q15 component，使 current bucket 相對 sibling buckets 保留正向 discrimination，再談 allowed_layers / execution guardrail 放行。

## Active repair plan
- phase: **support_ready_floor_or_execution_verify**
- primary_objective: exact support 已達標；下一步驗證 floor / allowed_layers / execution guardrail，而不是再累積 support。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **HOLD / 0 / decision_quality_below_trade_floor**
- support rows / minimum / gap: **173 / 50 / 0**
- stagnant_run_count: **5**
- actions: `['semantic_legacy_evidence_backfill', 'verify_floor_and_execution_guardrail']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['calibration_window']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- exact support 已達標，但最佳 component 目前未保留正向 discrimination；先重設 / 重訓 q15 component 並重跑 q15 support audit / runtime guardrail，再談 allowed_layers 或下單放行。

