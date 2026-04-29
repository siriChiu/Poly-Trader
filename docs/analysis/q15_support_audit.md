# q15 Support Audit

- generated_at: **2026-04-29 13:01:44.354856**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **bear / CAUTION / D**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q15**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (unsupported_exact_live_structure_bucket)
- execution_guardrail_reason: **unsupported_exact_live_structure_bucket**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|structure_quality_caution|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_proxy_available**
- verdict: **exact_bucket_missing_proxy_reference_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_bucket_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **687**
- exact-lane proxy rows: **822**
- supported neighbor rows: **132**
- reason: current q15 exact bucket 仍為 0 rows；即使已有 exact-bucket proxy，也只能作治理參考，不能作 deployment 放行證據。
- release_condition: 先把 current q15 exact bucket 補到 minimum support，再重查 entry floor；proxy / neighbor 只能保留為比較與校準參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **True**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `{'heartbeat': '20260419b', 'timestamp': '2026-04-18T17:55:51.910159+00:00', 'live_current_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'live_current_structure_bucket_rows': 53, 'minimum_support_rows': 50, 'support_route_verdict': 'exact_bucket_supported', 'support_governance_route': 'exact_live_bucket_supported', 'support_identity': None, 'reference_only_reason': 'missing_or_different_support_identity_or_bucket_semantic_signature'}`
- support_progress.reason: current q15 exact support 目前是 0/50，仍低於 minimum；歷史上同 bucket 曾有 53/50（heartbeat 20260419b），但該 artifact 缺少相同 support_identity / bucket_semantic_signature，只能當 legacy reference，不能宣稱為 same-identity regression。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0066**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.022**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.022），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Exact-supported component experiment
- verdict: **reference_only_until_exact_support_ready**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_support_missing)
- reason: exact support 尚未達 deployment 門檻；component experiment 只能作 reference-only 研究。
- verify_next: 先把 current q15 exact bucket rows 補到 minimum support，再回來做 component experiment。

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

