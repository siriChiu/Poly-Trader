# q15 Support Audit

- generated_at: **2026-04-28 04:22:37.884908**
- target_col: **simulated_pyramid_win**
- artifact_context_freshness: **current_context** (`[]`)

## Current live row
- signal: **CIRCUIT_BREAKER**
- regime / gate / label: **chop / CAUTION / D**
- current_live_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- current_live_structure_bucket_rows: **0**
- allowed_layers: **0** (unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active)
- execution_guardrail_reason: **unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active**

## Scope applicability
- status: **current_live_not_q15_lane**
- active_for_current_live_row: **False**
- current_structure_bucket: **CAUTION|base_caution_regime_or_bias|q00**
- target_structure_bucket: **CAUTION|structure_quality_caution|q15**
- reason: current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。

## Support route verdict
- support_governance_route: **exact_live_lane_proxy_available**
- verdict: **insufficient_support_everywhere**
- deployable: **False**
- governance_reference_only: **True**
- preferred_support_cohort: **None**
- current bucket gap to minimum: **50**
- exact-bucket proxy rows: **0**
- exact-lane proxy rows: **9**
- supported neighbor rows: **0**
- reason: current live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。
- release_condition: 先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。
- support_progress.status: **stalled_under_minimum**
- support_progress.regression_basis: **same_identity_same_semantic_signature**
- support_progress.current_rows / minimum: **0 / 50**
- support_progress.previous_rows: **0**
- support_progress.delta_vs_previous: **0**
- support_progress.stagnant_run_count: **3**
- support_progress.escalate_to_blocker: **True**
- support_identity: `{'target_col': 'simulated_pyramid_win', 'horizon_minutes': 1440, 'current_live_structure_bucket': 'CAUTION|base_caution_regime_or_bias|q00', 'regime_label': 'chop', 'regime_gate': 'CAUTION', 'entry_quality_label': 'D', 'calibration_window': 400, 'bucket_semantic_signature': 'live_structure_bucket:q15_support_identity:v2'}`
- legacy_supported_reference: `None`
- support_progress.reason: current live exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。

## Floor-cross legality
- verdict: **runtime_blocker_preempts_floor_analysis**
- legal_to_relax_runtime_gate: **False**
- remaining_gap_to_floor: **0.0749**
- best_single_component: **feat_4h_bias50**
- best_single_component_required_score_delta: **0.2497**
- best_single_component_can_cross_floor: **True**
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 26.00% < 30%），不能把 q15 floor-cross 當成當前 deploy 入口。

## Exact-supported component experiment
- verdict: **runtime_blocker_preempts_component_experiment**
- feature: **feat_4h_bias50**
- mode: **None**
- support_ready: **False**
- entry_quality_ge_0_55: **False**
- allowed_layers_gt_0: **False**
- preserves_positive_discrimination: **None** (not_measured_runtime_blocked)
- reason: 目前先被 runtime blocker 擋下（Recent 50-sample win rate: 26.00% < 30%），q15 component experiment 只能保留為背景研究。
- verify_next: 先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。

## Next action
- current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。

