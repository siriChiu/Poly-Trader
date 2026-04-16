from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "execution_metadata_external_monitor_install_contract.json"
DEFAULT_INTERVAL_SECONDS = 300.0
DEFAULT_SERVICE_NAME = "poly-trader-execution-metadata-external-monitor"


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _build_monitor_command(symbol: str, interval_seconds: float) -> str:
    interval_arg = _format_number(interval_seconds)
    return (
        f"cd {PROJECT_ROOT} && source venv/bin/activate && "
        f"python scripts/execution_metadata_external_monitor.py --symbol {symbol} "
        f"--interval-seconds {interval_arg}"
    )


def _build_schedule(interval_seconds: float) -> str:
    minutes = max(int(round(interval_seconds / 60.0)), 1)
    if interval_seconds % 60 == 0 and minutes <= 59:
        return f"*/{minutes} * * * *"
    return f"# every {minutes} minutes (manual/custom scheduler required)"


def build_install_contract(
    symbol: str = "BTCUSDT",
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> dict:
    monitor_command = _build_monitor_command(symbol, interval_seconds)
    log_path = PROJECT_ROOT / "data" / "execution_metadata_external_monitor.log"
    schedule = _build_schedule(interval_seconds)
    cron_entry = f"{schedule} {monitor_command} >> {log_path} 2>&1"
    service_file = f"~/.config/systemd/user/{service_name}.service"
    timer_file = f"~/.config/systemd/user/{service_name}.timer"
    service_unit = "\n".join([
        "[Unit]",
        "Description=Poly-Trader execution metadata external monitor",
        "After=network-online.target",
        "",
        "[Service]",
        "Type=oneshot",
        f"WorkingDirectory={PROJECT_ROOT}",
        f"ExecStart=/bin/bash -lc '{monitor_command}'",
        "",
    ])
    timer_unit = "\n".join([
        "[Unit]",
        "Description=Run Poly-Trader execution metadata external monitor on a fixed cadence",
        "",
        "[Timer]",
        f"OnBootSec={max(int(interval_seconds), 60)}",
        f"OnUnitActiveSec={max(int(interval_seconds), 60)}",
        "Persistent=true",
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])
    return {
        "version": 1,
        "preferred_host_lane": "user_crontab",
        "reason": "讓 execution metadata governance 在 API process 掛掉時仍保有 process-external 監看路徑",
        "project_root": str(PROJECT_ROOT),
        "symbol": symbol,
        "interval_seconds": interval_seconds,
        "generator_command": (
            f"cd {PROJECT_ROOT} && source venv/bin/activate && "
            f"python scripts/execution_metadata_external_monitor_install.py --symbol {symbol}"
        ),
        "manual_run_command": monitor_command,
        "verify_artifact_command": (
            f"test -f {PROJECT_ROOT / 'data' / 'execution_metadata_external_monitor.json'} && "
            f"tail -n 40 {PROJECT_ROOT / 'data' / 'execution_metadata_external_monitor.json'}"
        ),
        "fallback": {
            "mode": "manual_or_existing_scheduler",
            "reason": "若本輪無法直接安裝 host-level scheduler，至少保留可重跑 command 與 verify contract。",
            "command": monitor_command,
            "verify_command": f"test -f {PROJECT_ROOT / 'data' / 'execution_metadata_external_monitor.json'}",
        },
        "user_crontab": {
            "schedule": schedule,
            "entry": cron_entry,
            "install_command": (
                f"(crontab -l 2>/dev/null | grep -v '{service_name}'; "
                f"echo '{cron_entry} # {service_name}') | crontab -"
            ),
            "verify_command": f"crontab -l | grep '{service_name}'",
        },
        "systemd_user": {
            "service_name": service_name,
            "service_file": service_file,
            "timer_file": timer_file,
            "service_unit": service_unit,
            "timer_unit": timer_unit,
            "install_steps": [
                f"mkdir -p ~/.config/systemd/user && cat > {service_file}",
                f"cat > {timer_file}",
                "systemctl --user daemon-reload",
                f"systemctl --user enable --now {service_name}.timer",
            ],
            "verify_command": f"systemctl --user status {service_name}.timer --no-pager",
        },
        "output_artifact": str(DEFAULT_OUTPUT),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate host-level install/fallback contract for the external metadata monitor"
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol to embed in commands")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Expected cadence for the host-level scheduler",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Where to write the JSON contract")
    parser.add_argument(
        "--service-name",
        default=DEFAULT_SERVICE_NAME,
        help="Logical name used in cron tags/systemd unit names",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = build_install_contract(
        symbol=args.symbol,
        interval_seconds=args.interval_seconds,
        service_name=args.service_name,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(contract, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
