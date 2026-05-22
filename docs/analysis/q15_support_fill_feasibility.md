# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-22T11:13:15.377853+00:00`
- source live probe generated_at: `2026-05-22T11:13:11.566202Z`
- source q15 audit generated_at: `2026-05-22 11:12:34.311190`
- classification: **current_identity_support_ready**
- reason: current support_identity already has enough exact-bucket rows; deployment should depend on the remaining live/execution gates.
- current rows: **59/50**
- gap_to_minimum: **0**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- regime_label: `bear`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24622**
- current calibration window filled: **True**
- features_normalized: count=25054, range=`2024-04-14 07:00:00.000000` → `2026-05-22 11:12:34.311190`
- labels: count=67637, range=`2024-04-14 07:00:00.000000` → `2026-05-22 08:11:55.528798`
- raw_market_data: count=34054, range=`2024-04-13 22:00:00.000000` → `2026-05-22 11:12:34.311190`

## PM delivery pressure

- time_to_evidence_bucket: `ready_for_remaining_live_execution_gates`
- missing_capability_class: `Review`
- alternative_solution_required: **False**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 59/50 already meet minimum; keep deployable=false until circuit breaker, Top-K deployability, and venue/execution gates pass; reference rows stay non-deployable unless identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 0 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 200 | 64 | 59 | current_support_identity | True | 2026-05-20 06:10:25.311341 | win=1.0, pnl=0.0096, quality=0.5417 |
| 600 | 248 | 117 | reference_only_calibration_window_mismatch | False | 2026-05-20 06:10:25.311341 | win=0.7863, pnl=0.0055, quality=0.3663 |
| 1000 | 268 | 117 | reference_only_calibration_window_mismatch | False | 2026-05-20 06:10:25.311341 | win=0.7863, pnl=0.0055, quality=0.3663 |
| 5000 | 268 | 117 | reference_only_calibration_window_mismatch | False | 2026-05-20 06:10:25.311341 | win=0.7863, pnl=0.0055, quality=0.3663 |
| all | 269 | 118 | reference_only_calibration_window_mismatch | False | 2026-05-20 06:10:25.311341 | win=0.7881, pnl=0.0056, quality=0.3693 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 59/50 已達門檻，但 support gate 不是 deployment closure；reference windows 仍不可直接算作額外 deployment support。
  - success: current support_identity exact rows 維持 >= minimum，且 circuit breaker / Top-K / venue / execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=CAUTION、entry_label=C、bucket=CAUTION|base_caution_regime_or_bias|q15 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows 維持 >= 50 且 remaining live/execution gates 進入驗證。
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
