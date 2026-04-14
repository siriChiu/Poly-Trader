# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 17:17:41.888930**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.5604**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 205 | 0.3024 | -0.0297 | 0.2242 | 0.6375 | 11 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 28 | 0.5357 | 0.2363 | 0.1877 | 0.4095 | 11 | False |
| narrow `regime_label+entry_quality_label` | 158 | 0.1392 | -0.1466 | 0.2697 | 0.7553 | 11 | True |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7277 | 0.3816 | 0.2069 | 0.5619 | 13 | False |

## Shared shifts

- None
- worst_pathology_scope: **regime_label+entry_quality_label** rows=158 win_rate=0.1392 quality=-0.1466

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
