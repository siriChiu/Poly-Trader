"""Regression checks for the one-command local development launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import scripts.dev as dev


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dev_launcher_dry_run_pins_frontend_to_its_api() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/dev.py",
            "--dry-run",
            "--api-port",
            "9123",
            "--web-port",
            "5174",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "API：http://127.0.0.1:9123" in completed.stdout
    assert "Web：http://127.0.0.1:5174" in completed.stdout
    assert "uvicorn server.main:app" in completed.stdout
    assert "--strictPort" in completed.stdout
    assert "VITE_API_BASE=http://127.0.0.1:9123" in completed.stdout


def test_python_dependency_bootstrap_uses_project_virtualenv_pip(monkeypatch) -> None:
    project_python = PROJECT_ROOT / "venv" / "bin" / "python"
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(dev.subprocess, "run", fake_run)

    dev._install_python_dependencies(project_python)

    assert commands == [
        [str(project_python), "-m", "pip", "install", "-r", "requirements.txt"]
    ]
