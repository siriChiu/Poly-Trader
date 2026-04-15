# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-15 05:30:42.391751**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.5498**
- layers: **0 → 0**
- allowed_layers_reason: `entry_quality_below_trade_floor`
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket_blocks_trade`

## Entry-quality component breakdown

- final entry_quality: **0.4658** / trade_floor **0.55** / gap **-0.0842**
- base_quality: **0.5085** × weight **0.75**
- structure_quality: **0.3379** × weight **0.25**
- base components: feat_4h_bias50=0.0 (w=0.4, contrib=0.0), feat_nose=0.8159 (w=0.18, contrib=0.1469), feat_pulse=0.7969 (w=0.27, contrib=0.2151), feat_ear=0.9766 (w=0.15, contrib=0.1465)
- structure components: feat_4h_bb_pct_b=0.3836 (w=0.34, contrib=0.1304), feat_4h_dist_bb_lower=0.1529 (w=0.33, contrib=0.0505), feat_4h_dist_swing_low=0.4758 (w=0.33, contrib=0.157)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0842**
- base_group_max_entry_gain: **0.3686** | structure_group_max_entry_gain: **0.1655**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.2807, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.2807)
- bias50 fully relaxed: entry≈**0.7807** / layers≈**2** / required_bias50_cap≈**1.245**

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 197 | 0.9848 | 0.6714 | 0.0379 | 0.3045 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 82 | 1.0 | 0.7018 | 0.0321 | 0.1943 | 0 | False |
| narrow `regime_label+entry_quality_label` | 197 | 0.9848 | 0.6714 | 0.0379 | 0.3045 | 0 | False |
| broad `regime_gate+entry_quality_label` | 82 | 1.0 | 0.7018 | 0.0321 | 0.1943 | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
