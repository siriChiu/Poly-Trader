# Top-signal precision analysis (2026-04-11)

## Purpose
Find whether the model has a **small subset of very high-confidence signals** that are worth trading at low frequency.

## Artifact
- `model/top_signal_precision_report.json`

## Important caution
This analysis scores the currently available aligned frame using a model trained on the same frame.
That makes it useful for **ranking / separability diagnosis**, but **not** a production-grade out-of-sample claim.

So the right interpretation is:
- if top buckets are *not* much better than baseline → confidence is weak and not worth gating on
- if top buckets are dramatically better than baseline → there is likely useful separability, and the next step is a **walk-forward / holdout top-decile precision test**

## Main findings

### Overall base rate
Canonical target: `simulated_pyramid_win`
- base positive rate: **~64.7%**

### XGBoost
Top-score slices:
- top 1%: **100%** win, all **chop**
- top 5%: **100%** win, all **chop**
- top 10%: **100%** win, mostly **chop**, a small bear mix
- top 20%: **99.1%** win

Decile pattern:
- bottom decile win rate: **15.1%**
- top decile win rate: **100%**

Interpretation:
- score ranking is extremely polarized
- strongest signals are concentrated in **chop**, not broad bull-only behavior

### Random Forest
Top-score slices:
- top 1%: **100%** win
- top 5%: **100%** win
- top 10%: **100%** win
- top 20%: **99.96%** win

Decile pattern:
- bottom decile win rate: **4.6%**
- top decile win rate: **100%**

Interpretation:
- random forest currently shows the sharpest separation
- strongest signals are again heavily concentrated in **chop**

### Logistic Regression
Top-score slices:
- top 1%: **99.1%** win
- top 5%: **99.1%** win
- top 10%: **99.3%** win
- top 20%: **95.8%** win

Interpretation:
- even the simpler linear model shows strong top-bucket separation
- this suggests the project likely does have a detectable “best-signal subset”

## Regime-specific observations

### Chop dominates the best-signal buckets
Across all 3 models, the highest-confidence bands are dominated by **chop** rows.
This is not the usual intuition of “only trade bull”; it suggests the target currently rewards a specific kind of range/rebound setup.

### Bear is not uniformly bad if confidence is truly extreme
For XGBoost and Random Forest, the **top 5% / 10% of bear rows** also look very strong in this diagnostic ranking.
That means a blanket “never trade bear” rule may be too coarse.
A better rule is:
- do not trade ordinary bear rows
- only allow **extreme top-score bear rows** after walk-forward verification

### Neutral remains weak / noisy
Neutral rows stay unreliable, especially in logistic-regression top slices.
This regime should remain deprioritized or blocked.

## Actionable conclusion
The next best step is **not** adding more generic features first.
The next best step is:

1. build a **walk-forward top-decile precision test**
2. compare per model:
   - top 1% / 2% / 5% / 10%
   - by regime
3. only after that decide:
   - whether random forest should become the default high-confidence model
   - whether bear top-decile trades are truly robust or just in-sample artifacts

## Recommended product direction
Short-term Strategy Lab defaults for experimentation:
- add / keep a **high-confidence low-frequency preset**
- bias toward `bull + chop`
- block `neutral`
- treat `bear` as conditional, not default-allowed

## Recommended next implementation
Create a walk-forward evaluation script that reports:
- precision@top-k-percent by model
- precision@top-k-percent by regime
- trade count, ROI proxy, PF, DD proxy for each bucket

This will tell us whether the extremely strong top-score separability survives OOS.
