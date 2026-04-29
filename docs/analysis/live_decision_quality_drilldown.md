# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-29 07:14:23.032632**
- target: `simulated_pyramid_win`
- live path: **bear / CAUTION / C**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 22.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 22.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `insufficient_support_everywhere` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 22.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 11/50，至少還差 4 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['label_imbalance'] win_rate=0.18 avg_pnl=-0.0068 avg_quality=-0.1289 window=2026-04-26 00:23:53.820788->2026-04-28 08:00:00 adverse_streak=82x0 (2026-04-27 05:15:51.099763->2026-04-28 03:45:03.734300) vs sibling prev_win_rate=0.86 Δwin_rate=-0.68 prev_quality=0.4154 Δquality=-0.5443 prev_pnl=0.0067 Δpnl=-0.0135 top_shifts=feat_4h_dist_swing_low(0.7173→0.2234), feat_4h_dist_bb_lower(1.3153→0.9494), feat_4h_bb_pct_b(0.439→0.3152)。 exact-vs-spillover=同 quality 寬 scope 出現 chop|CAUTION spillover，5 rows / WR 20.0% / 品質 -0.012，明顯劣於 exact live lane WR — / 品質 —。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5617** / trade_floor **0.55** / gap **0.0117**
- base_quality: **0.6418** × weight **0.75**
- structure_quality: **0.3215** × weight **0.25**
- base components: feat_4h_bias50=0.5707 (w=0.4, contrib=0.2283), feat_nose=0.3209 (w=0.18, contrib=0.0578), feat_pulse=0.7986 (w=0.27, contrib=0.2156), feat_ear=0.9341 (w=0.15, contrib=0.1401)
- structure components: feat_4h_bb_pct_b=0.7137 (w=0.34, contrib=0.2426), feat_4h_dist_bb_lower=0.239 (w=0.33, contrib=0.0789), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2687** | structure_group_max_entry_gain: **0.1696**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate` | 236 | 0.5 | 0.1372 | 0.1579 | 0.5579 | 28 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 5 | 0.2 | -0.0116 | 0.1727 | 0.6695 | 0 | False |

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
