# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-25 13:31:33 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro_plus_all_4h | 50 | 0.6426 | 0.1682 | 0.4745 | 0.2595 | 0.7353 | 0.6295 | - |
| core_macro_plus_stable_4h | 38 | 0.6396 | 0.1652 | 0.4745 | 0.2569 | 0.8088 | 0.7158 | - |
| current_full_no_bull_collapse_4h | 119 | 0.5586 | 0.0841 | 0.4745 | 0.2605 | 0.8676 | 0.9286 | - |
| current_full | 131 | 0.5465 | 0.0721 | 0.4745 | 0.2599 | 0.8676 | 0.9048 | - |
| core_plus_macro | 10 | 0.4985 | 0.0240 | 0.4745 | 0.2696 | 0.8088 | 0.8810 | - |
| core_only | 8 | 0.4474 | 0.0270 | 0.4204 | 0.2687 | 0.5441 | 0.6592 | - |

## Notes

- Recommended profile this run: **`core_plus_macro_plus_all_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
