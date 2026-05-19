# q15 Support Audit

- generated_at: **2026-05-19 11:02:07.606268**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bear / CAUTION / C**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- current_live_structure_bucket_rows: **1**
- allowed_layers: **0** (decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **49**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **8**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **1 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **1**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **bear / CAUTION / C**
- support_identity.bucket/window/signature: **CAUTION|base_caution_regime_or_bias|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **reference-only; not deployment closure**
- legacy reference heartbeat/rows/minimum: **1250 / 173 / 50**
- legacy semantic verdict: **reference_only_semantic_mismatch_or_missing_fields**; supports_current_identity=**False**; promotable=**False**
- legacy semantic mismatch/missing fields: `['calibration_window', 'entry_quality_label', 'regime_label']` / `[]`
- legacy reference_only_reason: **semantic_evidence_mismatch_or_missing_fields**
- support_progress.reason: current q15 exact support 目前是 1/50，仍低於 minimum；歷史上同 bucket 曾有 173/50（heartbeat 1250），語義證據已回填但不吻合 current support_identity（mismatched=['calibration_window', 'entry_quality_label', 'regime_label'], missing=[]），只能當 legacy reference，不能宣稱為 same-identity regression。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0**
- best_single_component: **None**
- best_single_component_required_score_delta: **None**
- best_single_component_can_cross_floor: **False**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 20.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **None**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.6791**
- trade_floor: **0.55**
- current_trade_floor_gap: **0.1291**
- current_entry_quality_ge_0_55: **True**
- current_entry_quality_ge_trade_floor: **True**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 20.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Active repair plan
- phase: **semantic_evidence_backfill_or_exact_accumulation**
- primary_objective: 把舊版 supported reference 轉成可審計語義證據；不能補齊 identity 前，就主動累積新版 exact rows。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **CIRCUIT_BREAKER / 0 / decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active**
- support rows / minimum / gap: **1 / 50 / 49**
- stagnant_run_count: **0**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_legacy_evidence_backfill']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['calibration_window', 'entry_quality_label', 'regime_label']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

