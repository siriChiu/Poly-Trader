# Phase 16 — High Accuracy / High Win Rate / Low Drawdown Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Upgrade Poly-Trader from a working research/backtest platform into a decision-quality trading workbench that explicitly optimizes for high win rate, lower drawdown, and lower deep-trap risk for spot-long pyramid trading.

**Architecture:** Keep `simulated_pyramid_win` as the canonical foundation, but add a second layer of decision semantics on top: (1) a 4H regime gate that decides whether spot-long entries are allowed at all, and (2) a short-term entry-quality score that decides whether the current timing is good enough and how many pyramid layers are allowed. Separate mature core signals from sparse research signals so low-coverage sources no longer pollute primary decisions.

**Tech Stack:** FastAPI, SQLite, pandas, XGBoost / sklearn models, React + TypeScript + Tailwind, lightweight-charts, pytest.

---

## Scope and success definition

### Phase 16 P0 outcomes
1. System can output **regime gate** = `ALLOW | CAUTION | BLOCK`.
2. System can output **entry quality** = ordered score / class instead of only binary win.
3. Strategy layer can use **confidence-based layer sizing** rather than fixed full 20/30/50 deployment on all valid entries.
4. Leaderboard begins ranking models/strategies using **win rate + drawdown + stability**, not mostly ROI.

### Phase 16 P1 outcomes
1. Signals are clearly separated into **core** vs **research** across backend and UI.
2. Dynamic Window diagnostics become **distribution-aware**.
3. Strategy Lab starts speaking in **strategy archetypes** instead of only raw model names.

### Non-goals for this phase
- No fully autonomous live trading rollout.
- No new sparse-source historical exporter unless required by a specific P0 blocker.
- No model zoo expansion until decision-quality semantics land.

---

## Workstream A — Decision-quality target

### Objective
Replace the current "did this trade eventually win" emphasis with a target that better matches user preference: high win rate, low drawdown, low deep-trap behavior.

### Files likely involved
- Modify: `data_ingestion/labeling.py`
- Modify: `database/models.py`
- Modify: `backtesting/strategy_lab.py`
- Modify: `backtesting/model_leaderboard.py`
- Modify: `server/routes/api.py`
- Modify: `model/train.py`
- Modify: `model/predictor.py`
- Test: `tests/test_strategy_lab.py`
- Test: `tests/test_model_leaderboard.py`
- Test: `tests/test_api.py`

### Planned target shape
Add a derived trade-quality target alongside the existing canonical binary target:
- `simulated_pyramid_win` — keep as canonical binary gate
- `simulated_pyramid_quality_score` — continuous or ordinal
- `simulated_pyramid_drawdown_penalty`
- `simulated_pyramid_time_underwater`
- optional `simulated_pyramid_class` = `A/B/C` or `good/ok/bad`

### Task A1: Define scoring formula in labeling layer
**Objective:** Make the scoring rule explicit and reproducible.

**Implementation note:** Start simple. Do not overfit the formula on day one.

Candidate formula:
```python
quality_score = (
    0.45 * win_component
    + 0.25 * pnl_component
    - 0.20 * drawdown_penalty
    - 0.10 * underwater_penalty
)
```

### Task A2: Persist new label fields
**Objective:** Ensure labels table can carry decision-quality fields and backfills can populate them.

**Verification:**
- DB rows contain non-null values for recent horizons
- existing rows remain backward compatible

### Task A3: Feed quality target into training dataset assembly
**Objective:** Allow training / leaderboard / backtest layers to compare binary target vs quality target.

**Verification:**
- training script can select the new target without schema failure
- target comparison endpoint shows both binary and quality-oriented views

### Task A4: Expose quality metrics in API + Strategy Lab
**Objective:** Make the new semantics visible, not hidden in DB only.

**Verification:**
- Strategy Lab can display quality-oriented metrics
- API payload clearly documents which target is active

---

## Workstream B — Two-stage decision engine

### Objective
Stop using one undifferentiated score for everything. First ask whether the background allows spot-long at all. Only then evaluate entry timing.

### Files likely involved
- Modify: `backtesting/strategy_lab.py`
- Modify: `model/predictor.py`
- Modify: `server/routes/api.py`
- Modify: `feature_engine/preprocessor.py`
- Modify: `web/src/pages/StrategyLab.tsx`
- Test: `tests/test_strategy_lab.py`
- Test: `tests/test_api.py`

### Stage definitions
#### Stage 1 — 4H regime gate
Input examples:
- `feat_4h_bias50`
- `feat_4h_bias200`
- `feat_4h_ma_order`
- `feat_4h_rsi14`
- `feat_4h_macd_hist`
- `feat_adx`
- `feat_choppiness`
- `feat_4h_dist_swing_low`

Output:
- `ALLOW`
- `CAUTION`
- `BLOCK`

#### Stage 2 — short-term entry quality
Input examples:
- `feat_rsi14`
- `feat_vwap_dev`
- `feat_bb_pct_b` (NW position)
- `feat_nw_width`
- `feat_nw_slope`
- `feat_atr_pct`
- `feat_donchian_pos`
- `feat_pulse`

Output:
- score 0–1 or A/B/C class

### Task B1: Implement deterministic rule-based gate baseline
**Objective:** Land a simple, explainable first version before any model routing.

**Verification:**
- every backtest trade can explain whether it passed or failed the 4H gate
- API exposes gate reason text

### Task B2: Plug gate into backtest entry path
**Objective:** Prevent short-term triggers from firing when 4H backdrop is hostile.

**Verification:**
- blocked trades disappear in known bad 4H conditions
- trade count falls but win rate improves in regression comparison

### Task B3: Add gate + quality outputs to predictor/API
**Objective:** Live inference and Strategy Lab must use the same semantics as backtests.

**Verification:**
- predictor probe or API output includes both `regime_gate` and `entry_quality`

---

## Workstream C — Confidence-based layer sizing

### Objective
Turn pyramid layers into a risk control mechanism instead of a fixed entitlement.

### Files likely involved
- Modify: `backtesting/strategy_lab.py`
- Modify: `server/routes/api.py`
- Modify: `web/src/pages/StrategyLab.tsx`
- Test: `tests/test_strategy_lab.py`

### First release policy
- score < 0.60 → no trade
- 0.60–0.72 → layer 1 only (20%)
- 0.72–0.82 → layers 1–2 (20% + 30%)
- > 0.82 + gate=ALLOW → full 20/30/50
- if gate=`CAUTION` → cap to max 2 layers even if score is high
- if gate=`BLOCK` → zero entry

### Task C1: Implement size policy in backtest engine
**Verification:**
- trades record allowed layer count and actual capital deployed

### Task C2: Surface size policy in Strategy Lab
**Verification:**
- UI shows why only partial layers were allowed

### Task C3: Compare fixed sizing vs confidence sizing in benchmarks
**Verification:**
- benchmark card or leaderboard includes comparison for win rate and max drawdown delta

---

## Workstream D — Core vs research signal separation

### Objective
Prevent low-maturity sparse-source features from contaminating primary decisions.

### Files likely involved
- Modify: `web/src/config/senses.ts`
- Modify: `server/features_engine.py`
- Modify: `server/routes/api.py`
- Modify: `web/src/components/FeatureChart.tsx`
- Modify: `web/src/pages/StrategyLab.tsx`
- Test: `tests/test_api_feature_history_and_predictor.py`

### Proposed tiers
- `core` — high coverage, stable, directly usable in main decision path
- `research` — promising but not yet mature enough for equal-weight decision use
- `blocked` — auth/history/path blocker, diagnostic only

### Task D1: Add explicit maturity/tier metadata
### Task D2: Hide or down-rank research/blocked features from primary strategy controls
### Task D3: Show maturity badge in UI

**Verification:**
- Strategy Lab / FeatureChart clearly distinguish tiers
- sparse-source blockers stop looking like primary trading signals

---

## Workstream E — Leaderboard objective redesign

### Objective
Make rankings match user preference: higher win rate, lower drawdown, more stable across regimes.

### Files likely involved
- Modify: `backtesting/model_leaderboard.py`
- Modify: `server/routes/api.py`
- Modify: `web/src/pages/StrategyLab.tsx`
- Test: `tests/test_model_leaderboard.py`

### Proposed composite score (v1)
```python
composite = (
    0.35 * win_rate_score
    + 0.20 * roi_score
    + 0.20 * low_drawdown_score
    + 0.15 * regime_stability_score
    + 0.10 * profit_factor_score
)
```

### Task E1: Implement score function server-side
### Task E2: Return subscore breakdown via API
### Task E3: Show why a model ranks highly (not just final score)

**Verification:**
- models with high ROI but poor drawdown no longer dominate unfairly
- UI can explain rankings in plain language

---

## Workstream F — Dynamic Window distribution-aware diagnostics

### Objective
Stop treating constant-target recent windows as if they were valid competitive evaluations.

### Files likely involved
- Modify: `scripts/full_ic.py`
- Modify: dynamic-window script(s) currently generating `data/dw_result.json`
- Modify: `server/routes/api.py`
- Modify: `web/src/pages/StrategyLab.tsx`
- Test: add targeted tests under `tests/`

### Required additions
- window label distribution
- regime distribution
- constant-target flag
- minimum diversity threshold
- explicit downgrade of invalid windows

### Verification
- recent-window reports no longer overclaim confidence when target distribution collapses

---

## Workstream G — Strategy archetype layer

### Objective
Move beyond raw model names so the UI speaks a decision language users can reason about.

### Files likely involved
- Modify: `backtesting/strategy_lab.py`
- Modify: `web/src/pages/StrategyLab.tsx`
- Modify: `server/routes/api.py`

### Candidate archetypes
- 抄底型
- 趨勢延續型
- 均值回歸型
- 4H 濾網型
- 混合型

### Verification
- saved strategies expose archetype metadata
- leaderboard and detail views can explain the strategy in human terms

---

## Suggested implementation order

### P0 (do first)
1. Workstream B — Two-stage decision engine
2. Workstream C — Confidence-based layer sizing
3. Workstream A — Decision-quality target (initial version)

### P1 (do second)
4. Workstream E — Leaderboard redesign
5. Workstream D — Core vs research signal separation
6. Workstream F — Dynamic Window distribution-aware diagnostics

### P2 (do third)
7. Workstream G — Strategy archetypes
8. Additional UI polish after semantics are stable

---

## Verification matrix

### For every merged P0/P1 patch
Run at minimum:
```bash
source venv/bin/activate
python -m pytest tests/test_api.py tests/test_strategy_lab.py tests/test_model_leaderboard.py -q
cd web && npm run build
```

### Additional verification expectations
- compare old vs new win rate / max drawdown on at least one canonical saved strategy
- confirm predictor/API exposes new gate/quality fields
- confirm Strategy Lab displays new semantics coherently
- if a patch touches labels, verify DB rows and target comparison payload

---

## Doc sync requirements

When the first Phase 16 implementation PR lands, also update:
- `ISSUES.md` — mark which P0 issue moved from strategy recommendation to active implementation
- `ROADMAP.md` — tick the exact Phase 16 item(s)
- `ARCHITECTURE.md` — reflect any concrete contract changes
- `ORID_DECISIONS.md` — add the implementation round if direction materially changes

---

## Ready-to-execute first slice

If executing immediately, the best first slice is:
1. add a simple deterministic 4H regime gate
2. route backtest entries through that gate
3. cap layer count based on gate + quality threshold
4. expose gate/quality/layer decision in API and Strategy Lab
5. compare old vs new win rate and max drawdown

This slice is small enough to validate the new direction without waiting for the full target redesign.
