# HEARTBEAT.md - Poly-Trader 負熵心跳 (5 min loop)

> 角色定義: AI_AGENT_ROLE.md | 架構: ARCHITECTURE.md

## Core Mission: Negentropy

Poly-Trader is not a static system - it must continuously import energy (new data, new methods) and export entropy (bad features, stale models).

**Three Laws:**
1. Closed systems decay -> must regularly inject new data / new perspectives / new methods
2. Every sense must earn its place -> IC is the only judge; IC < 0.05 = replace
3. Every decision traces to "what work it did" -> results over intent

**Ultimate Target: sell_win_rate >= 90%**

---

## Loop Steps (every heartbeat, no skipping)

### Step 0: Read AI_AGENT_ROLE.md
- Confirm role, discipline, boundaries
- Confirm current P0/P1 issues
- Confirm 90% target

### Step 1: Data Collection
- Run `ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python scripts/dev_heartbeat.py"`
- Run collector for latest raw data
- Record: raw/feature/label counts, BTC price, derivatives

### Step 2: Sense Evidence Check
- IC per sense (h=4h horizon)
- Check std, range, unique_count
- IC < 0.05 = RED flag -> must replace or redesign
- std ~ 0 = WARNING -> no variance = noise
- Ask: "Did replacing this sense last round improve win rate?"

### Step 3: Multi-Forum Discussion
#### 3.1: Six Hats (every heartbeat)
| Hat | Question |
|-----|----------|
| WHITE | Facts: data volume, ICs, CV accuracy, test status? |
| RED | Gut feeling: does the system feel trustworthy? What's unsettling? |
| BLACK | Risk: where is entropy leaking? Overfit? Feature leak? Model selection unstable? |
| YELLOW | Value: what's working? What improved last round? |
| GREEN | Novelty: new data source? New method? Old assumption to discard? |
| BLUE | Decision: next step, priority, resource allocation? |

#### 3.2: ORID -> Action
| Phase | Content |
|-------|---------|
| O (Objective) | White facts + IC + test results |
| R (Reflective) | Red feelings + trend + risk |
| I (Interpretive) | Black risks + causal analysis |
| D (Decisional) | Blue priority -> P0-P5 actions written to ISSUES / PRD / ROADMAP / ARCHITECTURE |

### Step 4: ISSUES State
- List unresolved issues + priority
- Evaluate impact and urgency
- If ISSUES is empty, CREATE issues -> ask: "Why aren't we at 90% yet?"

### Step 5: Fix and Test
#### 5.1: Fix issues (no user questions, just fix)
- Fix code, don't just discuss
- git diff before committing
- Verify no regression

#### 5.2: Test if code changed
- `ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python tests/comprehensive_test.py"`
- Narrow tests if data pipeline or model changed

### Step 6: Report
```
Poly-Trader Heartbeat [time]
- Raw: N / Features: N / Labels: N
- BTC: $N | FNG: N | Derivatives: LSR=N GSR=N Taker=N OI=N
- Sense IC (h=4): Eye=N / Ear=N / Nose=N / Tongue=N / Body=N / Pulse=N / Aura=N / Mind=N
- Model: Train=% / CV=% / SellWR=%
- Hats: WHITE=[facts] BLACK=[risk] GREEN=[novelty] BLUE=[decision]
- ORID D: [action items]
- Changes this round: [what was done]
- Tests: pass/fail
- Gap to 90%: [delta, main blocker]
- Docs updated: ISSUES / PRD / ROADMAP / ARCHITECTURE
```

---

## Discipline
1. Always read AI_AGENT_ROLE.md first
2. Full Step 0-6, no shortcuts
3. D must produce action items (written to ISSUES counts)
4. No user questions - fix it directly
5. Every change = git commit
6. Negentropy - every round must ask: "Was today more ordered than yesterday?"

---

## Path to 90% Win Rate

### Phase A: Data Integrity
- [ ] raw -> features -> labels pipeline, zero leakage
- [ ] IC < 0.05 senses must be replaced
- [ ] Historical data replayable, recomputable, versioned
- [ ] sell_win label correctly aligned with trading behavior

### Phase B: Model Calibration
- [ ] Replace DummyPredictor with IC-weighted multi-signal fusion
- [ ] Confidence calibration (Platt / isotonic / temperature)
- [ ] Regime-aware model selection
- [ ] Abstain mechanism: low confidence = no trade

### Phase C: Backtest Verification
- [ ] Reproducible, comparable, auditable backtests
- [ ] sell_win_rate, profit_factor, sharpe visible on dashboard
- [ ] Online metrics match backtest definition

### Phase D: Dashboard Usability
- [ ] Price x Senses overlay chart clear and visible
- [ ] IC bars, win-rate heatmaps, regime-wise charts
- [ ] Empty charts show WHY, not blank
- [ ] Dark theme, Chinese, < 3s to understand

### Phase E: Perpetual Negentropy
- [ ] Each heartbeat: top sense, worst sense, replace?
- [ ] New sources: Twitter/X, news, Polymarket, VIX, DXY, macro calendar
- [ ] New methods: SHAP, ensemble stacking, online learning
- [ ] System health tracking: data volume, IC distribution, label balance, model drift

---

## Environment Constraints

All code development, modification, and testing must happen on Windows host:
- Host: Kazuha@192.168.0.238
- Dir: C:\Users\Kazuha\repo\Poly-Trader
- No Raspberry Pi development (only runs OpenClaw Gateway)

Rules:
1. Read: ssh Kazuha@192.168.0.238 "type C:\Users\Kazuha\repo\Poly-Trader\file"
2. Write: via SSH
3. Run: ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python script"
4. Git: ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && git ..."
5. Never create/modify code in ~/.openclaw/workspace/Poly-Trader/
