# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 12:53:13 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7224 | 0.1465 | 0.5810 | 0.2239 | 0.7643 | - | 0.4614 |
| core_plus_4h | 18 | 0.7056 | 0.1802 | 0.4742 | 0.2360 | 0.9333 | - | 0.7575 |
| core_plus_technical | 18 | 0.6975 | 0.1700 | 0.5198 | 0.2202 | 0.7905 | - | 0.6827 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6593 | 0.1978 | 0.4346 | 0.2636 | 0.7714 | - | 0.7960 |
| core_plus_macro | 10 | 0.6523 | 0.1866 | 0.4658 | 0.2600 | 0.9667 | - | 0.7785 |
| full_no_macro | 129 | 0.6483 | 0.1983 | 0.4382 | 0.2583 | 0.8476 | - | 0.6102 |
| core_macro_plus_stable_4h | 38 | 0.6483 | 0.1946 | 0.4334 | 0.2811 | 1.0000 | - | 0.8469 |
| core_plus_macro_plus_4h_trend | 22 | 0.6466 | 0.1908 | 0.4358 | 0.2594 | 0.9857 | - | 0.8141 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6466 | 0.1937 | 0.4298 | 0.2632 | 0.9810 | - | 0.8968 |
| full_no_technical | 121 | 0.6451 | 0.1987 | 0.4358 | 0.2746 | 0.8476 | - | 0.5698 |
| current_full_no_bull_collapse_4h | 119 | 0.6418 | 0.1954 | 0.4286 | 0.2613 | 0.9714 | - | 0.6948 |
| current_full | 131 | 0.6415 | 0.2054 | 0.4358 | 0.2747 | 0.8333 | - | 0.6035 |
| full_no_cross | 120 | 0.6353 | 0.2051 | 0.4262 | 0.2735 | 0.8071 | - | 0.5566 |
| core_plus_macro_plus_all_4h | 50 | 0.6315 | 0.1884 | 0.4310 | 0.2777 | 0.8167 | - | 0.6975 |
| full_no_4h | 121 | 0.6242 | 0.2271 | 0.3409 | 0.2658 | 0.8238 | - | 0.6610 |
| full_no_lags | 41 | 0.6221 | 0.2105 | 0.4358 | 0.2600 | 0.8976 | - | 0.7297 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
