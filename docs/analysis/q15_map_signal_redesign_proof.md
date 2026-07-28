# q15 Map/Signal redesign proof

- generated_at: `2026-07-28T14:46:21.413972Z`
- verdict: **map_signal_redesign_reference_only_current_window_unproven**
- decision: A map/signal redesign candidate exists only as historical/reference evidence; current-window support is empty or under-minimum.
- selected_candidate_id: `dominant_neighbor_exact_lane`
- selected_target_bucket: `BLOCK|structure_overextended_block|q85`
- selected_current_window_rows: **0**
- selected_all_history_rows: **338**
- best_reference_candidate_id: `dominant_neighbor_exact_lane`
- current exact support: **0/50**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## Root-cause context

- root verdict: `runtime_blocker_preempts_bucket_root_cause`
- candidate_patch_type: `None`
- candidate_patch_feature: `None`
- dominant_neighbor_bucket: `BLOCK|structure_overextended_block|q85`
- dominant_neighbor_rows: `233`
- near_boundary_rows: `71`

## Candidate matrix

| candidate | status | target | current rows | all rows | all win rate | current win rate | deployable |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `current_exact_identity_window` | `baseline_current_identity` | `BLOCK|structure_quality_block|q00` | 0 | 4 | 1.0 | None | False |
| `semantic_entry_quality_family` | `insufficient_rows` | `BLOCK|structure_quality_block|q00` | 0 | 4 | 1.0 | None | False |
| `dominant_neighbor_exact_lane` | `reference_candidate_current_window_empty` | `BLOCK|structure_overextended_block|q85` | 0 | 338 | 0.645 | None | False |
| `dominant_neighbor_semantic_family` | `reference_candidate_current_window_empty` | `BLOCK|structure_overextended_block|q85` | 0 | 2172 | 0.6192 | None | False |
| `q35_boundary_exact_lane` | `insufficient_rows` | `|q35` | 0 | 0 | None | None | False |
| `q35_regime_gate_family` | `insufficient_rows` | `|q35` | 0 | 0 | None | None | False |
| `best_historical_exact_lane_bucket` | `reference_candidate_current_window_empty` | `BLOCK|bear_bias200_hard_block|q00` | 0 | 56 | 0.5893 | None | False |

## Guardrail

This artifact is not deployment clearance. It is a forced-branch proof that evaluates redesign candidates while preserving current exact support as the live gate.
