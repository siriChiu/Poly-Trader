# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 17:46:25 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7438 | 0.1846 | 0.4538 | 0.2105 | 0.6738 | 0.5484 | 0.2933 |
| core_plus_macro | 10 | 0.6912 | 0.1672 | 0.4478 | 0.2276 | 0.9048 | 0.6452 | 0.3067 |
| core_plus_4h | 18 | 0.6771 | 0.1318 | 0.4550 | 0.2570 | 0.7095 | 0.4839 | 0.2533 |
| core_plus_technical | 18 | 0.6370 | 0.2096 | 0.3721 | 0.2544 | 0.8262 | 0.5806 | 0.2400 |
| full_no_technical | 121 | 0.5909 | 0.1493 | 0.3830 | 0.2885 | 0.8714 | 0.7097 | 0.3200 |
| full_no_lags | 41 | 0.5849 | 0.1106 | 0.4550 | 0.2839 | 0.8452 | 0.4839 | 0.2533 |
| core_macro_plus_stable_4h | 38 | 0.5753 | 0.1419 | 0.3794 | 0.3011 | 0.7500 | 0.5161 | 0.2400 |
| full_no_4h | 121 | 0.5664 | 0.1279 | 0.4274 | 0.2884 | 0.8786 | 0.7097 | 0.3067 |
| current_full | 131 | 0.5652 | 0.1450 | 0.3818 | 0.2954 | 0.8405 | 0.6774 | 0.3067 |
| full_no_macro | 129 | 0.5613 | 0.1522 | 0.3830 | 0.2973 | 0.8548 | 0.5806 | 0.3200 |
| full_no_cross | 120 | 0.5577 | 0.1419 | 0.3818 | 0.3021 | 0.8333 | 0.6129 | 0.3067 |
| current_full_no_bull_collapse_4h | 119 | 0.5364 | 0.1312 | 0.3842 | 0.3128 | 0.8524 | 0.7097 | 0.2933 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
