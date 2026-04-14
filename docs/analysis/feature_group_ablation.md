# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 16:26:45 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7453 | 0.1832 | 0.4538 | 0.2107 | 0.6857 | 0.4516 | 0.2949 |
| core_plus_macro | 10 | 0.6888 | 0.1676 | 0.4490 | 0.2323 | 0.9048 | 0.5484 | 0.3077 |
| core_plus_4h | 18 | 0.6550 | 0.1405 | 0.4550 | 0.2600 | 0.7476 | 0.4839 | 0.2564 |
| core_plus_technical | 18 | 0.6399 | 0.2089 | 0.3721 | 0.2542 | 0.8405 | 0.5806 | 0.2436 |
| full_no_technical | 121 | 0.5897 | 0.1485 | 0.3866 | 0.2942 | 0.9071 | 0.7097 | 0.3205 |
| core_macro_plus_stable_4h | 38 | 0.5748 | 0.1388 | 0.3854 | 0.3027 | 0.7452 | 0.4839 | 0.2308 |
| full_no_lags | 41 | 0.5705 | 0.1284 | 0.4190 | 0.2836 | 0.8476 | 0.5161 | 0.2564 |
| full_no_cross | 120 | 0.5666 | 0.1493 | 0.3866 | 0.2951 | 0.8500 | 0.6129 | 0.3205 |
| full_no_macro | 129 | 0.5647 | 0.1516 | 0.3866 | 0.2938 | 0.8643 | 0.6129 | 0.3077 |
| current_full | 131 | 0.5599 | 0.1474 | 0.3890 | 0.2954 | 0.8286 | 0.6129 | 0.3077 |
| full_no_4h | 121 | 0.5544 | 0.1390 | 0.3938 | 0.2939 | 0.9167 | 0.7097 | 0.3077 |
| current_full_no_bull_collapse_4h | 119 | 0.5325 | 0.1329 | 0.3878 | 0.3156 | 0.8262 | 0.7097 | 0.2949 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
