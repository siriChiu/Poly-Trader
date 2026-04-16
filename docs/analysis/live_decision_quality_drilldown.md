# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-16 10:49:08.303092**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.6534**
- layers: **0 → 0**
- allowed_layers_reason: `entry_quality_below_trade_floor`
- execution_guardrail_reason: `unsupported_live_structure_bucket_blocks_trade; under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`

## Entry-quality component breakdown

- final entry_quality: **0.4227** / trade_floor **0.55** / gap **-0.1273**
- base_quality: **0.4896** × weight **0.75**
- structure_quality: **0.2218** × weight **0.25**
- base components: feat_4h_bias50=0.0364 (w=0.4, contrib=0.0145), feat_nose=0.7265 (w=0.18, contrib=0.1308), feat_pulse=0.7431 (w=0.27, contrib=0.2006), feat_ear=0.958 (w=0.15, contrib=0.1437)
- structure components: feat_4h_bb_pct_b=0.3974 (w=0.34, contrib=0.1351), feat_4h_dist_bb_lower=0.1552 (w=0.33, contrib=0.0512), feat_4h_dist_swing_low=0.1076 (w=0.33, contrib=0.0355)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1273**
- base_group_max_entry_gain: **0.3827** | structure_group_max_entry_gain: **0.1945**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.4243, max_gain≈0.2891）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.4243)
- bias50 fully relaxed: entry≈**0.6766** / layers≈**1** / required_bias50_cap≈**-0.49**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 191 | 0.911 | 0.4002 | 0.168 | 0.6723 | 4 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 191 | 0.911 | 0.4002 | 0.168 | 0.6723 | 4 | False |
| narrow `regime_label+entry_quality_label` | 200 | 0.88 | 0.38 | 0.173 | 0.6803 | 4 | False |
| broad `regime_gate+entry_quality_label` | 191 | 0.911 | 0.4002 | 0.168 | 0.6723 | 4 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
