# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 16:51:13 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core_only | 8 | 0.7445 | 0.1838 | 0.4538 | 0.2108 | 0.6857 | 0.5161 | 0.2933 |
| core_plus_macro | 10 | 0.6872 | 0.1684 | 0.4478 | 0.2274 | 0.9071 | 0.6129 | 0.3067 |
| core_plus_4h | 18 | 0.6497 | 0.1478 | 0.4550 | 0.2586 | 0.7357 | 0.4839 | 0.2533 |
| core_plus_technical | 18 | 0.6403 | 0.2083 | 0.3782 | 0.2549 | 0.8429 | 0.6129 | 0.2400 |
| full_no_technical | 121 | 0.5849 | 0.1477 | 0.3854 | 0.2923 | 0.8857 | 0.6774 | 0.3200 |
| core_macro_plus_stable_4h | 38 | 0.5750 | 0.1397 | 0.3854 | 0.3039 | 0.7476 | 0.4839 | 0.2267 |
| full_no_lags | 41 | 0.5697 | 0.1231 | 0.4370 | 0.2830 | 0.8667 | 0.5484 | 0.2533 |
| full_no_macro | 129 | 0.5621 | 0.1464 | 0.3854 | 0.2992 | 0.8952 | 0.6129 | 0.3067 |
| full_no_cross | 120 | 0.5618 | 0.1444 | 0.3866 | 0.3011 | 0.8643 | 0.6774 | 0.3200 |
| current_full | 131 | 0.5580 | 0.1427 | 0.3854 | 0.3001 | 0.8976 | 0.6129 | 0.3067 |
| full_no_4h | 121 | 0.5510 | 0.1362 | 0.3854 | 0.2952 | 0.9000 | 0.6774 | 0.3200 |
| current_full_no_bull_collapse_4h | 119 | 0.5373 | 0.1334 | 0.3866 | 0.3149 | 0.8810 | 0.6452 | 0.2933 |

## Notes

- Recommended profile this run: **`core_only`**
- Bull collapse 4H watchlist carried into this run: `feat_4h_bb_pct_b, feat_4h_dist_bb_lower, feat_4h_dist_swing_low`
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?
- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.
- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.
