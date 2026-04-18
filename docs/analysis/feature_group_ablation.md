# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-18 20:15:38 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7318 | 0.1380 | 0.6026 | 0.2189 | 0.7357 | - | 0.5314 |
| core_plus_technical | 18 | 0.6903 | 0.1627 | 0.5462 | 0.2190 | 0.8167 | - | 0.5560 |
| core_plus_4h | 18 | 0.6886 | 0.1649 | 0.5222 | 0.2251 | 0.9738 | - | 0.7054 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6778 | 0.1948 | 0.4610 | 0.2465 | 0.8357 | - | 0.6851 |
| core_plus_macro_plus_4h_trend | 22 | 0.6756 | 0.1768 | 0.4622 | 0.2437 | 0.9619 | - | 0.7392 |
| current_full_no_bull_collapse_4h | 119 | 0.6732 | 0.1813 | 0.4658 | 0.2405 | 0.9690 | - | 0.7576 |
| core_plus_macro | 10 | 0.6723 | 0.1731 | 0.4922 | 0.2470 | 0.9690 | - | 0.8722 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6694 | 0.1807 | 0.4610 | 0.2468 | 0.9690 | - | 0.9687 |
| core_macro_plus_stable_4h | 38 | 0.6636 | 0.1822 | 0.4610 | 0.2572 | 0.9738 | - | 0.8513 |
| full_no_macro | 129 | 0.6595 | 0.1976 | 0.4562 | 0.2419 | 0.8524 | - | 0.6808 |
| full_no_cross | 120 | 0.6583 | 0.1984 | 0.4538 | 0.2554 | 0.8524 | - | 0.6463 |
| full_no_technical | 121 | 0.6576 | 0.1964 | 0.4610 | 0.2538 | 0.8619 | - | 0.6873 |
| current_full | 131 | 0.6574 | 0.1988 | 0.4562 | 0.2545 | 0.8548 | - | 0.6832 |
| full_no_lags | 41 | 0.6555 | 0.1895 | 0.4622 | 0.2461 | 0.9048 | - | 0.7025 |
| core_plus_macro_plus_all_4h | 50 | 0.6552 | 0.1887 | 0.4610 | 0.2612 | 0.8571 | - | 0.7023 |
| full_no_4h | 121 | 0.6466 | 0.2154 | 0.3794 | 0.2447 | 0.8167 | - | 0.7097 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
