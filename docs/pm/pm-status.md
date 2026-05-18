# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-18 10:33:12 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 站在**客戶成功**一側。最新 machine-readable artifacts（本輪讀取時約 19–31 分鐘新）仍證明 live buy/add 不可放行，但也證明產品不是停工：Strategy Lab、Dashboard、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 仍是可安全使用的交付階梯。

最新 `data/live_predict_probe.json`（`2026-05-18T02:13:33.914876Z`）顯示：`target_col=simulated_pyramid_win`、`signal=HOLD`、`should_trade=false`、`deployment_blocker=unsupported_exact_live_structure_bucket`、`deployment_blocker_source=decision_quality_contract`、`runtime_closure_state=patch_inactive_or_blocked`、`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00`、`support_route_verdict=exact_bucket_unsupported_block`、`support_governance_route=no_support_proxy`、`allowed_layers_raw=2`、final `allowed_layers=0`。當前 exact support 仍是 **0/50（gap=50）**，`support_progress.status=semantic_rebaseline_under_minimum`，`stagnant_run_count=3`，`stalled_support_accumulation=false`。因此真實買入 / 加倉、risk-on live exposure、自動送單與小額 live canary 仍不可放行。

本輪不升級為 `ORANGE_framework_capture_risk`：exact-support gate 有 artifact proof，而且這個 gate 保護客戶資本，不是單純流程慣性；safe customer lanes 也已被 current-state docs / artifacts 明確產品化。不過 PM 將 support 0/50 連續停滯列為**下一小時 customer-value 壓力點**：如果工程 heartbeat 下輪仍只有「等待」而沒有 support movement、root-cause falsification、venue proof、paper/shadow UI/API proof、或框架簡化，就升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 只會重複 blocker narrative，升級為 `ORANGE_framework_capture_risk`。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-18T02:13:33.914876Z`.
- Canonical target: `simulated_pyramid_win`.
- `signal=HOLD` / `should_trade=false`.
- `deployment_blocker=unsupported_exact_live_structure_bucket` / `deployment_blocker_source=decision_quality_contract`.
- `runtime_closure_state=patch_inactive_or_blocked`.
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00`.
- `current_live_structure_bucket_rows=0` / `minimum_support_rows=50` / `gap=50`.
- `support_route_verdict=exact_bucket_unsupported_block` / `support_governance_route=no_support_proxy`.
- `allowed_layers_raw=2` because caution gate caps at two layers; final `allowed_layers=0` because `allowed_layers_reason=unsupported_exact_live_structure_bucket`.
- `/api/trade` guardrail is active: buy/add risk-on path must fail closed; allowed risk-off sides are `reduce` and `sell` only.
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=0`, `minimum_support_rows=50`, `gap_to_minimum=50`, `support_rows_needed=50`, `previous_rows=0`, `delta_vs_previous=0`, `stagnant_run_count=3`, `stalled_support_accumulation=false`, `escalate_to_blocker=true`, `regression_basis=legacy_or_different_semantic_signature`.
- Legacy supported reference remains reference-only: 190/50 at heartbeat `1202` does **not** match current support identity because calibration window, entry quality label, and regime label differ.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-18T02:02:38.561608+00:00`; `artifact_freshness_status=fresh`, `artifact_age_minutes≈11.1` at engineering sync time, `artifact_deployment_blocking=false`.
- Matrix status: `samples=24522`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`.
- Runtime overlay is synced to live probe truth: `support_governance_route=no_support_proxy`, `support_route_verdict=exact_bucket_unsupported_block`, `bucket_rows=0/50`, `gap=50`, `deployment_blocker=unsupported_exact_live_structure_bucket`.
- Nearest deployable candidate: `logistic_regression / current_full / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `oos_gate_passed=true`; verdict remains `not_deployable` / `runtime_blocked_oos_pass` because live gate failures are `support_route_not_deployable` and `deployment_blocker_active`.

**PM verdict：可展示「最接近部署候選」並用於研究 / paper / shadow；不可標成 live deployable。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-18T02:13:43.439493Z`.
- `runtime_ready=false` / `runtime_ready_count=0` / `readiness_state=blocked_until_runtime_lifecycle_proof`.
- OKX: `adapter_supported=true`, `enabled_in_config=true`, `credentials_configured=false`, `proof_state=public_metadata_only`; missing live exchange credential, order ack lifecycle, and fill lifecycle.
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config, credential, order ack, and fill lifecycle are missing.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不得洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-18T02:13:30.273170+00:00`.
- Target: `simulated_pyramid_win`; primary/blocking window: last 100 rows.
- `win_rate=23.0%`, losses `77/100`, dominant regime `bear=100.0%`, `avg_simulated_pnl=-0.0060`, `avg_simulated_quality=-0.0797`, `avg_drawdown_penalty=0.2028`.
- Alerts: `regime_concentration`, `regime_shift`.
- Tail context: last-100 rows are weekend-heavy (`weekend_share=77%`) and feature compression is visible (`unexpected_compressed_count=9`, `null_heavy_count=17`); top shift examples include `feat_local_top_score`, `feat_rsi14`, and short-window NQ / 4H features in longer windows.

**PM verdict：近期品質惡化支持 fail-closed；也要求工程把 safe customer lane 做成可操作產品，而不是只說等待。**

### Issue tracker

- `issues.json` has 7 open issues: 2 P0 and 5 P1.
- Open P0s: `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`.
- PM-relevant P1s: model stability, venue readiness, fin_netflow auth blocker, leaderboard recent-window contract, nest_pred TLS verification.

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Strategy Lab**：看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；最接近部署候選可做研究與 paper/shadow，不可 live deploy。
2. **Dashboard**：看 current-live blocker、4H context、decision quality、feature continuity / source blockers；`unsupported_exact_live_structure_bucket` 是目前唯一 current-live deployment blocker。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；`risk_on_order_enabled=false`、`order_submission_enabled=false`，reduce-risk 仍可用。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 exact support rows、venue proof、runtime gates 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是 live safety blocker 仍有 artifact proof，而且 safe customer lanes 已存在並可由 artifacts/docs 支撐。`support_governance_route` 已從上一版 PM status 的 `exact_live_lane_proxy_available` 收斂為最新 artifact 的 `no_support_proxy`；PM 接受這是更嚴格、更安全的 blocker truth。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、support movement、venue proof、artifact sync 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Support evidence lane**：刷新 current bucket support audit，顯示 current rows、rows needed、delta vs previous、stagnant count、下一筆 exact row 如何累積；目標是把 0/50 往 50/50 推進，或明確證明為何三輪仍 0 並提出可測修法。
2. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
3. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
4. **Strategy Lab lane**：把 nearest-deployable Top-K 候選的「OOS 已過、live gate 未過、可 paper/shadow、不可 live」狀態用操作員繁中 copy 顯示清楚。
5. **Recent drift lane**：針對 last-100 win_rate 23%、bear 100%、losses 77/100、weekend-heavy / compressed-feature context 的 canonical pathology，下一輪給出一個可測的 blocker root-cause patch 或 falsification test。

---

## 6. Next-hour gate

**Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：fresh live probe、Top-K support overlay、ISSUES / ROADMAP / ORID current-state docs 保持 `no_support_proxy`、`exact_bucket_unsupported_block`、`0/50 gap=50` 一致；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；current bucket support audit refresh 並顯示 0/50 → 下一狀態；Strategy Lab nearest-deployable copy/API proof；venue dry-run proof；或 recent drift root-cause falsification test。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
