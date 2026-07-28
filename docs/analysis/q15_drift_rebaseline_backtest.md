# q15 drift-aware rebaseline backtest

- generated_at: `2026-07-28T14:46:19.392264Z`
- verdict: **no_rebaseline_candidate_found**
- decision: No semantic/rebaseline candidate has enough evidence; keep exact-row harvest or hard no-go as the forced branch.
- selected_candidate_id: `None`
- selected_current_window_rows: **None**
- selected_all_history_rows: **None**
- current exact support: **0/50**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## Recent drift context

- source_generated_at: `2026-07-28T14:46:02.116873+00:00`
- window: `100`
- win_rate: `0.63`
- dominant_regime: `chop` / share `0.57`
- avg_pnl: `0.0014` / avg_quality `0.2402` / drawdown_penalty `0.1315`

## Candidate matrix

| candidate | status | all rows | current-window rows | relaxed fields | deployable |
| --- | --- | ---: | ---: | --- | --- |
| current_exact_identity_window | baseline_current_identity | 4 | 0 | — | False |
| rebaseline_calibration_window_only | insufficient_rows | 4 | 0 | calibration_window | False |
| semantic_entry_quality_family | insufficient_rows | 4 | 0 | calibration_window,entry_quality_label | False |
| regime_gate_bucket_family | insufficient_rows | 4 | 0 | calibration_window,entry_quality_label,regime_label | False |
| bucket_only_family | insufficient_rows | 4 | 0 | calibration_window,entry_quality_label,regime_label,regime_gate | False |

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
