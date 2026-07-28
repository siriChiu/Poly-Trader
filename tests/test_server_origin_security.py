from __future__ import annotations

import asyncio
import ast
from types import SimpleNamespace
from typing import Any
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware


def _request(*, host: str = "127.0.0.1", origin: str | None = None) -> Any:
    headers = {} if origin is None else {"origin": origin}
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers)


async def _cors_preflight(app: Any, origin: str) -> tuple[int, dict[str, str]]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "http",
            "method": "OPTIONS",
            "path": "/api/execution/workers/poll",
            "raw_path": b"/api/execution/workers/poll",
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"origin", origin.encode("ascii")),
                (b"access-control-request-method", b"POST"),
            ],
            "client": ("127.0.0.1", 50123),
            "server": ("127.0.0.1", 8000),
        },
        receive,
        send,
    )
    start = next(message for message in messages if message["type"] == "http.response.start")
    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    return int(start["status"]), headers


def test_default_operator_origins_are_explicit_loopback_allowlist() -> None:
    from server.security import DEFAULT_ALLOWED_ORIGINS

    assert "*" not in DEFAULT_ALLOWED_ORIGINS
    assert set(DEFAULT_ALLOWED_ORIGINS) == {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:9119",
        "http://localhost:9119",
    }


@pytest.mark.parametrize("origin", ["https://evil.example", "http://192.168.1.8:5173"])
def test_configured_operator_origins_cannot_escape_loopback(
    origin: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.security import configured_allowed_origins

    monkeypatch.setenv("POLY_TRADER_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError, match="loopback"):
        configured_allowed_origins({})


def test_origin_normalization_removes_default_ports() -> None:
    from server.security import normalize_origin

    assert normalize_origin("http://localhost:80") == "http://localhost"
    assert normalize_origin("https://127.0.0.1:443") == "https://127.0.0.1"


def test_cors_middleware_never_uses_wildcard_origin() -> None:
    from server.main import app
    from server.security import DEFAULT_ALLOWED_ORIGINS

    cors_entries = [middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware]
    assert len(cors_entries) == 1
    cors = cors_entries[0]
    kwargs: Any = cors.kwargs
    assert kwargs["allow_origins"] == list(DEFAULT_ALLOWED_ORIGINS)
    assert "*" not in kwargs["allow_origins"]
    assert kwargs["allow_credentials"] is True


def test_cors_preflight_allows_configured_origin_and_rejects_untrusted_origin() -> None:
    from server.main import app

    allowed_status, allowed_headers = asyncio.run(
        _cors_preflight(app, "http://127.0.0.1:5173")
    )
    assert allowed_status == 200
    assert allowed_headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

    rejected_status, rejected_headers = asyncio.run(
        _cors_preflight(app, "https://evil.example")
    )
    assert rejected_status == 400
    assert "access-control-allow-origin" not in rejected_headers


def test_every_write_route_calls_local_operator_guard() -> None:
    source_path = Path(__file__).resolve().parents[1] / "server" / "routes" / "api.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    unguarded: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        write_routes: list[str] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr.lower() not in {"post", "put", "patch", "delete"}:
                continue
            route = decorator.args[0].value if decorator.args and isinstance(decorator.args[0], ast.Constant) else node.name
            write_routes.append(str(route))
        if not write_routes:
            continue
        executable = list(node.body)
        if executable and isinstance(executable[0], ast.Expr) and isinstance(executable[0].value, ast.Constant):
            executable = executable[1:]
        first = executable[0] if executable else None
        first_is_guard = (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Call)
            and isinstance(first.value.func, ast.Name)
            and first.value.func.id == "_assert_local_operator_request"
        )
        if not first_is_guard:
            unguarded.extend(write_routes)

    assert unguarded == []


def test_local_operator_write_rejects_untrusted_origin() -> None:
    from server.routes.api import _assert_local_operator_request

    with pytest.raises(HTTPException) as excinfo:
        _assert_local_operator_request(_request(origin="https://evil.example"))

    assert excinfo.value.status_code == 403
    assert "origin" in str(excinfo.value.detail).lower()


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "http://127.0.0.1:5173",
        "http://localhost:9119",
    ],
)
def test_local_operator_write_allows_cli_and_allowlisted_origins(origin: str | None) -> None:
    from server.routes.api import _assert_local_operator_request

    _assert_local_operator_request(_request(origin=origin))


def test_operator_write_still_rejects_remote_client_with_allowed_origin() -> None:
    from server.routes.api import _assert_local_operator_request

    with pytest.raises(HTTPException) as excinfo:
        _assert_local_operator_request(
            _request(host="10.0.0.8", origin="http://127.0.0.1:5173")
        )

    assert excinfo.value.status_code == 403


def test_websocket_rejects_untrusted_origin_before_accepting() -> None:
    from server.routes.ws import websocket_live

    class FakeWebSocket:
        client = SimpleNamespace(host="127.0.0.1")
        headers = {"origin": "https://evil.example"}
        accepted = False
        close_code: int | None = None

        async def accept(self) -> None:
            self.accepted = True

        async def close(self, *, code: int) -> None:
            self.close_code = code

    ws = FakeWebSocket()
    asyncio.run(websocket_live(ws))  # type: ignore[arg-type]
    assert ws.accepted is False
    assert ws.close_code == 1008


def test_websocket_subscribers_do_not_start_collection_writers() -> None:
    source_path = Path(__file__).resolve().parents[1] / "server" / "routes" / "ws.py"
    source = source_path.read_text(encoding="utf-8")
    assert "run_collection_and_save" not in source
    assert "run_preprocessor" not in source
