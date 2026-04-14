# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 18:40:28.725618**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.3309**
- layers: **0 → 0**
- execution_guardrail_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 59 | 0.7797 | 0.4908 | 0.093 | 0.2217 | 42 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 59 | 0.7797 | 0.4908 | 0.093 | 0.2217 | 42 | False |
| narrow `regime_label+entry_quality_label` | 189 | 0.2804 | -0.0043 | 0.2267 | 0.64 | 42 | False |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7356 | 0.3903 | 0.2037 | 0.557 | 44 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
