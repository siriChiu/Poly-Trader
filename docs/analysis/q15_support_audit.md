# q15 Support Audit

- generated_at: **2026-04-19 03:51:42.255204**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bull / BLOCK / D**
- current_live_structure_bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- current_live_structure_bucket_rows: **1**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_bucket_present_but_below_minimum**
- verdict: **exact_bucket_present_but_below_minimum**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **49**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **348**
- supported neighbor rows: **242**
- reason: current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。
- release_condition: exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。
- support_progress.status: **stalled_under_minimum**
- support_progress.current_rows / minimum: **1 / 50**
- support_progress.previous_rows: **1**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **5**
- support_progress.escalate_to_blocker: **True**
- support_progress.reason: current q15 exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.1457**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.4857**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 245 >= 50; Recent 50-sample win rate: 0.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 245 >= 50; Recent 50-sample win rate: 0.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

