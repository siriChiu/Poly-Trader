# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-20 11:15 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`**

PM 判定：客戶成功仍是北極星，但安全 gate 不可被 customer urgency 推翻。Fresh engineering artifacts supersede the previous PM handoff numbers：current-live exact q15 support is now `2/50` (`gap=48`)，not the previous `1/50` handoff and not the older stale `24/50`/legacy `173/50` story；`support_route_verdict=exact_bucket_present_but_below_minimum` while `support_governance_route=exact_live_bucket_present_but_below_minimum` remains reference-only. 這不是放寬 gate 的理由，而是把 PM challenge 轉成「證明 exact semantic rows 是否能持續累積，或交付可驗證替代 artifact」。客戶可安全使用 Dashboard、Strategy Lab、Execution Console、paper/shadow selective sleeve、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；**真實買入 / 加倉 / live buy-add / 自動送單 / 小額 live canary 仍不可放行**。

本輪 current artifacts 顯示 support progress：`current_rows=2`、`previous_rows=1`、`delta_vs_previous=1`、`minimum_support_rows=50`、`gap=48`、`support_rows_needed=48`、`stagnant_run_count=0`、`stalled_support_accumulation=false`、`escalate_to_blocker=true`。time-to-evidence 仍是 `unknown_to_within_week`：已有連續 +1 row movement，但樣本累積速率尚未穩定；若下輪停在 `2/50` 或 `delta_vs_previous=0`，PM 需要求 missing-capability proof 與 alternative-solution artifact 並行。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-20T03:14:13.771008Z` after final q15 root-cause resync；canonical target remains `simulated_pyramid_win`。
- Runtime signal: `signal=HOLD` / `should_trade=false` / confidence `0.397115`；`regime_label=bear` / `regime_gate=CAUTION` / `entry_quality_label=B` / `decision_quality_label=D`。
- Primary blocker: `deployment_blocker=under_minimum_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Guardrail truth: `allowed_layers_raw=2` but `allowed_layers=0`; `allowed_layers_reason=under_minimum_exact_live_structure_bucket`; `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- Current-live support: `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`, `support_route_verdict=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`, rows `2/50`, `gap=48`。
- Support progress: `status=semantic_rebaseline_under_minimum`, `current_rows=2`, `previous_rows=1`, `delta_vs_previous=1`, `minimum_support_rows=50`, `gap_to_minimum=48`, `support_rows_needed=48`, `stagnant_run_count=0`, `stalled_support_accumulation=false`, `regression_basis=legacy_or_different_semantic_signature`, `escalate_to_blocker=true`。
- Legacy reference: heartbeat `1250` had q15 `173/50`, but semantic identity mismatches `calibration_window / entry_quality_label / regime_label`; it remains reference-only, not deployment closure.
- Direct action truth: `api_trade_guardrail_active=true`; `api_trade_buy_guardrail=current_live_deployment_blocker_409`; risk-off sides remain `reduce / sell` only。

**PM verdict：接受「breaker 已清，但 current exact q15 support 仍只有 2/50、低於 minimum，所以 live buy/add 仍 fail-closed」。不可把 legacy q15 `173/50`、allowed raw layer、Top-K OOS pass、same-bucket movement 或 breaker_clear 包裝成 deployable。**

### Circuit breaker

- Latest heartbeat artifacts still classify breaker math as non-primary；current runtime blocker is exact-support shortage, not breaker release math。
- Release context remains clear: `release_ready=true`, `current_recent_window_wins=22/50`, `additional_recent_window_wins_needed=0`；這只代表 breaker math 不再是主 blocker，不代表 current exact q15 support 或 venue runtime proof 已通過。
- PM interpretation: even if breaker release math is clear, current exact q15 support and venue runtime proof still block live exposure.

**PM verdict：breaker math is not the primary live blocker now. Current exact q15 support and venue runtime proof still block live exposure.**

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-05-20T03:02:38.590889+00:00`; `artifact_freshness_status=fresh`, `artifact_deployment_blocking=false`, `artifact_stale_after_minutes=60.0`。
- Matrix payload: `samples=24655`, `row_count=24`, `deployable_rows=0`, `risk_qualified_rows=6`, `runtime_blocked_candidate_rows=6`。
- Nearest research candidate: `model=logistic_regression`, `top_k=top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.022`, `worst_fold=0.2068`, `trade_count=58`, `tier=runtime_blocked_oos_pass`, `verdict=not_deployable`, with `deployment_blocker=under_minimum_exact_live_structure_bucket`。
- Support overlay matches current live truth: bucket `CAUTION|base_caution_regime_or_bias|q15`, support `2/50`, `gap=48`, `support_route=exact_bucket_present_but_below_minimum`, `support_governance_route=exact_live_bucket_present_but_below_minimum`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence. Strategy Lab 可優先顯示 nearest-deployable research rows，但 `deployable_rows=0` means no risk-on live action.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-20T03:14:23.097107Z`。
- Summary: `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `ok_count=1`, `readiness_state=blocked_until_runtime_lifecycle_proof`。
- OKX: adapter supported and enabled, but `credentials_configured=false`, proof remains `public_metadata_only`; order ack and fill lifecycle are not verified.
- Binance: adapter unsupported and config disabled; metadata contract, credential state, order ack, and fill lifecycle are not verified.
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-20T03:14:08.631449+00:00`; target `simulated_pyramid_win`。
- Full sample win rate is `61.63%`; recent canonical window remains weak: window `250` win rate `23.6%`, dominant regime `bear(96.8%)`, avg quality `-0.0759`, avg PnL `-0.0057`, alerts `regime_concentration / regime_shift`。
- Window `100` remains `32/100` wins with all rows bear; tail target streak is `7x0` and adverse zero streak remains a no-new-risk falsification signal, not a release patch.

**PM verdict：recent drift supports paper/shadow-only research and no-new-risk falsification. It cannot be packaged as a live deployment patch.**

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

### PM answer — 客戶現在可用

1. **Dashboard**：看 current-live blocker、breaker/release context、4H context、decision quality、feature/source blockers；主阻塞是 `under_minimum_exact_live_structure_bucket`，support 邊界是 `2/50 gap=48`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows=0` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Range-chop playbook**：做區間影子觀察、取消掛單 / 減碼劇本與證據收集；risk-on order remains disabled。
5. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。
6. **Canary rehearsal**：先回答 canary gap；只有 exact support rows、runtime gates、venue proof、Top-K support overlay 全過後才談極小額 live canary。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 heartbeat 的 blocker 敘事捕獲。Fresh artifacts 顯示 q15 semantic identity 漂移後 current exact support 由 `1/50` 移到 `2/50`，`gap=48`；Top-K matrix fresh 且 nearest research row 很強，但仍由 current exact support 與 venue runtime proof fail-closed。

**time-to-evidence：** 由於 current rows 只有 2，不能把 +1 movement 推估成 same-day closure；目前 bucket=`unknown_to_within_week`（需看下一輪是否維持 +1 row movement 或揭露 missing capability）。PM 不把「unknown」當停工理由；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的替代解法 artifact。

**anti-equilibrium guard：** `customer-value delta` 是 current blocker 已被重新同步成 exact bucket present-but-below-minimum（2/50，而非 stale 24/50、previous PM 1/50 或 legacy 173/50）、Top-K remains `artifact_freshness_status=fresh`、Execution Console / Strategy Lab 的 paper-shadow lane 仍可用；`anti-repeat` 結果是不能再只重複 q15 gap，下一輪必須交付 support movement、missing-capability proof、venue dry-run proof 或替代 artifact；`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact q15 support 無法累積，最快會由 stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support 與 stale/fresh labeling，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：PM 不可為工程延遲辯護，若下輪沒有客戶可見位移，就要求替代解法 artifact，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact q15 support lane（最高 live blocker）**：刷新 live probe / q15 support audit，直接顯示 current rows 是否離開 `2/50`；若 `delta_vs_previous=0` 或 movement 低於可解釋節奏，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent bear pocket（window `250` win_rate `23.6%`、window `100` `32/100`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：因 exact support closure time-to-evidence 目前 unknown，PM 下輪至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；engineering heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。最低可接受證據是：q15 exact support rows 從目前 `2/50` 繼續 movement，或明確證明 stagnation 的 missing capability；recent drift no-new-risk / shadow-only falsification artifact clearly labels `deployable=false`；Top-K matrix 保持 fresh 或 Strategy Lab / `/api/models/leaderboard` stale label；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；或 venue dry-run proof。除此之外，PM 必須交付 time-to-evidence bucket（next heartbeat / same day / within week / weeks-months / unknown）與 `alternative-solution` 候選；若主路徑維持 weeks/months/unknown，選出一個下輪可驗證的替代 artifact。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若原因來自文件/skills/harness 過度限制，直接 patch/simplify/bypass 該框架；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock` 並要求 engineering heartbeat 暫停同一路徑敘事，先提出替代架構/產品線/資料源比較。
