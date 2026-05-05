# q15 support-fill feasibility scan

- generated_at: `2026-05-05T01:23:30.613414+00:00`
- source live probe generated_at: `2026-05-04T23:56:36.596810Z`
- source q15 audit generated_at: `2026-05-04 23:56:23.006167`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current rows: **0/50**
- gap_to_minimum: **50**
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

- joined labeled rows: **23788**
- current calibration window filled: **True**
- features_normalized: count=24127, range=`2024-04-14 07:00:00.000000` → `2026-05-05 01:00:00.000000`
- labels: count=65894, range=`2024-04-14 07:00:00.000000` → `2026-05-04 20:00:00.000000`
- raw_market_data: count=32726, range=`2024-04-13 22:00:00.000000` → `2026-05-05 01:00:00.000000`

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 0 | 0 | current_support_identity | False | None | win=None, pnl=None, quality=None |
| 200 | 0 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 600 | 166 | 66 | reference_only_calibration_window_mismatch | False | 2026-04-24 15:00:53.067369 | win=0.3333, pnl=-0.0002, quality=0.0685 |
| 1000 | 166 | 66 | reference_only_calibration_window_mismatch | False | 2026-04-24 15:00:53.067369 | win=0.3333, pnl=-0.0002, quality=0.0685 |
| 5000 | 256 | 71 | reference_only_calibration_window_mismatch | False | 2026-04-24 15:00:53.067369 | win=0.3803, pnl=0.0012, quality=0.1114 |
| all | 994 | 134 | reference_only_calibration_window_mismatch | False | 2026-04-24 15:00:53.067369 | win=0.6119, pnl=0.0077, quality=0.3067 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 unsupported_exact_live_structure_bucket / allowed_layers=0；reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=100、regime/gate/entry_label/bucket 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 600/all 等舊窗口的足量 rows，必須先改 support_identity / calibration_window policy，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
