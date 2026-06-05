#!/usr/bin/env python3
"""Verify the active backend `/health` payload is current-head and usable.

The probe accepts JSON from stdin, `--health-file`, or an HTTP `/health` URL.
It is intentionally small and stdlib-only so heartbeat/operator checks can
fail fast before trusting any API payload from a stale backend process.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
CURRENT_HEAD_STATUS = "current_head_commit"
ALLOWED_RAW_CONTINUITY = {"clean", "repaired"}
ALLOWED_FEATURE_CONTINUITY = {"clean", "repaired", "deferred"}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object in {path}")
    return payload


def _health_url(value: str | None) -> str:
    base = (value or DEFAULT_BASE_URL).strip()
    if not base:
        base = DEFAULT_BASE_URL
    if base.rstrip("/").endswith("/health"):
        return base.rstrip("/")
    return f"{base.rstrip('/')}/health"


def _read_stdin_payload() -> dict[str, Any] | None:
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object on stdin")
    return payload


def _fetch_health(url: str, *, timeout: float) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except (OSError, URLError) as exc:
        return None, str(exc)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from {url}: {exc.msg}"
    if not isinstance(payload, dict):
        return None, f"expected top-level JSON object from {url}"
    return payload, None


def summarize_health(payload: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    runtime = _mapping(payload.get("runtime_build"))
    raw_continuity = _mapping(payload.get("raw_continuity"))
    feature_continuity = _mapping(payload.get("feature_continuity"))

    health_status = payload.get("status")
    head_sync_status = runtime.get("head_sync_status")
    raw_status = raw_continuity.get("status")
    feature_status = feature_continuity.get("status")
    blockers: list[str] = []
    next_actions: list[str] = []

    if health_status != "ok":
        blockers.append("health_status_not_ok")
        next_actions.append("inspect backend startup logs and /health response")

    if not runtime:
        blockers.append("runtime_build_missing")
        next_actions.append("update /health to expose runtime_build metadata")
    elif head_sync_status != CURRENT_HEAD_STATUS:
        if head_sync_status == "stale_head_commit":
            blockers.append("active_backend_stale_head_commit")
            next_actions.append("restart the active backend process and rerun /health")
        else:
            blockers.append(f"active_backend_head_sync_{head_sync_status or 'missing'}")
            next_actions.append("inspect runtime_build.head_sync_status before trusting API payloads")

    if raw_status not in ALLOWED_RAW_CONTINUITY:
        blockers.append(f"raw_continuity_{raw_status or 'missing'}")
        next_actions.append("run startup/data continuity maintenance before operator proof")

    if feature_status not in ALLOWED_FEATURE_CONTINUITY:
        blockers.append(f"feature_continuity_{feature_status or 'missing'}")
        next_actions.append("run feature continuity maintenance before operator proof")

    # Preserve order while deduplicating next actions.
    deduped_actions: list[str] = []
    seen_actions: set[str] = set()
    for action in next_actions:
        if action not in seen_actions:
            seen_actions.add(action)
            deduped_actions.append(action)

    strict_ok = not blockers
    return {
        "probe": "active_backend_health",
        "source": source,
        "strict_ok": strict_ok,
        "active_backend_ready": strict_ok,
        "runtime_current": head_sync_status == CURRENT_HEAD_STATUS,
        "restart_required": head_sync_status == "stale_head_commit",
        "health_status": health_status,
        "head_sync_status": head_sync_status,
        "head_sync_basis": runtime.get("head_sync_basis"),
        "process_started_at": runtime.get("process_started_at"),
        "git_head_commit": runtime.get("git_head_commit"),
        "latest_runtime_source_path": runtime.get("latest_runtime_source_path"),
        "latest_runtime_source_modified_at": runtime.get(
            "latest_runtime_source_modified_at"
        ),
        "raw_continuity_status": raw_status,
        "feature_continuity_status": feature_status,
        "blockers": blockers,
        "next_actions": deduped_actions,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL. `/health` is appended when omitted.",
    )
    parser.add_argument(
        "--health-url",
        help="Explicit /health URL. Overrides --base-url.",
    )
    parser.add_argument(
        "--health-file",
        type=Path,
        help="Read a saved /health JSON payload instead of HTTP.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the active backend is not current and usable.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = "stdin"
    payload = _read_stdin_payload()
    if payload is None and args.health_file is not None:
        payload = _load_json(args.health_file)
        source = str(args.health_file)
    if payload is None:
        url = _health_url(args.health_url or args.base_url)
        payload, error = _fetch_health(url, timeout=args.timeout)
        source = url
        if payload is None:
            summary = {
                "probe": "active_backend_health",
                "source": source,
                "strict_ok": False,
                "active_backend_ready": False,
                "runtime_current": False,
                "restart_required": False,
                "health_status": None,
                "head_sync_status": None,
                "raw_continuity_status": None,
                "feature_continuity_status": None,
                "blockers": ["health_fetch_failed"],
                "next_actions": ["start or restart the active backend and rerun /health"],
                "error": error,
            }
            json.dump(
                summary,
                sys.stdout,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":") if args.compact else None,
                indent=None if args.compact else 2,
            )
            sys.stdout.write("\n")
            return 1 if args.strict else 0

    summary = summarize_health(payload, source=source)
    json.dump(
        summary,
        sys.stdout,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":") if args.compact else None,
        indent=None if args.compact else 2,
    )
    sys.stdout.write("\n")
    return 0 if summary["strict_ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
