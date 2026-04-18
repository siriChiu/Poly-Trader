# q15 Support Audit

- generated_at: **2026-04-18 22:45:46.849432**
- target_col: **simulated_pyramid_win**

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **bull / BLOCK / D**
- current_live_structure_bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_q15_lane_active**
- active_for_current_live_row: **True**
- current_structure_bucket: **BLOCK|bull_q15_bias50_overextended_block|q15**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。

## Support route verdict
- support_governance_route: **exact_live_lane_proxy_available**
- verdict: **exact_bucket_missing_exact_lane_proxy_only**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **bull_exact_live_lane_proxy**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **106**
- supported neighbor rows: **0**
- reason: current q15 exact bucket 缺樣本，只剩 same-lane proxy；這仍不足以解除 runtime blocker。
- release_condition: 必須先生成 current q15 exact bucket 真樣本，proxy 不可直接轉成 deployment allowance。
- support_progress.status: **no_recent_comparable_history**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **None**
- support_progress.delta_vs_previous: **None**
- support_progress.stagnant_run_count: **0**
- support_progress.escalate_to_blocker: **False**
- support_progress.reason: 目前找不到同一 q15 bucket 的最近 heartbeat 可比較；先持續累積 exact support。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.2119**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.7063**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 237 >= 50; Recent 50-sample win rate: 0.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Consecutive loss streak: 237 >= 50; Recent 50-sample win rate: 0.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Next action
- 先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。

