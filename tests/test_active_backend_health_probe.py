from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "active_backend_health_probe.py"


def _health_payload(
    *,
    head_sync_status: str = "current_head_commit",
    raw_status: str = "clean",
    feature_status: str = "clean",
    status: str = "ok",
) -> dict:
    return {
        "status": status,
        "runtime_build": {
            "process_started_at": "2026-06-04T06:57:44Z",
            "git_head_commit": "abc123",
            "head_sync_status": head_sync_status,
            "head_sync_basis": "latest_runtime_source_modified_at",
            "latest_runtime_source_path": "server/routes/api.py",
            "latest_runtime_source_modified_at": "2026-06-04T06:50:00Z",
        },
        "raw_continuity": {"status": raw_status},
        "feature_continuity": {"status": feature_status},
    }


def _run(args: list[str], *, input_payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(input_payload) if input_payload is not None else None,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
    )


def test_probe_passes_for_current_head_backend_from_stdin() -> None:
    result = _run(["--strict"], input_payload=_health_payload())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["active_backend_ready"] is True
    assert summary["runtime_current"] is True
    assert summary["restart_required"] is False
    assert summary["blockers"] == []
    assert summary["head_sync_status"] == "current_head_commit"


def test_probe_fails_strict_for_stale_active_backend() -> None:
    result = _run(
        ["--strict"],
        input_payload=_health_payload(head_sync_status="stale_head_commit"),
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["runtime_current"] is False
    assert summary["restart_required"] is True
    assert "active_backend_stale_head_commit" in summary["blockers"]
    assert any("restart" in action for action in summary["next_actions"])


def test_probe_fails_strict_for_continuity_error() -> None:
    result = _run(
        ["--strict"],
        input_payload=_health_payload(feature_status="error"),
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert "feature_continuity_error" in summary["blockers"]


def test_probe_accepts_saved_health_file(tmp_path: Path) -> None:
    health_file = tmp_path / "health.json"
    health_file.write_text(json.dumps(_health_payload(feature_status="deferred")), encoding="utf-8")

    result = _run(["--strict", "--health-file", str(health_file)])

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["source"] == str(health_file)
    assert summary["feature_continuity_status"] == "deferred"
    assert summary["strict_ok"] is True
