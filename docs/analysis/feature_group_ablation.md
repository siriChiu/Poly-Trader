# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 16:26:17 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7085 | 0.1756 | 0.5174 | 0.2322 | 0.7048 | - | 0.6366 |
| core_plus_macro_plus_4h_trend | 22 | 0.6559 | 0.2261 | 0.3661 | 0.2776 | 0.9690 | - | 0.6771 |
| core_plus_technical | 18 | 0.6543 | 0.1886 | 0.4574 | 0.2471 | 0.8119 | - | 0.5747 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6401 | 0.2060 | 0.3758 | 0.2820 | 0.8119 | - | 0.7142 |
| core_plus_macro_plus_all_4h | 50 | 0.6389 | 0.2103 | 0.3794 | 0.2944 | 0.8929 | - | 0.7072 |
| full_no_4h | 121 | 0.6288 | 0.2108 | 0.3673 | 0.2980 | 0.8048 | - | 0.6823 |
| current_full_no_bull_collapse_4h | 119 | 0.6286 | 0.2233 | 0.3625 | 0.2948 | 0.9905 | - | 0.8308 |
| full_no_macro | 129 | 0.6262 | 0.2125 | 0.3613 | 0.2938 | 0.9048 | - | 0.6885 |
| full_no_cross | 120 | 0.6223 | 0.2145 | 0.3625 | 0.3071 | 0.8976 | - | 0.7192 |
| current_full | 131 | 0.6209 | 0.2151 | 0.3613 | 0.3057 | 0.8952 | - | 0.7739 |
| full_no_technical | 121 | 0.6204 | 0.2149 | 0.3637 | 0.3063 | 0.9238 | - | 0.7980 |
| core_plus_macro | 10 | 0.6185 | 0.2110 | 0.3962 | 0.2856 | 0.9643 | - | 0.7578 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6166 | 0.2167 | 0.3794 | 0.2921 | 0.9714 | - | 0.8493 |
| core_plus_4h | 18 | 0.6139 | 0.2209 | 0.3890 | 0.2654 | 0.9357 | - | 0.7187 |
| core_macro_plus_stable_4h | 38 | 0.6113 | 0.2256 | 0.3733 | 0.3032 | 0.9833 | - | 0.7641 |
| full_no_lags | 41 | 0.5784 | 0.2402 | 0.3613 | 0.2968 | 0.9119 | - | 0.6633 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
