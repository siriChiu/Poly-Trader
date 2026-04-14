# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 18:15:16.436018**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.3987**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 35 | 0.6286 | 0.3328 | 0.1511 | 0.3298 | 18 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 35 | 0.6286 | 0.3328 | 0.1511 | 0.3298 | 18 | False |
| narrow `regime_label+entry_quality_label` | 165 | 0.1758 | -0.1099 | 0.2584 | 0.7237 | 18 | True |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7277 | 0.3818 | 0.2067 | 0.5617 | 20 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
