# q15 Exact Bucket Row Harvest Proof

- generated_at: `2026-06-05T03:46:33.530787Z`
- artifact: **q15_exact_bucket_row_harvest_proof**
- verdict: **exact_bucket_row_harvest_support_ready_remaining_gates**
- decision: Current exact bucket rows meet minimum support; this artifact proves support movement only, so live buy/add still waits for model, venue, API guardrail, and bounded-canary gates.
- current_live_structure_bucket: `BLOCK|bias200_below_min|q00`
- current exact rows: `131/50`
- previous rows: `131`
- delta_vs_previous: `0`
- rows_needed_to_minimum: `0`
- primary_failed_gate: `remaining_live_gates`
- live_exposure_allowed: `false`

## Current Calibration Window
- calibration_window: `200`
- exact_identity_rows: `183`
- exact_bucket_rows: `131`
- non_bucket_identity_rows: `52`
- latest_exact_bucket_timestamp: `2026-06-04 04:00:00.000000`
- oldest_exact_bucket_timestamp: `2026-05-28 21:00:00.000000`

## Symbol Alignment
- join_policy: `timestamp_plus_canonical_symbol_latest_feature_and_label_id`
- exact_bucket_symbol_join_modes: `{'canonical_symbol': 112, 'strict_symbol': 19}`
- exact_bucket_canonical_symbol_recovered_rows: `112`
- operator meaning: canonical symbol recovery is data cleanup evidence, not deployment clearance.

## Support Progress
- status: `exact_supported`
- regression_basis: `current_identity`
- stagnant_run_count: `4`
- semantic_signature_delta_vs_previous: `0`

## Safety Boundary
- This artifact is not deployment clearance.
- Positive row movement only proves support accumulation; live buy/add remains blocked until support, model, venue, API guardrail, and bounded-canary gates all pass.
