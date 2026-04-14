# Poly-Trader Leaderboard 2.0 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Upgrade Poly-Trader from a single-score leaderboard into an LLM-leaderboard-style evaluation surface with sortable multidimensional scorecards, quadrant visualization, and durable snapshot storage.

**Architecture:** Keep existing `/api/models/leaderboard` as the canonical fetch path, but enrich each model row with four capability dimensions (`Reliability`, `Return Power`, `Risk Control`, `Capital Efficiency`) plus `Overall Score`. Persist full leaderboard snapshots to SQLite for canonical history and continue using JSON cache for stale-while-revalidate frontend speed.

**Tech Stack:** Python + FastAPI + SQLite + existing model leaderboard engine, React + Recharts + Tailwind.

---

## Scope implemented in first slice

1. Extend `backtesting/model_leaderboard.py` with dimension scores and overall score.
2. Extend `server/routes/api.py` payload serialization with score dimensions, quadrant points, and storage metadata.
3. Persist model leaderboard snapshots into SQLite tables:
   - `leaderboard_model_snapshots`
   - `leaderboard_model_scorecards`
4. Upgrade `web/src/pages/StrategyLab.tsx` with:
   - sortable leaderboard table
   - quadrant plot
   - multidimensional scorecards
   - explicit storage explanation (`SQLite canonical + JSON cache`)
5. Verify with pytest + frontend build.

## Next slice

1. Add strategy-side Leaderboard 2.0 scorecards (same dimension philosophy for saved strategies).
2. Add history API (`/api/models/leaderboard/history`) from SQLite snapshots.
3. Add rank delta / trend chips.
4. Add filters for capital mode / regime / overfit status.
5. Add compare mode between `classic_pyramid` and `reserve_90` directly inside the leaderboard.
