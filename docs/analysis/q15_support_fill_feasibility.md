# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-24T12:30:14.768519+00:00`
- source live probe generated_at: `2026-05-24T12:30:06.976080Z`
- source q15 audit generated_at: `2026-05-24 12:29:21.452681`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current exact bucket rows (deployable support candidate): **1/50**
- current exact identity rows before bucket filter: **49** (non-current-bucket: **48**; reference only, not deployment support)
- gap_to_minimum: **49**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- regime_label: `chop`
- regime_gate: `CAUTION`
- entry_quality_label: `D`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24847**
- current calibration window filled: **True**
- features_normalized: count=25268, range=`2024-04-14 07:00:00.000000` → `2026-05-24 12:29:21.452681`
- labels: count=68071, range=`2024-04-14 07:00:00.000000` → `2026-05-24 09:25:41.866799`
- raw_market_data: count=34312, range=`2024-04-13 22:00:00.000000` → `2026-05-24 12:29:21.452681`

## PM delivery pressure

- time_to_evidence_bucket: `semantic_rebaseline_review_required_before_reference_rows_count`
- missing_capability_class: `Constraint/Review`
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
| 100 | 0 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 200 | 49 | 1 | current_support_identity | False | 2026-05-22 04:14:55.602330 | win=0.0, pnl=-0.0171, quality=-0.39 |
| 600 | 78 | 17 | reference_only_calibration_window_mismatch | False | 2026-05-22 04:14:55.602330 | win=0.1176, pnl=-0.0044, quality=-0.1328 |
| 1000 | 278 | 54 | reference_only_calibration_window_mismatch | False | 2026-05-22 04:14:55.602330 | win=0.037, pnl=-0.0096, quality=-0.2484 |
| 5000 | 1627 | 260 | reference_only_calibration_window_mismatch | False | 2026-05-22 04:14:55.602330 | win=0.2077, pnl=-0.0036, quality=-0.0636 |
| all | 9648 | 3279 | reference_only_calibration_window_mismatch | False | 2026-05-22 04:14:55.602330 | win=0.5962, pnl=0.0083, quality=0.2795 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 1/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=chop、gate=CAUTION、entry_label=D、bucket=CAUTION|base_caution_regime_or_bias|q35 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
