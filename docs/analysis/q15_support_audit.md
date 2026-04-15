# q15 Support Audit

- generated_at: **2026-04-15 08:22:43.467783**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **HOLD**
- regime / gate / label: **bull / CAUTION / D**
- current_live_structure_bucket: **CAUTION|structure_quality_caution|q15**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (entry_quality_below_trade_floor)
- execution_guardrail_reason: **unsupported_exact_live_structure_bucket_blocks_trade**

## Support route verdict
- support_governance_route: **exact_live_bucket_proxy_available**
- verdict: **exact_bucket_missing_proxy_reference_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_bucket_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **4**
- exact-lane proxy rows: **421**
- supported neighbor rows: **158**
- reason: current q15 exact bucket 仍為 0 rows；即使已有 exact-bucket proxy，也只能作治理參考，不能作 deployment 放行證據。
- release_condition: 先把 current q15 exact bucket 補到 minimum support，再重查 entry floor；proxy / neighbor 只能保留為比較與校準參考。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1148**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.3827**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.3827），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

