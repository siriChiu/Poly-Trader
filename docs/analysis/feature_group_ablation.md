# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 06:30:02 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7239 | 0.1446 | 0.5798 | 0.2229 | 0.7214 | - | 0.4942 |
| core_plus_4h | 18 | 0.7092 | 0.1752 | 0.4946 | 0.2277 | 0.9476 | - | 0.7149 |
| core_plus_technical | 18 | 0.6898 | 0.1681 | 0.5198 | 0.2201 | 0.8024 | - | 0.5806 |
| current_full_no_bull_collapse_4h | 119 | 0.6756 | 0.1926 | 0.4262 | 0.2488 | 0.9667 | - | 0.7952 |
| core_plus_macro | 10 | 0.6598 | 0.1819 | 0.4694 | 0.2595 | 0.9690 | - | 0.8202 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6598 | 0.1915 | 0.4382 | 0.2595 | 0.7905 | - | 0.6995 |
| core_macro_plus_stable_4h | 38 | 0.6557 | 0.1893 | 0.4346 | 0.2700 | 1.0000 | - | 0.8500 |
| core_plus_macro_plus_4h_trend | 22 | 0.6535 | 0.1881 | 0.4394 | 0.2524 | 0.9833 | - | 0.7998 |
| full_no_macro | 129 | 0.6521 | 0.1974 | 0.4406 | 0.2523 | 0.8786 | - | 0.6146 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6499 | 0.1924 | 0.4334 | 0.2569 | 0.9929 | - | 0.9042 |
| full_no_technical | 121 | 0.6490 | 0.1976 | 0.4322 | 0.2660 | 0.8762 | - | 0.6683 |
| current_full | 131 | 0.6483 | 0.2001 | 0.4298 | 0.2625 | 0.8452 | - | 0.6491 |
| full_no_lags | 41 | 0.6437 | 0.1977 | 0.4394 | 0.2535 | 0.9119 | - | 0.7157 |
| full_no_cross | 120 | 0.6401 | 0.2075 | 0.4286 | 0.2682 | 0.8238 | - | 0.6392 |
| core_plus_macro_plus_all_4h | 50 | 0.6360 | 0.1962 | 0.4346 | 0.2729 | 0.8238 | - | 0.7136 |
| full_no_4h | 121 | 0.6295 | 0.2200 | 0.3758 | 0.2565 | 0.8286 | - | 0.7238 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
