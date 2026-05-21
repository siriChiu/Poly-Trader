# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **1000**
- splits: **2** (TimeSeriesSplit)
- xgb_n_estimators: **40**
- refresh_mode: **bounded_candidate_refresh**
- generated_at: **2026-05-21 19:02:19 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_macro_plus_stable_4h | 38 | 0.5180 | 0.0345 | 0.4835 | 0.2755 | 0.2206 | 0.6131 | - |
| core_only | 8 | 0.4985 | 0.0150 | 0.4835 | 0.2833 | 0.5294 | 0.6131 | - |
| current_full_no_bull_collapse_4h | 119 | 0.4955 | 0.0120 | 0.4835 | 0.2794 | 0.2647 | 0.2798 | - |
| core_plus_macro | 10 | 0.4865 | 0.0030 | 0.4835 | 0.2775 | 0.6618 | 0.7500 | - |
| core_plus_macro_plus_all_4h | 50 | 0.4414 | 0.0420 | 0.3994 | 0.2790 | 0.2941 | 0.4464 | - |
| current_full | 131 | 0.4219 | 0.0616 | 0.3604 | 0.2848 | 0.1029 | 0.2976 | - |

## Notes

- Recommended profile this run: **`core_macro_plus_stable_4h`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
