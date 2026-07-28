# q15 Exact Bucket Row Harvest Proof

- generated_at: `2026-07-28T18:28:37.675880Z`
- artifact: **q15_exact_bucket_row_harvest_proof**
- verdict: **exact_bucket_row_harvest_stalled_under_minimum**
- decision: Current exact support is still under minimum and has no positive delta; anti-equilibrium forced execution must not fall back to observation-only.
- current_live_structure_bucket: `CAUTION|structure_quality_caution|q15`
- current exact rows: `10/50`
- previous rows: `10`
- delta_vs_previous: `0`
- rows_needed_to_minimum: `40`
- primary_failed_gate: `support_accumulation_stalled`
- live_exposure_allowed: `false`

## Current Calibration Window
- calibration_window: `200`
- exact_identity_rows: `10`
- exact_bucket_rows: `10`
- non_bucket_identity_rows: `0`
- latest_exact_bucket_timestamp: `2026-07-26 11:32:05.163038`
- oldest_exact_bucket_timestamp: `2026-07-26 01:55:17.731478`

## Symbol Alignment
- join_policy: `timestamp_plus_canonical_symbol_latest_feature_and_label_id`
- exact_bucket_symbol_join_modes: `{'strict_symbol': 10}`
- exact_bucket_canonical_symbol_recovered_rows: `0`
- operator meaning: canonical symbol recovery is data cleanup evidence, not deployment clearance.

## Support Progress
- status: `semantic_rebaseline_under_minimum`
- regression_basis: `legacy_or_different_semantic_signature`
- stagnant_run_count: `2`
- semantic_signature_delta_vs_previous: `0`

## Safety Boundary
- This artifact is not deployment clearance.
- Positive row movement only proves support accumulation; live buy/add remains blocked until support, model, venue, API guardrail, and bounded-canary gates all pass.
