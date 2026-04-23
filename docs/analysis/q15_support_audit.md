# q15 Support Audit

- generated_at: **2026-04-23 00:35:03.293025**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **HOLD**
- regime / gate / label: **bull / BLOCK / D**
- current_live_structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- current_live_structure_bucket_rows: **13**
- allowed_layers: **0** (under_minimum_exact_live_structure_bucket)
- execution_guardrail_reason: **under_minimum_exact_live_structure_bucket**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **BLOCK|bull_high_bias200_overheat_block|q35**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_live_exact_lane_bucket_proxy**
- current bucket gap to minimum: **37**
- exact-bucket proxy rows: **143**
- exact-lane proxy rows: **367**
- supported neighbor rows: **0**
- reason: current live exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **regressed_under_minimum**
- support_progress.current_rows / minimum: **13 / 50**
- support_progress.previous_rows: **22**
- support_progress.delta_vs_previous: **-9**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_progress.reason: current live exact support 較上一輪回落，需檢查 current bucket / support artifact 是否切換或退化。

## Floor-cross legality
- verdict: **math_cross_possible_but_illegal_without_exact_support**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1574**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.5247**
- best_single_component_can_cross_floor: **True**
- reason: feat_4h_bias50 在數學上可單點補足 floor gap（需要 score Δ≈0.5247），但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。

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
- current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。

