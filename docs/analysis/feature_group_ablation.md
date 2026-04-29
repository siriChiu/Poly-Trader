# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-04-29 00:28:46 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_full_no_bull_collapse_4h | 119 | 0.5526 | 0.0721 | 0.4805 | 0.2598 | 0.2206 | - | 0.4725 |
| current_full | 131 | 0.4760 | 0.0045 | 0.4715 | 0.2704 | 0.2353 | - | 0.4539 |
| core_plus_macro | 10 | 0.4520 | 0.0285 | 0.4234 | 0.2597 | 0.3529 | - | 0.3755 |
| core_only | 8 | 0.4174 | 0.0631 | 0.3544 | 0.2611 | 0.2647 | - | 0.1402 |
| core_plus_macro_plus_all_4h | 50 | 0.3994 | 0.0811 | 0.3183 | 0.2800 | 0.2353 | - | 0.2539 |
| core_macro_plus_stable_4h | 38 | 0.3964 | 0.0841 | 0.3123 | 0.2705 | 0.6029 | - | 0.4049 |

## Notes

- Recommended profile this run: **`current_full_no_bull_collapse_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
