# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-17 03:01:35 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.4249 | 0.0856 | 0.3393 | 0.2886 | 0.6324 | 0.7619 | 0.5000 |
| current_full_no_bull_collapse_4h | 119 | 0.4219 | 0.0405 | 0.3814 | 0.3067 | 0.5441 | 1.0000 | 0.5000 |
| core_plus_macro_plus_all_4h | 50 | 0.4144 | 0.0781 | 0.3363 | 0.3069 | 0.1029 | 0.5556 | 0.0000 |
| core_macro_plus_stable_4h | 38 | 0.4099 | 0.0826 | 0.3273 | 0.3054 | 0.0735 | 0.7778 | 0.0000 |
| core_only | 8 | 0.3904 | 0.0511 | 0.3393 | 0.2875 | 0.5588 | 0.8333 | 0.5000 |
| current_full | 131 | 0.3814 | 0.0390 | 0.3423 | 0.3058 | 0.3235 | 0.4603 | 0.0000 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
