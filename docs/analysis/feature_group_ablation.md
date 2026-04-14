# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 19:39:11 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7544 | 0.1722 | 0.4898 | 0.2115 | 0.7071 | 0.6774 | 0.1667 |
| core_plus_4h | 18 | 0.7275 | 0.1472 | 0.4958 | 0.2505 | 0.7286 | 0.5161 | 0.2000 |
| core_plus_macro | 10 | 0.6778 | 0.1688 | 0.4370 | 0.2414 | 0.9000 | 0.6452 | 0.3167 |
| core_plus_macro_plus_4h_structure_shift | 22 | 0.6394 | 0.1343 | 0.4370 | 0.2370 | 0.8810 | 0.9355 | 0.2500 |
| core_plus_macro_plus_4h_trend | 22 | 0.6247 | 0.0816 | 0.4790 | 0.2515 | 0.9024 | 0.5161 | 0.3167 |
| core_plus_technical | 18 | 0.6036 | 0.2172 | 0.3505 | 0.2685 | 0.8905 | 0.4194 | 0.2500 |
| full_no_lags | 41 | 0.5952 | 0.1121 | 0.4094 | 0.2614 | 0.8833 | 0.5161 | 0.2333 |
| current_full | 131 | 0.5942 | 0.1639 | 0.3433 | 0.2664 | 0.8262 | 0.5806 | 0.2667 |
| full_no_macro | 129 | 0.5942 | 0.1564 | 0.3349 | 0.2735 | 0.7595 | 0.5161 | 0.2833 |
| full_no_technical | 121 | 0.5892 | 0.1699 | 0.3049 | 0.2711 | 0.8000 | 0.5806 | 0.2500 |
| full_no_cross | 120 | 0.5844 | 0.1671 | 0.3109 | 0.2709 | 0.8024 | 0.5806 | 0.2833 |
| full_no_4h | 121 | 0.5830 | 0.1201 | 0.4274 | 0.2707 | 0.8690 | 0.6452 | 0.2333 |
| current_full_no_bull_collapse_4h | 119 | 0.5825 | 0.1237 | 0.3890 | 0.2846 | 0.8524 | 0.5161 | 0.2833 |
| core_macro_plus_stable_4h | 38 | 0.5791 | 0.1491 | 0.3277 | 0.2755 | 0.8929 | 0.6774 | 0.2333 |
| core_plus_macro_plus_all_4h | 50 | 0.5784 | 0.1687 | 0.2857 | 0.2648 | 0.8786 | 0.7419 | 0.2167 |
| core_plus_macro_plus_4h_momentum | 22 | 0.5623 | 0.1519 | 0.2905 | 0.2857 | 0.8643 | 0.7097 | 0.2000 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
