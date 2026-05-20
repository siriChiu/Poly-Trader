# PM Heartbeat Q&A Gate

> These gates force the PM heartbeat to arbitrate from the customer's side using evidence. The PM must actively solve the customer's usability/value problem, challenge engineering and framework inertia, and still preserve live-trading safety.

---

## Usage

- Run `python scripts/pm_heartbeat_check.py --format text` at the start of PM heartbeat work.
- The final customer report can be short, but the run must internally answer PMHQ0-PMHQ10.
- If any answer lacks evidence, the PM action should be to request/produce evidence, not to invent certainty.
- If the process itself blocks customer progress, mark `framework-capture` risk and propose a smaller safe deliverable or framework patch.

---

## Phase 0 — Context map

### PMHQ0_context_map
**Question:** Do I have the minimal map of PM, engineering, and runtime truth?

**Answer rules:**
- Read `PM_HEARTBEAT.md`, `docs/pm/README.md`, `docs/pm/pm-status.md`.
- Read engineering truth from `HEARTBEAT.md`, `ISSUES.md`, `ROADMAP.md`, and `ORID_DECISIONS.md`.
- Check dirty files before editing.

**Evidence:** `git status --short --branch`, file paths read, PM checker result.

**If fail:** Do not arbitrate; collect context first.

---

## Phase 1 — Stakeholder expectation

### PMHQ1_stakeholder_expectation
**Question:** What does the customer need now, and what would satisfy them without unsafe live trading?

**Answer rules:**
- State the customer’s expectation in one sentence.
- Treat customer urgency as a real product-risk signal, not as noise.
- Separate “use product now” from “send real buy/add orders now”.
- Identify at least one safe immediate usage lane when live trading is blocked.
- If no lane is visible, challenge the framework/engineering plan before telling the customer to wait.
- If the proposed proof path looks weeks/months long or has unknown time-to-evidence, trigger an `alternative-solution` review immediately.

**Evidence:** user request, PM status, UI/API surfaces, current ROADMAP gate.

**If fail:** Create a customer-facing explanation before asking engineering for more research.

---

## Phase 2 — Artifact truth

### PMHQ2_artifact_truth
**Question:** What do the artifacts prove right now?

**Answer rules:**
- Read machine-readable artifacts before accepting a narrative.
- At minimum classify: current-live blocker, research/deployment candidates, venue readiness, recent drift/pathology.
- Mark stale or missing artifacts explicitly.

**Evidence entrypoints:**
- `data/live_predict_probe.json`
- `data/high_conviction_topk_oos_matrix.json`
- `data/execution_metadata_smoke.json`
- `data/recent_drift_report.json`
- `issues.json`

**If fail:** Ask engineering for artifact refresh or produce a PM blocker.

---

## Phase 3 — Conflict diagnosis

### PMHQ3_conflict_diagnosis
**Question:** Is this a real safety blocker, a communication gap, or a delivery deadlock?

**Answer rules:**
Classify the conflict as one or more:

1. **Safety blocker** — buy/add live exposure would violate a gate.
2. **Evidence gap** — the claim may be true but lacks proof.
3. **UX gap** — safe product value exists but the customer cannot see it.
4. **Planning gap** — no one has named the next smallest deliverable.
5. **Deadlock** — repeated “wait” without artifact movement or safe output.
6. **Framework-capture** — docs, custom skills, or harness rules cause the agent to preserve a blocker narrative instead of finding the next safe customer deliverable.

**Evidence:** blocker fields, UI/API copy, tests, cron/heartbeat outputs, PM status.

**If fail:** Update PM status with the missing classification.

---

## Phase 4 — Engineering claim audit

### PMHQ4_engineering_claim_audit
**Question:** What exactly did engineering claim, and do we accept it?

**Answer rules:**
For each important engineering claim, record:

- claim;
- evidence path/command;
- PM verdict: accepted / rejected / insufficient evidence;
- smaller deliverable if the claim blocks the customer;
- framework verdict if the claim depends on a doc/skill/process rule: customer protection / framework-capture risk / needs patch.

**Evidence:** artifacts, tests, current-state docs, skill/doc paths, browser/API checks when applicable.

**If fail:** Do not tell the customer the claim is true; request evidence.

---

## Phase 5 — Delivery ladder

### PMHQ5_delivery_ladder
**Question:** What can be delivered or used in the next hour?

**Answer rules:**
Start from customer value and choose the highest safe ladder rung, not the lowest process-comfort rung. State the time-to-evidence for the selected rung; if the proof path is weeks/months/unknown, select a parallel `alternative-solution` track too:

1. Diagnostics/visibility only.
2. Research/Strategy Lab usage.
3. Paper or shadow observation.
4. Venue dry-run proof.
5. Live canary rehearsal checklist.
6. Tiny live canary only if all gates pass.

**Evidence:** deployment blocker, support rows/minimum/gap, venue proof, OOS gate, UI/API readiness.

**If fail:** Ask engineering for the smallest safe rung, not a broad “continue research”.

---

## Phase 6 — Action contract

### PMHQ6_action_contract
**Question:** What is the next action, owner, artifact, and verification?

**Answer rules:**
Every PM run must leave a concrete action contract:

- owner: PM / engineering heartbeat / customer;
- action;
- artifact to create or refresh;
- verification command or route;
- fallback if it fails.

**Evidence:** `docs/pm/pm-status.md`, issue ID, command, route, or artifact path.

**If fail:** The PM heartbeat is report-only and should be classified as delivery risk.

---

## Phase 7 — Deadlock escape

### PMHQ7_deadlock_escape
**Question:** If the same blocker repeats, what changes in the system?

**Answer rules:**
- Same “wait” twice → require a one-hour safe deliverable.
- Same blocker three times with no movement → classify missing capability: Map / Tool / Signal / Constraint / Review.
- Same failed patch path three times → ask for an alternative architecture or product lane.
- Same docs/skills/framework loop twice → mark `ORANGE_framework_capture_risk` and patch/simplify the constraining framework.
- Same blocker path projects weeks/months before customer value → mark `ORANGE_alternative_solution_required` and start a parallel option search instead of echoing engineering delay.
- Same PM report has no customer-value delta and repeats prior wording/action → run the anti-equilibrium guard before finalizing.

**Evidence:** PM status, issue ID, prior gates, repeated blocker fields.

**If fail:** Mark `RED_delivery_deadlock` in PM status.

---

## Phase 8 — Alternative solution review

### PMHQ9_alternative_solution_review
**Question:** If engineering validation takes weeks/months or stays stuck, what other solution should start now?

**Answer rules:**
- Estimate time-to-evidence: next heartbeat / same day / within week / weeks-months / unknown.
- If the answer is weeks-months or unknown, do not follow the engineering heartbeat into passive waiting; open an `alternative-solution` track now.
- Alternative tracks may include: simpler strategy scope, different data/source/provider, external tool, manual/paper workflow, narrower market/asset scope, alternate model/architecture, UI-only decision support, or explicit stop/pivot recommendation.
- Preserve non-negotiable live-trading proof gates; the alternative cannot be “lower thresholds until it trades”.
- State the first artifact, route, test, or decision memo that proves whether the alternative is worth continuing.

**Evidence:** time-to-evidence estimate, option list, selected option, proof artifact, rejection reason for unsafe shortcuts.

**If fail:** Classify as `ORANGE_alternative_solution_required` and do not let the PM report sound like engineering delay is the only plan.

---

## Phase 9 — Anti-equilibrium review

### PMHQ10_anti_equilibrium_review
**Question:** Is this PM heartbeat resisting convergence, or did it just rebalance around engineering delay?

**Answer rules:**
- State the **customer-value delta**: what became more usable, clearer, safer, faster to verify, or more honestly blocked.
- Run the **anti-repeat** detector: same blocker, same next action, same safe lane, or same wording requires an escalation or a new artifact ask.
- Estimate **cost-of-delay** for one more heartbeat of waiting: customer value, confidence, opportunity, engineering focus, or capital-safety clarity.
- Perform **hypothesis inversion**: if the main proof path is wrong or too slow, what evidence exposes it fastest?
- Maintain an **option portfolio**: main engineering proof path, adjacent safe deliverable, and true alternative/pivot; select which one gets evidence next.
- Add a **red-team PM** challenge: “am I rationalizing engineering delay, and what would I demand if I represented only customer success?”
- Preserve non-negotiable live-trading proof gates; anti-equilibrium means changing product route or proof strategy, not lowering thresholds.

**Evidence:** previous PM status, current artifact movement, selected option, escalation state, falsification artifact, safe-lane proof.

**If fail:** Mark `ORANGE_framework_capture_risk` or `ORANGE_alternative_solution_required`; after three no-delta repeats, mark `RED_delivery_deadlock`.

---

## Phase 10 — Customer report

### PMHQ8_customer_report
**Question:** Can the customer understand the state in 30 seconds?

**Answer rules:**
Report in Traditional Chinese:

- PM decision color and reason;
- what they can use now;
- what PM actively did or demanded on the customer's behalf;
- what remains blocked and why;
- what engineering must prove next;
- files/verification if anything changed.

**Evidence:** final report, changed files, checker/test results, commit hash when applicable.

---

## Minimal PM Q&A output template

```text
Q: 客戶現在需要什麼？
A: <需求 + 不等於 unsafe live trading 的邊界>

Q: artifact 現在證明什麼？
A: <live blocker / candidate / venue / drift>

Q: 工程說法是否接受？
A: <accepted/rejected/insufficient + evidence>

Q: 下一小時可交付什麼？
A: <safe ladder rung + artifact>

Q: 是否有 framework-capture 風險？
A: <none / constraining doc-skill-rule + patch or bypass>

Q: time-to-evidence 是否太長？替代解法是什麼？
A: <next-hour/same-day/within-week/weeks-months/unknown + alternative-solution track>

Q: 本輪是否避免趨向平衡？
A: <customer-value delta + anti-repeat + cost-of-delay + hypothesis inversion + option portfolio + red-team PM>

Q: 若又卡住怎麼辦？
A: <deadlock escape>
```
