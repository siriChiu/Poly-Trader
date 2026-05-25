# q15 Support Audit

- generated_at: **2026-05-25 22:11:22.037342**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q15**
- current_live_structure_bucket_rows: **7**
- allowed_layers: **0** (under_minimum_exact_live_structure_bucket)
- execution_guardrail_reason: **under_minimum_exact_live_structure_bucket**

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
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **43**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **860**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **regressed_under_minimum**
- support_progress.regression_basis: **same_identity_same_semantic_signature**
- support_progress.current_rows / minimum: **7 / 50**
- support_progress.previous_rows: **7**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **4**
- support_progress.semantic_signature_delta_vs_previous: **0**
- support_progress.semantic_signature_stagnant_run_count: **4**
- support_progress.semantic_signature_stalled_support_accumulation: **True**
- support_progress.escalate_to_blocker: **True**
- support_identity.target/horizon: **simulated_pyramid_win / 1440m**
- support_identity.path: **chop / CAUTION / D**
- support_identity.bucket/window/signature: **CAUTION|base_caution_regime_or_bias|q15 / 200 / live_structure_bucket:q15_support_identity:v2**
- legacy_supported_reference: **reference-only; not deployment closure**
- legacy reference heartbeat/rows/minimum: **1436 / 59 / 50**
- legacy semantic verdict: **reference_only_semantic_mismatch_or_missing_fields**; supports_current_identity=**False**; promotable=**False**
- legacy semantic mismatch/missing fields: `['entry_quality_label', 'regime_label']` / `[]`
- legacy reference_only_reason: **semantic_evidence_mismatch_or_missing_fields**
- support_progress.reason: current q15 exact support 最近曾達 minimum support（最近一次 121/50，heartbeat 1067），但目前仍停在 7/50；這不是一般停滯，而是 support regression。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0362**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.1207**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.1207），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Exact-supported component experiment
- verdict: **reference_only_until_exact_support_ready**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- entry_quality_ge_0_55_scope: **component_experiment_counterfactual**
- component_experiment_entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5138**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0362**
- current_entry_quality_ge_0_55: **False**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_support_missing)
- reason: exact support 尚未達 deployment 門檻；component experiment 只能作 reference-only 研究。
- verify_next: 先把 current q15 exact bucket rows 補到 minimum support，再回來做 component experiment。

## Active repair plan
- phase: **semantic_evidence_backfill_or_exact_accumulation**
- primary_objective: 同 bucket semantic signature 仍停在相同 exact rows；entry-quality 標籤變動不能把 support delta 歸零，下一輪必須交付 Map/Signal redesign 或 exact-bucket row harvest 證據。
- component_verify_ready: **False**
- live_exposure_allowed: **False**
- shadow_or_paper_allowed: **True**
- current_signal / layers / guardrail: **HOLD / 0 / under_minimum_exact_live_structure_bucket**
- support rows / minimum / gap: **7 / 50 / 43**
- stagnant_run_count: **4**
- semantic_signature_delta_vs_previous / stagnant: **0 / 4**
- actions: `['collect_exact_current_bucket_rows', 'force_q15_support_audit_refresh', 'semantic_legacy_evidence_backfill', 'semantic_rebaseline_reference_review', 'semantic_signature_map_signal_redesign_or_row_harvest']`
- legacy_semantic_evidence.verdict: **reference_only_semantic_mismatch_or_missing_fields**
- legacy_semantic_evidence.supports_current_identity: **False**
- legacy_semantic_evidence.mismatched_fields: `['entry_quality_label', 'regime_label']`
- legacy_semantic_evidence.missing_fields: `[]`
- entropy_reduction_rules: `['引入外部能量：每輪刷新 current-live rows / venue proof / semantic evidence，而不是重用 under-minimum cache。', '建立系統與規則：support_identity 完全一致且 rows>=minimum 才能進入 deployment verify。', '主動代謝與清理：proxy、neighbor、legacy reference 未補齊語義證據前全部標記 reference-only。']`

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

