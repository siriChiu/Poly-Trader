# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-01 23:03:31 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full | 131 | 0.5661 | 0.0976 | 0.4685 | 0.2600 | 0.3235 | 1.0000 | 0.2031 |
| core_only | 8 | 0.5375 | 0.0691 | 0.4685 | 0.2496 | 0.8088 | 1.0000 | 0.4281 |
| current_full_no_bull_collapse_4h | 119 | 0.5030 | 0.0345 | 0.4685 | 0.2606 | 0.3676 | 1.0000 | 0.3344 |
| core_plus_macro_plus_all_4h | 50 | 0.4189 | 0.0495 | 0.3694 | 0.2621 | 0.7353 | 1.0000 | 0.2344 |
| core_plus_macro | 10 | 0.3949 | 0.0736 | 0.3213 | 0.2529 | 0.6912 | 1.0000 | 0.3344 |
| core_macro_plus_stable_4h | 38 | 0.3844 | 0.0841 | 0.3003 | 0.2652 | 0.5588 | 1.0000 | 0.2188 |

## Notes

- Recommended profile this run: **`current_full`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
