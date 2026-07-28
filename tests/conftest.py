from __future__ import annotations

import atexit
import os
import shutil
import sqlite3
import sqlite3.dbapi2 as sqlite_dbapi2
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
while PROJECT_ROOT_TEXT in sys.path:
    sys.path.remove(PROJECT_ROOT_TEXT)
sys.path.insert(0, PROJECT_ROOT_TEXT)

os.environ["POLY_TRADER_PYTEST_ACTIVE"] = "1"
_preconfigured_url = str(os.environ.get("POLY_TRADER_DATABASE_URL", "")).strip()
_preconfigured_path = str(os.environ.get("POLY_TRADER_DATABASE_PATH", "")).strip()
_TEST_DB_ROOT = Path(tempfile.mkdtemp(prefix="poly-trader-pytest-")).resolve()
atexit.register(shutil.rmtree, _TEST_DB_ROOT, ignore_errors=True)
os.environ["POLY_TRADER_PYTEST_TEMP_ROOT"] = str(_TEST_DB_ROOT)

if not _preconfigured_url and not _preconfigured_path:
    _test_db_path = (_TEST_DB_ROOT / "poly_trader-test.sqlite").resolve()
    os.environ["POLY_TRADER_DATABASE_PATH"] = str(_test_db_path)
    os.environ["POLY_TRADER_DATABASE_URL"] = f"sqlite:///{_test_db_path}"
elif _preconfigured_path and not _preconfigured_url:
    _configured_path = Path(_preconfigured_path).expanduser().resolve()
    os.environ["POLY_TRADER_DATABASE_PATH"] = str(_configured_path)
    os.environ["POLY_TRADER_DATABASE_URL"] = f"sqlite:///{_configured_path}"

from database.runtime import (  # noqa: E402
    _pytest_allowed_roots,
    assert_database_url_allowed,
    sqlite_database_path,
)

if _preconfigured_url and not _preconfigured_path:
    _url_path = sqlite_database_path(_preconfigured_url)
    if _url_path is not None:
        os.environ["POLY_TRADER_DATABASE_PATH"] = str(_url_path)


def _assert_pytest_database_environment_is_isolated() -> None:
    database_url = str(os.environ.get("POLY_TRADER_DATABASE_URL", "")).strip()
    database_path = str(os.environ.get("POLY_TRADER_DATABASE_PATH", "")).strip()
    if not database_url:
        raise RuntimeError("pytest database isolation requires POLY_TRADER_DATABASE_URL")
    assert_database_url_allowed(database_url)
    if database_path:
        assert_database_url_allowed(f"sqlite:///{Path(database_path).expanduser().resolve()}")


_assert_pytest_database_environment_is_isolated()
_ORIGINAL_SQLITE_CONNECT = sqlite3.connect


@pytest.fixture(scope="session", autouse=True)
def _register_pytest_basetemp(tmp_path_factory: pytest.TempPathFactory):
    base_temp = tmp_path_factory.getbasetemp().resolve()
    existing = [
        item for item in os.environ.get("POLY_TRADER_PYTEST_TEMP_ROOT", "").split(os.pathsep) if item
    ]
    if str(base_temp) not in existing:
        existing.append(str(base_temp))
    os.environ["POLY_TRADER_PYTEST_TEMP_ROOT"] = os.pathsep.join(existing)
    yield


def _guarded_sqlite_connect(database, *args, **kwargs):
    database_text = os.fspath(database)
    is_uri = bool(kwargs.get("uri")) and database_text.startswith("file:")
    read_only = False
    if is_uri:
        parsed = urlsplit(database_text)
        candidate_text = unquote(parsed.path)
        read_only = "ro" in parse_qs(parsed.query).get("mode", [])
    else:
        candidate_text = database_text

    if candidate_text in {":memory:", ""}:
        return _ORIGINAL_SQLITE_CONNECT(database, *args, **kwargs)

    candidate = Path(candidate_text).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    allowed_roots = _pytest_allowed_roots()
    if not read_only and not any(resolved.is_relative_to(root) for root in allowed_roots):
        raise RuntimeError(
            "pytest database isolation rejects writable SQLite databases outside pytest-owned temporary roots"
        )
    return _ORIGINAL_SQLITE_CONNECT(database, *args, **kwargs)


sqlite3.connect = _guarded_sqlite_connect
sqlite_dbapi2.connect = _guarded_sqlite_connect
