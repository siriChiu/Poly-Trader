# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-05-26T21:15:30.668191+00:00`
- source live probe generated_at: `2026-05-26T21:15:26.607960Z`
- source q15 audit generated_at: `2026-05-26 21:14:48.332682`
- classification: **semantic_window_gap_not_raw_backfill_gap**
- reason: older calibration windows have enough exact-bucket rows by count, but they mismatch the current support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity.
- current exact bucket rows (deployable support candidate): **0/50**
- current exact identity rows before bucket filter: **3** (non-current-bucket: **3**; reference only, not deployment support)
- gap_to_minimum: **50**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `BLOCK|bear_bias200_hard_block|q00`
- regime_label: `bear`
- regime_gate: `BLOCK`
- entry_quality_label: `D`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **25069**
- current calibration window filled: **True**
- features_normalized: count=25480, range=`2024-04-14 07:00:00.000000` → `2026-05-26 21:14:48.332682`
- labels: count=68494, range=`2024-04-14 07:00:00.000000` → `2026-05-26 18:12:22.204875`
- raw_market_data: count=34570, range=`2024-04-13 22:00:00.000000` → `2026-05-26 21:14:48.332682`

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

## Support identity compression proof

- decision: **candidate_found_not_deployable**
- selected_candidate_id: `rebaseline_calibration_window_only`
- selected_candidate_rows: **366**
- live_exposure_allowed: **False**
- operator meaning: this is a structural redesign proof, not deployment clearance; buy/add remains fail-closed.

| candidate | rows | count-ready | metric-candidate | relaxed fields | deployable | metrics |
| --- | ---: | --- | --- | --- | --- | --- |
| current_exact_identity_window | 0 | False | False | — | False | win=None, pnl=None, dd=None |
| rebaseline_calibration_window_only | 366 | True | True | calibration_window | False | win=0.6667, pnl=0.0059, dd=0.2048 |
| semantic_entry_quality_family | 445 | True | True | calibration_window,entry_quality_label | False | win=0.7079, pnl=0.0092, dd=0.1971 |
| regime_gate_bucket_family | 445 | True | True | calibration_window,entry_quality_label,regime_label | False | win=0.7079, pnl=0.0092, dd=0.1971 |
| bucket_only_family | 445 | True | True | calibration_window,entry_quality_label,regime_label,regime_gate | False | win=0.7079, pnl=0.0092, dd=0.1971 |

Promotion requirements before any live buy/add:
- rerun replay/OOS/Top-K under the proposed compressed identity
- rerun q15 support audit with the new identity as the explicit support contract
- keep proxy/reference rows non-deployable until governance accepts the new identity
- keep /api/trade buy/add fail-closed until exact support, bounded live-canary policy, and venue lifecycle proof all pass

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 0 | 0 | reference_only_calibration_window_mismatch | False | None | win=None, pnl=None, quality=None |
| 200 | 3 | 0 | current_support_identity | False | None | win=None, pnl=None, quality=None |
| 600 | 10 | 3 | reference_only_calibration_window_mismatch | False | 2026-05-23 13:00:00.000000 | win=1.0, pnl=0.0255, quality=0.6816 |
| 1000 | 34 | 3 | reference_only_calibration_window_mismatch | False | 2026-05-23 13:00:00.000000 | win=1.0, pnl=0.0255, quality=0.6816 |
| 5000 | 36 | 3 | reference_only_calibration_window_mismatch | False | 2026-05-23 13:00:00.000000 | win=1.0, pnl=0.0255, quality=0.6816 |
| all | 1036 | 366 | reference_only_calibration_window_mismatch | False | 2026-05-23 13:00:00.000000 | win=0.6667, pnl=0.0059, quality=0.296 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 0/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=BLOCK、entry_label=D、bucket=BLOCK|bear_bias200_hard_block|q00 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=all 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。
- **support_identity_compression_proof** (P0): 停止把主解法寫成反覆蒐集同一 exact key；改交付 support identity compression proof，目前選中候選=rebaseline_calibration_window_only，但所有候選都維持 deployable=false，直到 replay/OOS/Top-K/support audit/API guardrail 重跑通過。
  - success: 選定 compressed identity 後重跑治理證據；未完成前 buy/add live exposure 仍 fail-closed。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
