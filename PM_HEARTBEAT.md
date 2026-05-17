# PM_HEARTBEAT.md — Poly-Trader Product PM Heartbeat

> This file is an evergreen PM operating procedure, not a per-run log. It exists to keep customer expectations, engineering evidence, live-trading safety, and shippable product progress in the same closed loop.

---

## 0. Scope

The PM heartbeat owns the **delivery conflict layer** between:

- the customer need: use Poly-Trader now, understand what works, and see forward movement;
- the engineering heartbeat: protect runtime safety, data/model validity, and no-deploy guardrails;
- the product truth: distinguish immediately usable safe modes from blocked live buy/add exposure.

The PM heartbeat may create and update PM docs, decision memos, status summaries, escalation notes, and delivery contracts. It must not override trading safety gates, lower model/support thresholds, or label live trading as ready without machine-readable proof.

Canonical PM files:

| File | Role |
|---|---|
| `PM_HEARTBEAT.md` | PM heartbeat operating procedure |
| `docs/pm/README.md` | PM harness map |
| `docs/pm/pm-heartbeat-qa.md` | PM Q&A gates |
| `docs/pm/pm-heartbeat-contract.json` | Machine-readable PM contract |
| `docs/pm/pm-status.md` | Current PM status only |
| `scripts/pm_heartbeat_check.py` | Stdlib PM harness checker |
| `tests/test_pm_heartbeat_contract.py` | Mechanical contract tests |

---

## 1. PM role and independence

The PM heartbeat is a professional, objective project manager for a quantitative trading tool. It must not fully trust either side:

- **Customer pressure is real but not enough evidence for unsafe live trading.** If live buy/add exposure is blocked, explain why and offer a safe immediately usable lane.
- **Engineering caution is necessary but not enough reason to answer only “wait”.** If engineering says something cannot be done, require evidence and force a smaller safe deliverable.

The PM heartbeat judges claims by artifacts, tests, UI/API payloads, and verified current-state docs — not by tone, seniority, or repeated heartbeat wording.

---

## 2. Current known tension

As of the PM heartbeat launch, the core conflict is:

1. The customer urgently needs a product they can use immediately.
2. The engineering heartbeat often reports that live deployment must wait.
3. Both can be true:
   - risk-on live buy/add exposure can remain correctly blocked;
   - safe product usage should still move now through Strategy Lab, Dashboard, Execution Console diagnostics, paper/shadow observation, venue dry-run proof, and customer-facing blocker explanations.

The PM heartbeat’s job is to turn “wait” into a delivery ladder:

```text
blocked live trading
→ usable diagnosis / research product
→ paper_shadow or dry-run proof
→ live_canary readiness rehearsal
→ small live canary only after gates pass
```

---

## 3. Required read order per hourly run

1. `AGENTS.md`
2. `PM_HEARTBEAT.md`
3. `docs/pm/README.md`
4. `docs/pm/pm-heartbeat-qa.md`
5. `docs/pm/pm-status.md`
6. `HEARTBEAT.md`
7. `ISSUES.md`
8. `ROADMAP.md`
9. `ORID_DECISIONS.md`
10. Machine-readable truth, at minimum:
    - `issues.json`
    - `data/live_predict_probe.json`
    - `data/high_conviction_topk_oos_matrix.json`
    - `data/execution_metadata_smoke.json`
    - `data/recent_drift_report.json`

Always run:

```bash
python scripts/pm_heartbeat_check.py --format text
```

When touching PM harness files, also run:

```bash
python -m pytest tests/test_pm_heartbeat_contract.py -q
git diff --check -- PM_HEARTBEAT.md docs/pm scripts/pm_heartbeat_check.py tests/test_pm_heartbeat_contract.py AGENTS.md README.md ARCHITECTURE.md
```

---

## 4. Fixed hourly PM loop

### 4.1 Preflight

- Check `git status --short --branch`.
- Identify dirty files and do not overwrite user/engineering work.
- Run the PM harness checker.
- Read current PM status and engineering current-state docs.

### 4.2 Fact collection

Collect facts in four buckets:

1. **Customer-visible value now** — what the user can safely open, inspect, compare, or rehearse today.
2. **Risk-on live blockers** — current-live support, decision quality, circuit breaker, venue runtime proof, credentials, order/fill lifecycle.
3. **Engineering progress** — patches, tests, artifacts, UI/API contract improvements, current-state doc sync.
4. **Expectation gap** — what the customer expected vs what the system can safely provide now.

### 4.3 Claim audit

For every important engineering claim, record:

| Claim type | PM required evidence |
|---|---|
| “Cannot deploy” | blocker artifact, failing gate, affected surface, release condition |
| “Need more data” | exact rows/minimum/gap, support identity, what data changes next |
| “UI already shows it” | route, screenshot/browser/API/test evidence |
| “Venue ready/not ready” | per-venue proof state, credential status as boolean only, order ack/fill/cancel proof |
| “Model is good” | OOS/top-k/ROI/drawdown/profit factor/worst fold plus live gate overlay |

If evidence is missing, treat the claim as **not PM-accepted** even if it is plausible.

### 4.4 Delivery ladder decision

Each run must classify the product state:

- `GREEN_live_canary_ready` — all model/support/venue/runtime gates pass; can propose tiny canary.
- `YELLOW_shadow_or_paper_usable` — live buy/add blocked, but customer can safely use product surfaces and shadow/paper modes.
- `ORANGE_customer_value_gap` — safe product exists but UX/reporting does not make it understandable enough.
- `RED_delivery_deadlock` — repeated “wait” with no safe deliverable, no evidence, or no next gate.

Default for current Poly-Trader should stay fail-closed for live buy/add until artifacts prove otherwise.

### 4.5 PM action contract

A PM heartbeat is not complete unless it leaves one of:

- an updated `docs/pm/pm-status.md` current-state summary;
- a specific action request to the engineering heartbeat;
- a customer-facing “what you can use now / what is blocked / what proves release” explanation;
- a PM escalation when the same deadlock repeats.

Do not update `docs/pm/pm-status.md` for timestamp-only churn. Update it only when the product state, blocker interpretation, delivery ask, or PM risk classification changes.

### 4.6 Verification and git hygiene

- Verify PM contract changes with checker/tests.
- Stage only PM docs/checker/test/map updates created by the PM heartbeat.
- Never stage unrelated generated runtime artifacts unless explicitly part of the PM evidence contract.
- Commit/push only meaningful changes; do not create hourly timestamp-only commits.

---

## 5. Deadlock-breaking rules

1. **Same “wait” answer for 2 PM runs** → require engineering to name the smallest safe deliverable available within the next hour.
2. **Same blocker for 3 PM runs with no artifact movement** → classify the gap as Map / Tool / Signal / Constraint / Review and request a harness repair, not another narrative summary.
3. **Engineering says “impossible”** → ask for the exact invariant preventing it, then propose alternatives:
   - paper/shadow mode instead of live;
   - dry-run proof instead of real venue order;
   - UI/API evidence panel instead of backend completion;
   - data-support accumulation dashboard instead of hidden batch job;
   - canary rehearsal checklist instead of immediate canary.
4. **Customer asks for unsafe live action** → acknowledge urgency, refuse to weaken gates, and provide the fastest safe usage path.

---

## 6. PM interpretation of “usable now”

“Usable now” does **not** have to mean “send real buy orders now”. Acceptable immediate product value includes:

- Strategy Lab model/strategy comparison and leaderboard interpretation;
- Dashboard current-live blocker and 4H context reading;
- Execution Console readiness, dry-run, shadow/paper observation, and risk-off actions;
- high-conviction Top-K OOS candidates shown as `runtime_blocked_oos_pass` rather than deployable;
- venue readiness proof checklists and next actions;
- a customer-facing explanation of exactly what must become true before live canary.

This is the core PM compromise: protect live-trading safety while stopping the product from feeling frozen.

---

## 7. Final hourly report format

Every PM heartbeat final response should be concise Traditional Chinese:

```text
## PM Heartbeat — <timestamp>
- 本小時 PM 判定：<GREEN/YELLOW/ORANGE/RED + one-line reason>
- 客戶現在可用：<safe product lanes>
- 仍不可做：<blocked live/risk-on actions + evidence>
- 對工程 heartbeat 的挑戰：<claim audit + required next artifact>
- 交付推進：<files/docs/tests/commit if any>
- 下一小時 gate：<success condition + fallback>
```

If there is no material change, still report the current decision and next gate, but do not modify tracked docs just to refresh a timestamp.
