# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-20 01:21:37 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：維持 **YELLOW**；PM 仍站在**客戶成功**一側。最新工程 heartbeat #1364 已把 live probe / drift / Top-K / venue / current-state docs 刷新到 `2026-05-19T17:20–17:21Z`。`live buy/add`、真實買入 / 加倉、自動送單與小額 live canary 仍禁止；但客戶不是只能等待：Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 仍可安全使用來做研究、影子觀察、減風險與證據累積。

本輪 overwrite sync 解決上一版 PM status 的 runtime-number drift：上一版仍引用 heartbeat #1361 的 `circuit_breaker_active`、q00 `28/50 gap=22` 與 breaker `14/50`。工程 heartbeat #1364 的 fresh artifacts 顯示 canonical breaker 已解除（`breaker_clear` / `release_ready=true` / `20/50` / `additional_recent_window_wins_needed=0`），但部署仍 fail-closed，因為 current-live bucket 回到 `CAUTION|base_caution_regime_or_bias|q15`，exact support 只有 `2/50`（`gap=48`），`deployment_blocker=under_minimum_exact_live_structure_bucket`。這是 blocker 來源轉移，不是 live-ready 升級。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-19T17:21:05.518657Z`; canonical target `simulated_pyramid_win`。
- `signal=HOLD` / `should_trade=false`。
- Primary blocker: `deployment_blocker=under_minimum_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Current-live support remains fail-closed: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`, rows `2/50`, `gap=48`。
- Layer truth: `allowed_layers_raw=1` but final `allowed_layers=0`; `allowed_layers_reason=under_minimum_exact_live_structure_bucket`; `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=2`, `previous_rows=2`, `delta_vs_previous=0`, `stagnant_run_count=5`, `support_rows_needed=48`, `regression_basis=legacy_or_different_semantic_signature`, `escalate_to_blocker=true`。歷史 reference heartbeat `1250` 有 q15 `173/50`，但 `calibration_window`、`entry_quality_label`、`regime_label` 不吻合 current support_identity；只能作 legacy reference，不能宣稱 current identity 已被支持。
- Circuit breaker audit: `data/circuit_breaker_audit.json` generated at `2026-05-19T17:21:07.716749Z`; verdict `breaker_clear`; release math `release_ready=true`, recent-window `20/50` wins, required `15/50`, `additional_recent_window_wins_needed=0`, `current_streak=0`。
- Direct action truth: wait/observe path stays no-order；buy/add/live-risk path remains blocked by current-live support guardrail；risk-off `reduce / sell` plus wait/diagnostics/mode toggle remain the only acceptable runtime-side actions.

**PM verdict：接受「breaker 已清但 live buy/add 仍不能放行」。不可把 `breaker_clear`、`entry_quality >= floor`、legacy q15 `173/50` 或 Top-K OOS pass 包裝成 deployment closure；current exact support `2/50 gap=48` 才是第一 blocker。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-19T17:09:32.523340+00:00`; `artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `artifact_stale_after_minutes=60.0`。
- Matrix payload: `samples=24623`, `row_count=24`, `deployable_rows=0`, `runtime_blocked_candidate_rows=6`。OOS-pass 候選仍只能作 paper/shadow evidence，因為 live support route is not deployable。
- Nearest deployable / runtime-blocked OOS-pass row: `logistic_regression / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`; verdict remains `not_deployable` because `support_route_not_deployable` and `deployment_blocker_active`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence; Strategy Lab can show high-conviction research with blocker-first copy, not deployable evidence.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-19T17:21:15.064119Z`。
- `runtime_ready=false` / `runtime_ready_count=0` / `venues_checked=2` / `ok_count=1`; `readiness_state=blocked_until_runtime_lifecycle_proof`。
- Runtime blockers: fill lifecycle not verified, live exchange credential not verified, order ack lifecycle not verified, metadata contract not passed, venue adapter not connected, venue config disabled。
- OKX: adapter supported and enabled, but `credentials_configured=false`, `proof_state=public_metadata_only`; live exchange credential, order ack lifecycle, and fill lifecycle are not verified。
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config enablement, credential, order ack, and fill lifecycle are missing。

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-19T17:08:49.802558+00:00`。
- Target: `simulated_pyramid_win`; full sample rows `24485`, full sample win rate `61.66%`。
- Primary recent 250 rows: `win_rate=0.188`（47/250 wins, 203 losses）, dominant regime `bear=84%`, alerts `label_imbalance, regime_shift`, `avg_simulated_pnl=-0.0071`, `avg_simulated_quality=-0.1258`。
- Latest 100 rows remain weak: `win_rate=0.24`, dominant regime `bear=100%`, `avg_simulated_pnl=-0.0052`, `avg_simulated_quality=-0.0738`。

**PM verdict：近期品質惡化仍支持 fail-closed；drift artifacts 可作研究與影子觀察題目，但不能被包裝成 live patch 或 deployable gate。**

### Data/source continuity and issue tracker

- Heartbeat #1364 final collection moved data by `+1 raw`, `+1 features`, `+0 labels`: DB counts are Raw `33696`, Features `24759`, Labels `67077`, `simulated_win=0.5654`。
- Source blockers remain `8`: `fin_netflow` auth missing, `claw` / `claw_intensity` auth missing, `nest_pred` TLS verify failed, plus other sparse-source history gaps. Existing forward archives are being logged; credential-like values stay `[REDACTED]`。
- `issues.json` has `10` open issues. Open P0s remain: `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`。
- PM-relevant P1s remain: train-CV/model stability, venue readiness, fin_netflow auth blocker, leaderboard contract, nest_pred TLS verification, source coverage, and q15 exact support under-minimum governance。

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature continuity / source blockers；現在主阻塞是 `under_minimum_exact_live_structure_bucket`，breaker 已是 `breaker_clear`，support 邊界是 `exact_bucket_present_but_below_minimum` / `exact_live_bucket_present_but_below_minimum` reference lane 與 `2/50 gap=48`。
2. **Strategy Lab**：可看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；矩陣 fresh，但仍只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；live buy/add 仍由 guardrail fail-closed。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 exact support rows、runtime gates、venue proof、Top-K support overlay 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是工程 heartbeat #1364 有 artifact movement：breaker 從 `circuit_breaker_active` 轉為 `breaker_clear`，current-live blocker 被重新定位到 q15 exact support `2/50 gap=48`，Top-K matrix 保持 fresh，venue smoke 仍揭示 proof gap，recent drift / support artifacts 明確標示不可部署。PM 的修正是把 PM status overwrite sync 到 `17:20–17:21Z` current truth；安全 gate 沒有降低。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、Top-K freshness proof、breaker/support movement、venue proof、artifact sync、recent-tail falsification 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact q15 support lane（本小時最高 live blocker）**：刷新 live probe / q15 support audit，直接顯示 current rows 是否從 `2/50` 往 `50/50` 前進、rows needed、delta vs previous、stagnant count，且 legacy/proxy/neighbor support 只能作 reference/governance lane。
2. **Recent tail root-cause lane**：針對 latest-250 `47/250`、bear dominant、`avg_simulated_quality=-0.1258`、`avg_simulated_pnl=-0.0071` 與 compressed/null-heavy feature diagnostics，交付一個可測的 no-new-risk / shadow-only falsification artifact；不得把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only；不可用過期 matrix 暗示 fresh deployable evidence。
4. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免下一輪 PM heartbeat 再用 stale q00/circuit-breaker literals 誤通過。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：fresh live probe / q15 support audit 顯示 `2/50 gap=48` 是否有 movement；recent drift no-new-risk / shadow-only falsification artifact clearly labels deployable=false；Top-K matrix 保持 fresh 或 Strategy Lab / `/api/models/leaderboard` stale label；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
