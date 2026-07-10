#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
RUNNER_BINARY = PROJECT_ROOT / "bin" / "poly-trader-live"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "poly_trader_live_install_contract.json"
DEFAULT_SERVICE_NAME = "poly-trader-live"
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_verify_command(command: str) -> dict:
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as exc:
        return {
            "installed": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "checked_at": _utc_now(),
        }
    return {
        "installed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
        "checked_at": _utc_now(),
    }


def _runner_command(config_path: Path, *, dry_run: bool = False, no_submit: bool = False, shadow_candidate: bool = False) -> str:
    parts = [
        str(RUNNER_BINARY),
        "--config",
        str(config_path),
    ]
    if dry_run:
        parts.append("--dry-run")
    if no_submit:
        parts.append("--no-submit")
    if shadow_candidate:
        parts.append("--shadow-candidate")
    return " ".join(shlex.quote(part) for part in parts)


def build_install_contract(
    *,
    config_path: Path = DEFAULT_CONFIG,
    service_name: str = DEFAULT_SERVICE_NAME,
    dry_run: bool = False,
    no_submit: bool = False,
    shadow_candidate: bool = False,
) -> dict:
    command = f"cd {shlex.quote(str(PROJECT_ROOT))} && {_runner_command(config_path, dry_run=dry_run, no_submit=no_submit, shadow_candidate=shadow_candidate)}"
    service_file = f"~/.config/systemd/user/{service_name}.service"
    verify_command = f"systemctl --user status {service_name}.service --no-pager"
    service_status = _run_verify_command(verify_command)
    service_unit = "\n".join(
        [
            "[Unit]",
            "Description=Poly-Trader standalone live trading runner",
            "Wants=network-online.target",
            "After=network-online.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={PROJECT_ROOT}",
            "Environment=PYTHONUNBUFFERED=1",
            f"ExecStart=/bin/bash -lc {shlex.quote(command)}",
            "Restart=on-failure",
            "RestartSec=15",
            "KillSignal=SIGTERM",
            "TimeoutStopSec=30",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )
    return {
        "version": 1,
        "preferred_host_lane": "systemd_user",
        "reason": "讓 standalone live runner 可在 dashboard/API 之外背景持續執行",
        "project_root": str(PROJECT_ROOT),
        "runner_binary": str(RUNNER_BINARY),
        "python_cli": f"{VENV_PYTHON} scripts/poly_trader_live.py",
        "config_path": str(config_path),
        "service_name": service_name,
        "dry_run": bool(dry_run),
        "no_submit": bool(no_submit),
        "shadow_candidate": bool(shadow_candidate),
        "shadow_evidence_mode": bool(dry_run and no_submit and shadow_candidate),
        "generated_at": _utc_now(),
        "manual_run_command": command,
        "install_status": {
            "status": "installed" if service_status["installed"] else "install_ready",
            "installed": service_status["installed"],
            "checked_at": service_status["checked_at"],
            "systemd_user": {
                **service_status,
                "verify_command": verify_command,
            },
        },
        "systemd_user": {
            "service_name": service_name,
            "service_file": service_file,
            "service_unit": service_unit,
            "install_steps": [
                "mkdir -p ~/.config/systemd/user",
                f"cat > {service_file}",
                "systemctl --user daemon-reload",
                f"systemctl --user enable --now {service_name}.service",
            ],
            "start_command": f"systemctl --user start {service_name}.service",
            "stop_command": f"systemctl --user stop {service_name}.service",
            "restart_command": f"systemctl --user restart {service_name}.service",
            "verify_command": verify_command,
            "logs_command": f"journalctl --user -u {service_name}.service -f",
        },
        "audit_outputs": {
            "decision_tables": ["live_runner_runs", "live_runner_decisions"],
            "jsonl_dir": str(PROJECT_ROOT / "data" / "live_trading"),
            "trade_tables": ["trade_history", "order_lifecycle_events"],
        },
        "output_artifact": str(DEFAULT_OUTPUT),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate user-systemd install contract for Poly-Trader live runner")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Config file path embedded in the service")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Where to write the JSON contract")
    parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME, help="systemd user service name without .service")
    parser.add_argument("--dry-run", action="store_true", help="Embed --dry-run in ExecStart")
    parser.add_argument("--no-submit", action="store_true", help="Embed --no-submit in ExecStart")
    parser.add_argument("--shadow-candidate", action="store_true", help="Embed --shadow-candidate in ExecStart for no-submit 24h evidence")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = build_install_contract(
        config_path=Path(args.config).expanduser().resolve(),
        service_name=args.service_name,
        dry_run=args.dry_run,
        no_submit=args.no_submit,
        shadow_candidate=args.shadow_candidate,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(contract, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
