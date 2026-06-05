# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-06-05T03:46:28.397005+00:00`
- source live probe generated_at: `2026-06-05T03:46:21.654036Z`
- source q15 audit generated_at: `2026-06-05T03:46:21.646189Z`
- classification: **current_identity_support_ready**
- reason: current support_identity already has enough exact-bucket rows; deployment should depend on the remaining live/execution gates.
- current exact bucket rows (deployable support candidate): **131/50**
- current exact identity rows before bucket filter: **183** (non-current-bucket: **52**; reference only, not deployment support)
- gap_to_minimum: **0**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `BLOCK|bias200_below_min|q00`
- regime_label: `bear`
- regime_gate: `BLOCK`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **25536**
- current calibration window filled: **True**
- symbol join policy: `timestamp_plus_canonical_symbol_latest_feature_and_label_id`
- canonical symbol recovered rows: **361** (strict=25175, canonical=361)
- symbol alignment evidence role: data cleanup only; live exposure remains fail-closed until all live gates pass.
- features_normalized: count=25839, range=`2024-04-14 07:00:00.000000` → `2026-06-05 03:00:00.000000`
- labels: count=69413, range=`2024-04-14 07:00:00.000000` → `2026-06-04 22:00:00.000000`
- raw_market_data: count=35124, range=`2024-04-13 22:00:00.000000` → `2026-06-05 03:00:00.000000`

## PM delivery pressure

- time_to_evidence_bucket: `ready_for_remaining_live_execution_gates`
- missing_capability_class: `Review`
- alternative_solution_required: **False**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 131/50 already meet minimum; keep deployable=false until circuit breaker, Top-K deployability, and venue/execution gates pass; reference rows stay non-deployable unless identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Support identity compression proof

- decision: **no_safe_compression_candidate_found**
- selected_candidate_id: `None`
- selected_candidate_rows: **0**
- live_exposure_allowed: **False**
- operator meaning: this is a structural redesign proof, not deployment clearance; buy/add remains fail-closed.

| candidate | rows | count-ready | metric-candidate | relaxed fields | deployable | metrics |
| --- | ---: | --- | --- | --- | --- | --- |
| current_exact_identity_window | 131 | True | False | — | False | win=0.3053, pnl=-0.0072, dd=0.3565 |
| rebaseline_calibration_window_only | 141 | True | False | calibration_window | False | win=0.3546, pnl=-0.0057, dd=0.3344 |
| semantic_entry_quality_family | 384 | True | False | calibration_window,entry_quality_label | False | win=0.5677, pnl=0.0009, dd=0.3449 |
| regime_gate_bucket_family | 559 | True | False | calibration_window,entry_quality_label,regime_label | False | win=0.6512, pnl=0.0054, dd=0.3259 |
| bucket_only_family | 559 | True | False | calibration_window,entry_quality_label,regime_label,regime_gate | False | win=0.6512, pnl=0.0054, dd=0.3259 |

Promotion requirements before any live buy/add:
- rerun replay/OOS/Top-K under the proposed compressed identity
- rerun q15 support audit with the new identity as the explicit support contract
- keep proxy/reference rows non-deployable until governance accepts the new identity
- keep /api/trade buy/add fail-closed until exact support, bounded live-canary policy, and venue lifecycle proof all pass

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 90 | 90 | reference_only_calibration_window_mismatch | False | 2026-06-04 04:00:00.000000 | win=0.2111, pnl=-0.0105, quality=-0.197 |
| 200 | 183 | 131 | current_support_identity | True | 2026-06-04 04:00:00.000000 | win=0.3053, pnl=-0.0072, quality=-0.082 |
| 600 | 269 | 131 | reference_only_calibration_window_mismatch | False | 2026-06-04 04:00:00.000000 | win=0.3053, pnl=-0.0072, quality=-0.082 |
| 1000 | 363 | 131 | reference_only_calibration_window_mismatch | False | 2026-06-04 04:00:00.000000 | win=0.3053, pnl=-0.0072, quality=-0.082 |
| 5000 | 473 | 139 | reference_only_calibration_window_mismatch | False | 2026-06-04 04:00:00.000000 | win=0.3453, pnl=-0.0062, quality=-0.0445 |
| all | 624 | 141 | reference_only_calibration_window_mismatch | False | 2026-06-04 04:00:00.000000 | win=0.3546, pnl=-0.0057, quality=-0.0335 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 131/50 已達門檻，但 support gate 不是 deployment closure；reference windows 仍不可直接算作額外 deployment support。
  - success: current support_identity exact rows 維持 >= minimum，且 circuit breaker / Top-K / venue / execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=BLOCK、entry_label=C、bucket=BLOCK|bias200_below_min|q00 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows 維持 >= 50 且 remaining live/execution gates 進入驗證。
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。
- **support_identity_compression_proof** (P0): 停止把主解法寫成反覆蒐集同一 exact key；改交付 support identity compression proof，目前選中候選=None，但所有候選都維持 deployable=false，直到 replay/OOS/Top-K/support audit/API guardrail 重跑通過。
  - success: 選定 compressed identity 後重跑治理證據；未完成前 buy/add live exposure 仍 fail-closed。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
