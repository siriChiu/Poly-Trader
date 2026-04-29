# High-Conviction Top-K OOS Surfacing Implementation Plan

> **For Hermes:** Execute this plan task-by-task with strict TDD. Keep current-live blockers fail-closed and do not promote any research-only candidate to live deployment.

**Goal:** Productize `data/high_conviction_topk_oos_matrix.json` into `/api/models/leaderboard` and Strategy Lab so operators can see 離線 ROI / 勝率 / 最大回撤 / 盈虧比 / 最差分折 / 部署判定 before considering deployment.

**Architecture:** Keep the existing walk-forward matrix generator as the offline evidence producer. Add a small backend loader that compactly validates and attaches the artifact to the model leaderboard payload. Add a Strategy Lab read-only card that renders the best high-conviction rows and explains why candidates remain 模擬觀察 / 影子驗證 / 僅觀察 when gates fail.

**Tech Stack:** Python FastAPI route helpers, pytest, React/TypeScript Strategy Lab, Vite build, graphify.

---

## Current State Snapshot

- Branch: `main`, currently one local commit ahead of `origin/main`: `d335382 心跳 #1124: 產品化 high-conviction OOS gate`.
- Working tree before this plan: clean.
- Existing artifact: `data/high_conviction_topk_oos_matrix.json` with 24 rows and `deployable_verdict` / `gate_failures` fields.
- Existing generator: `scripts/topk_walkforward_precision.py` writes both canonical `data/high_conviction_topk_oos_matrix.json` and legacy `model/topk_walkforward_precision.json`.
- Remaining product gap from `issues.json`: Strategy Lab leaderboard/API/UI still need high-conviction top-k OOS matrix surfacing before `P0_high_conviction_topk_roi_gate` can close.

## Non-Goals / Guardrails

- Do **not** mark any strategy deployable unless all artifact gates pass and current-live support is deployable.
- Do **not** relax `min_trades`, `win_rate`, `max_drawdown`, `profit_factor`, `worst_fold`, or support-route gates to force a deployable result.
- Do **not** commit timestamp-only runtime metadata drift unless intentionally part of current-state truth.
- Do **not** expose raw secrets or connection strings; secret scan added diff before staging.

---

## Task 1 — Backend RED: require leaderboard payload to include high-conviction top-k summary

**Objective:** Prove `/api/models/leaderboard` has a stable machine-readable `high_conviction_topk` contract.

**Files:**
- Modify test: `tests/test_model_leaderboard.py`
- Later modify implementation: `server/routes/api.py`

**Step 1: Write failing test**

Add a test near existing `_build_model_leaderboard_payload` tests:

```python
def test_build_model_leaderboard_payload_includes_high_conviction_topk(monkeypatch, tmp_path):
    artifact = tmp_path / "high_conviction_topk_oos_matrix.json"
    artifact.write_text(json.dumps({
        "generated_at": "2026-04-29T10:15:21Z",
        "target_col": "simulated_pyramid_win",
        "samples": 1234,
        "top_k_grid": ["top_1pct", "top_2pct"],
        "minimum_deployment_gates": {"min_trades": 50, "min_win_rate": 0.6},
        "support_context": {"deployment_blocker": "circuit_breaker_active"},
        "rows": [
            {
                "model": "xgboost",
                "regime": "all",
                "top_k": "top_1pct",
                "oos_roi": 0.22,
                "win_rate": 0.71,
                "profit_factor": 2.4,
                "max_drawdown": 0.04,
                "worst_fold": -0.02,
                "trade_count": 44,
                "deployable_verdict": "not_deployable",
                "gate_failures": ["min_trades_not_met", "deployment_blocker_active"],
            }
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "HIGH_CONVICTION_TOPK_PATH", artifact)

    # Patch the expensive leaderboard frame/model work using the existing local test patterns.
    ...

    payload = api_module._build_model_leaderboard_payload()

    summary = payload["high_conviction_topk"]
    assert summary["source_artifact"] == str(artifact)
    assert summary["row_count"] == 1
    assert summary["deployable_count"] == 0
    assert summary["status"] == "paper_shadow_only"
    assert summary["best_rows"][0]["gate_failures"] == ["min_trades_not_met", "deployment_blocker_active"]
```

**Step 2: Run RED**

Run:

```bash
source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q
```

Expected: FAIL because `high_conviction_topk` does not exist yet.

---

## Task 2 — Backend GREEN: load and compact artifact into API payload

**Objective:** Add the minimal backend helper to pass Task 1 while preserving fail-closed semantics.

**Files:**
- Modify: `server/routes/api.py`

**Implementation sketch:**

1. Add constant near model leaderboard paths:

```python
HIGH_CONVICTION_TOPK_PATH = Path("data/high_conviction_topk_oos_matrix.json")
```

2. Add helpers before `_build_model_leaderboard_payload`:

```python
def _compact_high_conviction_topk_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return { ... only operator/API-safe fields ... }


def _load_high_conviction_topk_summary(path: Optional[Path] = None, limit: int = 12) -> Optional[Dict[str, Any]]:
    path = path or HIGH_CONVICTION_TOPK_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"source_artifact": str(path), "status": "unreadable", "error": str(exc), "rows": [], "best_rows": [], "row_count": 0, "deployable_count": 0}
    rows = [row for row in payload.get("rows", []) if isinstance(row, dict)]
    rows.sort(key=lambda row: (
        row.get("deployable_verdict") == "deployable",
        float(row.get("oos_roi") or -999),
        float(row.get("win_rate") or -999),
        int(row.get("trade_count") or 0),
    ), reverse=True)
    deployable_count = sum(1 for row in rows if row.get("deployable_verdict") == "deployable")
    return {
        "source_artifact": str(path),
        "generated_at": payload.get("generated_at"),
        "target_col": payload.get("target_col"),
        "samples": payload.get("samples"),
        "top_k_grid": payload.get("top_k_grid") or [],
        "minimum_deployment_gates": payload.get("minimum_deployment_gates") or {},
        "support_context": payload.get("support_context") or {},
        "row_count": len(rows),
        "deployable_count": deployable_count,
        "status": "deployable_candidates_available" if deployable_count else "paper_shadow_only",
        "best_rows": [_compact_high_conviction_topk_row(row) for row in rows[:limit]],
    }
```

3. Include this key in both empty-frame and normal payloads:

```python
"high_conviction_topk": _load_high_conviction_topk_summary(),
```

**Step 3: Run GREEN**

Run:

```bash
source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q
```

Expected: PASS.

---

## Task 3 — Frontend RED: require Strategy Lab to understand and render high-conviction top-k contract

**Objective:** Lock a frontend contract so Strategy Lab cannot silently drop the API payload.

**Files:**
- Modify test: `tests/test_frontend_decision_contract.py`
- Later modify UI: `web/src/pages/StrategyLab.tsx`

**Step 1: Write failing source contract test**

Add assertions that `StrategyLab.tsx`:

- Defines `HighConvictionTopKSummary` / row fields.
- Copies `data?.high_conviction_topk` into `nextModelMeta`.
- Renders the card title `高信心 OOS Top-K 部署門檻`.
- Shows Traditional Chinese fail-closed copy such as `未通過前維持模擬觀察 / 影子驗證 / 僅觀察`.
- Renders metrics: `離線 ROI`, `勝率`, `最大回撤`, `盈虧比`, `最差分折`, `部署判定`.

**Step 2: Run RED**

Run:

```bash
source venv/bin/activate && python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk -q
```

Expected: FAIL because Strategy Lab does not render this card yet.

---

## Task 4 — Frontend GREEN: render read-only Strategy Lab high-conviction card

**Objective:** Show top-k OOS matrix evidence on the leaderboard tab without enabling deployment.

**Files:**
- Modify: `web/src/pages/StrategyLab.tsx`

**Implementation sketch:**

1. Add interfaces:

```ts
interface HighConvictionTopKRow { ... }
interface HighConvictionTopKSummary { ... }
```

2. Add `high_conviction_topk?: HighConvictionTopKSummary | null;` to `ModelLeaderboardMeta`.

3. In `loadModelLeaderboard`, add:

```ts
high_conviction_topk: data?.high_conviction_topk ?? null,
```

4. After `modelFallbackCandidates`, derive:

```ts
const highConvictionTopK = modelMeta.high_conviction_topk ?? null;
const highConvictionRows = Array.isArray(highConvictionTopK?.best_rows) ? highConvictionTopK.best_rows : [];
```

5. Render card in the leaderboard panel before the model table:

- Title: `高信心 OOS Top-K 部署門檻`
- Status badge: `研究觀察 / 影子驗證` or `可部署候選`
- Summary: generated time, row count, deployable count, support/blocker reason.
- Rows: model, regime, top-k, 離線 ROI, 勝率, 最大回撤, 盈虧比, 最差分折, 交易數, 部署判定, 門檻失敗。
- Copy must explicitly state that failed gates remain 模擬觀察 / 影子驗證 / 僅觀察 and do not open new exposure.

**Step 3: Run GREEN**

Run:

```bash
source venv/bin/activate && python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk -q
```

Expected: PASS.

---

## Task 5 — Integration verification

**Objective:** Confirm backend, frontend source contract, existing top-k generator tests, and build are all valid.

Run:

```bash
source venv/bin/activate && python -m pytest \
  tests/test_model_leaderboard.py -k 'high_conviction_topk or build_model_leaderboard_payload' \
  tests/test_topk_walkforward_precision.py \
  tests/test_frontend_decision_contract.py -k 'high_conviction_topk or model_leaderboard_contract' \
  -q
```

Then:

```bash
cd web && npm run build
```

Expected: all pass.

---

## Task 6 — Runtime artifact / current-state hygiene

**Objective:** Avoid mixing heartbeat runtime noise with the API/UI productization commit.

Steps:

1. Run:

```bash
git status --short --branch
git diff --name-status
```

2. Restore timestamp-only or unrelated runtime artifacts unless semantic current-state truth intentionally changed:

```bash
git restore -- data/execution_metadata_external_monitor.json data/execution_metadata_smoke.json 2>/dev/null || true
```

3. Keep tracked changes focused on:

- `docs/plans/2026-04-29-high-conviction-topk-oos-surfacing.md`
- `server/routes/api.py`
- `web/src/pages/StrategyLab.tsx`
- relevant tests
- current-state docs/issues only if generator truth changes

---

## Task 7 — Final gates, commit, push

**Objective:** Ship only verified changes.

Run:

```bash
source venv/bin/activate && python -m pytest tests/test_repo_hygiene.py -q
python -m py_compile server/routes/api.py scripts/topk_walkforward_precision.py
cd web && npm run build
```

Run graphify rebuild because code files changed:

```bash
source venv/bin/activate && python -c "from pathlib import Path; from graphify.watch import _rebuild_code; _rebuild_code(Path('.')); print('graphify rebuild completed')"
```

Run diff checks and secret scan:

```bash
git diff --check
# scan added diff lines for tokens / private keys / URLs with credentials
```

Commit and push:

```bash
git add docs/plans/2026-04-29-high-conviction-topk-oos-surfacing.md server/routes/api.py web/src/pages/StrategyLab.tsx tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py
git commit -m "心跳 #1125: surfacing high-conviction top-k gate"
git push origin main
git status --short --branch
```

Expected final status: clean and synced with `origin/main`.
