# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-18 19:24:58.625590**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 137 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 137 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 137 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0104 avg_quality=-0.2824 window=2026-04-17 14:27:52.171389->2026-04-17 19:48:03.281485 adverse_streak=100x0 (2026-04-17 14:27:52.171389->2026-04-17 19:48:03.281485) vs sibling prev_win_rate=0.6263 Δwin_rate=-0.6263 prev_quality=0.3313 Δquality=-0.6137 prev_pnl=0.0084 Δpnl=-0.0188 top_shifts=feat_4h_dist_swing_low(3.2046→5.4074), feat_4h_dist_bb_lower(2.5591→3.8945), feat_4h_bb_pct_b(0.7837→1.1228)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`

## Entry-quality component breakdown

- final entry_quality: **0.3867** / trade_floor **0.55** / gap **-0.1633**
- base_quality: **0.4587** × weight **0.75**
- structure_quality: **0.1709** × weight **0.25**
- base components: feat_4h_bias50=0.0244 (w=0.4, contrib=0.0098), feat_nose=0.5907 (w=0.18, contrib=0.1063), feat_pulse=0.7142 (w=0.27, contrib=0.1928), feat_ear=0.9982 (w=0.15, contrib=0.1497)
- structure components: feat_4h_bb_pct_b=0.1497 (w=0.34, contrib=0.0509), feat_4h_dist_bb_lower=0.0543 (w=0.33, contrib=0.0179), feat_4h_dist_swing_low=0.3094 (w=0.33, contrib=0.1021)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1633**
- base_group_max_entry_gain: **0.4061** | structure_group_max_entry_gain: **0.2073**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.5443, max_gain≈0.2927）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.5443)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 199 | 0.3116 | 0.0229 | 0.2597 | 0.524 | 41 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 41 | 1.0 | 0.697 | 0.0237 | 0.2347 | 41 | False |
| narrow `regime_label+entry_quality_label` | 199 | 0.3116 | 0.0229 | 0.2597 | 0.524 | 41 | True |
| broad `regime_gate+entry_quality_label` | 41 | 1.0 | 0.697 | 0.0237 | 0.2347 | 41 | False |

## Shared shifts

- feat_4h_dist_swing_low (x2), feat_4h_dist_bb_lower (x2), feat_4h_bb_pct_b (x2)
- worst_pathology_scope: **regime_label+entry_quality_label** rows=199 win_rate=0.3116 quality=0.0229

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
