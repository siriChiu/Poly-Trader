# q15 Support Audit

- generated_at: **2026-05-01 21:55:39.040809**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q35**
- current_live_structure_bucket_rows: **11**
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
- preferred_support_cohort: **bull_live_exact_lane_bucket_proxy**
- current bucket gap to minimum: **39**
- exact-bucket proxy rows: **132**
- exact-lane proxy rows: **821**
- supported neighbor rows: **687**
- reason: current live exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **stalled_under_minimum**
- support_progress.regression_basis: **same_identity_same_semantic_signature**
- support_progress.current_rows / minimum: **11 / 50**
- support_progress.previous_rows: **11**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **2**
- support_progress.escalate_to_blocker: **False**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q35', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `None`
- support_progress.reason: current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1124**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.3747**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.3747），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Exact-supported component experiment
- verdict: **reference_only_current_live_not_q15_and_support_not_ready**
- feature: **feat_4h_bias50**
- mode: **reference_only_non_current_live_scope**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- current_entry_quality: **0.4376**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.1124**
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
- support rows / minimum / gap: **11 / 50 / 39**
- stagnant_run_count: **2**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh']`
- legacy_semantic_evidence.verdict: **None**
- legacy_semantic_evidence.supports_current_identity: **None**
- legacy_semantic_evidence.mismatched_fields: `None`
- legacy_semantic_evidence.missing_fields: `None`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- current live row 目前不在 q15 lane（current=CAUTION|base_caution_regime_or_bias|q35, target=CAUTION|structure_quality_caution|q15）；q15 audit 只保留 standby/reference route readiness。下一輪主焦點應回到 current-live exact-support blocker / deployment verify，除非 live row 再次回到 q15 bucket。

