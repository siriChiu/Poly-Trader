# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-25 11:42:14 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.4865 | 0.1351 | 0.3514 | 0.3642 | 0.4118 | - | 0.3899 |
| core_macro_plus_stable_4h | 38 | 0.4820 | 0.1306 | 0.3514 | 0.3741 | 0.3824 | - | 0.3445 |
| core_plus_macro_plus_all_4h | 50 | 0.4414 | 0.0901 | 0.3514 | 0.3835 | 0.3824 | - | 0.3596 |
| current_full | 131 | 0.4399 | 0.0886 | 0.3514 | 0.3799 | 0.3971 | - | 0.3596 |
| core_only | 8 | 0.4294 | 0.0781 | 0.3514 | 0.3749 | 0.2353 | - | 0.2384 |
| core_plus_macro | 10 | 0.4294 | 0.0781 | 0.3514 | 0.3729 | 0.1176 | - | 0.1324 |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
