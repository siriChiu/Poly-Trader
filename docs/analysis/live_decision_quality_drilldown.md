# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-19 01:29:25.283211**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 240 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 240 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_missing_exact_lane_proxy_only` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 240 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0095 avg_quality=-0.2874 window=2026-04-17 19:51:05.267699->2026-04-18 02:00:00 adverse_streak=100x0 (2026-04-17 19:51:05.267699->2026-04-18 02:00:00) vs sibling prev_win_rate=0.0 Δwin_rate=0.0 prev_quality=-0.2835 Δquality=-0.0039 prev_pnl=-0.0105 Δpnl=0.001 top_shifts=feat_4h_dist_bb_lower(3.8585→3.011), feat_4h_bb_pct_b(1.1116→0.8936), feat_4h_dist_swing_low(5.3939→5.2286)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.3948** / trade_floor **0.55** / gap **-0.1552**
- base_quality: **0.4538** × weight **0.75**
- structure_quality: **0.2178** × weight **0.25**
- base components: feat_4h_bias50=0.0835 (w=0.4, contrib=0.0334), feat_nose=0.6334 (w=0.18, contrib=0.114), feat_pulse=0.5857 (w=0.27, contrib=0.1581), feat_ear=0.9885 (w=0.15, contrib=0.1483)
- structure components: feat_4h_bb_pct_b=0.2614 (w=0.34, contrib=0.0889), feat_4h_dist_bb_lower=0.0947 (w=0.33, contrib=0.0313), feat_4h_dist_swing_low=0.2958 (w=0.33, contrib=0.0976)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1552**
- base_group_max_entry_gain: **0.4097** | structure_group_max_entry_gain: **0.1956**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.5173, max_gain≈0.275）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.5173)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 200 | 0.0 | -0.2854 | 0.3787 | 0.845 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **entry_quality_label** rows=199 win_rate=0.0 quality=-0.2853

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
