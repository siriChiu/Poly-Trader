from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
FALLBACK_DATABASE_URL = "sqlite:///poly_trader.db"


def _env_flag(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _project_database_url() -> str:
    try:
        payload = yaml.safe_load(PROJECT_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        configured = str((payload.get("database") or {}).get("url") or "").strip()
    except (OSError, TypeError, yaml.YAMLError):
        configured = ""
    return configured or FALLBACK_DATABASE_URL


DEFAULT_DATABASE_URL = _project_database_url()


def sqlite_database_path(database_url: str) -> Optional[Path]:
    """Resolve a SQLite URL to an absolute path; memory/non-SQLite URLs return ``None``."""
    try:
        parsed = make_url(str(database_url))
    except Exception:
        return None
    if not str(parsed.drivername).startswith("sqlite"):
        return None
    database = parsed.database
    if not database or database == ":memory:":
        return None
    if str(database).startswith("file:"):
        return None
    path = Path(database).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


CANONICAL_DATABASE_PATH = sqlite_database_path(DEFAULT_DATABASE_URL) or (PROJECT_ROOT / "poly_trader.db").resolve()


def _database_environment_overrides() -> tuple[str, str]:
    explicit_url = str(os.getenv("POLY_TRADER_DATABASE_URL", "")).strip()
    explicit_path = str(os.getenv("POLY_TRADER_DATABASE_PATH", "")).strip()
    if explicit_url and explicit_path:
        url_path = sqlite_database_path(explicit_url)
        resolved_path = Path(explicit_path).expanduser().resolve()
        if url_path is None or url_path != resolved_path:
            raise ValueError(
                "POLY_TRADER_DATABASE_URL and POLY_TRADER_DATABASE_PATH identify different databases"
            )
    return explicit_url, explicit_path


def configured_database_url(default: str | None = None) -> str:
    explicit_url, explicit_path = _database_environment_overrides()
    if explicit_url:
        return explicit_url
    if explicit_path:
        return f"sqlite:///{Path(explicit_path).expanduser().resolve()}"
    return str(DEFAULT_DATABASE_URL if default is None else default)


def configured_database_path(default: Path | str | None = None) -> Path:
    explicit_url, explicit_path = _database_environment_overrides()
    if explicit_url:
        path = sqlite_database_path(explicit_url)
        if path is None:
            raise ValueError("POLY_TRADER_DATABASE_URL does not identify a file-backed SQLite database")
        return path
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    if default is None:
        path = sqlite_database_path(DEFAULT_DATABASE_URL)
        if path is None:
            raise ValueError("configured project database URL does not identify a file-backed SQLite database")
        return path
    if isinstance(default, Path):
        return default.expanduser().resolve()
    default_text = str(default)
    if "://" in default_text or default_text.startswith("sqlite:"):
        path = sqlite_database_path(default_text)
        if path is None:
            raise ValueError("default database URL does not identify a file-backed SQLite database")
        return path
    return Path(default_text).expanduser().resolve()


def _pytest_allowed_roots() -> tuple[Path, ...]:
    raw_values = [
        item.strip()
        for item in str(os.getenv("POLY_TRADER_PYTEST_TEMP_ROOT", "")).split(os.pathsep)
        if item.strip()
    ]
    roots: list[Path] = []
    for raw in raw_values:
        if not raw:
            continue
        root = Path(raw).expanduser().resolve()
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def assert_database_url_allowed(database_url: str) -> str:
    """In pytest, allow only memory DBs or SQLite files inside pytest-owned temp roots."""
    if not _env_flag("POLY_TRADER_PYTEST_ACTIVE"):
        return str(database_url)

    try:
        parsed = make_url(str(database_url))
    except Exception as exc:
        raise RuntimeError("pytest database isolation rejected an invalid database URL") from exc

    if not str(parsed.drivername).startswith("sqlite"):
        raise RuntimeError("pytest database isolation rejects non-SQLite databases")
    if parsed.database == ":memory:":
        return str(database_url)
    if str(parsed.database or "").startswith("file:"):
        raise RuntimeError("pytest database isolation rejects SQLite file URIs")

    path = sqlite_database_path(str(database_url))
    allowed_roots = _pytest_allowed_roots()
    if path is None or not allowed_roots:
        raise RuntimeError("pytest database isolation requires a pytest-owned temporary SQLite database")
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise RuntimeError(
            "pytest database isolation rejects writable databases outside pytest-owned temporary roots"
        )
    return str(database_url)
