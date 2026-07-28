# q15 Exact Bucket Row Harvest Proof

- generated_at: `2026-07-28T14:46:17.368066Z`
- artifact: **q15_exact_bucket_row_harvest_proof**
- verdict: **exact_bucket_row_harvest_no_current_rows**
- decision: No current exact bucket rows are available; keep exact-row harvest or hard no-go as the forced branch.
- current_live_structure_bucket: `BLOCK|structure_quality_block|q00`
- current exact rows: `0/50`
- previous rows: `0`
- delta_vs_previous: `0`
- rows_needed_to_minimum: `50`
- primary_failed_gate: `current_live_support_gate`
- live_exposure_allowed: `false`

## Current Calibration Window
- calibration_window: `200`
- exact_identity_rows: `0`
- exact_bucket_rows: `0`
- non_bucket_identity_rows: `0`
- latest_exact_bucket_timestamp: `None`
- oldest_exact_bucket_timestamp: `None`

## Symbol Alignment
- join_policy: `timestamp_plus_canonical_symbol_latest_feature_and_label_id`
- exact_bucket_symbol_join_modes: `{}`
- exact_bucket_canonical_symbol_recovered_rows: `0`
- operator meaning: canonical symbol recovery is data cleanup evidence, not deployment clearance.

## Support Progress
- status: `stalled_under_minimum`
- regression_basis: `same_identity_same_semantic_signature`
- stagnant_run_count: `2`
- semantic_signature_delta_vs_previous: `0`

## Safety Boundary
- This artifact is not deployment clearance.
- Positive row movement only proves support accumulation; live buy/add remains blocked until support, model, venue, API guardrail, and bounded-canary gates all pass.
