# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 07:49:01.325711**
- target: `simulated_pyramid_win`
- live path: **bull / ALLOW / D**
- signal: **HOLD** @ confidence **0.6996**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 194 | 0.2629 | -0.071 | 0.2319 | 0.6677 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 14 | 0.5 | 0.2412 | 0.2041 | 0.4575 | 0 | False |
| narrow `regime_label+entry_quality_label` | 147 | 0.0748 | -0.2098 | 0.2833 | 0.804 | 0 | True |
| broad `regime_gate+entry_quality_label` | 115 | 0.2348 | -0.0575 | 0.3297 | 0.7464 | 66 | True |

## Shared shifts

- feat_4h_dist_swing_low (x2), feat_4h_dist_bb_lower (x2), feat_4h_bb_pct_b (x2)
- worst_pathology_scope: **regime_label+entry_quality_label** rows=147 win_rate=0.0748 quality=-0.2098

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
