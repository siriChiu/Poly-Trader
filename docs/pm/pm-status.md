# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-20 08:18 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`**

PM 判定：接受使用者修正，PM heartbeat 不可只是 engineering heartbeat 的下游同步或「跟著工程一起等」；PM 仍以**客戶成功**為北極星。客戶可安全使用的產品 lane 仍是 **YELLOW**：Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；但 **live buy/add / 真實買入 / 加倉 / 自動送單 / 小額 live canary 仍不可放行**。

本輪工程 heartbeat 已完成 fast artifact refresh + collect/backfill；相較上個 PM handoff 的 `14/50`，current exact q15 support 目前是 `19/50`（`gap=31`）。machine-readable `support_progress` 目前顯示 `delta_vs_previous=1`、`previous_rows=18`、`stagnant_run_count=0`，所以 PM 接受「breaker_clear 但 live buy/add 仍 fail-closed」並把本輪工程交付的 **time-to-evidence** 作為客戶側答案：若每輪同速增加 1 筆支持樣本，還需 31 輪；若工程 heartbeat 約每小時一次，約 1.29 天。由於估算未超過一週，本輪維持 `watch_only` alternative review；但如果後續回到 weeks/months 或 unknown，立即進入 `ORANGE_alternative_solution_required` 的 `alternative-solution` 搜尋，而不是讓客戶等幾個月。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-20T00:12:32.669682Z`；canonical target is `simulated_pyramid_win`。
- Runtime signal: `signal=HOLD` / `should_trade=false` / confidence `0.354213`；regime `bear` / `regime_gate=CAUTION` / `entry_quality_label=C` / `decision_quality_label=D`。
- Primary blocker: `deployment_blocker=under_minimum_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Guardrail truth: `allowed_layers_raw=1` but `allowed_layers=0`; `allowed_layers_reason=under_minimum_exact_live_structure_bucket`; `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- Current-live support remains fail-closed: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`, rows `19/50`, `gap=31`。
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=19`, `previous_rows=18`, `delta_vs_previous=1`, `minimum_support_rows=50`, `gap_to_minimum=31`, `stagnant_run_count=0`, `regression_basis=legacy_or_different_semantic_signature`, `escalate_to_blocker=true`。
- Governance reference: historical heartbeat `1250` had q15 `173/50`, but current support identity mismatches `calibration_window / entry_quality_label / regime_label`; it remains legacy reference only, not deployment closure.
- Direct action truth: `api_trade_guardrail_active=true`; `api_trade_buy_guardrail=current_live_deployment_blocker_409`; risk-off sides remain `reduce / sell` only。

**PM verdict：接受「breaker 已清但 current exact support 未達 minimum，所以 live buy/add 仍不可放行」。不可把 `breaker_clear`、legacy q15 `173/50`、allowed raw layer 或 Top-K OOS pass 包裝成 deployment closure。**

### Circuit breaker

- `data/circuit_breaker_audit.json` generated at `2026-05-20T00:12:25.281273Z`。
- Verdict: `breaker_clear`; release math `release_ready=true`, current recent-window wins `19/50`, required `15/50`, `additional_recent_window_wins_needed=0`, `current_streak=12`。

**PM verdict：breaker math is not the live blocker now. It is clear, but exact q15 support and venue runtime proof still block live exposure.**

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-20T00:05:03.771159+00:00`; payload says `artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `artifact_stale_after_minutes=60.0`。
- Matrix payload: `samples=24641`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`。
- Nearest research candidate now includes `model=random_forest`, `top_k=top_2pct`, `oos_roi=0.6884`, `win_rate=0.8621`, `profit_factor=12.4161`, `max_drawdown=0.027`, `worst_fold=0.0959`, `trade_count=58`, `tier=runtime_blocked_oos_pass`, `verdict=not_deployable`, with `deployment_blocker=under_minimum_exact_live_structure_bucket`。
- Support overlay matches current-live truth: bucket `CAUTION|base_caution_regime_or_bias|q15`, support `19/50`, `gap=31`, `support_route=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`, `deployment_blocker=under_minimum_exact_live_structure_bucket`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence. Strategy Lab may prioritize nearest-deployable research rows, but `deployable_rows=0` means no risk-on live action.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-20T00:12:36.634603Z`。
- Summary: `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `ok_count=1`, `readiness_state=blocked_until_runtime_lifecycle_proof`。
- OKX: adapter supported and enabled, but credential state is not live-verified; proof remains `public_metadata_only`; order ack and fill lifecycle are not verified.
- Binance: adapter unsupported and config disabled; metadata contract, credential state, order ack, and fill lifecycle are not verified.
- Credential-like values remain secret-safe; PM status only accepts boolean/proof-state language.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-20T00:12:19.445232+00:00`; target `simulated_pyramid_win`。
- Full sample win rate is about `61.63%`, but primary recent window remains pathological: window `100`, win rate `28.0%`, avg quality `-0.0245`, avg PnL `-0.0029`, alerts `regime_concentration` and `regime_shift`。
- Shadow-only falsification lane remains the acceptable product path: no-new-risk evidence is useful, but it is not a release patch and must keep `deployable=false` / risk-on disabled semantics.

**PM verdict：近期品質惡化支持 paper/shadow-only research；drift artifact 不能被包裝成 live deployment patch。**

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

### PM answer — 客戶現在可用

1. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature/source blockers；主阻塞是 `under_minimum_exact_live_structure_bucket`，support 邊界是 `19/50 gap=31`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows=0` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Range-chop playbook**：做區間影子觀察、取消掛單 / 減碼劇本與證據收集；risk-on order remains disabled。
5. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。
6. **Canary rehearsal**：先回答 canary gap；只有 exact support rows、runtime gates、venue proof、Top-K support overlay 全過後才談極小額 live canary。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪升級為 **`ORANGE_framework_capture_risk` governance overlay**，原因不是 live gate 被否定，而是 PM 必須防止自己被工程 heartbeat 的 blocker 敘事捕獲。Fresh artifacts 有實際刷新與 customer-usable proof：collect/backfill 已執行，live probe、q15 audit、Top-K、breaker audit、recent drift 與 venue smoke 均已刷新；目前 current support 是 `19/50`、`gap=31`，safe lane 仍是 `YELLOW_shadow_or_paper_usable`。本輪 `support_progress` 已有 `delta_vs_previous=1`，且工程已把 time-to-evidence 露出到 Execution Console / `/api/execution/overview`，所以 PM 可以用同一組 artifact 跟客戶說明「仍 fail-closed，但不是沒有進度」。

PM 現在要求每輪都產出 **time-to-evidence**：q15 exact support 何時可能從 `19/50` 往 `50/50` 前進？本輪估算為 `31` 輪 / 約 `1.29` 天（以每輪 +1、工程心跳約 hourly 為假設）；近期品質 `win_rate=28.0%` 何時能被 no-new-risk / shadow-only artifact 證偽？venue runtime proof 何時能從 metadata 走到 dry-run？若答案回到 weeks/months 或 unknown，PM 必須標記 `ORANGE_alternative_solution_required` 並提出 `alternative-solution` portfolio：縮小策略/市場範圍、換資料源或外部工具、改走 manual/paper decision-support、替代模型/架構、或明確 stop/pivot recommendation；不可只把工程 heartbeat 的下一步轉述給客戶。

**Anti-equilibrium guard：** 本輪必須把 PM 從「平衡式等待」拉回客戶價值搜尋。`customer-value delta` 目前是：support 從 `18/50` 到 `19/50` 有 artifact movement、Execution Console / `/api/execution/overview` 已露出 time-to-evidence，客戶可以理解「仍 fail-closed，但不是停工」。`anti-repeat` 結果：不可再只重複 q15 gap；下輪若仍是同一 blocker，必須提供新 artifact movement、missing-capability proof、或替代解法驗證。`cost-of-delay`：每多等一輪但沒有支持樣本/venue proof/UI proof 位移，客戶信心與策略可用性下降，且工程焦點會被單一路徑綁住。`hypothesis inversion`：如果 exact q15 support 累積太慢或近期品質無法證偽，最快暴露點是 stagnation counter、no-new-risk shadow artifact、與 venue dry-run proof 是否仍卡住。`option portfolio`：70% 主路徑追 exact support + venue proof，20% 鄰近安全交付推 paper/shadow decision-support 與 stale/fresh labeling，10% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot。`red-team PM` 挑戰：PM 不可為工程延遲辯護；若下輪沒有客戶可見位移，直接把 governance overlay 升到 `ORANGE_alternative_solution_required`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact q15 support lane（最高 live blocker）**：刷新 live probe / q15 support audit，直接顯示 current rows 是否從 `19/50` 往 `50/50` 前進；若 `delta_vs_previous=0`，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent window `100` 的 `win_rate=28.0%`、`avg_quality=-0.0245`、`avg_pnl=-0.0029` 交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **Alternative-solution lane**：若 exact support closure / recent-tail falsification / venue proof 的 time-to-evidence 超過一週、落入 weeks/months、或工程無法估計，PM 必須在同一輪提出至少三個替代解法並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；engineering heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：q15 exact support rows 從目前 `19/50` 持續 movement，或明確證明 stagnation 的 missing capability；recent drift no-new-risk / shadow-only falsification artifact clearly labels `deployable=false`；Top-K matrix 保持 fresh 或 Strategy Lab / `/api/models/leaderboard` stale label；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。除此之外，PM 必須交付 time-to-evidence bucket（next heartbeat / same day / within week / weeks-months / unknown）與 `alternative-solution` 候選；若主路徑落入 weeks/months/unknown，選出一個下輪可驗證的替代 artifact。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若原因來自文件/skills/harness 過度限制，直接 patch/simplify/bypass 該框架；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 暫停同一路徑敘事，先提出替代架構/產品線/資料源比較。
