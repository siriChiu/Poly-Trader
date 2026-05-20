# current support-fill feasibility scan (q15/q35)

- generated_at: `2026-05-20T06:12:57.238268+00:00`
- source live probe generated_at: `2026-05-20T06:12:46.217516Z`
- source q15 audit generated_at: `2026-05-20 06:12:25.971102`
- classification: **no_exact_bucket_history**
- reason: no exact-bucket rows were found under current bucket semantics; this is a support-harvest/design gap, not a backtest-results gap.
- current rows: **0/50**
- gap_to_minimum: **50**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned q15 support identity

This section is the q15 identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|base_caution_regime_or_bias|q35`
- regime_label: `bear`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **24400**
- current calibration window filled: **True**
- features_normalized: count=24814, range=`2024-04-14 07:00:00.000000` → `2026-05-20 06:12:25.971102`
- labels: count=67174, range=`2024-04-14 07:00:00.000000` → `2026-05-20 03:10:38.844453`
- raw_market_data: count=33762, range=`2024-04-13 22:00:00.000000` → `2026-05-20 06:12:25.971102`

## PM delivery pressure

- time_to_evidence_bucket: `unknown_until_bucket_map_or_signal_redesign`
- missing_capability_class: `Map/Signal`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 0/50 must reach minimum; gap=50; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 86 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 200 | 146 | 0 | current_support_identity | False | None | win=None, pnl=None, quality=None |
| 600 | 167 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 1000 | 187 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 5000 | 187 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| all | 188 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 0/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=CAUTION、entry_label=C、bucket=CAUTION|base_caution_regime_or_bias|q35 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=100 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
