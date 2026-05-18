# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-19 07:33:25 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 站在**客戶成功**一側。最新 machine-readable artifacts 仍明確禁止 `live buy/add`、真實買入 / 加倉、自動送單與小額 live canary；但產品不是停工，客戶現在可安全使用 Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 做研究、影子觀察、減風險與證據累積。

最新 `data/live_predict_probe.json`（`2026-05-18T23:02:03.378792Z`，本 PM run wall-clock age 約 `30.7m`）顯示：`target_col=simulated_pyramid_win`、`signal=CIRCUIT_BREAKER`、`should_trade=false`、`deployment_blocker=circuit_breaker_active`、`deployment_blocker_source=circuit_breaker`、`runtime_closure_state=circuit_breaker_active`、`release_ready=false`。熔斷 release math 維持 `9/50`：最近 50 筆 `current_recent_window_wins=9/50`、`current_recent_window_win_rate=18.0%`，至少需要 `15/50` 與 `>=30%`，因此 `additional_recent_window_wins_needed=6`；`current_streak=2` 仍通過 `<50` 的連敗上限，但 recent-win-rate gate 未通過。

Current-live support 仍 fail-closed：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`、`support_route_verdict=insufficient_support_everywhere`、`support_governance_route=exact_live_lane_proxy_available`、`support_route_deployable=false`、`current_live_structure_bucket_rows=0/50`、`gap=50`、`allowed_layers_raw=1` 但 final `allowed_layers=0`，`allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`。PM 接受這是保護客戶資本的 live blocker；`exact_live_lane_proxy_available` 只是治理 / reference lane，不是部署證明，且 legacy `173/50@1250` 因 `calibration_window / entry_quality_label / regime_label` 不吻合 current support identity，只能 reference-only。

本輪 PM 狀態維持 `YELLOW_shadow_or_paper_usable`，但新增一個 customer-facing freshness pressure：`data/high_conviction_topk_oos_matrix.json` 生成於 `2026-05-18T22:15:53.217046+00:00`，本 PM run wall-clock age 約 `76.9m`，已超過 `artifact_stale_after_minutes=60.0`。它仍可作 last-known fail-closed reference（`deployable_rows=0`、`risk_qualified_rows=6`、`runtime_blocked_candidate_rows=6`），但不再能被 PM 當成 fresh Strategy Lab approval；下一小時必須刷新矩陣，或在 `/api/models/leaderboard` / Strategy Lab 清楚標示 stale / reference-only。

本輪不升級為 `ORANGE_framework_capture_risk`：熔斷、exact support、venue proof 這些 gate 都有 artifact proof，且 safe customer lanes 已產品化，不是只有「等」。但如果下一輪只重複 fail-closed，沒有 Top-K refresh 或 UI/API stale 標記、沒有 breaker/support movement、沒有 venue proof、也沒有 safe lane proof，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自 docs/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-18T23:02:03.378792Z`；canonical target `simulated_pyramid_win`。
- `signal=CIRCUIT_BREAKER` / `should_trade=false`。
- Primary blocker: `deployment_blocker=circuit_breaker_active` / `runtime_closure_state=circuit_breaker_active`。
- Release condition: `release_ready=false`; recent-window gate is `9/50` wins, requires `15/50`, so `additional_recent_window_wins_needed=6`; `current_streak=2` passes the `<50` streak ceiling.
- Support boundary is not deployable proof: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=insufficient_support_everywhere`, `support_governance_route=exact_live_lane_proxy_available`, `support_route_deployable=false`, `current_live_structure_bucket_rows=0`, `minimum_support_rows=50`, `gap=50`.
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=0`, `minimum_support_rows=50`, `gap_to_minimum=50`, `delta_vs_previous=0`, `stagnant_run_count=5`; legacy `173/50@1250` remains reference-only because semantic identity mismatches current bucket support identity.
- `/api/trade` guardrail is active: `api_trade_guardrail_active=true`; buy/add risk-on path returns `current_live_deployment_blocker_409`; allowed risk-off sides are `reduce / sell`, with wait / diagnostics / mode toggle still available.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-18T22:15:53.217046+00:00`; payload 自身仍寫 `artifact_freshness_status=fresh`，但本 PM run 以 wall-clock 計算 age 約 `76.9m > artifact_stale_after_minutes=60.0`，因此 PM 視為 stale pressure / last-known reference。
- Matrix payload: `samples=24578`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`。
- Runtime overlay: `deployment_blocker=circuit_breaker_active`, `release_ready=false`, `recent_window_wins=9/50`, `additional_recent_window_wins_needed=6`, `support_route_verdict=insufficient_support_everywhere`, `support_governance_route=exact_live_lane_proxy_available`, bucket rows `0/50`, `gap=50`。
- Nearest candidate remains research / paper-shadow only: `logistic_regression / current_full / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `tier=runtime_blocked_oos_pass`; verdict remains `not_deployable` because live gate failures are `support_route_not_deployable`, `deployment_blocker_active`, and `breaker_release_not_ready`。

**PM verdict：可展示為「上次刷新時的最接近部署候選 / paper-shadow reference」；不可當 fresh deployable evidence。下一小時必須 refresh Top-K matrix 或讓 UI/API 顯示 stale/reference-only。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-18T23:02:44.667183Z`。
- `runtime_ready=false` / `runtime_ready_count=0` / `readiness_state=blocked_until_runtime_lifecycle_proof`。
- Runtime blockers: fill lifecycle 尚未驗證、live exchange credential 尚未驗證、order ack lifecycle 尚未驗證、元資料契約尚未通過、場館 adapter 尚未接入、場館設定停用。
- OKX: `adapter_supported=true`, `enabled_in_config=true`, `credentials_configured=false`, `proof_state=public_metadata_only`; missing live exchange credential, order ack lifecycle, and fill lifecycle.
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config enablement, credential, order ack, and fill lifecycle are missing.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-18T23:01:59.162908+00:00`。
- Target: `simulated_pyramid_win`; full sample `24442` rows, full win rate `61.71%`。
- Blocking window truth: last 100 rows win rate `22.0%`, wins/losses `22/78`, delta vs full sample `-39.71pp`, dominant regime `bear=100.0%`。
- Quality metrics: `avg_simulated_pnl=-0.0058`, `avg_simulated_quality=-0.0875`, weekend share `98.0%`。
- Feature diagnostics flag low-variance / compressed / sparse inputs: `low_variance_count=16`, `compressed_count=13`, `null_heavy_count=17`。

**PM verdict：近期品質惡化支持 fail-closed；也要求工程把 safe customer lane 做成可操作產品，而不是只說等待。**

### Issue tracker

- `issues.json` has 9 open issues: 2 P0 and 7 P1.
- Open P0s: `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`.
- PM-relevant P1s: train-CV/model stability, venue readiness, fin_netflow auth blocker, leaderboard recent-window contract, nest_pred TLS verification, and q15 exact support under-minimum governance.

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature continuity / source blockers；現在主阻塞是 `circuit_breaker_active`，release 還差 `6` 勝，support 邊界是 `insufficient_support_everywhere` / `exact_live_lane_proxy_available` reference lane 與 `0/50 gap=50`。
2. **Strategy Lab**：可看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；但 Top-K matrix 本小時已超過 60 分鐘 freshness target，必須視為 last-known reference，直到刷新或 UI/API 明確標 stale。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；`risk_on_order_enabled=false`、`order_submission_enabled=false`，reduce-risk 仍可用。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 breaker release、exact support rows、venue proof、runtime gates 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是 live safety blocker 仍有 artifact proof，而且 safe customer lanes 已存在並可由 artifacts/docs 支撐。`support_governance_route=exact_live_lane_proxy_available` 不是 deployable proof；它只代表治理 / 參考 lane 可用，不能覆蓋 `support_route_verdict=insufficient_support_everywhere`、`0/50`、`gap=50`、`release_ready=false` 與 `allowed_layers=0` 的 current-live fail-closed truth。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、Top-K refresh 或 stale label、breaker/support movement、venue proof、artifact sync 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Top-K freshness lane（本小時最高 PM 壓力）**：刷新 `data/high_conviction_topk_oos_matrix.json`，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示矩陣 stale/reference-only；不可用 76.9m old matrix 暗示 fresh deployable evidence。
2. **Breaker release lane**：刷新 live probe / circuit-breaker audit，直接顯示最近 50 筆是否從 `9/50` 往 `15/50` 前進；若仍停住，提出 recent-window loss root-cause falsification test。
3. **Support evidence lane**：刷新 current q15 bucket support audit，顯示 current rows 是否從 `0/50` 往 `50/50` 前進、rows needed、delta vs previous、stagnant count、`exact_live_lane_proxy_available` governance lane 能提供什麼 reference evidence。
4. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **Recent drift lane**：針對 last-100 win_rate `22.0%`、bear `100%`、losses `78/100`、weekend concentration / regime shift / compressed sparse features 的 canonical pathology，下一輪給出一個可測的 blocker root-cause patch 或 falsification test。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：Top-K matrix refresh 或 Strategy Lab / `/api/models/leaderboard` stale label；fresh live probe / circuit-breaker audit 顯示 `release_ready`、recent-window wins、required wins、additional wins needed；q15 support audit 顯示 `0/50 gap=50` 是否有 movement；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；venue dry-run proof；或 recent drift root-cause falsification test。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
