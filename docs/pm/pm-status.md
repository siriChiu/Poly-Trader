# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-18 18:31:00 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 站在**客戶成功**一側。最新 machine-readable artifacts 仍明確禁止 live buy/add、真實買入 / 加倉、自動送單與小額 live canary；但產品不是停工，客戶現在可安全使用 Strategy Lab、Dashboard、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 做研究、影子觀察、減風險與證據累積。

最新 `data/live_predict_probe.json`（`2026-05-18T10:02:44.981786Z`）顯示：`target_col=simulated_pyramid_win`、`signal=CIRCUIT_BREAKER`、`should_trade=false`、`deployment_blocker=circuit_breaker_active`、`deployment_blocker_source=circuit_breaker`、`runtime_closure_state=circuit_breaker_active`、`release_ready=false`。熔斷 release math 是：`current_streak=34`（需 `<50`，這一項已達）、最近 50 筆 `wins=6/50`、`current_recent_window_win_rate=12.0%`，需至少 `15/50` 與 `>=30%`，因此 `additional_recent_window_wins_needed=9`。

同一 live probe 保留 current-live support 邊界：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00`、`support_route_verdict=exact_bucket_unsupported_block`、`support_governance_route=exact_live_lane_proxy_available`、`current_live_structure_bucket_rows=0/50`、`gap=50`、`support_progress.status=semantic_rebaseline_under_minimum`、`stagnant_run_count=5`、`stalled_support_accumulation=false`。`allowed_layers_raw=1` 但 final `allowed_layers=0`，原因是 `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`。因此 risk-on live exposure 仍必須 fail-closed。

本輪不升級為 `ORANGE_framework_capture_risk`：熔斷、exact support、venue proof 這些 gate 都有 artifact proof，且保護客戶資本；同時 safe customer lanes 已被 API/UI/docs 產品化。不過 PM 將 `release_ready=false`（還差 9 勝）、support `0/50`、`stagnant_run_count=5`、recent last-100 `win_rate=23.0%` / `bear=100%` / adverse streak `34`、以及 3 個 P0 + 7 個 P1 開放議題列為 customer-value 壓力點：工程 heartbeat 下輪不得只說等待，必須交付 breaker release movement、support movement/root-cause falsification、venue proof、paper/shadow UI/API proof，或框架簡化之一。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-18T10:02:44.981786Z`.
- Canonical target: `simulated_pyramid_win`.
- `signal=CIRCUIT_BREAKER` / `should_trade=false`.
- Primary blocker: `deployment_blocker=circuit_breaker_active` / `deployment_blocker_source=circuit_breaker` / `runtime_closure_state=circuit_breaker_active`.
- Release condition: `release_ready=false`; recent-window gate is `6/50` wins, needs `15/50`, so `additional_recent_window_wins_needed=9`; current streak is `34`, below the `<50` streak ceiling.
- Support boundary still matters but is not deployable proof: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00`, `support_route_verdict=exact_bucket_unsupported_block`, `support_governance_route=exact_live_lane_proxy_available`, `current_live_structure_bucket_rows=0`, `minimum_support_rows=50`, `gap=50`.
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=0`, `previous_rows=0`, `delta_vs_previous=0`, `stagnant_run_count=5`, `stalled_support_accumulation=false`, `regression_basis=legacy_or_different_semantic_signature`; legacy `190/50@1202` remains reference-only because calibration window / entry-quality label / regime label mismatch current identity.
- `/api/trade` guardrail is active: buy/add risk-on path must fail closed; allowed risk-off sides are reduce / sell / wait / observe only.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-18T10:03:24.209231+00:00`; freshness checked at `2026-05-18T10:03:37.910038+00:00`; `artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`.
- Matrix status: `samples=24544`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`.
- Runtime overlay is synced to live truth: `deployment_blocker=circuit_breaker_active`, `release_ready=false`, `recent_window_wins=6/50`, `additional_recent_window_wins_needed=9`, `support_governance_route=exact_live_lane_proxy_available`, bucket rows `0/50`, `gap=50`, source live probe `2026-05-18T10:02:44.981786Z`.
- Nearest deployable candidate: `logistic_regression / current_full / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `oos_gate_passed=true`; verdict remains `not_deployable` / `runtime_blocked_oos_pass` because live gate failures are `support_route_not_deployable`, `deployment_blocker_active`, and `breaker_release_not_ready`.

**PM verdict：可展示「最接近部署候選」並用於 research / paper / shadow；不可標成 live deployable。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-18T10:03:33.683748Z`.
- `runtime_ready=false` / `runtime_ready_count=0` / `readiness_state=blocked_until_runtime_lifecycle_proof`.
- OKX: `adapter_supported=true`, `enabled_in_config=true`, `credentials_configured=false`, `proof_state=public_metadata_only`; missing live exchange credential, order ack lifecycle, and fill lifecycle.
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config, credential, order ack, and fill lifecycle are missing.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-18T10:02:40.994028+00:00`.
- Target: `simulated_pyramid_win`; blocking window: last 100 rows.
- `win_rate=23.0%`, wins/losses `23/77`, dominant regime `bear=100.0%`.
- Quality metrics: `avg_simulated_pnl=-0.0067`, `avg_simulated_quality=-0.0800`, `avg_drawdown_penalty=0.1951`.
- Alerts: `regime_concentration`, `regime_shift`; tail/adverse target-0 streak is `34`.
- Top shift features: `feat_4h_rsi14`, `feat_4h_ma_order`, `feat_nq_return_24h`, `feat_4h_bias20`, `feat_tunnel_distance`.

**PM verdict：近期品質惡化支持 fail-closed；也要求工程把 safe customer lane 做成可操作產品，而不是只說等待。**

### Issue tracker

- `issues.json` has 10 open issues: 3 P0 and 7 P1.
- Open P0s: `#H_AUTO_STREAK`, `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`.
- PM-relevant P1s: train-CV gap, model stability, regime drift, venue readiness, fin_netflow auth blocker, leaderboard recent-window contract, nest_pred TLS verification.

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Strategy Lab**：看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；最接近部署候選可做研究與 paper/shadow，不可 live deploy。
2. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature continuity / source blockers；現在主阻塞是 `circuit_breaker_active`，support 邊界是 `exact_bucket_unsupported_block` 與 `0/50 gap=50`。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；`risk_on_order_enabled=false`、`order_submission_enabled=false`，reduce-risk 仍可用。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 breaker release、exact support rows、venue proof、runtime gates 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是 live safety blocker 仍有 artifact proof，而且 safe customer lanes 已存在並可由 artifacts/docs 支撐。`support_governance_route=exact_live_lane_proxy_available` 不是 deployable proof；它只代表治理上有可參照的 lane，不能覆蓋 `support_route_verdict=exact_bucket_unsupported_block`、`0/50`、`release_ready=false` 與 `allowed_layers=0` 的 current-live fail-closed truth。PM 接受這組 blocker 保護客戶資本。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、breaker/support movement、venue proof、artifact sync 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Breaker release lane**：刷新 live probe / circuit-breaker audit，直接顯示最近 50 筆從 `6/50` 往 `15/50` 的變化；若仍停住，提出 recent-window loss root-cause falsification test。
2. **Support evidence lane**：刷新 current bucket support audit，顯示 current rows、rows needed、delta vs previous、stagnant count、下一筆 exact row 如何累積；若 0/50 仍不動，明確證明原因並提出可測修法。
3. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
4. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
5. **Strategy Lab lane**：把 nearest-deployable Top-K 候選的「OOS 已過、live gate 未過、可 paper/shadow、不可 live」狀態用操作員繁中 copy 顯示清楚。
6. **Recent drift lane**：針對 last-100 win_rate 23%、bear 100%、losses 77/100、regime concentration / regime shift、target-0 streak 34 的 canonical pathology，下一輪給出一個可測的 blocker root-cause patch 或 falsification test。

---

## 6. Next-hour gate

**Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：fresh live probe / circuit-breaker audit 顯示 `release_ready`、recent-window wins、required wins、additional wins needed；Top-K support overlay 維持 `deployable_rows=0` 與 `runtime_blocked_candidate_rows=6` 的 fail-closed truth；ISSUES / ROADMAP / ORID current-state docs 保持 `circuit_breaker_active`、`exact_live_lane_proxy_available`、`exact_bucket_unsupported_block`、`0/50 gap=50` 一致；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；current bucket support audit refresh；Strategy Lab nearest-deployable copy/API proof；venue dry-run proof；或 recent drift root-cause falsification test。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
