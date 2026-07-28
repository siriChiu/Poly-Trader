#!/usr/bin/env python3
"""Start the local Poly-Trader API and web development server together.

Run from the repository root with one command:

    python scripts/dev.py

On a fresh checkout the launcher creates a project virtual environment and
installs missing Python / frontend dependencies.  It never installs packages
into the operating system Python.

The launcher deliberately uses fixed ports by default.  It does not silently
fall back to a different port, because doing so can leave the browser connected
to an old API process and make Strategy Lab results look inconsistent.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"


class LauncherError(RuntimeError):
    """A local prerequisite prevents the development servers from starting."""


def _port_type(value: str | int, *, label: str = "埠號") -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label} 必須是有效的埠號：{value!r}") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"{label} 必須介於 1 到 65535：{port}")
    return port


def _env_port(name: str, default: int) -> int:
    return _port_type(os.environ.get(name, str(default)), label=name)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="以一個指令同時啟動 Poly-Trader API 與 Web 開發伺服器。"
    )
    parser.add_argument(
        "--api-host",
        default=os.environ.get("POLY_TRADER_API_HOST", "127.0.0.1"),
        help="API 綁定位址（預設：127.0.0.1）。",
    )
    parser.add_argument(
        "--api-port",
        type=_port_type,
        default=_env_port("POLY_TRADER_API_PORT", 8000),
        help="API 埠號（預設：8000）。",
    )
    parser.add_argument(
        "--web-host",
        default=os.environ.get("POLY_TRADER_WEB_HOST", "127.0.0.1"),
        help="前端綁定位址（預設：127.0.0.1）。",
    )
    parser.add_argument(
        "--web-port",
        type=_port_type,
        default=_env_port("POLY_TRADER_WEB_PORT", 5173),
        help="前端埠號（預設：5173）。",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="停用 API 的程式碼自動重載。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出將執行的指令，不啟動服務。",
    )
    return parser


def _candidate_python_paths() -> list[Path]:
    override = os.environ.get("POLY_TRADER_PYTHON")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(shutil.which(override) or override).expanduser())

    candidates.extend(_project_virtualenv_pythons())
    candidates.append(Path(sys.executable))

    unique: list[Path] = []
    for candidate in candidates:
        # Do not call ``resolve()`` here.  A virtualenv's Python executable is
        # normally a symlink to the system interpreter; resolving it would
        # discard the virtualenv context and accidentally run global Python.
        absolute = candidate.absolute()
        if absolute not in unique:
            unique.append(absolute)
    return unique


def _project_virtualenv_pythons() -> list[Path]:
    if os.name == "nt":
        return [
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        ]
    return [
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / "venv" / "bin" / "python",
    ]


def _is_project_virtualenv_python(python: Path) -> bool:
    return python.is_file() and (python.parent.parent / "pyvenv.cfg").is_file()


def _has_api_dependencies(python: Path) -> bool:
    if not python.is_file():
        return False
    check = subprocess.run(
        # Import the actual application rather than only uvicorn.  The API
        # imports model dependencies such as xgboost during startup, so this
        # prevents a partial virtualenv from being selected.
        [str(python), "-c", "import server.main"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return check.returncode == 0


def _install_python_dependencies(python: Path) -> None:
    print(f"正在使用專案虛擬環境安裝 Python 相依套件：{python}")
    try:
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=PROJECT_ROOT,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LauncherError(
            "無法在專案虛擬環境安裝 Python 相依套件。"
            "請確認網路與 pip 可用；不要使用 --break-system-packages。"
        ) from exc


def _bootstrap_python_environment() -> Path:
    python = next(
        (candidate for candidate in _project_virtualenv_pythons() if _is_project_virtualenv_python(candidate)),
        None,
    )
    if python is None:
        environment_dir = PROJECT_ROOT / ".venv"
        if environment_dir.exists():
            raise LauncherError(
                f"{environment_dir} 不是可用的虛擬環境。請移除或修復它後再執行。"
            )
        print(f"正在建立專案虛擬環境：{environment_dir}")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(environment_dir)],
                cwd=PROJECT_ROOT,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise LauncherError(
                "無法建立 Python 虛擬環境。Ubuntu / Debian 可先安裝 python3-venv。"
            ) from exc
        python = _project_virtualenv_pythons()[0]

    _install_python_dependencies(python)
    if _has_api_dependencies(python):
        return python
    raise LauncherError(
        "Python 相依套件安裝完成後仍無法載入 API。"
        f"請以 {python} 執行 `-c 'import server.main'` 查看詳細錯誤。"
    )


def _resolve_python() -> Path:
    for candidate in _candidate_python_paths():
        if _has_api_dependencies(candidate):
            return candidate
    return _bootstrap_python_environment()


def _resolve_npm() -> str:
    executable = "npm.cmd" if os.name == "nt" else "npm"
    npm = shutil.which(executable)
    if not npm:
        raise LauncherError("找不到 npm。請先安裝 Node.js 18+。")
    if not WEB_DIR.is_dir():
        raise LauncherError(f"找不到前端目錄：{WEB_DIR}")
    vite_paths = [
        WEB_DIR / "node_modules" / ".bin" / "vite",
        WEB_DIR / "node_modules" / ".bin" / "vite.cmd",
    ]
    if not any(path.exists() for path in vite_paths):
        print("正在安裝前端相依套件…")
        try:
            subprocess.run([npm, "--prefix", "web", "install"], cwd=PROJECT_ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise LauncherError("無法安裝前端相依套件。請確認網路與 npm 可用。") from exc
        if not any(path.exists() for path in vite_paths):
            raise LauncherError("前端相依套件安裝後仍找不到 Vite。")
    return npm


def _assert_port_available(host: str, port: int, service_name: str) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
    except OSError as exc:
        raise LauncherError(
            f"{service_name} 埠 {host}:{port} 已被使用。為避免前端誤連到舊服務，"
            "啟動器不會自動改用其他埠。\n"
            f"請關閉佔用程序後再執行，或改用：python scripts/dev.py "
            f"--{'api' if service_name == 'API' else 'web'}-port <新埠號>"
        ) from exc


def _popen_kwargs() -> dict[str, object]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _stop_process(process: subprocess.Popen[object] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _format_command(command: Sequence[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def _http_base(host: str, port: int) -> str:
    # URLs require brackets around an IPv6 literal, unlike socket.bind().
    url_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{url_host}:{port}"


def _build_commands(args: argparse.Namespace, python: Path, npm: str) -> tuple[list[str], list[str], dict[str, str]]:
    api_command = [
        str(python),
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    if not args.no_reload:
        api_command.append("--reload")

    web_command = [
        npm,
        "--prefix",
        "web",
        "run",
        "dev",
        "--",
        "--host",
        args.web_host,
        "--port",
        str(args.web_port),
        "--strictPort",
    ]
    api_base = _http_base(args.api_host, args.api_port)
    web_env = os.environ.copy()
    # Pin both direct API calls and Vite's proxy to the newly launched backend.
    # This avoids the browser choosing a stale 8001/9123 development process.
    web_env["VITE_API_BASE"] = api_base
    web_env["VITE_API_PROXY_TARGET"] = api_base
    return api_command, web_command, web_env


def _run(args: argparse.Namespace) -> int:
    if args.api_port == args.web_port and args.api_host == args.web_host:
        raise LauncherError("API 與前端不能使用相同的 host / port。")

    if args.dry_run:
        python = Path("<project-python>")
        npm = "npm.cmd" if os.name == "nt" else "npm"
    else:
        _assert_port_available(args.api_host, args.api_port, "API")
        _assert_port_available(args.web_host, args.web_port, "前端")
        python = _resolve_python()
        npm = _resolve_npm()

    api_command, web_command, web_env = _build_commands(args, python, npm)
    api_base = web_env["VITE_API_BASE"]
    print(f"API：{api_base}")
    print(f"Web：{_http_base(args.web_host, args.web_port)}")
    print(f"API command：{_format_command(api_command)}")
    print(f"Web command：VITE_API_BASE={api_base} {_format_command(web_command)}")

    if args.dry_run:
        return 0

    print("\n正在啟動 API 與前端；按 Ctrl+C 可一併停止。")
    api_process: subprocess.Popen[object] | None = None
    web_process: subprocess.Popen[object] | None = None
    try:
        api_process = subprocess.Popen(
            api_command,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            **_popen_kwargs(),
        )
        web_process = subprocess.Popen(
            web_command,
            cwd=PROJECT_ROOT,
            env=web_env,
            **_popen_kwargs(),
        )

        while True:
            api_code = api_process.poll()
            web_code = web_process.poll()
            if api_code is not None:
                print(f"\nAPI 已結束（exit code {api_code}），正在關閉前端。", file=sys.stderr)
                return api_code or 1
            if web_code is not None:
                print(f"\n前端已結束（exit code {web_code}），正在關閉 API。", file=sys.stderr)
                return web_code or 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\n正在停止 API 與前端…")
        return 0
    finally:
        _stop_process(web_process)
        _stop_process(api_process)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return _run(args)
    except LauncherError as exc:
        print(f"無法啟動：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
