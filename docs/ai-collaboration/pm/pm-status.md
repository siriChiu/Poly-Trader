# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-07-11 05:25 CST_

> Current-state PM interpretation. Do not append hourly history here; this file is generated from current runtime artifacts by `scripts/sync_pm_status.py` so PM checks fail on real drift, not stale literals.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`；`ORANGE_alternative_solution_required` remains active.**

PM 結論：客戶成功仍是北極星，但 live buy/add safety gate 不可被 customer urgency 推翻。承接上一輪 PM handoff：維持 current-live exact-support blocker、交付 paper/shadow / dry-run / falsification / support-fill proof，且不可降低 live gate。fresh runtime truth 顯示 current-live bucket 是 `CAUTION|structure_quality_caution|q35`；PM 決策不變：current exact support 是 `0/50`、`gap=50`、`support_route_verdict=exact_bucket_unsupported_block`，`support_governance_route=no_support_proxy` 只能當治理 / proxy reference，不是部署閉環。pivot lane role 是 `no_trade_block_lane` / `no_trade_decision_validation_not_deployable_support`：當前即時 lane 是 BLOCK / 不交易決策 lane。0/50 exact support 應視為無風險觀望驗證，不是可收集來支撐買入 / 加倉部署的 support。 no-trade replay verdict 是 `validated_abstain_reduce_only_no_trade_lane` / `validated=true` / `deployable=false` / `buy_add_support_closure_allowed=false`。

安全答案：`signal=HOLD` / `should_trade=false` / `deployment_blocker=unsupported_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked` / `allowed_layers_raw=0` / `allowed_layers=0` / `allowed_layers_reason=unsupported_exact_live_structure_bucket` / `execution_guardrail_reason=unsupported_exact_live_structure_bucket` / `api_trade_guardrail_active=true` / `api_trade_buy_guardrail=current_live_deployment_blocker_409`。客戶可以使用 Dashboard、Strategy Lab、Execution Console、paper/shadow decision-support、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；Execution API 只允許 `shadow_buy` / `paper_buy` 以強制 dry-run paper/shadow 模式寫入演練證據，不可繞過 current-live guardrail；**真實買入 / 加倉 / live buy/add / 自動送單 / 小額 live canary 仍不可放行**，除非 bounded live-canary policy、current-live gate、support/breaker gate 與 venue lifecycle proof 全部通過。

---

## 2. Artifact truth accepted by PM

### PM current-artifact freshness guard

- `data/live_predict_probe.json freshness_status=fresh` / `artifact_age_minutes=647.24` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_within_policy`。
- `data/live_decision_quality_drilldown.json freshness_status=fresh` / `artifact_age_minutes=647.24` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_within_policy`。
- `data/circuit_breaker_audit.json freshness_status=stale` / `artifact_age_minutes=2116.04` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/recent_drift_report.json freshness_status=stale` / `artifact_age_minutes=51458.93` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/execution_metadata_smoke.json freshness_status=fresh` / `artifact_age_minutes=5.44` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_within_policy`。
- `data/venue_dry_run_proof.json freshness_status=stale` / `artifact_age_minutes=51032.40` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/q15_support_audit.json freshness_status=fresh` / `artifact_age_minutes=647.24` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_within_policy`。
- `data/q15_support_fill_feasibility.json freshness_status=stale` / `artifact_age_minutes=51458.58` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/q15_exact_bucket_row_harvest_proof.json freshness_status=stale` / `artifact_age_minutes=51458.49` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/q15_drift_rebaseline_backtest.json freshness_status=stale` / `artifact_age_minutes=51458.41` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/q15_map_signal_redesign_proof.json freshness_status=stale` / `artifact_age_minutes=51458.31` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/customer_safe_alternative_proof.json freshness_status=stale` / `artifact_age_minutes=50844.37` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/live_canary_structural_pivot.json freshness_status=stale` / `artifact_age_minutes=51458.00` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/no_trade_lane_replay.json freshness_status=stale` / `artifact_age_minutes=51032.38` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_older_than_policy`。
- `data/paper_shadow_outcome_reconciliation.json freshness_status=fresh` / `artifact_age_minutes=1.41` / `artifact_stale_after_minutes=1440` / `freshness_reason=artifact_within_policy`。

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-07-10T10:37:48.632204Z`；canonical target is `simulated_pyramid_win`。
- Runtime signal: `signal=HOLD` / `should_trade=false` / confidence `0.444447`；`regime_label=bull` / `regime_gate=CAUTION` / `entry_quality_label=D` / `decision_quality_score=0.0509`。
- Primary blocker: `deployment_blocker=unsupported_exact_live_structure_bucket` / `runtime_closure_state=patch_inactive_or_blocked`。
- Guardrail truth: `allowed_layers_raw=0` but `allowed_layers=0`；`allowed_layers_reason=unsupported_exact_live_structure_bucket`；`execution_guardrail_reason=unsupported_exact_live_structure_bucket`。
- Current-live support: `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`, `support_route_verdict=exact_bucket_unsupported_block`, `support_governance_route=no_support_proxy`, rows `0/50`, `gap=50`。
- Current-lane role from structural pivot: `current_lane_actionability=no_trade_block_lane`, `support_evidence_role=no_trade_decision_validation_not_deployable_support`；當前即時 lane 是 BLOCK / 不交易決策 lane。0/50 exact support 應視為無風險觀望驗證，不是可收集來支撐買入 / 加倉部署的 support。
- Support progress: `support_progress_status=stalled_under_minimum` / `regression_basis=no_same_identity_same_semantic_signature_history` / `previous_rows=None` / `delta_vs_previous=None` / `stagnant_run_count=0` / `semantic_signature_delta_vs_previous=—` / `semantic_signature_stagnant_run_count=0` / `semantic_signature_stalled_support_accumulation=false` / legacy reference is reference-only because support identity does not close current deployment.
- Direct action truth: `api_trade_guardrail_active=true`; `api_trade_buy_guardrail=current_live_deployment_blocker_409`; live risk-off sides remain `reduce, sell`；paper/shadow rehearsal sides are `shadow_buy,paper_buy` and must return `dry_run=true`, `live_order_submitted=false`。

**PM verdict：接受「熔斷已解除，但 current exact support 仍是 `0/50`、gap `50`，尚未建立同一 support identity 的精準樣本，所以 live buy/add 仍 fail-closed」。不可把 legacy rows、exact-live-lane proxy rows、Top-K OOS pass、或單一 support/governance gate 包裝成 deployable。**

### Circuit breaker

- Latest artifact `data/circuit_breaker_audit.json` generated at `2026-07-09T10:09:00.639599Z`；verdict `breaker_clear`。
- Release context: `release_ready=true`, recent-window wins `15/50`, required wins `15/50`, `additional_recent_window_wins_needed=0`。
- PM interpretation: breaker math is clear, but any remaining support, Top-K deployability, and venue runtime proof gates still block live exposure.

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `2026-07-10T10:37:48.849020+00:00`；`artifact_freshness_status=stale`, `artifact_deployment_blocking=true`, `artifact_age_minutes=647.24`, `artifact_stale_after_minutes=60`, `samples=26108`, `row_count=24`, `runtime_blocked_candidate_rows=6`。
- Top-K live support overlay freshness：`support_context_status=stale_live_probe_shadow_only`, `support_context_freshness_status=stale`, `support_context_freshness_reason=artifact_older_than_policy`, `support_context_deployment_blocking=true`, `support_context_age_minutes=647.24`, `support_context_stale_after_minutes=30`, `support_context_refresh_status=refreshed`, `support_context_refresh_attempted=true`, `support_context_refresh_error=None`, `live_truth_overlay_blocker=artifact_older_than_policy`；freshness is recalculated from `data/live_predict_probe.json.generated_at`; if stale, Top-K remains reference-only until refreshed.
- Runtime API overlay：`/api/models/leaderboard` must overlay request-time runtime truth for Strategy Lab, accept Strategy Lab's `?refresh=true` alias as a force-refresh request, auto-queue stale Top-K matrix refresh, refreshes stale live support probe before matrix build, and serialize request-time ML cold-load before background model leaderboard refresh; compact probe fields `hc_support_context_status / hc_support_context_freshness_status / hc_live_truth_freshness_status / hc_support_context_refresh_status / hc_refreshing / hc_refresh_reason` are the current endpoint truth. Fresh runtime overlay can clear persisted-probe staleness, but it does not clear live gates unless support, breaker, model, and venue proof all pass.
- Matrix payload: `deployable_rows=0`, `risk_qualified_rows=6`, `support_route=exact_bucket_unsupported_block`, `deployment_blocker=unsupported_exact_live_structure_bucket`, `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`, bucket rows `0/50`, `gap=50`。
- Nearest research candidate: `model=logistic_regression`, `feature_profile=current_full`, `top_k=top_2pct`, `oos_roi=0.9324`, `win_rate=0.8621`, `profit_factor=19.8864`, `max_drawdown=0.0220`, `worst_fold=0.2068`, `trade_count=58`, `deployment_candidate_tier=runtime_blocked_oos_pass`, `deployable_verdict=not_deployable`。

**PM verdict：Top-K matrix 目前已 stale/reference-only；Strategy Lab / leaderboard 必須標示 stale 或 shadow-only，重跑 matrix 前不可把候選包裝成 risk-on live action。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-07-10T21:19:36.912397Z`。
- Summary: `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `ok_count=1`, `readiness_state=blocked_until_runtime_lifecycle_proof`。
- okx: adapter_supported=true, enabled_in_config=true, credentials_configured=false, proof_state=public_metadata_only, runtime_ready=false, blockers=live exchange credential 尚未驗證, order ack lifecycle 尚未驗證, fill lifecycle 尚未驗證。
- binance: adapter_supported=false, enabled_in_config=false, credentials_configured=false, proof_state=adapter_unsupported, runtime_ready=false, blockers=場館 adapter 尚未接入, 元資料契約尚未通過, 場館設定停用, live exchange credential 尚未驗證, order ack lifecycle 尚未驗證, fill lifecycle 尚未驗證。
- `data/venue_dry_run_proof.json` generated at `2026-06-05T10:52:39.406369Z`；`venue_dry_run_status=blocked_missing_runtime_backed_proof`, `runtime_ready=false`, `runtime_ready_count=0`, `venues_checked=2`, `order_submission_enabled=false`, `risk_on_order_enabled=false`, `dry_run_only=true`。
- Dry-run lifecycle status: `ack=blocked_missing_credentials`, `cancel=blocked_missing_credentials`, `fill=blocked_missing_credentials`, `reconciliation=blocked_missing_credentials`；venue rows：okx: preview=blocked_missing_credentials, runtime_ready=false, credentials_configured=false; binance: preview=blocked_adapter_unsupported, runtime_ready=false, credentials_configured=false。
- API source-of-truth: `/api/status` exposes `venue_dry_run_proof`, and `/api/execution/overview` prefers that artifact so UI/API/customer-safe proof use the same fail-closed venue lifecycle status.
- API consistency verification: save `/api/status` and `/api/execution/overview` JSON, then run `python scripts/venue_dry_run_api_consistency_probe.py --status-file <status.json> --overview-file <overview.json> --artifact-file data/venue_dry_run_proof.json --strict`; expected `strict_ok=true`, `api_consistent=true`, `artifact_consistent=true`, `fail_closed=true`, and `secret_safe=true`.
- `/api/status.execution_surface_contract.live_canary_policy_gate`, Execution Console readiness gate stack, and Dashboard / Execution Status / Strategy Lab status-only summaries now all expose `live_canary_policy_gate` with operator-safe blocker copy; canary readiness remains false unless mode/live flag/explicit allowed symbol/symbol cap/kill switch all satisfy the local bounded live-canary policy, even if runtime gates later pass.
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-06-05T03:46:07.357078+00:00`。
- Full sample rows `25717`。
- Recent canonical window `100`: win_rate `21.0%`, dominant regime `bear(94.0%)`, alerts `regime_concentration, regime_shift`。

**PM verdict：recent drift reinforces paper/shadow-only research and root-cause work. It cannot be packaged as a live deployment patch.**

### Support-fill feasibility / alternative-solution pressure

- `data/q15_support_fill_feasibility.json` generated at `2026-06-05T03:46:28.397005+00:00`；scanned current support identity bucket is `BLOCK|bias200_below_min|q00`。
- Verdict: `classification=current_identity_support_ready`, current calibration window `200`, current exact bucket rows `131/50`, identity rows before bucket filter `183`, non-current-bucket identity rows `52`, `gap=0`, `time_to_evidence_bucket=ready_for_remaining_live_execution_gates`, `missing_capability_class=Review`, `alternative_solution_required=false`。
- Reference-only evidence: `best_reference_window=all`, `best_reference_exact_bucket_rows=141`, `best_reference_evidence_role=reference_only_calibration_window_mismatch`；reference rows cannot be counted as deployable support unless support identity is deliberately rebaselined and fully reverified.
- Selected next safe artifact: `data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy`。

### Exact row-harvest proof

- `data/q15_exact_bucket_row_harvest_proof.json` generated at `2026-06-05T03:46:33.530787Z`。
- Verdict: `status=exact_bucket_row_harvest_support_ready_remaining_gates`, current exact rows `131/50`, previous rows `131`, `delta_vs_previous=0`, `gap=0`, `rows_needed=0`, `time_to_evidence_bucket=ready_for_remaining_live_execution_gates`, `primary_failed_gate=remaining_live_gates`。
- Safety interpretation: `support_gate_ready=true`, `live_exposure_allowed=false`, `order_submission_enabled=false`；row movement is support evidence only, not live deployment clearance.

### Drift-aware rebaseline backtest

- `data/q15_drift_rebaseline_backtest.json` generated at `2026-06-05T03:46:38.416907Z`。
- Verdict: `status=current_identity_support_ready_rebaseline_not_needed`, `decision=current exact support already meets minimum; rebaseline proof is not the primary gate, but live buy/add still waits for remaining gates.`, `selected_candidate=None`, `selected_candidate_status=None`, current-window rows `None/50`, all-history rows `None`, current exact bucket rows `131/50`, `gap=0`, `primary_failed_gate=current_live_support_gate`。
- Safety interpretation: `live_exposure_allowed=false`, `order_submission_enabled=false`；historical or semantic rebaseline candidates are OOS replay/redesign evidence only, not current-live deployment clearance.

### Map/Signal redesign proof

- `data/q15_map_signal_redesign_proof.json` generated at `2026-06-05T03:46:44.756417Z`。
- Verdict: `status=map_signal_redesign_no_current_window_deployable_candidate`, `decision=Map/signal candidates were evaluated but none passed current-window support and metric gates.`, `selected_candidate=dominant_neighbor_exact_lane`, `selected_candidate_status=count_ready_metric_rejected`, `target_bucket=BLOCK|bear_bias200_hard_block|q00`, current-window rows `28/50`, all-history rows `174`, `best_reference=best_historical_exact_lane_bucket:133`, `primary_failed_gate=current_live_support_gate`。
- Root-cause link: `root_cause=same_lane_neighbor_bucket_dominates`, `candidate_patch_type=structure_component_scoring`, `candidate_patch_feature=feat_4h_bb_pct_b`。
- Safety interpretation: `live_exposure_allowed=false`, `order_submission_enabled=false`；neighbor/q35/reference rows are replay/redesign inputs only, not current exact support closure.

### Customer-safe alternative proof

- `data/customer_safe_alternative_proof.json` generated at `2026-06-05T14:00:41.175580Z`。
- Live gate: `canary_ready=false`, `live_exposure_allowed=false`, `order_submission_enabled=false`, `risk_on_order_enabled=false`, `support_ready=true`, `topk_deployable=false`, `venue_runtime_ready=false`。
- Allowed today: paper/shadow decision-support, API `shadow_buy` / `paper_buy` dry-run rehearsal, Shadow Trade Ledger, venue dry-run checklist, reduce-only / wait modes. Not allowed: buy/add live exposure, automatic live order submission, canary live order without exact support and runtime venue proof.

### Paper/shadow worker parity

- `/api/execution/workers/poll` is a local-operator controlled state poller for running execution runs; it may write `paper_shadow_worker_poll` only when `execution_runs.state=running`, bundle hash parity passes, and the run does not already have a pending 24h proposal.
- Duplicate poll attempts during the observation window must return `pending_outcome_blocked` without writing another event; proposal payloads remain fail-closed with `order_submission_enabled=false`, `risk_on_order_enabled=false`, `live_order_submitted=false`.
- Current local artifact: `status=recording_with_resolved_outcomes`, `worker_poll_events=1`, `pending_outcomes=0`, `resolved_outcomes=1`, `awaiting_label_replay=0`, `live_order_submitted=false`。
- Rehearsal proof: `status=resolved_evidence_ready`, `can_poll_workers=true`, `poll_blocked_by_pending_outcome=false`, `order_submission_enabled=false`, `risk_on_order_enabled=false`, `live_order_submitted=false`, `next_reconcile_at=None`, `current_pending_hours_remaining_hours=—`, `artifact_pending_hours_remaining_hours=None`；這是 customer-usable rehearsal evidence，不是 live trading readiness。

### Forced-execution / bounded live-canary structural pivot

- `forced-execution` trigger is active when same semantic signature repeats, support `delta_vs_previous=0`, `stagnant_run_count` rises, or the customer flags equilibrium/repetition.
- Forced lanes: **Venue lifecycle proof**, **Model shadow to decision**, **Strategy micro-canary readiness**, **Map-Signal redesign**, or **hard no-go single failed gate**；observation-only status refresh is not accepted.
- Current q15/current-support audit: `data/q15_support_audit.json` generated at `2026-07-10T10:37:48.625577Z`；`scope=current_live_not_q15_lane`, `equilibrium_deadlock=not_applicable_current_live_not_target_lane`, `equilibrium_deadlock_confirmed=false`, `forced_research_action_required=false`, `forced_branch_status=not_required`, `selected_branch=None`, `single_failed_gate=support_gate`, `next_validation_artifact=data/q15_support_audit.json`, `decision_clock=72h_micro_canary_or_single_failed_gate`, `live_exposure_allowed=false`, `shadow_or_paper_allowed=true`。若此列是 `hard_no_go_recorded`，PM 視為本輪已留下 single failed gate artifact，而不是 observation-only refresh。
- Exact row-harvest proof: `data/q15_exact_bucket_row_harvest_proof.json` generated at `2026-06-05T03:46:33.530787Z`；`status=exact_bucket_row_harvest_support_ready_remaining_gates`, `current_rows=131/50`, `previous_rows=131`, `delta_vs_previous=0`, `rows_needed=0`, `primary_failed_gate=remaining_live_gates`, `live_exposure_allowed=false`；PM treats positive row movement as evidence, not live clearance.
- Drift rebaseline proof: `data/q15_drift_rebaseline_backtest.json` generated at `2026-06-05T03:46:38.416907Z`；`status=current_identity_support_ready_rebaseline_not_needed`, `selected_candidate=None`, `current_window_rows=None/50`, `all_history_rows=None`, `primary_failed_gate=current_live_support_gate`, `live_exposure_allowed=false`；PM treats this as forced-branch evidence, not live clearance.
- Map/Signal redesign proof: `data/q15_map_signal_redesign_proof.json` generated at `2026-06-05T03:46:44.756417Z`；`status=map_signal_redesign_no_current_window_deployable_candidate`, `selected_candidate=dominant_neighbor_exact_lane`, `target_bucket=BLOCK|bear_bias200_hard_block|q00`, `current_window_rows=28/50`, `all_history_rows=174`, `best_reference=best_historical_exact_lane_bucket:133`, `primary_failed_gate=current_live_support_gate`, `live_exposure_allowed=false`；PM treats this as forced-branch evidence, not live clearance.
- Structural pivot reference: `docs/plans/2026-05-23-live-canary-structural-pivot.md` and `data/live_canary_structural_pivot.json`；implementation guard is `execution.live_canary` in `execution/execution_service.py` with tests `tests/test_execution_service.py -k live_canary`.
- Structural pivot current truth: generated_at `2026-06-05T03:47:03.285566Z`；bucket `BLOCK|bias200_below_min|q00`；support `131/50` gap `0`；release_ready `true`；recent wins `20/50`；Top-K deployable `0`；venue_runtime_ready `false`；live_canary_policy_ready `false`。
- Structural pivot Map/Signal lane: `current_lane_actionability=no_trade_block_lane` / `support_evidence_role=no_trade_decision_validation_not_deployable_support` / `map_signal_forced_lane=no_trade_lane_audit`；next artifact `data/no_trade_lane_replay.json；驗證觀望 / reduce-only 行為，不把它寫成 risk-on support closure。`。
- No-trade lane replay: `data/no_trade_lane_replay.json` generated at `2026-06-05T10:52:40.138706Z`；`verdict=validated_abstain_reduce_only_no_trade_lane` / `validated=true` / `deployable=false` / `risk_on_order_enabled=false` / `order_submission_enabled=false` / `buy_add_support_closure_allowed=false` / `checks_all_passed=true`；recent replay gate `observable_4h_shift_shadow_gate` stayed shadow-only with kept win rate `21.5%`。這是 no-trade / reduce-only / paper-shadow proof，不是 live buy/add support closure。
- Structural pivot 72h hard gate: `single_failed_gate_for_72h_decision=model_shadow_outcome_gate`；`next_validation_artifact=data/high_conviction_topk_oos_matrix.json + Shadow Trade Ledger 24h pyramid outcome rows`；`micro_canary_ready=false`；`order_submission_enabled=false`；config mode `paper`。
- bounded live-canary policy is required for any live buy/add pilot: `execution.mode=live`, `enable_live_trading=true`, `execution.live_canary.enabled=true`, explicit `allowed_symbols`, symbol-specific `max_base_qty_by_symbol`, and adapter-pre cap enforcement. Missing policy is `live_canary_policy_required`; over-cap is `live_canary_qty_cap_exceeded`.
- **72h decision clock:** either verify a bounded micro-canary under policy after all live gates pass, or name the single failed gate and next artifact. “Continue observing” is forbidden as fallback.

---

## 3. Customer expectation vs PM answer

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

Customer-usable lanes now:
1. **Dashboard**：看 current-live blocker、breaker release context、4H context、decision quality、feature/source blockers；主阻塞是 `unsupported_exact_live_structure_bucket`，support 邊界是 `CAUTION|structure_quality_caution|q35` `0/50 gap=50`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows=0`、`artifact_freshness_status=stale`、`support_context_freshness_status=stale` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、API `shadow_buy` / `paper_buy` dry-run rehearsal、`/api/execution/workers/poll` worker parity event、worker outcome reconciliation `rehearsal_proof`、Shadow Trade Ledger、dry-run readiness、`live_canary_policy_gate`、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay** 與 **`ORANGE_alternative_solution_required`**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 blocker 敘事捕獲。`customer-value delta`：PM status 已承認最新 bucket `CAUTION|structure_quality_caution|q35`、exact support `0/50 gap=50`、breaker `release_ready=true` / `15/50`、Top-K `artifact_freshness_status=stale` / `support_context_freshness_status=stale` / `samples=26108`，並保留 Execution Console / Strategy Lab 的 paper-shadow lane；但 no live exposure。

**time-to-evidence：** `ready_for_remaining_live_execution_gates` for exact support movement；`same_day` for venue dry-run metadata proof if credentials/config are supplied；`within_week_or_unknown` for true venue lifecycle proof without credentials。PM 不把「治理參考」包裝成 deploy-ready；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的 alternative-solution artifact。

**anti-equilibrium guard：** `anti-repeat` 結果是不能再只重複 support gap；若 same semantic signature + support `delta_vs_previous=0` 再出現，PM 必須轉入 `forced-execution`：Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign、或 hard no-go single failed gate。`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact support 無法累積，最快會由 support stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：若下輪沒有客戶可見位移，就要求替代解法 artifact 或 bounded live-canary 72h hard gate，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact current support lane**：刷新 live probe / support audit / support-fill feasibility，直接顯示 current exact bucket rows 是否從 `0/50` 開始 movement，並同時列出 identity rows / non-current-bucket rows，避免把 near-lane/proxy/reference rows 誤包成 deployable；若 `delta_vs_previous=0` 或 `stagnant_run_count` 持續增加，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent canonical pocket（window `100` win_rate `21.0%`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 與 live support overlay 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、worker parity event、worker outcome reconciliation `rehearsal_proof`、pending poll guard / ETA、Shadow Trade Ledger、range-chop playbook、dry-run readiness 或 `live_canary_policy_gate` 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/ai-collaboration/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。
8. **forced-execution lane**：若 same semantic signature / support delta=0 再重複，必須選 Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign 或 hard no-go single failed gate；任何 live buy/add 都必須先通過 bounded live-canary policy 與 adapter-pre cap enforcement。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據。最低可接受證據是：current exact support rows 從目前 `0/50` 開始 movement 或明確證明 stagnation 的 missing capability；`data/no_trade_lane_replay.json` clearly labels `deployable=false` / `buy_add_support_closure_allowed=false` while validating abstain / reduce-only / paper-shadow behavior；Top-K matrix 與 live support overlay 保持 fresh，或明確標示 stale/reference-only；`/execution` paper/shadow worker parity event 可操作，且 outcome reconciliation 的 `rehearsal_proof.status=pending_observation_window` 於 pending 期間禁止重複 poll 並顯示 ETA，24h 後轉成 resolved 或 label replay；venue dry-run proof；或 forced-execution lane 的 72h bounded live-canary / single failed gate artifact。除此之外，PM 必須交付 time-to-evidence bucket 與 `alternative-solution` 候選。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若 same semantic signature + support delta=0 重複卻沒有 forced-execution lane，升級 `RED_forced_execution_required`；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock`。
