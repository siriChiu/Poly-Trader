# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-14 16:25:16.529217**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **HOLD** @ confidence **0.6694**
- layers: **0 → 0**
- execution_guardrail_reason: `decision_quality_below_trade_floor`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 203 | 0.2956 | -0.0371 | 0.226 | 0.6433 | 9 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 26 | 0.5 | 0.1985 | 0.1991 | 0.4373 | 9 | False |
| narrow `regime_label+entry_quality_label` | 156 | 0.1282 | -0.1578 | 0.2726 | 0.7644 | 9 | True |
| broad `regime_gate+entry_quality_label` | 2784 | 0.7277 | 0.3816 | 0.2069 | 0.562 | 11 | False |

## Shared shifts

- None
- worst_pathology_scope: **regime_label+entry_quality_label** rows=156 win_rate=0.1282 quality=-0.1578

## Interpretation

- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
