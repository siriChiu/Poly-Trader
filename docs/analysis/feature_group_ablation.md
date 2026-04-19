# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 15:55:09 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7126 | 0.1616 | 0.5438 | 0.2285 | 0.7381 | - | 0.6053 |
| core_plus_technical | 18 | 0.6675 | 0.1819 | 0.4958 | 0.2330 | 0.7786 | - | 0.5889 |
| core_plus_macro_plus_4h_trend | 22 | 0.6627 | 0.2086 | 0.4022 | 0.2690 | 0.9738 | - | 0.7556 |
| core_plus_macro_plus_all_4h | 50 | 0.6538 | 0.1999 | 0.3998 | 0.2849 | 0.8381 | - | 0.6650 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6531 | 0.1978 | 0.4010 | 0.2721 | 0.7738 | - | 0.7364 |
| current_full_no_bull_collapse_4h | 119 | 0.6468 | 0.2082 | 0.4034 | 0.2776 | 0.9619 | - | 0.7761 |
| full_no_macro | 129 | 0.6442 | 0.1995 | 0.3974 | 0.2794 | 0.8595 | - | 0.6776 |
| core_plus_macro | 10 | 0.6399 | 0.1963 | 0.4322 | 0.2721 | 0.9476 | - | 0.7872 |
| full_no_4h | 121 | 0.6391 | 0.2016 | 0.4046 | 0.2793 | 0.7881 | - | 0.6431 |
| core_plus_4h | 18 | 0.6355 | 0.1992 | 0.4250 | 0.2567 | 0.9429 | - | 0.7096 |
| current_full | 131 | 0.6348 | 0.2039 | 0.3926 | 0.2931 | 0.7905 | - | 0.5647 |
| full_no_technical | 121 | 0.6343 | 0.2031 | 0.3998 | 0.2904 | 0.8619 | - | 0.7103 |
| full_no_cross | 120 | 0.6334 | 0.2038 | 0.3974 | 0.2858 | 0.8452 | - | 0.6401 |
| core_plus_macro_plus_4h_momentum | 22 | 0.6264 | 0.2106 | 0.3998 | 0.2818 | 0.9738 | - | 0.8447 |
| core_macro_plus_stable_4h | 38 | 0.6250 | 0.2130 | 0.4058 | 0.2902 | 0.9714 | - | 0.7789 |
| full_no_lags | 41 | 0.6010 | 0.2231 | 0.4022 | 0.2834 | 0.9071 | - | 0.6895 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
