# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 16:49:47.243439**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.5904**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 204 | 0.299 | -0.0334 | 0.2253 | 0.6406 | 10 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 27 | 0.5185 | 0.2177 | 0.1946 | 0.4247 | 10 | False |
| narrow `regime_label+entry_quality_label` | 157 | 0.1338 | -0.1522 | 0.2714 | 0.7601 | 10 | True |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7277 | 0.3816 | 0.2069 | 0.5619 | 12 | False |

## Shared shifts

- None
- worst_pathology_scope: **regime_label+entry_quality_label** rows=157 win_rate=0.1338 quality=-0.1522

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
