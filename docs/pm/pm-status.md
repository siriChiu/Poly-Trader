# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-20 18:16 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`；`ORANGE_alternative_solution_required` remains active.**

PM 結論：客戶成功仍是北極星，但 live buy/add safety gate 不可被 customer urgency 推翻。本輪工程 heartbeat 已驗證 PM handoff 的 q15 `0/50` 是上一輪 artifact truth；fresh runtime probe 顯示 current-live 已移到 `CAUTION|base_caution_regime_or_bias|q35`，current exact support 仍是 `0/50`、`gap=50`、`support_route_verdict=exact_bucket_unsupported_block`，`support_governance_route=exact_live_lane_proxy_available` 只能當治理 / proxy reference，不是部署閉環。

安全答案：`signal=HOLD` / `should_trade=false` / `deployment_blocker=unsupported_exact_live_structure_bucket` / `allowed_layers_raw=1` / `allowed_layers=0` / `allowed_layers_reason=unsupported_exact_live_structure_bucket` / `execution_guardrail_reason=unsupported_exact_live_structure_bucket` / `api_trade_guardrail_active=true` / `api_trade_buy_guardrail=current_live_deployment_blocker_409`。客戶可以使用 Dashboard、Strategy Lab、Execution Console、paper/shadow decision-support、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；**真實買入 / 加倉 / live buy/add / 自動送單 / 小額 live canary 仍不可放行**。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-20T10:15:25.994479Z`；canonical target remains `simulated_pyramid_win`。
- Runtime signal: `signal=HOLD` / `should_trade=false` / confidence `0.58655`；`regime_label=chop` / `regime_gate=CAUTION` / `entry_quality_label=C` / `decision_quality_label=D` / decision quality score `0.0642`。
- Primary blocker: `deployment_blocker=unsupported_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Guardrail truth: `allowed_layers_raw=1` but `allowed_layers=0`；`allowed_layers_reason=unsupported_exact_live_structure_bucket`；`execution_guardrail_reason=unsupported_exact_live_structure_bucket`。
- Current-live support: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35`, `support_route_verdict=exact_bucket_unsupported_block`, `support_governance_route=exact_live_lane_proxy_available`, rows `0/50`, `gap=50`。
- Support progress: `support_progress_status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `previous_rows=0` / `delta_vs_previous=0` / `stagnant_run_count=3` / exact-live-lane proxy rows `8` reference-only。
- Direct action truth: `api_trade_guardrail_active=true`; `api_trade_buy_guardrail=current_live_deployment_blocker_409`; risk-off sides remain `reduce / sell` only。

**PM verdict：接受「breaker_clear，但 current exact q35 support 是 0/50、尚未建立同一 support identity 的精準樣本，所以 live buy/add 仍 fail-closed」。不可把 exact-live-lane proxy rows、legacy reference、Top-K OOS pass 或 governance route 包裝成 deployable。**

### Circuit breaker

- Latest artifact `data/circuit_breaker_audit.json` generated at `2026-05-20T10:15:28.034871Z`；verdict `breaker_clear`。
- Release context: `release_ready=true`, recent-window wins `32/50`, required wins `15/50`, `additional_recent_window_wins_needed=0`。
- PM interpretation: breaker math is clear, but q35 exact support and venue runtime proof still block live exposure.

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-20T10:02:33.641095+00:00`；`artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `samples=24681`, `row_count=24`, `runtime_blocked_candidate_rows=6`。
- Matrix payload: `deployable_rows=0`, `risk_qualified_rows=6`, `support_route=exact_bucket_unsupported_block`, `deployment_blocker=unsupported_exact_live_structure_bucket`, `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35`, bucket rows `0/50`, `gap=50`。
- Nearest research candidate: `model=random_forest`, `feature_profile=current_full`, `top_k=top_2pct`, `oos_roi=0.6884`, `win_rate=0.8621`, `profit_factor=12.4161`, `max_drawdown=0.027`, `worst_fold=0.0959`, `trade_count=58`, `deployment_candidate_tier=runtime_blocked_oos_pass`, `deployable_verdict=not_deployable`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence. Strategy Lab 可優先顯示 nearest-deployable research rows，但 `deployable_rows=0` means no risk-on live action.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-20T10:15:38.223220Z`。
- Summary: `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `ok_count=1`, `readiness_state=blocked_until_runtime_lifecycle_proof`。
- OKX: adapter supported/enabled, but credentials, order-ack lifecycle, and fill lifecycle proof remain incomplete.
- Binance: adapter unsupported/config disabled, metadata contract not passed, credentials and lifecycle proof missing.
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-20T10:15:13.710949+00:00`。
- Full sample rows `24545`。
- Recent canonical window `250`: wins `83`, losses `167`, win_rate `33.2%`, dominant regime `bear(100.0%)`, alerts `regime_concentration, regime_shift`。
- Window `100`: wins `51`, losses `49`, win_rate `51.0%`, also bear-concentrated。

**PM verdict：recent drift reinforces paper/shadow-only research and root-cause work. It cannot be packaged as a live deployment patch.**

### Support-fill feasibility / alternative-solution pressure

- `data/q15_support_fill_feasibility.json` generated at `2026-05-20T10:15:35.543601+00:00`（artifact name still says q15 for compatibility, but scanned current support identity is q35）。
- Verdict: `classification=semantic_window_gap_not_raw_backfill_gap`, current calibration window `200`, current exact bucket rows `0/50`, `gap=50`, `time_to_evidence_bucket=semantic_rebaseline_review_required_before_reference_rows_count`, `missing_capability_class=Constraint/Review`, `alternative_solution_required=True`。
- Reference-only evidence: `best_reference_window=all`, `best_reference_exact_bucket_rows=537`, but `best_reference_evidence_role=reference_only_calibration_window_mismatch`; reference rows cannot be counted as deployable support unless support identity is deliberately rebaselined and fully reverified.
- Selected next safe artifact: Execution Console / Strategy Lab paper-shadow proof with deployable=false copy.

---

## 3. Customer expectation vs PM answer

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

Customer-usable lanes now:
1. **Dashboard**：看 current-live blocker、breaker release context、4H context、decision quality、feature/source blockers；主阻塞是 `unsupported_exact_live_structure_bucket`，support 邊界是 q35 `0/50 gap=50`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows=0` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay** 與 **`ORANGE_alternative_solution_required`**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 blocker 敘事捕獲。`customer-value delta`：PM status 已承認最新 q35 `0/50 gap=50`、breaker `release_ready=true` / `32/50`、Top-K `artifact_freshness_status=fresh` / `samples=24681`，並保留 Execution Console / Strategy Lab 的 paper-shadow lane；但 no live exposure。

**time-to-evidence：** `next_heartbeat_or_same_day` for exact q35 support movement if the same support identity keeps accumulating；`same_day` for venue dry-run metadata proof if credentials/config are supplied；`within_week_or_unknown` for true venue lifecycle proof without credentials。PM 不把「治理參考」包裝成 deploy-ready；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的 alternative-solution artifact。

**anti-equilibrium guard：** `anti-repeat` 結果是不能再只重複 q35 gap；`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact support 無法累積，最快會由 support stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：若下輪沒有客戶可見位移，就要求替代解法 artifact，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact current support lane**：刷新 live probe / support audit / support-fill feasibility，直接顯示 current rows 是否從 `0/50` 開始 movement；若仍為 0，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent bear pocket（window `250` win_rate `32.0%`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據。最低可接受證據是：current exact support rows 從目前 `0/50` 開始 movement 或明確證明 stagnation 的 missing capability；recent drift no-new-risk / shadow-only falsification artifact clearly labels `deployable=false`；Top-K matrix 保持 fresh；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。除此之外，PM 必須交付 time-to-evidence bucket 與 `alternative-solution` 候選。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock`。
