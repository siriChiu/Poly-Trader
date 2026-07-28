from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException

DEFAULT_ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:9119",
    "http://localhost:9119",
)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def normalize_origin(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text == "*":
        raise ValueError("CORS origins must be explicit; wildcard or empty origins are forbidden")

    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"invalid HTTP(S) origin: {text!r}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"origin must not include credentials, query, or fragment: {text!r}")
    if parsed.path not in {"", "/"}:
        raise ValueError(f"origin must not include a path: {text!r}")

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    parsed_port = parsed.port
    if (parsed.scheme.lower(), parsed_port) in {("http", 80), ("https", 443)}:
        parsed_port = None
    port = f":{parsed_port}" if parsed_port is not None else ""
    return f"{parsed.scheme.lower()}://{host}{port}"


def normalize_loopback_origin(value: Any) -> str:
    origin = normalize_origin(value)
    if urlsplit(origin).hostname not in LOOPBACK_HOSTS:
        raise ValueError(f"operator origins must use an explicit loopback host: {origin!r}")
    return origin


def configured_allowed_origins(config: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    env_value = os.environ.get("POLY_TRADER_ALLOWED_ORIGINS")
    if env_value is not None:
        raw_origins: Sequence[Any] = [item for item in env_value.split(",") if item.strip()]
    else:
        server_config = (config or {}).get("server", {})
        configured = server_config.get("allowed_origins") if isinstance(server_config, Mapping) else None
        raw_origins = configured if isinstance(configured, Sequence) and not isinstance(configured, str) else DEFAULT_ALLOWED_ORIGINS

    normalized: list[str] = []
    for raw_origin in raw_origins:
        origin = normalize_loopback_origin(raw_origin)
        if origin not in normalized:
            normalized.append(origin)
    if not normalized:
        raise ValueError("at least one explicit CORS origin is required")
    return tuple(normalized)


def assert_local_operator_request(
    request: Any,
    *,
    allowed_origins: Sequence[str] = DEFAULT_ALLOWED_ORIGINS,
) -> None:
    client = getattr(request, "client", None)
    client_host = getattr(client, "host", None)
    if client_host not in LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=403,
            detail="operator write endpoints are restricted to local access",
        )

    headers = getattr(request, "headers", None)
    origin = headers.get("origin") if headers is not None and hasattr(headers, "get") else None
    if origin is None:
        return

    try:
        normalized_origin = normalize_loopback_origin(origin)
        normalized_allowed = {normalize_loopback_origin(item) for item in allowed_origins}
    except ValueError:
        normalized_origin = ""
        normalized_allowed = set()
    if normalized_origin not in normalized_allowed:
        raise HTTPException(
            status_code=403,
            detail="operator write origin is not allowlisted",
        )
