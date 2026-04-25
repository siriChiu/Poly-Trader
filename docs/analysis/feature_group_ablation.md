# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-25 07:27:04 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.4399 | 0.0465 | 0.3934 | 0.3665 | 0.2647 | - | 0.2500 |
| core_plus_macro | 10 | 0.4399 | 0.0465 | 0.3934 | 0.3628 | 0.2059 | - | 0.2059 |
| core_macro_plus_stable_4h | 38 | 0.4399 | 0.0465 | 0.3934 | 0.3633 | 0.3529 | - | 0.3529 |
| core_plus_macro_plus_all_4h | 50 | 0.4399 | 0.0465 | 0.3934 | 0.3677 | 0.3824 | - | 0.3676 |
| current_full | 131 | 0.4399 | 0.0465 | 0.3934 | 0.3706 | 0.3676 | - | 0.3529 |
| current_full_no_bull_collapse_4h | 119 | 0.4204 | 0.0270 | 0.3934 | 0.3587 | 0.3824 | - | 0.3676 |

## Notes

- Recommended profile this run: **`core_plus_macro`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
