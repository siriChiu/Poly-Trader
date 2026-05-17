# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-18 04:31:43 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 站在**客戶成功**一側。工程端「不能放行 risk-on live buy/add」目前仍有 machine-readable artifact 支撐，而且這個 gate 保護客戶資金，不能降低；但它只阻止真實買入 / 加倉 / 啟用自動送單，不阻止客戶現在使用 Poly-Trader 做研究、診斷、paper/shadow、dry-run readiness、Shadow Trade Ledger 與 canary rehearsal。

當前不是 `GREEN_live_canary_ready`，因為 current-live q15 exact support 仍只有 7/50，且 venue runtime proof 仍缺。也不是 `ORANGE_framework_capture_risk`，因為 engineering/PM current-state docs 已把 safe customer lane 產品化（Strategy Lab、Execution Console shadow、M5 readiness、venue checklist、區間影子觀察），沒有把「等待」當成唯一輸出；但 framework-capture 仍是每輪必檢風險。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-17T20:15:01.516002Z`.
- `signal=HOLD` / `should_trade=false`.
- `deployment_blocker=under_minimum_exact_live_structure_bucket`.
- `runtime_closure_state=patch_inactive_or_blocked`.
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`.
- `current_live_structure_bucket_rows=7` / `minimum_support_rows=50` / `gap=43`.
- `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum`.
- `allowed_layers_raw=1` but `allowed_layers=0` because `allowed_layers_reason=under_minimum_exact_live_structure_bucket`.
- `api_trade_guardrail_active=true`; allowed risk-off sides are `reduce` and `sell` only.
- Support progress: `status=semantic_rebaseline_under_minimum`, `delta_vs_previous=0`, `previous_rows=7`, `stagnant_run_count=2`, `regression_basis=legacy_or_different_semantic_signature`, `escalate_to_blocker=true`.
- Active repair: `phase=semantic_evidence_backfill_or_exact_accumulation`, `component_verify_ready=false`, `live_exposure_allowed=false`, `shadow_or_paper_allowed=true`, `current_signal=HOLD`, `current_allowed_layers=0`, `guardrail=under_minimum_exact_live_structure_bucket`.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-17T20:02:57.647032+00:00`; freshness status is `fresh` at latest check.
- Matrix status: `row_count=24`, `samples=24506`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`.
- Runtime overlay remains blocked by exact support: `support_route_verdict=exact_bucket_present_but_below_minimum`, `bucket_rows=7/50`, `gap=43`, `deployment_blocker=under_minimum_exact_live_structure_bucket`.
- Nearest deployable candidate: `logistic_regression / current_full / all / top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `oos_gate_passed=true`, but `deployable_verdict=not_deployable` because live gate failures remain `support_route_not_deployable` and `deployment_blocker_active`.
- Highest ROI row (`xgboost / top_10pct`) is also `not_deployable` and fails model gates (`max_drawdown_too_high`, `worst_fold_negative`) plus live gates.

**PM verdict：可展示「最接近部署候選」與「為何還不能部署」，可用於研究與 paper/shadow；不可標成 live deployable。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-17T20:15:11.000384Z`.
- `runtime_ready=false` / `runtime_ready_count=0` / `readiness_state=blocked_until_runtime_lifecycle_proof`.
- OKX: `adapter_supported=true`, `enabled_in_config=true`, `credentials_configured=false`, `proof_state=public_metadata_only`; missing live exchange credential, order ack lifecycle, and fill lifecycle.
- Binance: `adapter_supported=false`, `enabled_in_config=false`, `credentials_configured=false`, `proof_state=adapter_unsupported`; adapter, metadata contract, config, credential, order ack, and fill lifecycle are missing.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-17T20:14:57.931153+00:00`.
- Target: `simulated_pyramid_win`; primary window: last 100 rows.
- `win_rate=20.0%`, `wins=20`, `losses=80`.
- Dominant regime: `bear=92.0%`.
- `avg_simulated_quality=-0.1273`, `avg_simulated_pnl=-0.0076`, `avg_drawdown_penalty=0.2381`.
- Alerts: `label_imbalance`, `regime_concentration`, `regime_shift`.
- Adverse streak: 63 consecutive `target=0` rows from `2026-05-15 10:17:22.108364` to `2026-05-16 09:01:34.702823`.
- Top shift features: `feat_local_top_score`, `feat_rsi14`, `feat_local_bottom_score`, `feat_eye`, `feat_4h_bb_pct_b`.

**PM verdict：近期品質惡化支持 fail-closed；更需要把 safe customer lane 做成可操作產品，而不是只說等待。**

### Issue tracker

- `issues.json` has 8 open issues.
- Open P0s: `P0_current_live_deployment_blocker`, `P0_high_conviction_topk_roi_gate`.
- PM-relevant P1s: model stability, venue readiness, fin_netflow auth blocker, leaderboard recent-window contract, nest_pred TLS verification, q15 exact support stalled under breaker context.

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看工程心跳每小時都只說等。

### PM answer

可以立刻使用的產品價值：

1. **Strategy Lab**：看 high-conviction Top-K / leaderboard 候選策略、OOS ROI、win rate、drawdown、profit factor、worst fold，以及 runtime-blocked 原因；最接近部署候選可做研究與 paper/shadow，不可 live deploy。
2. **Dashboard**：看 current-live blocker、4H context、decision quality、feature continuity / source blockers；`under_minimum_exact_live_structure_bucket` 是目前唯一 current-live deployment blocker。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、風險降低 / 診斷；不可做真實買入 / 加倉。
4. **區間 / 擁塞實戰拆解**：使用 range-chop playbook 做區間影子觀察、取消掛單 / 減碼劇本與證據收集；`risk_on_order_enabled=false`、`order_submission_enabled=false`，reduce-risk 仍可用。
5. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段；credential 只顯示布林，不洩漏 secret。
6. **Canary rehearsal**：先做 canary gap checklist；等 support rows、venue proof、runtime gates 全過後才談極小額 live canary。

---

## 4. Framework-capture guard

本輪沒有升級為 `ORANGE_framework_capture_risk`，理由是 current-state docs 和 artifacts 已列出安全可用 lane，且本輪 PM 主動把 `docs/pm/pm-status.md` 從 5/50 舊 truth 同步到 7/50 最新 truth，而不是只複述 blocker。

但 PM 保留 framework-capture 檢查：如果 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 下輪只重複 fail-closed，而沒有交付 safe customer lane、route/API/test/UI proof 或框架簡化，就升級為 `ORANGE_framework_capture_risk`。若連續三輪沒有 artifact movement，升級為 `RED_delivery_deadlock`。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Support evidence lane**：刷新 q15 support audit，顯示 current rows、rows needed、delta vs previous、stagnant count、下一筆 exact row 如何累積；目標是把 7/50 往 50/50 推進，或證明為何停滯。
2. **Customer-usable lane**：確認 `/execution` 的 paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作，並以 route/API/test/browser proof 支撐。
3. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
4. **Strategy Lab lane**：把 nearest-deployable Top-K 候選的「OOS 已過、live gate 未過、可 paper/shadow、不可 live」狀態用操作員繁中 copy 顯示清楚。
5. **Recent drift lane**：針對 last-100 win_rate 20%、bear 92%、adverse streak 63、top-shift features 的 canonical pathology，要求下一輪給出一個可測的 blocker root-cause patch 或 falsification test。
6. **Framework simplification lane**：若 custom skills/docs 造成反覆等待，必須點名限制來源並提出不降低安全 gate 的簡化、旁路或文件修補。

---

## 6. Next-hour gate

**Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：`/execution` paper/shadow 或 dry-run readiness 可操作 proof、q15 exact support audit refresh 並顯示 7/50 → 下一狀態、Strategy Lab nearest-deployable copy/API proof、或 recent drift root-cause falsification test。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk`；若連續三次沒有 artifact movement，升級為 `RED_delivery_deadlock` 並要求工程 heartbeat 先修 harness gap。
