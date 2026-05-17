"""Repository hygiene contracts.

These tests keep heartbeat run logs and one-off scripts from drifting back into the
source tree.  They intentionally check git-tracked files, not ignored local output.
"""

from __future__ import annotations

import fnmatch
import subprocess
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
    ]

    for pattern in required_patterns:
        assert pattern in gitignore


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
