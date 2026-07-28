# current support-fill feasibility scan (q15/q35 compatibility)

- generated_at: `2026-07-28T18:28:27.877149+00:00`
- source live probe generated_at: `2026-07-28T18:28:22.623339Z`
- source q15 audit generated_at: `2026-07-28T18:28:22.609544Z`
- classification: **true_support_under_minimum**
- reason: current identity is missing support and full history also remains under minimum; collect forward exact rows or redesign the bucket.
- current exact bucket rows (deployable support candidate): **10/50**
- current exact identity rows before bucket filter: **10** (non-current-bucket: **0**; reference only, not deployment support)
- gap_to_minimum: **40**
- historical backfill can close current identity: **False**
- reference windows deployable by count alone: **False**

## Scanned current support identity

This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.

- target_col: `simulated_pyramid_win`
- horizon_minutes: `1440`
- current_live_structure_bucket: `CAUTION|structure_quality_caution|q15`
- regime_label: `bear`
- regime_gate: `CAUTION`
- entry_quality_label: `C`
- calibration_window: `200`
- bucket_semantic_signature: `live_structure_bucket:q15_support_identity:v2`

## Data coverage

- joined labeled rows: **29152**
- current calibration window filled: **True**
- symbol join policy: `timestamp_plus_canonical_symbol_latest_feature_and_label_id`
- canonical symbol recovered rows: **2019** (strict=27133, canonical=2019)
- symbol alignment evidence role: data cleanup only; live exposure remains fail-closed until all live gates pass.
- features_normalized: count=29364, range=`2024-04-14 07:00:00.000000` → `2026-07-28 18:09:30.410367`
- labels: count=76425, range=`2024-04-14 07:00:00.000000` → `2026-07-28 11:29:42.581059`
- raw_market_data: count=38689, range=`2024-04-13 22:00:00.000000` → `2026-07-28 18:09:30.410367`

## PM delivery pressure

- time_to_evidence_bucket: `within_week_if_exact_identity_keeps_accumulating`
- missing_capability_class: `Signal/Support`
- alternative_solution_required: **True**
- selected_next_alternative_artifact: data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy
- customer_safe_lane: paper/shadow decision-support; no buy/add live exposure
- engineering_next_gate: exact current support rows 10/50 must reach minimum; gap=40; reference rows stay non-deployable until identity is deliberately rebaselined and reverified

### Alternative-solution candidates

- `paper_shadow_decision_support_sleeve` (customer_usable_now): data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy / live_exposure_allowed=False
- `semantic_rebaseline_review` (support_policy_alternative): OOS + Top-K + support audit replay under any proposed new calibration_window identity / live_exposure_allowed=False
- `venue_dry_run_readiness_proof` (delivery_risk_reduction): OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only / live_exposure_allowed=False

## Support identity compression proof

- decision: **candidate_found_not_deployable**
- selected_candidate_id: `semantic_entry_quality_family`
- selected_candidate_rows: **57**
- live_exposure_allowed: **False**
- operator meaning: this is a structural redesign proof, not deployment clearance; buy/add remains fail-closed.

| candidate | rows | count-ready | metric-candidate | relaxed fields | deployable | metrics |
| --- | ---: | --- | --- | --- | --- | --- |
| current_exact_identity_window | 10 | False | False | — | False | win=1.0, pnl=0.0126, dd=0.0272 |
| rebaseline_calibration_window_only | 22 | False | False | calibration_window | False | win=0.5909, pnl=0.0047, dd=0.1726 |
| semantic_entry_quality_family | 57 | True | True | calibration_window,entry_quality_label | False | win=0.8421, pnl=0.0082, dd=0.092 |
| regime_gate_bucket_family | 171 | True | True | calibration_window,entry_quality_label,regime_label | False | win=0.6667, pnl=0.0055, dd=0.1921 |
| bucket_only_family | 171 | True | True | calibration_window,entry_quality_label,regime_label,regime_gate | False | win=0.6667, pnl=0.0055, dd=0.1921 |

Promotion requirements before any live buy/add:
- rerun replay/OOS/Top-K under the proposed compressed identity
- rerun q15 support audit with the new identity as the explicit support contract
- keep proxy/reference rows non-deployable until governance accepts the new identity
- keep /api/trade buy/add fail-closed until exact support, bounded live-canary policy, and venue lifecycle proof all pass

## Window scan

| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |
| --- | ---: | ---: | --- | --- | --- | --- |
| 100 | 10 | 10 | reference_only_calibration_window_mismatch | False | 2026-07-26 11:32:05.163038 | win=1.0, pnl=0.0126, quality=0.5907 |
| 200 | 10 | 10 | current_support_identity | False | 2026-07-26 11:32:05.163038 | win=1.0, pnl=0.0126, quality=0.5907 |
| 600 | 10 | 10 | reference_only_calibration_window_mismatch | False | 2026-07-26 11:32:05.163038 | win=1.0, pnl=0.0126, quality=0.5907 |
| 1000 | 10 | 10 | reference_only_calibration_window_mismatch | False | 2026-07-26 11:32:05.163038 | win=1.0, pnl=0.0126, quality=0.5907 |
| 5000 | 74 | 22 | reference_only_calibration_window_mismatch | False | 2026-07-26 11:32:05.163038 | win=0.5909, pnl=0.0047, quality=0.2452 |
| all | 74 | 22 | reference_only_calibration_window_mismatch | False | 2026-07-26 11:32:05.163038 | win=0.5909, pnl=0.0047, quality=0.2452 |

## Recommended actions

- **keep_deployment_fail_closed** (P0): 維持 deployable=false / allowed_layers=0；current support identity exact rows 10/50，未達門檻前 reference windows 不可直接算作 deployment support。
  - success: current support_identity exact rows >= minimum 且 live/execution gates 同步通過。
- **collect_forward_exact_current_identity_rows** (P0): 繼續收集與 current calibration_window=200、regime=bear、gate=CAUTION、entry_label=C、bucket=CAUTION|structure_quality_caution|q15 完全一致的真實 labeled rows。
  - success: current_exact_bucket_rows >= 50
- **semantic_rebaseline_if_using_older_windows** (P1): 若要採用 reference window=5000 的 rows 或改變 calibration_window policy，必須先改 support_identity，重跑 OOS、Top-K、support audit、API/trade guardrail，而不是把舊 rows 直接補進 current identity。
  - success: 新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。
- **support_identity_compression_proof** (P0): 停止把主解法寫成反覆蒐集同一 exact key；改交付 support identity compression proof，目前選中候選=semantic_entry_quality_family，但所有候選都維持 deployable=false，直到 replay/OOS/Top-K/support audit/API guardrail 重跑通過。
  - success: 選定 compressed identity 後重跑治理證據；未完成前 buy/add live exposure 仍 fail-closed。

## Operator conclusion

舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。
