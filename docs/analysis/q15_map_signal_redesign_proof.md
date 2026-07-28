# q15 Map/Signal redesign proof

- generated_at: `2026-07-28T18:28:48.584829Z`
- verdict: **map_signal_redesign_no_current_window_deployable_candidate**
- decision: Map/signal candidates were evaluated but none passed current-window support and metric gates.
- selected_candidate_id: `dominant_neighbor_exact_lane`
- selected_target_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- selected_current_window_rows: **0**
- selected_all_history_rows: **38**
- best_reference_candidate_id: `semantic_entry_quality_family`
- current exact support: **10/50**
- live_exposure_allowed: **False**
- order_submission_enabled: **False**

## Root-cause context

- root verdict: `runtime_blocker_preempts_bucket_root_cause`
- candidate_patch_type: `None`
- candidate_patch_feature: `None`
- dominant_neighbor_bucket: `CAUTION|base_caution_regime_or_bias|q15`
- dominant_neighbor_rows: `38`
- near_boundary_rows: `50`

## Candidate matrix

| candidate | status | target | current rows | all rows | all win rate | current win rate | deployable |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `current_exact_identity_window` | `baseline_current_identity` | `CAUTION|structure_quality_caution|q15` | 10 | 22 | 0.5909 | 1.0 | False |
| `semantic_entry_quality_family` | `reference_candidate_current_window_under_minimum` | `CAUTION|structure_quality_caution|q15` | 43 | 57 | 0.8421 | 1.0 | False |
| `dominant_neighbor_exact_lane` | `insufficient_rows` | `CAUTION|base_caution_regime_or_bias|q15` | 0 | 38 | 0.7368 | None | False |
| `dominant_neighbor_semantic_family` | `insufficient_rows` | `CAUTION|base_caution_regime_or_bias|q15` | 0 | 46 | 0.7609 | None | False |
| `q35_boundary_exact_lane` | `insufficient_rows` | `|q35` | 0 | 1 | 1.0 | None | False |
| `q35_regime_gate_family` | `insufficient_rows` | `|q35` | 0 | 4 | 1.0 | None | False |

## Guardrail

This artifact is not deployment clearance. It is a forced-branch proof that evaluates redesign candidates while preserving current exact support as the live gate.
