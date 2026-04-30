# q15 Support Audit

- generated_at: **2026-04-30 04:01:27.744662**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **HOLD**
- regime / gate / label: **bear / CAUTION / D**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q15**
- current_live_structure_bucket_rows: **10**
- allowed_layers: **0** (under_minimum_exact_live_structure_bucket)
- execution_guardrail_reason: **under_minimum_exact_live_structure_bucket**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **CAUTION|structure_quality_caution|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_lane_bucket_proxy**
- current bucket gap to minimum: **40**
- exact-bucket proxy rows: **132**
- exact-lane proxy rows: **821**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **semantic_rebaseline_under_minimum**
- support_progress.regression_basis: **legacy_or_different_semantic_signature**
- support_progress.current_rows / minimum: **10 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **10**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **True**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'regime_label': 'bear', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 100, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `{'heartbeat': '20260419b', 'timestamp': '2026-04-18T17:55:51.910159+00:00', 'live_current_structure_bucket': 'CAUTION|structure_quality_caution|q15', 'live_current_structure_bucket_rows': 53, 'minimum_support_rows': 50, 'support_route_verdict': 'exact_bucket_supported', 'support_governance_route': 'exact_live_bucket_supported', 'support_identity': None, 'reference_only_reason': 'missing_or_different_support_identity_or_bucket_semantic_signature'}`
- support_progress.reason: current q15 exact support 目前是 10/50，仍低於 minimum；歷史上同 bucket 曾有 53/50（heartbeat 20260419b），但該 artifact 缺少相同 support_identity / bucket_semantic_signature，只能當 legacy reference，不能宣稱為 same-identity regression。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0131**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.0437**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.0437），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Exact-supported component experiment
- verdict: **reference_only_until_exact_support_ready**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- current_entry_quality: **0.5369**
- trade_floor: **0.55**
- current_trade_floor_gap: **-0.0131**
- current_entry_quality_ge_trade_floor: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_support_missing)
- reason: exact support 尚未達 deployment 門檻；component experiment 只能作 reference-only 研究。
- verify_next: 先把 current q15 exact bucket rows 補到 minimum support，再回來做 component experiment。

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

