"""Repository hygiene contracts.

These tests keep heartbeat run logs and one-off scripts from drifting back into the
source tree.  They intentionally check git-tracked files, not ignored local output.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_ls_files(*patterns: str) -> list[str]:
    cmd = ["git", "ls-files", *patterns]
    output = subprocess.check_output(cmd, cwd=PROJECT_ROOT, text=True)
    return [line for line in output.splitlines() if line.strip()]


def test_generated_heartbeat_run_logs_are_not_tracked() -> None:
    """Per-run heartbeat summaries/progress reports belong to ignored runtime output."""

    tracked = _git_ls_files(
        "HEARTBEAT_SUMMARY*.md",
        "HEARTBEAT_*_SUMMARY.md",
        "data/heartbeat_*",
    )

    assert tracked == []


def test_root_python_files_are_only_runtime_entrypoints() -> None:
    """Ad-hoc diagnostics should live under scripts/legacy_checks or formal CLIs."""

    root_python = sorted(
        path
        for path in _git_ls_files("*.py")
        if "/" not in path
    )

    assert root_python == ["config.py", "main.py"]


def test_architecture_doc_is_not_a_heartbeat_changelog() -> None:
    """Architecture docs should describe current contracts, not append historical logs."""

    architecture = (PROJECT_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert len(architecture) < 40_000
    assert "Heartbeat #" not in architecture
    assert "Heartbeat 2026-" not in architecture
    assert "每輪 summary" not in architecture


def test_gitignore_blocks_future_heartbeat_log_pollution() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = [
        "HEARTBEAT_SUMMARY*.md",
        "HEARTBEAT_*_SUMMARY.md",
        "data/heartbeat_*_summary.json",
        "data/heartbeat_*_progress.json",
        "data/heartbeat_*_summary.md",
        "data/heartbeat_*_report.md",
        "data/heartbeat_*_report.txt",
        "data/heartbeat_*_results.json",
        "data/hb*_summary.json",
        "data/hb*_results.json",
        "data/hb_*_probe.json",
        "data/hb_parallel_summary_*.json",
    ]

    required_unignored_contracts = [
        "!data/live_predict_probe.json",
        "!data/high_conviction_topk_oos_matrix.json",
        "!data/no_trade_lane_replay.json",
        "!data/venue_dry_run_proof.json",
        "!model/xgb_model.pkl",
    ]

    for pattern in required_patterns + required_unignored_contracts:
        assert pattern in gitignore

    lines = set(gitignore.splitlines())
    assert "/_*.py" in lines
    assert "/hb_*.py" in lines
    assert "scripts/hb_*.py" in lines
    assert "!scripts/hb_parallel_runner.py" in lines
    assert "_*.py" not in lines
    assert "hb_*.py" not in lines


def test_moved_legacy_scripts_are_documented() -> None:
    readme = (PROJECT_ROOT / "scripts/legacy_checks/README.md").read_text(
        encoding="utf-8"
    )

    assert "New temporary checks should not be added to the project root" in readme
    assert "tests/comprehensive_test.py" in readme
    assert "promote it into `scripts/` with tests" in readme


def test_prd_high_conviction_truth_tracks_current_live_blocker() -> None:
    """PRD product truth must not advertise stale breaker/supported-bucket closure."""

    prd = (PROJECT_ROOT / "PRD.md").read_text(encoding="utf-8")
    section = prd.split("### 5. High-Conviction Top-k ROI Gate（P0）", 1)[1].split("---", 1)[0]

    assert "deployment_blocker=unsupported_exact_live_structure_bucket" in section
    assert "support_route=insufficient_support_everywhere" in section
    assert "support_governance_route=exact_live_lane_proxy_available" in section
    assert "bucket=CAUTION|structure_quality_caution|q15" in section
    assert "bucket_rows=0/50" in section
    assert "deployment_blocker=circuit_breaker_active" not in section
    assert "support route 已是 `exact_bucket_supported`" not in section


def test_repo_cleanroom_audit_preserves_operational_state() -> None:
    """Cleanroom audit must not be a thin wrapper around destructive git clean."""

    output = subprocess.check_output(
        [sys.executable, "scripts/repo_cleanroom_audit.py", "--format", "json"],
        cwd=PROJECT_ROOT,
        text=True,
    )
    payload = json.loads(output)

    assert "scripts/repo_cleanroom_audit.py" in payload["closed_loop_entrypoints"]
    assert "venv" in payload["protected_policy"]["never_clean_by_default"]
    candidate_paths = [candidate["path"] for candidate in payload["cleanup_candidates"]]
    assert not any(
        path.startswith(("model/", "model_4h/")) and "__pycache__" not in path
        for path in candidate_paths
    )

    forbidden_prefixes = (
        "venv/",
        ".venv/",
        "env/",
        "web/node_modules/",
        "data/live_",
        "data/q15_",
        "data/high_conviction_",
        "data/customer_safe_",
    )
    for candidate in payload["cleanup_candidates"]:
        path = candidate["path"]
        assert not path.startswith(forbidden_prefixes)
        if path.startswith("data/execution_metadata_"):
            assert path.endswith(".log")

    protected_paths = list(payload["protected_policy"]["heavy_protected_artifacts"])
    assert "poly_trader.db" in protected_paths


def test_cleanroom_entrypoint_is_documented() -> None:
    docs = [
        (PROJECT_ROOT / "README.md").read_text(encoding="utf-8"),
        (PROJECT_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8"),
        (PROJECT_ROOT / "docs/ai-collaboration/HEARTBEAT.md").read_text(encoding="utf-8"),
        (PROJECT_ROOT / "docs/ai-collaboration/harness/README.md").read_text(encoding="utf-8"),
    ]

    for text in docs:
        assert "scripts/repo_cleanroom_audit.py" in text
    assert "git clean -fdX" in docs[1]
