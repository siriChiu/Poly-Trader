# q15 support-fill feasibility scan

- generated_at: `2026-05-07T11:32:57.589655+00:00`
- source live probe generated_at: `2026-05-07T11:32:38.540109Z`
- source q15 audit generated_at: `2026-05-07 11:30:55.146061`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current rows: **38/50**
- gap_to_minimum: **12**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned q15 support identity

This section is the q15 identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `BLOCK|bull_q15_bias50_overextended_block|q15`
- regime_label: `bull`
- regime_gate: `BLOCK`
- entry_quality_label: `D`
- calibration_window: `100`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **23840**
- current calibration window filled: **True**
- features_normalized: count=24178, range=`2024-04-14 07:00:00.000000` → `2026-05-07 11:30:55.146061`
- labels: count=65996, range=`2024-04-14 07:00:00.000000` → `2026-05-07 08:00:00.000000`
- raw_market_data: count=32777, range=`2024-04-13 22:00:00.000000` → `2026-05-07 11:30:55.146061`

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 38 | 38 | current_support_identity | False | 2026-05-06 12:00:00.000000 | win=0.5526, pnl=0.004, quality=0.2309 |
| 200 | 38 | 38 | reference_only_calibration_window_mismatch | False | 2026-05-06 12:00:00.000000 | win=0.5526, pnl=0.004, quality=0.2309 |
| 600 | 191 | 95 | reference_only_calibration_window_mismatch | False | 2026-05-06 12:00:00.000000 | win=0.4316, pnl=0.0016, quality=0.1416 |
| 1000 | 204 | 104 | reference_only_calibration_window_mismatch | False | 2026-05-06 12:00:00.000000 | win=0.4135, pnl=0.0013, quality=0.1278 |
| 5000 | 294 | 109 | reference_only_calibration_window_mismatch | False | 2026-05-06 12:00:00.000000 | win=0.4404, pnl=0.0022, quality=0.153 |
| all | 1032 | 172 | reference_only_calibration_window_mismatch | False | 2026-05-06 12:00:00.000000 | win=0.5988, pnl=0.0069, quality=0.29 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 unsupported_exact_live_structure_bucket / allowed_layers=0；reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=100、regime/gate/entry_label/bucket 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 600/all 等舊窗口的足量 rows，必須先改 support_identity / calibration_window policy，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
