# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-22T07:13:22.652596+00:00`
- source live probe generated_at: `2026-05-22T07:13:08.523161Z`
- source q15 audit generated_at: `2026-05-22 07:12:52.531896`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current rows: **33/50**
- gap_to_minimum: **17**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- regime_label: `chop`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24601**
- current calibration window filled: **True**
- features_normalized: count=25035, range=`2024-04-14 07:00:00.000000` → `2026-05-22 07:12:52.531896`
- labels: count=67596, range=`2024-04-14 07:00:00.000000` → `2026-05-22 04:11:56.675626`
- raw_market_data: count=34031, range=`2024-04-13 22:00:00.000000` → `2026-05-22 07:12:52.531896`

## PM delivery pressure

- time_to_evidence_bucket: `semantic_rebaseline_review_required_before_reference_rows_count`
- missing_capability_class: `Constraint/Review`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 33/50 must reach minimum; gap=17; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 81 | 30 | reference_only_calibration_window_mismatch | False | 2026-05-21 07:12:43.279502 | win=0.5, pnl=0.0004, quality=0.165 |
| 200 | 89 | 33 | current_support_identity | False | 2026-05-21 07:12:43.279502 | win=0.5455, pnl=0.0009, quality=0.1978 |
| 600 | 104 | 35 | reference_only_calibration_window_mismatch | False | 2026-05-21 07:12:43.279502 | win=0.5429, pnl=0.0007, quality=0.1895 |
| 1000 | 182 | 35 | reference_only_calibration_window_mismatch | False | 2026-05-21 07:12:43.279502 | win=0.5429, pnl=0.0007, quality=0.1895 |
| 5000 | 328 | 82 | reference_only_calibration_window_mismatch | False | 2026-05-21 07:12:43.279502 | win=0.8049, pnl=0.0113, quality=0.4403 |
| all | 1418 | 325 | reference_only_calibration_window_mismatch | False | 2026-05-21 07:12:43.279502 | win=0.9292, pnl=0.0194, quality=0.5928 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 33/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=chop、gate=CAUTION、entry_label=C、bucket=CAUTION|base_caution_regime_or_bias|q15 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
