# Legacy diagnostics / check scripts

This folder contains one-off diagnostic scripts that were previously scattered across
the repo root and `scripts/`.

## Why they were moved here

- They were not imported by production code.
- They were mostly ad-hoc inspection scripts for DB, labels, regimes, IC checks, and
  model sanity checks.
- Keeping them in one place reduces top-level clutter and makes it easier to decide
  what should be deleted later.
- Many of the old `_*check*.py` helpers are now replaced by `scripts/diagnose.py`.

## Layout

- `root/` — old root-level `check_*.py`, `_check_*.py`, and heartbeat-style scripts
- `scripts/` — old `scripts/check_*.py`, `scripts/_check_*.py`, and related diagnostics

## Notes

- These scripts are kept for reference and manual debugging.
- If a diagnostic becomes part of the real workflow, it should be promoted into a
  proper module or CLI command instead of staying here.
- New temporary checks should not be added to the project root.
