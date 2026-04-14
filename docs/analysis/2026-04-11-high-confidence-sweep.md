# High-confidence low-frequency sweep (2026-04-11)

## Goal
Optimize for **higher-confidence, lower-frequency entries** in Strategy Lab rather than raw CV accuracy or trade count.

## Artifacts
- `model/high_confidence_threshold_sweep.json`
- `model/rule_high_winrate_sweep.json`

## Main findings

### 1. Simply increasing hybrid confidence thresholds did **not** materially improve win rate
Hybrid sweep tested:
- models: `xgboost`, `logistic_regression`, `random_forest`
- `confidence_min`: 0.45 / 0.55 / 0.65 / 0.75
- `entry_quality_min`: 0.55 / 0.68 / 0.75 / 0.82
- allowed regimes: `all`, `bull+chop`, `bull`

Best min-8-trade config:
- model: `random_forest`
- `confidence_min=0.75`
- `entry_quality_min=0.55`
- allowed regimes: `bull+chop`
- win rate: **53.66%**
- ROI: **+2.77%**
- PF: **1.0576**
- trades: **41**
- max DD: **18.49%**

Interpretation:
- threshold tightening alone is **not enough**
- current hybrid confidence scores are not sharply separating “must-win” entries yet

### 2. Rule-based sweep can push win rate higher, but often at the cost of profitability
Best min-8-trade win-rate configs clustered around:
- `bias50_max=0`
- `nose_max≈0.45`
- `tp_roi=0.04`
- `stop_loss=-0.05`

Top raw win-rate result:
- win rate: **58.70%**
- trades: **46**
- ROI: **negative**
- PF: **<1**

Interpretation:
- maximizing win rate alone creates many small wins but still loses money overall
- user goal must remain: **high confidence + acceptable PF / DD**, not just headline win rate

### 3. Existing saved strategy evidence still shows the same pattern
`My Strategy` currently has:
- win rate: **80%**
- ROI: **+2.06%**
- trades: **55**
- max DD: **32.74%**
- PF: **1.024**

Interpretation:
- the system can manufacture high win rate
- but it still allows losses large enough to hollow out the edge

## Recommended direction
1. Keep `simulated_pyramid_win` as canonical target
2. Add UI/backend controls for:
   - `confidence_min`
   - `entry_quality_min`
   - `allowed_regimes`
3. Default high-confidence preset should prefer:
   - `bull+chop`
   - confidence gate raised
   - quality gate raised
4. Next model work should focus on **precision at top-decile signals**, not overall accuracy
5. Next strategy work should reduce loss magnitude / bad entries in bear regime

## Implemented after this sweep
- Strategy Lab now exposes:
  - confidence threshold
  - entry-quality threshold
  - allowed regime selector
- Added preset: `🎯 高勝率低頻`
- Backend `run_rule_backtest()` / `run_hybrid_backtest()` now honor:
  - `entry.entry_quality_min`
  - `entry.allowed_regimes`
