# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-16 23:00:23.100224**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.3470**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `entry_quality_below_trade_floor`
- execution_guardrail_reason: `None`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `None` | reason: `None`

## Entry-quality component breakdown

- final entry_quality: **0.3238** / trade_floor **0.55** / gap **-0.2262**
- base_quality: **0.3318** × weight **0.75**
- structure_quality: **0.2999** × weight **0.25**
- base components: feat_4h_bias50=0.0 (w=0.4, contrib=0.0), feat_nose=0.3893 (w=0.18, contrib=0.0701), feat_pulse=0.4451 (w=0.27, contrib=0.1202), feat_ear=0.9439 (w=0.15, contrib=0.1416)
- structure components: feat_4h_bb_pct_b=0.5099 (w=0.34, contrib=0.1734), feat_4h_dist_bb_lower=0.206 (w=0.33, contrib=0.068), feat_4h_dist_swing_low=0.1773 (w=0.33, contrib=0.0585)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.2262**
- base_group_max_entry_gain: **0.5011** | structure_group_max_entry_gain: **0.1751**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.754, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.754)
- bias50 fully relaxed: entry≈**0.5916** / layers≈**1** / required_bias50_cap≈**-1.9065**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 200 | 0.91 | 0.4151 | 0.1069 | 0.2458 | 77 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 200 | 0.91 | 0.4151 | 0.1069 | 0.2458 | 77 | False |
| narrow `regime_label+entry_quality_label` | 200 | 0.91 | 0.4151 | 0.1069 | 0.2458 | 77 | False |
| broad `regime_gate+entry_quality_label` | 200 | 0.91 | 0.4151 | 0.1069 | 0.2458 | 77 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
