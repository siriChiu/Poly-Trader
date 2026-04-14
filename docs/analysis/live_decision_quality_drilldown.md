# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 19:07:57.762244**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.1831**
- layers: **0 → 0**
- execution_guardrail_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 78 | 0.8333 | 0.5429 | 0.0878 | 0.2384 | 61 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 78 | 0.8333 | 0.5429 | 0.0878 | 0.2384 | 61 | False |
| narrow `regime_label+entry_quality_label` | 208 | 0.3462 | 0.0605 | 0.2125 | 0.608 | 61 | False |
| broad `regime_gate+entry_quality_label` | 2785 | 0.7422 | 0.3983 | 0.2 | 0.553 | 63 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
