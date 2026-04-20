# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-20 05:52:01.160266**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / C**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 6.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 6.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 6.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 3/50，至少還差 12 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['label_imbalance'] win_rate=0.03 avg_pnl=-0.0083 avg_quality=-0.2138 window=2026-04-18 18:20:32.847127->2026-04-19 06:47:15.452349 adverse_streak=76x0 (2026-04-18 18:20:32.847127->2026-04-19 01:10:17.732530) vs sibling prev_win_rate=0.0 Δwin_rate=0.03 prev_quality=-0.1898 Δquality=-0.024 prev_pnl=-0.0045 Δpnl=-0.0038 top_shifts=feat_4h_dist_swing_low(3.3696→3.1017), feat_4h_dist_bb_lower(0.6589→0.6405), feat_4h_bb_pct_b(0.229→0.221)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.552** / trade_floor **0.55** / gap **0.002**
- base_quality: **0.6847** × weight **0.75**
- structure_quality: **0.1541** × weight **0.25**
- base components: feat_4h_bias50=0.511 (w=0.4, contrib=0.2044), feat_nose=0.7634 (w=0.18, contrib=0.1374), feat_pulse=0.7224 (w=0.27, contrib=0.195), feat_ear=0.9855 (w=0.15, contrib=0.1478)
- structure components: feat_4h_bb_pct_b=0.2418 (w=0.34, contrib=0.0822), feat_4h_dist_bb_lower=0.0944 (w=0.33, contrib=0.0312), feat_4h_dist_swing_low=0.1234 (w=0.33, contrib=0.0407)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2364** | structure_group_max_entry_gain: **0.2114**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 200 | 0.015 | -0.2018 | 0.2481 | 0.7886 | 14 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

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
