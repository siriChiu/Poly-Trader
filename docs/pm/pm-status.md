# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-20 03:37 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：維持 **YELLOW**；PM 仍站在**客戶成功**一側。Engineering fast heartbeat #1369 已刷新 collect / probe / drift / Top-K / venue / current-state docs 到 `2026-05-19T19:33Z`。客戶現在可以安全使用 Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal 來做研究、影子觀察、減風險與證據累積；但真實買入 / 加倉、自動送單與小額 live canary 仍禁止。

本輪 PM overwrite sync 解決上一版 PM status 的 artifact drift：上一版仍引用 heartbeat #1367 的 support `2/50 gap=48`、breaker `20/50` 與 Top-K `samples=24624`。heartbeat #1369 的 fresh artifacts 顯示 canonical breaker 為 `breaker_clear`（`release_ready=true` / `17/50` / `additional_recent_window_wins_needed=0`），但部署仍 fail-closed，因為 current-live bucket 是 `CAUTION|base_caution_regime_or_bias|q15`，exact support 只有 `5/50`（`gap=45`），`deployment_blocker=under_minimum_exact_live_structure_bucket`。這是「可做影子 / 研究 / 減風險」，不是 live-ready。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-19T19:33:05.929038Z`; canonical target is `simulated_pyramid_win`。
- `signal=HOLD` / `should_trade=false` / confidence `0.360556`；regime `bear` / gate `CAUTION` / entry quality label `C`。
- Primary blocker: `deployment_blocker=under_minimum_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Current-live support remains fail-closed: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`, rows `5/50`, `gap=45`。
- Layer truth: `allowed_layers_raw=1` but final `allowed_layers=0`; `allowed_layers_reason=under_minimum_exact_live_structure_bucket`; `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=5`, `previous_rows=5`, `delta_vs_previous=0`, `stagnant_run_count=2`, `support_rows_needed=45`, `regression_basis=legacy_or_different_semantic_signature`, `escalate_to_blocker=true`。歷史 reference heartbeat `1250` 有 q15 `173/50`，但 `calibration_window`、`entry_quality_label`、`regime_label` 不吻合 current support_identity；只能作 legacy reference，不能宣稱 current identity 已被支持。
- Circuit breaker audit: `data/circuit_breaker_audit.json` generated at `2026-05-19T19:33:07.508505Z`; verdict `breaker_clear`; release math `release_ready=true`, recent-window `17/50` wins, required `15/50`, `additional_recent_window_wins_needed=0`, `current_streak=3`。
- Direct action truth: wait/observe path stays no-order；buy/add/live-risk path remains blocked by current-live support guardrail；risk-off `reduce / sell` plus wait/diagnostics/mode toggle remain the only acceptable runtime-side actions。

**PM verdict：接受「breaker 已清但 live buy/add 仍不能放行」。不可把 `breaker_clear`、entry-quality floor、legacy q15 `173/50` 或 Top-K OOS pass 包裝成 deployment closure；current exact support `5/50 gap=45` 才是第一 blocker。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-19T19:02:53.755758+00:00`; `artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `artifact_age_minutes=30.93`, `artifact_stale_after_minutes=60.0`。
- Matrix payload: `samples=24626`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`。OOS-pass 候選仍只能作 paper/shadow evidence，因為 live support route is not deployable。
- Nearest runtime-blocked OOS-pass row: `random_forest / all / current_full / top_2pct`, `oos_roi=0.6884`, `win_rate=0.8621`, `profit_factor=12.4161`, `max_drawdown=0.027`, `worst_fold=0.0959`, `trade_count=58`; verdict remains `not_deployable` because `deployment_blocker=under_minimum_exact_live_structure_bucket` and current support is only `5/50 gap=45`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence; Strategy Lab can show high-conviction research with blocker-first copy, not deployable evidence.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-19T19:33:47.913722Z`。
- `runtime_ready=false` / `runtime_ready_count=0` / `venues_checked=2` / `ok_count=1`; `readiness_state=blocked_until_runtime_lifecycle_proof`。
- Runtime blockers: fill lifecycle not verified, live exchange credential not verified, order ack lifecycle not verified, metadata contract not passed, venue adapter not connected, venue config disabled。
- OKX: adapter supported and enabled, but `credentials_configured=false`, `proof_state=public_metadata_only`; live exchange credential, order ack lifecycle, and fill lifecycle are not verified。
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config enablement, credential, order ack, and fill lifecycle are missing。

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。Credential 只顯示布林，不洩漏 secret。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-19T19:33:01.650689+00:00`。
- Target: `simulated_pyramid_win`; full sample rows `24490`, full sample win rate `61.66%`。
- Primary recent 250 rows: `wins=49/250`, `win_rate=19.6%`, dominant regime `bear=86.0%`, alerts `label_imbalance, regime_shift`, `avg_quality=-0.1176`, `avg_pnl=-0.0069`, `avg_time_underwater=0.6968`。
- Latest 100 rows: `wins=26/100`, `win_rate=26.0%`, dominant regime `bear=100%`, `avg_simulated_pnl=-0.0045`, `avg_simulated_quality=-0.0545`。

**PM verdict：近期品質惡化仍支持 fail-closed；drift artifacts 可作研究與影子觀察題目，但不能被包裝成 live patch 或 deployable gate。**

### Data/source continuity and issue tracker

- Heartbeat #1369 final collection moved data by `+1 raw`, `+1 features`, `+0 labels`: DB counts are Raw `33707`, Features `24769`, Labels `67088`, `simulated_pyramid_win=56.54%`。
- Label horizon status is expected lookahead lag, not current collector failure: 240m rows `701/701`, latest target `2026-05-19 16:09:42.797462`; 1440m rows `625/625`, latest target `2026-05-18 20:10:05.492332`。
- Source blockers remain `8`: examples include sparse-source archive gaps, `[REDACTED]` credential/auth blockers, and Polymarket Gamma TLS verification failure under `tls_verify_required_no_insecure_fallback`。Forward archives are being logged; credential-like values stay `[REDACTED]`。
- `issues.json` has `10` open issues. Open P0s remain: current-live deployment blocker and high-conviction Top-K live-release blocker; PM-relevant P1s remain model stability, venue readiness, source coverage, TLS verification, leaderboard contract, and q15 exact support under-minimum governance。

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看 engineering heartbeat 每小時只說等。

### PM answer

可以立刻使用的產品價值：

1. **Dashboard**：看 current-live blocker、breaker release math、4H context、decision quality、feature continuity / source blockers；現在主阻塞是 `under_minimum_exact_live_structure_bucket`，breaker 是 `breaker_clear`，support 邊界是 `exact_bucket_present_but_below_minimum` / `exact_live_bucket_present_but_below_minimum` reference lane 與 `5/50 gap=45`。
2. **Strategy Lab**：可看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；矩陣 fresh（`samples=24626`），但仍只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；live buy/add 仍由 guardrail fail-closed。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 exact support rows、runtime gates、venue proof、Top-K support overlay 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪不升級為 `ORANGE_framework_capture_risk`，理由是 engineering heartbeat #1369 有 artifact movement：資料新增 `+1/+1/+0`，q15 support 從 #1367 的 `2/50 gap=48` 前進到 `5/50 gap=45`，breaker release math 仍 clear，Top-K matrix 保持 `artifact_freshness_status=fresh` 且 `samples=24626`，venue smoke 仍揭示 proof gap，recent drift / support artifacts 明確標示不可部署，current-state docs 已被 runner overwrite sync。PM 的修正是把 PM status overwrite sync 到 `19:33Z` current truth；安全 gate 沒有降低。

PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof、Top-K freshness proof、breaker/support movement、venue proof、artifact sync、recent-tail falsification 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有任何 artifact movement 或 customer-usable lane proof，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact q15 support lane（本小時最高 live blocker）**：刷新 live probe / q15 support audit，直接顯示 current rows 是否從 `5/50` 往 `50/50` 前進、rows needed、delta vs previous、stagnant count，且 legacy/proxy/neighbor support 只能作 reference/governance lane。
2. **Recent tail root-cause lane**：針對 latest-250 `19.6%` win rate、bear dominant、`avg_quality=-0.1176`、`avg_pnl=-0.0069` 與 compressed/null-heavy feature diagnostics，交付一個可測的 no-new-risk / shadow-only falsification artifact；不得把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only；不可用過期 matrix 暗示 fresh deployable evidence。
4. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免下一輪 PM heartbeat 再用 stale q00/circuit-breaker literals 誤通過。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；engineering heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：fresh live probe / q15 support audit 顯示 `5/50 gap=45` 是否有 movement；recent drift no-new-risk / shadow-only falsification artifact clearly labels deployable=false；Top-K matrix 保持 fresh 或 Strategy Lab / `/api/models/leaderboard` stale label；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement 或 safe product proof，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 先修 harness gap。
