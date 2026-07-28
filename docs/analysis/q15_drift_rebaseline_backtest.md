# q15 drift-aware rebaseline backtest

- generated_at: `2026-07-28T19:03:42.152018Z`
- verdict: **reference_candidate_found_but_current_window_unproven**
- decision: A historical semantic candidate exists, but current calibration-window evidence is empty or under-minimum; it is reference-only and cannot release live buy/add.
- selected_candidate_id: `semantic_entry_quality_family`
- selected_current_window_rows: **43**
- selected_all_history_rows: **57**
- current exact support: **10/50**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## Recent drift context

- source_generated_at: `2026-07-28T19:03:21.143142+00:00`
- window: `100`
- win_rate: `0.63`
- dominant_regime: `chop` / share `0.57`
- avg_pnl: `0.0014` / avg_quality `0.2402` / drawdown_penalty `0.1315`

## Candidate matrix

| candidate | status | all rows | current-window rows | relaxed fields | deployable |
| --- | --- | ---: | ---: | --- | --- |
| current_exact_identity_window | baseline_current_identity | 22 | 10 | — | False |
| rebaseline_calibration_window_only | insufficient_rows | 22 | 10 | calibration_window | False |
| semantic_entry_quality_family | reference_candidate_current_window_under_minimum | 57 | 43 | calibration_window,entry_quality_label | False |
| regime_gate_bucket_family | reference_candidate_current_window_under_minimum | 171 | 43 | calibration_window,entry_quality_label,regime_label | False |
| bucket_only_family | reference_candidate_current_window_under_minimum | 171 | 43 | calibration_window,entry_quality_label,regime_label,regime_gate | False |

## Promotion requirements

- declare a new support_identity / semantic bucket contract before using any relaxed candidate
- rerun drift-aware replay, walk-forward OOS Top-K, q15 support audit, live probe, and API/trade guardrail checks
- keep current exact support rows separate from reference/rebaseline rows
- keep live buy/add fail-closed until support, breaker, model, venue lifecycle, and bounded live-canary policy gates all pass

## Forbidden shortcuts

- lower_minimum_support_rows
- count_reference_or_rebaseline_rows_as current exact support
- enable_live_buy_or_add_from_rebaseline_proof_alone

## Operator conclusion

This artifact can nominate a semantic/rebaseline candidate for replay, but it is not deployment clearance. Current live buy/add remains fail-closed.
