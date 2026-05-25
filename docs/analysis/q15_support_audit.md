# q15 Support Audit

- generated_at: **2026-05-25 06:25:59.397907**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- current_live_structure_bucket_rows: **12**
- allowed_layers: **0** (under_minimum_exact_live_structure_bucket)
- execution_guardrail_reason: **under_minimum_exact_live_structure_bucket**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **38**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **860**
- supported neighbor rows: **0**
- reason: current live exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **12 / 50**
- support_progress.previous_rows: **12**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **2**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **chop / CAUTION / D**
- support_identity.bucket/window/signature: **CAUTION|base_caution_regime_or_bias|q35 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **reference-only; not deployment closure**
- legacy reference heartbeat/rows/minimum: **1238 / 0 / 50**
- legacy semantic verdict: **reference_only_semantic_mismatch_or_missing_fields**; supports_current_identity=**False**; promotable=**False**
- legacy semantic mismatch/missing fields: `['calibration_window']` / `[]`
- legacy reference_only_reason: **semantic_evidence_mismatch_or_missing_fields**
- support_progress.reason: current live exact support 目前是 12/50，仍低於 minimum；歷史上同 bucket 曾有 0/50（heartbeat 1238），語義證據已回填但不吻合 current support_identity（mismatched=['calibration_window'], missing=[]），只能當 legacy reference，不能宣稱為 same-identity regression。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0031**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.0103**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.0103），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Exact-supported component experiment
- verdict: **reference_only_current_live_not_q15_and_support_not_ready**
- feature: **feat_4h_bias50**
- mode: **reference_only_non_current_live_scope**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5469**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0031**
- current_entry_quality_ge_0_55: **False**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_applicable_current_live_not_q15_lane)
- reason: current live row 目前停在 CAUTION|base_caution_regime_or_bias|q35，不在 q15 target lane CAUTION|structure_quality_caution|q15；本 artifact 只能描述非 current-live 的 q15/reference route，不得當成 current-live deployment closure。
- verify_next: 先處理 current-live bucket CAUTION|base_caution_regime_or_bias|q35 的 exact-support / runtime blocker；只有 live row 回到 q15 lane 且 exact support deployable 時，q15 component experiment 才可進入 deployment verify。

## Active repair plan
- phase: **current_bucket_first**
- primary_objective: 先處理當前 live bucket 的 exact-support / runtime gate；q15 lane 只保留 standby repair。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **HOLD / 0 / under_minimum_exact_live_structure_bucket**
- support rows / minimum / gap: **12 / 50 / 38**
- stagnant_run_count: **2**
- semantic_signature_delta_vs_previous / stagnant: **0 / 2**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_legacy_evidence_backfill', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['calibration_window']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=CAUTION|base_caution_regime_or_bias|q35, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

