# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-20T22:11:57.460311+00:00`
- source live probe generated_at: `2026-05-20T22:11:48.422120Z`
- source q15 audit generated_at: `2026-05-20 22:11:32.960610`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current rows: **0/50**
- gap_to_minimum: **50**
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

- joined labeled rows: **24461**
- current calibration window filled: **True**
- features_normalized: count=24882, range=`2024-04-14 07:00:00.000000` → `2026-05-20 22:11:32.960610`
- labels: count=67302, range=`2024-04-14 07:00:00.000000` → `2026-05-20 19:10:28.393393`
- raw_market_data: count=33845, range=`2024-04-13 22:00:00.000000` → `2026-05-20 22:11:32.960610`

## PM delivery pressure

- time_to_evidence_bucket: `semantic_rebaseline_review_required_before_reference_rows_count`
- missing_capability_class: `Constraint/Review`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 0/50 must reach minimum; gap=50; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 0 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 200 | 0 | 0 | current_support_identity | False | None | win=None, pnl=None, quality=None |
| 600 | 47 | 2 | reference_only_calibration_window_mismatch | False | 2026-05-15 07:02:23.735185 | win=0.5, pnl=-0.0024, quality=0.0519 |
| 1000 | 93 | 2 | reference_only_calibration_window_mismatch | False | 2026-05-15 07:02:23.735185 | win=0.5, pnl=-0.0024, quality=0.0519 |
| 5000 | 281 | 49 | reference_only_calibration_window_mismatch | False | 2026-05-15 07:02:23.735185 | win=0.9796, pnl=0.0183, quality=0.6036 |
| all | 1329 | 292 | reference_only_calibration_window_mismatch | False | 2026-05-15 07:02:23.735185 | win=0.9726, pnl=0.0215, quality=0.6374 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 0/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=chop、gate=CAUTION、entry_label=C、bucket=CAUTION|base_caution_regime_or_bias|q15 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
