# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-25 06:26:34 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.6577 | 0.1922 | 0.4655 | 0.2449 | 0.7206 | 0.7292 | - |
| core_macro_plus_stable_4h | 38 | 0.6246 | 0.1592 | 0.4655 | 0.2488 | 0.8088 | 0.7708 | - |
| core_plus_macro | 10 | 0.6231 | 0.1577 | 0.4655 | 0.2567 | 0.6029 | 0.6979 | - |
| current_full | 131 | 0.5796 | 0.1141 | 0.4655 | 0.2538 | 0.8088 | 0.7917 | - |
| current_full_no_bull_collapse_4h | 119 | 0.5766 | 0.1111 | 0.4655 | 0.2527 | 0.9118 | 0.9167 | - |
| core_only | 8 | 0.5060 | 0.0405 | 0.4655 | 0.2582 | 0.5882 | 0.6979 | - |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
