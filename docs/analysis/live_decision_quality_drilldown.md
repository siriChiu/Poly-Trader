# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-18 16:33:30.024994**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 77 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 77 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 77 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`

## Entry-quality component breakdown

- final entry_quality: **0.3434** / trade_floor **0.55** / gap **-0.2066**
- base_quality: **0.3762** × weight **0.75**
- structure_quality: **0.2451** × weight **0.25**
- base components: feat_4h_bias50=0.0 (w=0.4, contrib=0.0), feat_nose=0.621 (w=0.18, contrib=0.1118), feat_pulse=0.447 (w=0.27, contrib=0.1207), feat_ear=0.9581 (w=0.15, contrib=0.1437)
- structure components: feat_4h_bb_pct_b=0.2797 (w=0.34, contrib=0.0951), feat_4h_dist_bb_lower=0.1003 (w=0.33, contrib=0.0331), feat_4h_dist_swing_low=0.3543 (w=0.33, contrib=0.1169)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.2066**
- base_group_max_entry_gain: **0.4679** | structure_group_max_entry_gain: **0.1887**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.6887, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.6887)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 128 | 0.6797 | 0.4019 | 0.1166 | 0.3503 | 69 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 128 | 0.6797 | 0.4019 | 0.1166 | 0.3503 | 69 | False |
| narrow `regime_label+entry_quality_label` | 196 | 0.4439 | 0.1676 | 0.2013 | 0.4743 | 69 | False |
| broad `regime_gate+entry_quality_label` | 132 | 0.6894 | 0.4101 | 0.1147 | 0.344 | 69 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
