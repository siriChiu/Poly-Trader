# q15 Map/Signal redesign proof

- generated_at: `2026-06-05T03:46:44.756417Z`
- verdict: **map_signal_redesign_no_current_window_deployable_candidate**
- decision: Map/signal candidates were evaluated but none passed current-window support and metric gates.
- selected_candidate_id: `dominant_neighbor_exact_lane`
- selected_target_bucket: `BLOCK|bear_bias200_hard_block|q00`
- selected_current_window_rows: **28**
- selected_all_history_rows: **174**
- best_reference_candidate_id: `best_historical_exact_lane_bucket`
- current exact support: **131/50**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## Root-cause context

- root verdict: `same_lane_neighbor_bucket_dominates`
- candidate_patch_type: `structure_component_scoring`
- candidate_patch_feature: `feat_4h_bb_pct_b`
- dominant_neighbor_bucket: `BLOCK|bear_bias200_hard_block|q00`
- dominant_neighbor_rows: `174`
- near_boundary_rows: `293`

## Candidate matrix

| candidate | status | target | current rows | all rows | all win rate | current win rate | deployable |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `current_exact_identity_window` | `baseline_current_identity` | `BLOCK|bias200_below_min|q00` | 131 | 141 | 0.3546 | 0.3053 | False |
| `semantic_entry_quality_family` | `current_window_count_ready_metric_rejected` | `BLOCK|bias200_below_min|q00` | 137 | 384 | 0.5677 | 0.3139 | False |
| `dominant_neighbor_exact_lane` | `count_ready_metric_rejected` | `BLOCK|bear_bias200_hard_block|q00` | 28 | 174 | 0.523 | 0.8214 | False |
| `dominant_neighbor_semantic_family` | `reference_candidate_current_window_under_minimum` | `BLOCK|bear_bias200_hard_block|q00` | 29 | 586 | 0.5853 | 0.8276 | False |
| `q35_boundary_exact_lane` | `insufficient_rows` | `|q35` | 0 | 25 | 0.92 | None | False |
| `q35_regime_gate_family` | `reference_candidate_current_window_empty` | `|q35` | 0 | 108 | 0.6667 | None | False |
| `best_historical_exact_lane_bucket` | `reference_candidate_current_window_empty` | `BLOCK|bear_bias200_hard_block|q15` | 0 | 133 | 0.9549 | None | False |

## Guardrail

This artifact is not deployment clearance. It is a forced-branch proof that evaluates redesign candidates while preserving current exact support as the live gate.
