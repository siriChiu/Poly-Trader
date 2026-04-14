# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 19:37:33.425841**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.4420**
- layers: **0 → 0**
- execution_guardrail_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 102 | 0.8725 | 0.576 | 0.0746 | 0.2487 | 85 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 102 | 0.8725 | 0.576 | 0.0746 | 0.2487 | 85 | False |
| narrow `regime_label+entry_quality_label` | 232 | 0.4138 | 0.1249 | 0.1938 | 0.5743 | 85 | False |
| broad `regime_gate+entry_quality_label` | 2809 | 0.7444 | 0.4007 | 0.1986 | 0.5506 | 87 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
