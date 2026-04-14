# Feature Group Ablation Report

- target: `simulated_pyramid_win`
- recent_rows: **5000**
- splits: **5** (TimeSeriesSplit)
- generated_at: **2026-04-14 08:05:22 UTC**

## Ranking (accuracy / worst fold / stability)

| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| core_plus_macro | 10 | 0.7364 | 0.1769 | 0.4610 | 0.1928 | 0.8190 | 0.7414 |
| core_only | 8 | 0.7239 | 0.1857 | 0.4538 | 0.2190 | 0.7667 | 0.7241 |
| core_plus_technical | 18 | 0.6922 | 0.2151 | 0.4346 | 0.2232 | 0.8619 | 0.7069 |
| core_plus_4h | 18 | 0.6816 | 0.1815 | 0.4538 | 0.2372 | 0.7929 | 0.7759 |
| full_no_macro | 129 | 0.6783 | 0.1770 | 0.4538 | 0.2503 | 0.9214 | 0.9138 |
| full_no_technical | 121 | 0.6641 | 0.1632 | 0.4538 | 0.2537 | 0.9190 | 0.9483 |
| full_no_4h | 121 | 0.6624 | 0.1657 | 0.4538 | 0.2523 | 0.9524 | 0.9138 |
| full_no_cross | 120 | 0.6600 | 0.1642 | 0.4538 | 0.2543 | 0.9405 | 0.9138 |
| full_no_lags | 41 | 0.6586 | 0.1638 | 0.4538 | 0.2437 | 0.9548 | 0.9483 |
| current_full | 131 | 0.6533 | 0.1598 | 0.4538 | 0.2522 | 0.9381 | 0.9138 |

## Notes

- Best profile this run: **`core_plus_macro`**
- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.
- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.
