# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-23 10:22 CST_

> Current-state PM interpretation. Do not append hourly history here; this file is generated from current runtime artifacts by `scripts/sync_pm_status.py` so PM checks fail on real drift, not stale literals.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`；`ORANGE_alternative_solution_required` remains active.**

PM 結論：客戶成功仍是北極星，但 live buy/add safety gate 不可被 customer urgency 推翻。承接上一輪 PM handoff：維持 current-live exact-support blocker、交付 paper/shadow / dry-run / falsification / support-fill proof，且不可降低 live gate。fresh runtime truth 顯示 current-live bucket 是 `BLOCK|bear_bias200_hard_block|q00`；PM 決策不變：current exact support 是 `0/50`、`gap=50`、`support_route_verdict=exact_bucket_unsupported_block`，`support_governance_route=exact_live_lane_proxy_available` 只能當治理 / proxy reference，不是部署閉環。

安全答案：`signal=CIRCUIT_BREAKER` / `should_trade=false` / `deployment_blocker=circuit_breaker_active` / `runtime_closure_state=circuit_breaker_active` / `allowed_layers_raw=0` / `allowed_layers=0` / `allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `execution_guardrail_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active` / `api_trade_guardrail_active=true` / `api_trade_buy_guardrail=current_live_deployment_blocker_409`。客戶可以使用 Dashboard、Strategy Lab、Execution Console、paper/shadow decision-support、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；**真實買入 / 加倉 / live buy/add / 自動送單 / 小額 live canary 仍不可放行**，除非 bounded live-canary policy、current-live gate、support/breaker gate 與 venue lifecycle proof 全部通過。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-23T02:21:25.928808Z`；canonical target is `simulated_pyramid_win`。
- Runtime signal: `signal=CIRCUIT_BREAKER` / `should_trade=false` / confidence `0.500000`；`regime_label=bear` / `regime_gate=BLOCK` / `entry_quality_label=C` / decision quality score `—`。
- Primary blocker: `deployment_blocker=circuit_breaker_active` / `runtime_closure_state=circuit_breaker_active`。
- Guardrail truth: `allowed_layers_raw=0` but `allowed_layers=0`；`allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`；`execution_guardrail_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`。
- Current-live support: `current_live_structure_bucket=BLOCK|bear_bias200_hard_block|q00`, `support_route_verdict=exact_bucket_unsupported_block`, `support_governance_route=exact_live_lane_proxy_available`, rows `0/50`, `gap=50`。
- Support progress: `support_progress_status=stalled_under_minimum` / `regression_basis=same_identity_same_semantic_signature` / `previous_rows=0` / `delta_vs_previous=0` / `stagnant_run_count=5` / legacy reference is reference-only because support identity does not close current deployment.
- Direct action truth: `api_trade_guardrail_active=true`; `api_trade_buy_guardrail=current_live_deployment_blocker_409`; risk-off sides remain `reduce, sell` only。

**PM verdict：接受「熔斷仍 active（recent `0/50`，需要 `15/50`，還差 `15` 勝），且 current exact support 仍是 `0/50`、gap `50`，尚未建立同一 support identity 的精準樣本，所以 live buy/add 仍 fail-closed」。不可把 legacy rows、exact-live-lane proxy rows、Top-K OOS pass、或單一 support/governance gate 包裝成 deployable。**

### Circuit breaker

- Latest artifact `data/circuit_breaker_audit.json` generated at `2026-05-23T02:21:28.411991Z`；verdict `canonical_breaker_active`。
- Release context: `release_ready=false`, recent-window wins `0/50`, required wins `15/50`, `additional_recent_window_wins_needed=15`。
- PM interpretation: breaker is currently active; even after it clears, support evidence, Top-K deployability, and venue runtime proof must all remain verified before live exposure.

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-23T02:22:05.740724+00:00`；`artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `samples=24964`, `row_count=24`, `runtime_blocked_candidate_rows=6`。
- Matrix payload: `deployable_rows=0`, `risk_qualified_rows=6`, `support_route=exact_bucket_unsupported_block`, `deployment_blocker=circuit_breaker_active`, `current_live_structure_bucket=BLOCK|bear_bias200_hard_block|q00`, bucket rows `0/50`, `gap=50`。
- Nearest research candidate: `model=logistic_regression`, `feature_profile=current_full`, `top_k=top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.0220`, `worst_fold=0.2068`, `trade_count=58`, `deployment_candidate_tier=runtime_blocked_oos_pass`, `deployable_verdict=not_deployable`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence. Strategy Lab 可優先顯示 nearest-deployable research rows，但 `deployable_rows=0` means no risk-on live action.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-23T02:22:24.950348Z`。
- Summary: `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `ok_count=1`, `readiness_state=blocked_until_runtime_lifecycle_proof`。
- okx: adapter_supported=true, enabled_in_config=true, credentials_configured=false, proof_state=public_metadata_only, runtime_ready=false, blockers=live exchange credential 尚未驗證, order ack lifecycle 尚未驗證, fill lifecycle 尚未驗證。
- binance: adapter_supported=false, enabled_in_config=false, credentials_configured=false, proof_state=adapter_unsupported, runtime_ready=false, blockers=場館 adapter 尚未接入, 元資料契約尚未通過, 場館設定停用, live exchange credential 尚未驗證, order ack lifecycle 尚未驗證, fill lifecycle 尚未驗證。
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-23T02:21:21.537493+00:00`。
- Full sample rows `24826`。
- Recent canonical window `100`: win_rate `24.0%`, dominant regime `chop(94.0%)`, alerts `regime_concentration, regime_shift`。

**PM verdict：recent drift reinforces paper/shadow-only research and root-cause work. It cannot be packaged as a live deployment patch.**

### Support-fill feasibility / alternative-solution pressure

- `data/q15_support_fill_feasibility.json` generated at `2026-05-23T02:22:22.066618+00:00`；scanned current support identity bucket is `BLOCK|bear_bias200_hard_block|q00`。
- Verdict: `classification=no_exact_bucket_history`, current calibration window `200`, current exact bucket rows `0/50`, identity rows before bucket filter `0`, non-current-bucket identity rows `0`, `gap=50`, `time_to_evidence_bucket=unknown_until_bucket_map_or_signal_redesign`, `missing_capability_class=Map/Signal`, `alternative_solution_required=true`。
- Reference-only evidence: `best_reference_window=100`, `best_reference_exact_bucket_rows=0`, `best_reference_evidence_role=reference_only_calibration_window_mismatch`；reference rows cannot be counted as deployable support unless support identity is deliberately rebaselined and fully reverified.
- Selected next safe artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`。

### Customer-safe alternative proof

- `data/customer_safe_alternative_proof.json` generated at `2026-05-23T02:22:25.553944Z`。
- Live gate: `canary_ready=false`, `live_exposure_allowed=false`, `order_submission_enabled=false`, `risk_on_order_enabled=false`, `support_ready=false`, `topk_deployable=false`, `venue_runtime_ready=false`。
- Allowed today: paper/shadow decision-support, Shadow Trade Ledger, venue dry-run checklist, reduce-only / wait modes. Not allowed: buy/add live exposure, automatic order submission, canary live order without exact support and runtime venue proof.

### Forced-execution / bounded live-canary structural pivot

- `forced-execution` trigger is active when same semantic signature repeats, support `delta_vs_previous=0`, `stagnant_run_count` rises, or the customer flags equilibrium/repetition.
- Forced lanes: **Venue lifecycle proof**, **Model shadow to decision**, **Strategy micro-canary readiness**, **Map-Signal redesign**, or **hard no-go single failed gate**；observation-only status refresh is not accepted.
- Structural pivot reference: `docs/plans/2026-05-23-live-canary-structural-pivot.md` and `data/live_canary_structural_pivot.json`；implementation guard is `execution.live_canary` in `execution/execution_service.py` with tests `tests/test_execution_service.py -k live_canary`.
- bounded live-canary policy is required for any live buy/add pilot: `execution.mode=live`, `enable_live_trading=true`, `execution.live_canary.enabled=true`, explicit `allowed_symbols`, symbol-specific `max_base_qty_by_symbol`, and adapter-pre cap enforcement. Missing policy is `live_canary_policy_required`; over-cap is `live_canary_qty_cap_exceeded`.
- **72h decision clock:** either verify a bounded micro-canary under policy after all live gates pass, or name the single failed gate and next artifact. “Continue observing” is forbidden as fallback.

---

## 3. Customer expectation vs PM answer

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

Customer-usable lanes now:
1. **Dashboard**：看 current-live blocker、breaker release context、4H context、decision quality、feature/source blockers；主阻塞是 `circuit_breaker_active`，support 邊界是 `BLOCK|bear_bias200_hard_block|q00` `0/50 gap=50`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows=0` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay** 與 **`ORANGE_alternative_solution_required`**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 blocker 敘事捕獲。`customer-value delta`：PM status 已承認最新 bucket `BLOCK|bear_bias200_hard_block|q00`、exact support `0/50 gap=50`、breaker `release_ready=false` / `0/50`、Top-K `artifact_freshness_status=fresh` / `samples=24964`，並保留 Execution Console / Strategy Lab 的 paper-shadow lane；但 no live exposure。

**time-to-evidence：** `unknown_until_bucket_map_or_signal_redesign` for exact support movement；`same_day` for venue dry-run metadata proof if credentials/config are supplied；`within_week_or_unknown` for true venue lifecycle proof without credentials。PM 不把「治理參考」包裝成 deploy-ready；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的 alternative-solution artifact。

**anti-equilibrium guard：** `anti-repeat` 結果是不能再只重複 support gap；若 same semantic signature + support `delta_vs_previous=0` 再出現，PM 必須轉入 `forced-execution`：Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign、或 hard no-go single failed gate。`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact support 無法累積，最快會由 support stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：若下輪沒有客戶可見位移，就要求替代解法 artifact 或 bounded live-canary 72h hard gate，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact current support lane**：刷新 live probe / support audit / support-fill feasibility，直接顯示 current exact bucket rows 是否從 `0/50` 開始 movement，並同時列出 identity rows / non-current-bucket rows，避免把 near-lane/proxy/reference rows 誤包成 deployable；若 `delta_vs_previous=0` 或 `stagnant_run_count` 持續增加，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent canonical pocket（window `100` win_rate `24.0%`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。
8. **forced-execution lane**：若 same semantic signature / support delta=0 再重複，必須選 Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign 或 hard no-go single failed gate；任何 live buy/add 都必須先通過 bounded live-canary policy 與 adapter-pre cap enforcement。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據。最低可接受證據是：current exact support rows 從目前 `0/50` 開始 movement 或明確證明 stagnation 的 missing capability；recent drift no-new-risk / shadow-only falsification artifact clearly labels `deployable=false`；Top-K matrix 保持 fresh；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；venue dry-run proof；或 forced-execution lane 的 72h bounded live-canary / single failed gate artifact。除此之外，PM 必須交付 time-to-evidence bucket 與 `alternative-solution` 候選。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若 same semantic signature + support delta=0 重複卻沒有 forced-execution lane，升級 `RED_forced_execution_required`；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock`。
