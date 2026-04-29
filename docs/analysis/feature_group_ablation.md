# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-29 04:03:55 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.4955 | 0.0480 | 0.4474 | 0.2595 | 0.3088 | - | 0.0798 |
| core_plus_macro | 10 | 0.4895 | 0.0420 | 0.4474 | 0.2584 | 0.2941 | - | 0.1303 |
| current_full_no_bull_collapse_4h | 119 | 0.4685 | 0.0210 | 0.4474 | 0.2595 | 0.2059 | - | 0.3487 |
| current_full | 131 | 0.4670 | 0.0195 | 0.4474 | 0.2698 | 0.2353 | - | 0.3866 |
| core_macro_plus_stable_4h | 38 | 0.4625 | 0.0150 | 0.4474 | 0.2656 | 0.1176 | - | 0.1954 |
| core_plus_macro_plus_all_4h | 50 | 0.4354 | 0.0120 | 0.4234 | 0.2708 | 0.2059 | - | 0.1891 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
