# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-22T19:12:13.726515+00:00`
- source live probe generated_at: `2026-05-22T19:12:04.684496Z`
- source q15 audit generated_at: `2026-05-22 19:11:48.681614`
- classification: **true_support_under_minimum**
- reason: current identity is missing support and full history also remains under minimum; collect forward exact rows or redesign the bucket.
- current exact bucket rows (deployable support candidate): **1/50**
- current exact identity rows before bucket filter: **32** (non-current-bucket: **31**; reference only, not deployment support)
- gap_to_minimum: **49**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q00`
- regime_label: `bear`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24661**
- current calibration window filled: **True**
- features_normalized: count=25089, range=`2024-04-14 07:00:00.000000` → `2026-05-22 19:11:48.681614`
- labels: count=67710, range=`2024-04-14 07:00:00.000000` → `2026-05-22 16:11:08.540506`
- raw_market_data: count=34097, range=`2024-04-13 22:00:00.000000` → `2026-05-22 19:11:48.681614`

## PM delivery pressure

- time_to_evidence_bucket: `within_week_if_exact_identity_keeps_accumulating`
- missing_capability_class: `Signal/Support`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 1/50 must reach minimum; gap=49; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 6 | 1 | reference_only_calibration_window_mismatch | False | 2026-05-21 15:08:24.852438 | win=1.0, pnl=0.0025, quality=0.4815 |
| 200 | 32 | 1 | current_support_identity | False | 2026-05-21 15:08:24.852438 | win=1.0, pnl=0.0025, quality=0.4815 |
| 600 | 247 | 40 | reference_only_calibration_window_mismatch | False | 2026-05-21 15:08:24.852438 | win=0.45, pnl=0.0004, quality=0.1404 |
| 1000 | 270 | 40 | reference_only_calibration_window_mismatch | False | 2026-05-21 15:08:24.852438 | win=0.45, pnl=0.0004, quality=0.1404 |
| 5000 | 274 | 40 | reference_only_calibration_window_mismatch | False | 2026-05-21 15:08:24.852438 | win=0.45, pnl=0.0004, quality=0.1404 |
| all | 275 | 40 | reference_only_calibration_window_mismatch | False | 2026-05-21 15:08:24.852438 | win=0.45, pnl=0.0004, quality=0.1404 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 1/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=CAUTION、entry_label=C、bucket=CAUTION|base_caution_regime_or_bias|q00 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=600 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
