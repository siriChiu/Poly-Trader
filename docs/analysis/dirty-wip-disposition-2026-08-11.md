# Dirty WIP Disposition — 2026-08-11

> Classification: **historical audit snapshot**
> Repository observed: `/home/kazuha/Poly-Trader`
> Stable source baseline: `9e973bba9aa3c01aece12b18d1229f3e13c49e91`
> Refactor worktree: `/home/kazuha/Poly-Trader-refactor`
> Refactor branch: `refactor/bdd-authority-20260811`

## Purpose

Freeze the pre-refactor dirty worktree without describing it as committed behavior and without mixing generated runtime reports into domain refactoring commits.

## Observed boundary

At capture time:

- `main` and `origin/main` both pointed to `9e973bba9aa3c01aece12b18d1229f3e13c49e91`;
- the index had no staged changes;
- 52 tracked files were modified;
- two untracked entries existed: `.hermes/` and the literal accidental filename `docs/analysis/venu...[truncated]`;
- no tracked-but-ignored files existed.

The original dirty worktree was deliberately left untouched.

## Verified backup

Repo-external backup:

```text
/home/kazuha/poly-trader-wip-backups/2026-08-11-main-9e973bba/
```

Contents:

- `tracked-full.patch` — all tracked changes, binary-capable;
- `source-tests.patch` — only the four source/test changes below;
- `untracked-venue-report/venu...[truncated]` — the accidental untracked generated report;
- `MANIFEST.md` and `SHA256SUMS`.

Both patches passed `git apply --check --cached` against the stable index. `sha256sum -c SHA256SUMS` passed for every backed-up file. `.hermes/`, databases, credentials, logs, venvs, node_modules and graph indexes were explicitly excluded.

## Source/test WIP disposition

### Preserve and re-implement with stronger tests

1. `execution/exchanges/okx_adapter.py`
2. `tests/test_execution_service.py`

Intent:

- normalize OKX `cash` to CCXT `spot`;
- restrict market catalog loading to the configured spot type;
- keep spot sell free of derivative-only `reduceOnly`.

Audit result:

- direction is a safety improvement and does not unlock live execution;
- existing WIP test proves constructor options but does not fully prove authenticated `connect()`, `load_markets()`, aliases, invalid types or final request payload;
- integrate into the refactor branch through TDD, with Phase-1 non-spot rejection.

Observed source hashes:

- adapter: `e7a6e55015c270152520043cb2ad90a8e53831a687898eda1796136d384a7ca9`
- test: `605006747d27eaad5de8a9757db3faf035c99f74a2e7e0926edc9c980018cf92`

### Preserve intent, do not merge current patch as final

1. `scripts/hb_parallel_runner.py`
2. `tests/test_hb_parallel_runner.py`

Useful intent:

- a forced external-governor branch may not be downgraded to standby when a valid current receipt is bound;
- without valid external proof, heartbeat must not self-certify completion.

Required repairs before integration:

- receipt validation must also bind blocker, minimum rows, delta, semantic signature, generation/freshness, independent verifier and safety fields;
- the consumer should share the receipt validator instead of trusting persisted `receipt_valid=true`;
- fast heartbeat needs one real global 240-second deadline, not an elapsed value captured before later serial lanes;
- subprocess/pool exceptions must produce an honest non-zero CLI exit;
- add stale/malformed/mismatch tests and CLI deadline/failure contracts.

Observed source hashes:

- runner: `d5ecafe7a5a2de4ce841a883b65ee0921dfac37f96bffb6ddfd2f2380e96a563`
- test: `718931d892960c6b1fd624087a8517345bf1cf7c37bb2b0eafc870c7f259b0af`

The exact source patch is preserved and checksum-verified in the backup directory.

## Generated/current-state artifacts

Forty-five modified Markdown/JSON outputs had meaningful generated-state changes. They are not hand-written normative policy and will not be manually merged. This family includes:

- generated `data/*.json` except the timestamp-only files listed below;
- generated `docs/analysis/*.md` except the timestamp-only file below;
- `model/ic_signs.json` and `model/topk_walkforward_precision.json`;
- `issues.json`, `ISSUES.md`, `ROADMAP.md`, `ORID_DECISIONS.md`;
- `docs/ai-collaboration/pm/pm-status.md`;
- generated `docs/plans/2026-05-23-live-canary-structural-pivot.md`.

Disposition:

1. finish and verify source refactors;
2. run the canonical producer chain once;
3. publish one same-generation final sync;
4. keep generated outputs separate from domain implementation commits.

The family was not one atomic snapshot: embedded generations ranged across feature/ablation, Top-K, heartbeat/current-state and later paper/shadow reconciliation runs. Therefore individual files must not be cherry-picked as one timeless truth.

## Safe churn / discard

The following were timestamp-only or obsolete duplicate churn and must not be carried into refactor commits:

- `data/execution_metadata_smoke.json`;
- `data/venue_dry_run_proof.json`;
- `docs/analysis/venue_dry_run_proof.md`;
- untracked literal `docs/analysis/venu...[truncated]`.

The accidental untracked report has no repository references and is superseded by the tracked companion.

## Agent-local plan

`.hermes/plans/2026-07-16_164000-poly-trader-feasibility-rearchitecture-roadmap.md` is a meaningful historical plan but is not product runtime authority. It remains excluded from Git. If retained later, it must be reviewed, marked historical and deliberately moved into the canonical docs topology.

## Safety verification

- Credential values were not read, copied or printed.
- Focused execution tests observed by the audit: 33 passed.
- Full heartbeat-runner test file observed by the audit: 187 passed.
- Related receipt/governor tests observed by the audit: 5 passed.
- Production SQLite size/mtime/inode and WAL/SHM state were unchanged by the read-only audit.
- These passing tests characterize the WIP; they do not resolve the listed P1 heartbeat gaps.

## Result

Phase 0.2 is complete because every dirty file now has an explicit disposition and a verified recovery path. All implementation continues from the clean refactor worktree; the dirty `main` checkout remains an untouched evidence generation, not a development base.
