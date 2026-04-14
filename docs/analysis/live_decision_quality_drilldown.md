# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 17:44:59.970970**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.3044**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 30 | 0.5667 | 0.2694 | 0.1752 | 0.3822 | 13 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 30 | 0.5667 | 0.2694 | 0.1752 | 0.3822 | 13 | False |
| narrow `regime_label+entry_quality_label` | 160 | 0.15 | -0.1356 | 0.2663 | 0.7459 | 13 | True |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7277 | 0.3816 | 0.2068 | 0.5619 | 15 | False |

## Shared shifts

- None
- worst_pathology_scope: **regime_label+entry_quality_label** rows=160 win_rate=0.15 quality=-0.1356

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
