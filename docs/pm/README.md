# Poly-Trader PM Heartbeat Harness

> PM heartbeat exists to keep delivery moving when customer expectations and engineering guardrails collide. It converts “wait” into an evidence-based delivery ladder without weakening live-trading safety.

---

## 1. Purpose

The PM heartbeat is a repo-native harness for product management:

1. **Translate conflict** — customer urgency vs engineering blockers.
2. **Audit claims** — do not accept “can” or “cannot” without artifacts.
3. **Preserve safety** — live buy/add exposure remains fail-closed until support, model, and venue proof pass.
4. **Find usable value now** — Strategy Lab, Dashboard, Execution diagnostics, paper/shadow, dry-run, and canary rehearsal.
5. **Break deadlocks** — repeated “wait” must become a smaller safe deliverable, a harness repair, or a clear escalation.

---

## 2. PM entry map

| File / command | Role |
|---|---|
| `PM_HEARTBEAT.md` | PM operating procedure and escalation rules |
| `docs/pm/pm-heartbeat-qa.md` | PM Q&A gates for every hourly run |
| `docs/pm/pm-heartbeat-contract.json` | Machine-readable PM contract |
| `docs/pm/pm-status.md` | Current PM interpretation only |
| `scripts/pm_heartbeat_check.py --format text` | Mechanical PM harness check |
| `tests/test_pm_heartbeat_contract.py` | Pytest contract for PM harness |
| `HEARTBEAT.md` / `docs/harness/*` | Engineering heartbeat harness |
| `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` | Current engineering truth |
| `data/live_predict_probe.json` | Current live blocker / signal / support truth |
| `data/high_conviction_topk_oos_matrix.json` | Research-to-deployment candidate truth |
| `data/execution_metadata_smoke.json` | Venue readiness and proof gaps |
| `data/recent_drift_report.json` | Recent regime / quality pathology |

---

## 3. PM stance

The PM heartbeat should be tough on both sides:

- To the customer: urgency is valid, but live trading cannot bypass safety gates.
- To engineering: safety is valid, but “wait” is not a deliverable; provide a safe lane, proof, UX, or a precise release condition.

Accepted PM outcome examples:

- “Live buy/add remains blocked because exact q15 support is 3/50, but the customer can use paper shadow and Strategy Lab Top-K candidates now.”
- “Venue live proof is missing, but OKX public metadata is valid; the next one-hour deliverable is dry-run proof and a checklist panel.”
- “Engineering says impossible; PM rejects that wording. The smaller deliverable is an artifact that proves which gate is missing and what changes it.”

Rejected PM outcome examples:

- “Just wait.”
- “Everything is ready” without runtime proof.
- “The model looks good” without OOS, drawdown, support, and live gate overlay.
- “Customer can trade now” while buy/add exposure is fail-closed.

---

## 4. Hourly PM heartbeat minimum checks

```bash
git status --short --branch
python scripts/pm_heartbeat_check.py --format text
```

When PM harness files change:

```bash
python -m pytest tests/test_pm_heartbeat_contract.py -q
git diff --check -- PM_HEARTBEAT.md docs/pm scripts/pm_heartbeat_check.py tests/test_pm_heartbeat_contract.py AGENTS.md README.md ARCHITECTURE.md
```

---

## 5. Current-state policy

`docs/pm/pm-status.md` is current-state only. Do not append hourly history. Update it only when one of these changes:

- PM classification: GREEN / YELLOW / ORANGE / RED;
- live blocker interpretation;
- customer-usable safe lane;
- engineering action request;
- deadlock/escalation state;
- next-hour gate.

Hourly reports are delivered by cron; durable history belongs in git history, session logs, or ignored artifacts, not in PM status prose.
