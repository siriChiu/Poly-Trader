# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-15 13:22:43.755638**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.2365**
- layers: **0 → 0**
- allowed_layers_reason: `entry_quality_below_trade_floor`
- execution_guardrail_reason: `None`
- runtime_blocker: `None` | reason: `None`

## Entry-quality component breakdown

- final entry_quality: **0.3944** / trade_floor **0.55** / gap **-0.1556**
- base_quality: **0.388** × weight **0.75**
- structure_quality: **0.4138** × weight **0.25**
- base components: feat_4h_bias50=0.2347 (w=0.4, contrib=0.0939), feat_nose=0.2716 (w=0.18, contrib=0.0489), feat_pulse=0.3644 (w=0.27, contrib=0.0984), feat_ear=0.9787 (w=0.15, contrib=0.1468)
- structure components: feat_4h_bb_pct_b=0.5235 (w=0.34, contrib=0.178), feat_4h_dist_bb_lower=0.2063 (w=0.33, contrib=0.0681), feat_4h_dist_swing_low=0.5084 (w=0.33, contrib=0.1678)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1556**
- base_group_max_entry_gain: **0.459** | structure_group_max_entry_gain: **0.1466**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.5187, max_gain≈0.2296）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.5187)
- bias50 fully relaxed: entry≈**0.624** / layers≈**1** / required_bias50_cap≈**-1.3665**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 53 | 0.8491 | 0.5502 | 0.0691 | 0.3674 | 53 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 53 | 0.8491 | 0.5502 | 0.0691 | 0.3674 | 53 | False |
| narrow `regime_label+entry_quality_label` | 176 | 0.9091 | 0.5974 | 0.0567 | 0.394 | 53 | False |
| broad `regime_gate+entry_quality_label` | 53 | 0.8491 | 0.5502 | 0.0691 | 0.3674 | 53 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
