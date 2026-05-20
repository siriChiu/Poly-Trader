# current support-fill feasibility scan (q15/q35)

- generated_at: `2026-05-20T05:25:04.688072+00:00`
- source live probe generated_at: `2026-05-20T05:24:53.790535Z`
- source q15 audit generated_at: `2026-05-20 05:24:39.050807`
- classification: **true_support_under_minimum**
- reason: current identity is missing support and full history also remains under minimum; collect forward exact rows or redesign the bucket.
- current rows: **38/50**
- gap_to_minimum: **12**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned q15 support identity

This section is the q15 identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- regime_label: `bear`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24396**
- current calibration window filled: **True**
- features_normalized: count=24810, range=`2024-04-14 07:00:00.000000` → `2026-05-20 05:24:39.050807`
- labels: count=67167, range=`2024-04-14 07:00:00.000000` → `2026-05-20 02:14:07.763698`
- raw_market_data: count=33757, range=`2024-04-13 22:00:00.000000` → `2026-05-20 05:24:39.050807`

## PM delivery pressure

- time_to_evidence_bucket: `same_day_or_next_heartbeat_if_exact_identity_keeps_accumulating`
- missing_capability_class: `Signal/Support`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 38/50 must reach minimum; gap=12; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 87 | 38 | reference_only_calibration_window_mismatch | False | 2026-05-19 06:00:00.000000 | win=0.3421, pnl=-0.0011, quality=0.0564 |
| 200 | 143 | 38 | current_support_identity | False | 2026-05-19 06:00:00.000000 | win=0.3421, pnl=-0.0011, quality=0.0564 |
| 600 | 164 | 38 | reference_only_calibration_window_mismatch | False | 2026-05-19 06:00:00.000000 | win=0.3421, pnl=-0.0011, quality=0.0564 |
| 1000 | 184 | 38 | reference_only_calibration_window_mismatch | False | 2026-05-19 06:00:00.000000 | win=0.3421, pnl=-0.0011, quality=0.0564 |
| 5000 | 184 | 38 | reference_only_calibration_window_mismatch | False | 2026-05-19 06:00:00.000000 | win=0.3421, pnl=-0.0011, quality=0.0564 |
| all | 185 | 39 | reference_only_calibration_window_mismatch | False | 2026-05-19 06:00:00.000000 | win=0.359, pnl=-0.0005, quality=0.0733 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 unsupported_exact_live_structure_bucket / allowed_layers=0；reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=100、regime/gate/entry_label/bucket 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 600/all 等舊窗口的足量 rows，必須先改 support_identity / calibration_window policy，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
