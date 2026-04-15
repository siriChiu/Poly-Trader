# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-15 17:35:54.349131**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.3486**
- layers: **0 → 0**
- allowed_layers_reason: `entry_quality_below_trade_floor`
- execution_guardrail_reason: `None`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `None` | reason: `None`

## Entry-quality component breakdown

- final entry_quality: **0.4115** / trade_floor **0.55** / gap **-0.1385**
- base_quality: **0.4167** × weight **0.75**
- structure_quality: **0.3958** × weight **0.25**
- base components: feat_4h_bias50=0.2346 (w=0.4, contrib=0.0938), feat_nose=0.4038 (w=0.18, contrib=0.0727), feat_pulse=0.3863 (w=0.27, contrib=0.1043), feat_ear=0.9724 (w=0.15, contrib=0.1459)
- structure components: feat_4h_bb_pct_b=0.4993 (w=0.34, contrib=0.1698), feat_4h_dist_bb_lower=0.1976 (w=0.33, contrib=0.0652), feat_4h_dist_swing_low=0.4874 (w=0.33, contrib=0.1609)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1385**
- base_group_max_entry_gain: **0.4375** | structure_group_max_entry_gain: **0.1511**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.4617, max_gain≈0.2296）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.4617)
- bias50 fully relaxed: entry≈**0.6411** / layers≈**1** / required_bias50_cap≈**-1.0815**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 50 | 0.7 | 0.4041 | 0.1035 | 0.4525 | 50 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 50 | 0.7 | 0.4041 | 0.1035 | 0.4525 | 50 | False |
| narrow `regime_label+entry_quality_label` | 176 | 0.8523 | 0.5423 | 0.0714 | 0.4285 | 50 | False |
| broad `regime_gate+entry_quality_label` | 50 | 0.7 | 0.4041 | 0.1035 | 0.4525 | 50 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
