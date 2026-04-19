# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-19 17:38:24 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.6922 | 0.2230 | 0.4370 | 0.2421 | 0.7286 | - | 0.6804 |
| core_plus_macro_plus_all_4h | 50 | 0.6226 | 0.2419 | 0.3313 | 0.3119 | 0.8095 | - | 0.6862 |
| core_plus_macro_plus_4h_trend | 22 | 0.6106 | 0.2586 | 0.2845 | 0.3131 | 0.8667 | - | 0.6585 |
| core_plus_technical | 18 | 0.6062 | 0.2203 | 0.3685 | 0.2730 | 0.8095 | - | 0.4653 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.5971 | 0.2321 | 0.3265 | 0.3122 | 0.8643 | - | 0.7143 |
| core_plus_4h | 18 | 0.5921 | 0.2452 | 0.3037 | 0.2884 | 0.8286 | - | 0.6018 |
| core_macro_plus_stable_4h | 38 | 0.5914 | 0.2570 | 0.2977 | 0.3227 | 0.9048 | - | 0.7489 |
| full_no_technical | 121 | 0.5839 | 0.2402 | 0.3109 | 0.3418 | 0.8476 | - | 0.6459 |
| full_no_macro | 129 | 0.5777 | 0.2422 | 0.3097 | 0.3393 | 0.8310 | - | 0.6531 |
| core_plus_macro | 10 | 0.5767 | 0.2431 | 0.3109 | 0.3204 | 0.9643 | - | 0.6694 |
| current_full | 131 | 0.5758 | 0.2433 | 0.3073 | 0.3430 | 0.8548 | - | 0.6555 |
| full_no_4h | 121 | 0.5729 | 0.2484 | 0.2857 | 0.3402 | 0.8452 | - | 0.6983 |
| full_no_cross | 120 | 0.5676 | 0.2480 | 0.3061 | 0.3388 | 0.8548 | - | 0.7031 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5676 | 0.2469 | 0.3349 | 0.3085 | 0.8857 | - | 0.7785 |
| current_full_no_bull_collapse_4h | 119 | 0.5534 | 0.2604 | 0.2737 | 0.3421 | 0.8976 | - | 0.7392 |
| full_no_lags | 41 | 0.5400 | 0.2735 | 0.2737 | 0.3257 | 0.8214 | - | 0.6633 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
