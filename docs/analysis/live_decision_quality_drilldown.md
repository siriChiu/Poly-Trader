# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-15 16:49:37.984252**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **HOLD** @ confidence **0.4069**
- layers: **1 → 1**
- allowed_layers_reason: `entry_quality_C_single_layer`
- execution_guardrail_reason: `None`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `None` | reason: `None`

## Entry-quality component breakdown

- final entry_quality: **0.5667** / trade_floor **0.55** / gap **0.0167**
- base_quality: **0.6367** × weight **0.75**
- structure_quality: **0.3569** × weight **0.25**
- base components: feat_4h_bias50=0.0319 (w=0.0, contrib=0.0), feat_nose=0.466 (w=0.0, contrib=0.0), feat_pulse=0.2016 (w=0.45, contrib=0.0907), feat_ear=0.9926 (w=0.55, contrib=0.5459)
- structure components: feat_4h_bb_pct_b=0.4341 (w=0.34, contrib=0.1476), feat_4h_dist_bb_lower=0.1708 (w=0.33, contrib=0.0564), feat_4h_dist_swing_low=0.4636 (w=0.33, contrib=0.153)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2726** | structure_group_max_entry_gain: **0.1608**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.6047** / layers≈**1** / required_bias50_cap≈**-1.6895**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 200 | 0.875 | 0.565 | 0.064 | 0.398 | 72 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 23 | 1.0 | 0.6936 | 0.018 | 0.1894 | 23 | False |
| narrow `regime_label+entry_quality_label` | 25 | 1.0 | 0.6961 | 0.0177 | 0.1798 | 23 | False |
| broad `regime_gate+entry_quality_label` | 23 | 1.0 | 0.6936 | 0.018 | 0.1894 | 23 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
