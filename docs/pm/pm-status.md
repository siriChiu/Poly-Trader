# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-19 11:33:46 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 站在**客戶成功**一側。最新 machine-readable artifacts 已由工程 heartbeat #1349 / fast diagnostics 刷新到 `2026-05-19T03:18Z` 左右；它們仍明確禁止 `live buy/add`、真實買入 / 加倉、自動送單與小額 live canary，但產品不是停工。客戶現在可安全使用 Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 做研究、影子觀察、減風險與證據累積。

本輪 PM overwrite sync 的材料變化不是 timestamp-only：上一版 PM status 仍引用 `2026-05-19T02:08Z` artifacts、issue count `10`、Top-K matrix `02:03Z`、venue smoke `02:08Z`；最新 artifacts 已推進到 `03:18Z`，Top-K matrix 為 `03:07Z` 且仍 fresh，issues.json 變為 `11` open issues（`2 P0 / 9 P1`）。Recent drift latest-100 仍是 `15.0%` / `15W-85L` / `bear=100%`，但 tail pathology 進一步明確為 `tp_miss=85/85`、`dd_breach=0/85`、`high_underwater=71/85`；shadow replay 顯示 4H observable gate 只能作 falsification / paper-shadow，尚未帶來可部署改善。Live breaker release math 仍是 `9/50`、`additional_recent_window_wins_needed=6`，因此 PM classification 不升級 live-ready，只同步 current truth 與下一小時客戶側要求。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-19T03:18:20.755306Z`；canonical target `simulated_pyramid_win`。
- `signal=CIRCUIT_BREAKER` / `should_trade=false`。
- Primary blocker: `deployment_blocker=circuit_breaker_active` / `deployment_blocker_source=circuit_breaker` / `runtime_closure_state=circuit_breaker_active`。
- Release condition: `release_ready=false`; recent-window gate is `9/50` wins, requires `15/50`, so `additional_recent_window_wins_needed=6`; `current_streak=13` still passes the `<50` streak ceiling, but recent win-rate `18.0% < 30%` does not pass。
- Current-live support remains fail-closed: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=insufficient_support_everywhere`, `support_governance_route=exact_live_lane_proxy_available`, `support_route_deployable=false`, `current_live_structure_bucket_rows=0/50`, `minimum_support_rows=50`, `gap=50`。
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=0`, `previous_rows=0`, `delta_vs_previous=0`, `stagnant_run_count=2`, `support_rows_needed=50`。Legacy `173/50@1250` remains reference-only because semantic identity mismatches current support identity (`calibration_window`, `entry_quality_label`, `regime_label`)；`exact_live_lane_proxy_available` 只提供 governance / reference lane，不能取代 `support_route_verdict=insufficient_support_everywhere` 與 `0/50 gap=50`。
- Layer truth: `allowed_layers_raw=2` but final `allowed_layers=0`; `allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`。
- `/api/trade` guardrail is active: `api_trade_guardrail_active=true`, buy/add path returns `current_live_deployment_blocker_409`; allowed risk-off sides are `reduce / sell`.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-19T03:07:46.299556+00:00`; `artifact_freshness_status=fresh`, `artifact_stale_after_minutes=60.0`。本 PM run wall-clock age 約 26 分鐘，仍低於 freshness target。
- Matrix payload: `samples=24591`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`。
- Runtime overlay remains fail-closed: `deployment_blocker=circuit_breaker_active`, `release_ready=false`, recent-window wins `9/50`, `additional_recent_window_wins_needed=6`, `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, bucket rows `0/50`, `gap=50`。
- Nearest deployable / runtime-blocked OOS-pass row: `logistic_regression / current_full / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `tier=runtime_blocked_oos_pass`; verdict remains `not_deployable` because gate failures are `support_route_not_deployable`, `deployment_blocker_active`, and `breaker_release_not_ready`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence; Strategy Lab can show it as high-conviction research, not deployable evidence.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-19T03:18:30.283902Z`。
- `runtime_ready=false` / `runtime_ready_count=0` / `readiness_state=blocked_until_runtime_lifecycle_proof`。
- Runtime blockers: fill lifecycle 尚未驗證、live exchange credential 尚未驗證、order ack lifecycle 尚未驗證、元資料契約尚未通過、場館 adapter 尚未接入、場館設定停用。
- OKX: `adapter_supported=true`, `enabled_in_config=true`, `credentials_configured=false`, `proof_state=public_metadata_only`; missing live exchange credential, order ack lifecycle, and fill lifecycle。
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config enablement, credential, order ack, and fill lifecycle are missing。

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-19T03:18:17.100708+00:00`。
- Target: `simulated_pyramid_win`; full sample `24453` rows, full win rate約 `61.68%`。
- Latest 100 rows: win rate `15.0%`, wins/losses `15/85`, dominant regime `bear=100.0%`, alerts=`label_imbalance, regime_concentration, regime_shift`。
- Latest-window quality remains negative: baseline `avg_simulated_pnl=-0.0063`, `avg_simulated_quality=-0.1319`。
- Canonical tail root cause: `tp_miss=85/85`, `dd_breach=0/85`, `high_underwater=71/85`; 4H shift root-cause candidates: `feat_4h_bias200`, `feat_4h_bias50`, `feat_4h_rsi14`, `feat_4h_bb_pct_b`, `feat_4h_bias20`。
- No-new-risk shadow replay is **not** deployment proof: `dominant_regime_shadow_gate` blocks all rows and is inconclusive; `observable_4h_shift_shadow_gate` keeps `64` rows with `kept_win_rate=15.62%`, only `+0.62pp` vs baseline and `deployment_verdict=not_deployable_shadow_only_runtime_blocked`; outcome-based gate uses future fields and is falsification-only。

**PM verdict：近期品質惡化支持 fail-closed；shadow replay 已提供可用研究 / 影子觀察題目，但不能被包裝成 live patch 或 deployable gate。**

### Issue tracker

- `issues.json` has 11 open issues: 2 P0 and 9 P1。
- Open P0s: `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`。
- PM-relevant P1s: raw/features/labels gap, live DQ pathology, train-CV/model stability, TW-IC/regime drift, venue readiness, fin_netflow auth blocker, leaderboard recent-window contract, nest_pred TLS verification, and q15 exact support under-minimum governance。

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature continuity / source blockers；現在主阻塞是 `circuit_breaker_active`，release 還差 `6` 勝，support 邊界是 `insufficient_support_everywhere` / `exact_live_lane_proxy_available` reference lane 與 `0/50 gap=50`。
2. **Strategy Lab**：可看 fresh high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；矩陣目前低於 60 分鐘 freshness target，但仍只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；`risk_on_order_enabled=false`、`order_submission_enabled=false`，reduce-risk 仍可用。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 breaker release、exact support rows、venue proof、runtime gates 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是 live safety blocker 仍有 artifact proof，且 safe customer lanes 已存在並可由 artifacts/docs 支撐。`support_governance_route=exact_live_lane_proxy_available` 不是 deployable proof；它只代表治理 / 參考 lane 可用，不能覆蓋 `support_route_verdict=insufficient_support_everywhere`、`0/50`、`gap=50`、`release_ready=false` 與 `allowed_layers=0` 的 current-live fail-closed truth。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、Top-K freshness proof、breaker/support movement、venue proof、artifact sync、recent-tail falsification 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Breaker release lane（本小時最高 live blocker）**：刷新 live probe / circuit-breaker audit，直接顯示最近 50 筆是否從 `9/50` 往 `15/50` 前進；若仍停住，提出 recent-window loss root-cause falsification test。
2. **Recent tail root-cause lane**：針對 latest-100 `15/85`、bear `100%`、`tp_miss=85/85`、`dd_breach=0/85`、`high_underwater=71/85` 與 4H shift features，交付一個可測的 no-new-risk / shadow-only falsification artifact；不得把 `observable_4h_shift_shadow_gate` 目前 `kept_win_rate=15.62%` 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only；不可用過期 matrix 暗示 fresh deployable evidence。
4. **Support evidence lane**：刷新 current q15 bucket support audit，顯示 current rows 是否從 `0/50` 往 `50/50` 前進、rows needed、delta vs previous、stagnant count、`exact_live_lane_proxy_available` governance lane 能提供什麼 reference evidence。
5. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
6. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：fresh live probe / circuit-breaker audit 顯示 `release_ready`、recent-window wins、required wins、additional wins needed；recent drift no-new-risk / shadow-only falsification artifact clearly labels deployable=false；q15 support audit 顯示 `0/50 gap=50` 是否有 movement；Top-K matrix 保持 fresh 或 Strategy Lab / `/api/models/leaderboard` stale label；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
