# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-16 20:18:23.397928**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **HOLD** @ confidence **0.2449**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`

## Entry-quality component breakdown

- final entry_quality: **0.5717** / trade_floor **0.55** / gap **0.0217**
- base_quality: **0.6304** × weight **0.75**
- structure_quality: **0.3953** × weight **0.25**
- base components: feat_4h_bias50=0.1978 (w=0.0, contrib=0.0), feat_nose=0.1768 (w=0.0, contrib=0.0), feat_pulse=0.3006 (w=0.5, contrib=0.1503), feat_ear=0.9603 (w=0.5, contrib=0.4802)
- structure components: feat_4h_bb_pct_b=0.6724 (w=0.34, contrib=0.2286), feat_4h_dist_bb_lower=0.2662 (w=0.33, contrib=0.0878), feat_4h_dist_swing_low=0.239 (w=0.33, contrib=0.0789)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2772** | structure_group_max_entry_gain: **0.1511**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.5916** / layers≈**1** / required_bias50_cap≈**-1.9065**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 200 | 0.88 | 0.38 | 0.173 | 0.6803 | 187 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 1 | 1.0 | 0.4441 | 0.1883 | 0.7917 | 1 | False |
| narrow `regime_label+entry_quality_label` | 1 | 1.0 | 0.4441 | 0.1883 | 0.7917 | 1 | False |
| broad `regime_gate+entry_quality_label` | 1 | 1.0 | 0.4441 | 0.1883 | 0.7917 | 1 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
