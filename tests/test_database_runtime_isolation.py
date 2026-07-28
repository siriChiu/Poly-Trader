from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKTREE_DB = (PROJECT_ROOT / "poly_trader.db").resolve()
RAW_CONFIG = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
CONFIGURED_PRODUCTION_URL = str(RAW_CONFIG["database"]["url"])
CANONICAL_DB = Path(make_url(CONFIGURED_PRODUCTION_URL).database or "").expanduser().resolve()


def _session_temp_root() -> Path:
    return Path(os.environ["POLY_TRADER_PYTEST_TEMP_ROOT"].split(os.pathsep)[0]).resolve()


def test_pytest_guard_rejects_canonical_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from database.runtime import assert_database_url_allowed

    monkeypatch.setenv("POLY_TRADER_PYTEST_ACTIVE", "1")

    with pytest.raises(RuntimeError, match="pytest database isolation"):
        assert_database_url_allowed(f"sqlite:///{CANONICAL_DB}")


def test_pytest_guard_allows_isolated_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.runtime import assert_database_url_allowed

    isolated_db = (_session_temp_root() / "isolated.sqlite").resolve()
    monkeypatch.setenv("POLY_TRADER_PYTEST_ACTIVE", "1")

    assert assert_database_url_allowed(f"sqlite:///{isolated_db}") == f"sqlite:///{isolated_db}"
    assert assert_database_url_allowed("sqlite:///:memory:") == "sqlite:///:memory:"


@pytest.mark.parametrize(
    "database_url",
    [
        f"sqlite:///{CANONICAL_DB}",
        f"sqlite:///{WORKTREE_DB}",
        "postgresql://prod.example/poly_trader",
        f"sqlite:///file:{CANONICAL_DB}?mode=rw&uri=true",
    ],
)
def test_pytest_guard_rejects_every_database_outside_session_temp_root(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.runtime import assert_database_url_allowed

    monkeypatch.setenv("POLY_TRADER_PYTEST_ACTIVE", "1")
    with pytest.raises(RuntimeError, match="pytest database isolation"):
        assert_database_url_allowed(database_url)


def test_no_override_resolves_configured_production_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from database.runtime import CANONICAL_DATABASE_PATH, configured_database_path, configured_database_url

    monkeypatch.delenv("POLY_TRADER_DATABASE_URL", raising=False)
    monkeypatch.delenv("POLY_TRADER_DATABASE_PATH", raising=False)

    assert CANONICAL_DATABASE_PATH == CANONICAL_DB
    assert configured_database_url() == CONFIGURED_PRODUCTION_URL
    assert configured_database_path() == CANONICAL_DB


def test_database_environment_override_is_shared_by_config_loaders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config import load_config
    from server import dependencies

    isolated_db = (tmp_path / "shared.sqlite").resolve()
    database_url = f"sqlite:///{isolated_db}"
    monkeypatch.delenv("POLY_TRADER_DATABASE_PATH", raising=False)
    monkeypatch.setenv("POLY_TRADER_DATABASE_URL", database_url)
    dependencies._config = None

    assert load_config()["database"]["url"] == database_url
    assert dependencies.load_app_config()["database"]["url"] == database_url


def test_pytest_session_uses_isolated_database_environment() -> None:
    import os

    from database.runtime import configured_database_path

    assert os.environ.get("POLY_TRADER_PYTEST_ACTIVE") == "1"
    selected = configured_database_path()
    temp_root = _session_temp_root()
    assert selected.is_relative_to(temp_root)
    assert selected != CANONICAL_DB


def test_api_and_heartbeat_use_configured_database_path() -> None:
    import config
    from database import models
    from scripts import hb_parallel_runner
    from server import dependencies
    from server.routes import api
    from database.runtime import configured_database_path

    for module in (config, models, dependencies, api, hb_parallel_runner):
        assert module.__file__ is not None
        assert Path(module.__file__).resolve().is_relative_to(PROJECT_ROOT.resolve()), module.__file__

    dependencies._config = None
    expected = str(configured_database_path())
    assert dependencies.get_config()["database"]["url"] == f"sqlite:///{expected}"
    assert Path(hb_parallel_runner.PROJECT_ROOT).resolve() == PROJECT_ROOT.resolve()
    assert api.DB_PATH == expected
    assert hb_parallel_runner.DB_PATH == expected


def test_active_heartbeat_modules_share_one_database_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    from database.runtime import configured_database_path, configured_database_url

    expected_path = configured_database_path()
    expected_url = configured_database_url()
    cwd_before = Path.cwd()
    module_attributes = {
        "model.train": ("DB_PATH", str(expected_path)),
        "scripts.dynamic_window_train": ("DB_PATH", expected_path),
        "scripts.feature_group_ablation": ("DB_URL", expected_url),
        "scripts.full_ic": ("DB_PATH", str(expected_path)),
        "scripts.hb_circuit_breaker_audit": ("DB_PATH", expected_path),
        "scripts.hb_predict_probe": ("DB_URL", expected_url),
        "scripts.hb_q35_scaling_audit": ("DB_PATH", expected_path),
        "scripts.paper_shadow_outcome_reconciliation": ("DEFAULT_DB_URL", expected_url),
        "scripts.q15_support_fill_feasibility_scan": ("DB_PATH", expected_path),
        "scripts.recent_drift_report": ("DB_PATH", expected_path),
        "scripts.regime_aware_ic": ("DB_PATH", str(expected_path)),
    }
    for module_name in module_attributes:
        sys.modules.pop(module_name, None)
    sys.modules.pop("scripts", None)
    importlib.invalidate_caches()

    for module_name, (attribute, expected) in module_attributes.items():
        module = importlib.import_module(module_name)
        module_path = Path(module.__file__ or "").resolve()
        assert module_path.is_relative_to(PROJECT_ROOT), (module_name, module_path)
        assert getattr(module, attribute) == expected, module_name
        assert Path.cwd() == cwd_before, module_name

    auto_propose_source = (PROJECT_ROOT / "scripts" / "auto_propose_fixes.py").read_text(encoding="utf-8")
    assert "sqlite3.connect(str(configured_database_path()))" in auto_propose_source


def test_pytest_sqlite_guard_blocks_every_external_write_but_allows_read_only_production() -> None:
    import sqlite3

    external_tmp = Path("/tmp/poly-trader-non-pytest-external.sqlite")
    for candidate in (CANONICAL_DB, WORKTREE_DB, external_tmp):
        with pytest.raises(RuntimeError, match="pytest database isolation"):
            sqlite3.connect(str(candidate))

    connection = sqlite3.connect(f"file:{CANONICAL_DB}?mode=ro", uri=True)
    connection.close()


def test_pytest_sqlite_guard_allows_session_owned_database() -> None:
    import sqlite3

    temp_root = _session_temp_root()
    allowed_db = temp_root / "direct.sqlite"
    connection = sqlite3.connect(str(allowed_db))
    try:
        connection.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    assert allowed_db.exists()


def test_pytest_sqlite_guard_blocks_relative_canonical_name_in_project_cwd(monkeypatch) -> None:
    import sqlite3

    monkeypatch.chdir(PROJECT_ROOT)
    with pytest.raises(RuntimeError, match="pytest database isolation"):
        sqlite3.connect("poly_trader.db")


def test_database_path_environment_override_is_not_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.runtime import configured_database_path

    isolated_db = (tmp_path / "path.sqlite").resolve()
    monkeypatch.delenv("POLY_TRADER_DATABASE_URL", raising=False)
    monkeypatch.setenv("POLY_TRADER_DATABASE_PATH", str(isolated_db))

    assert configured_database_path() == isolated_db
    assert configured_database_path() != CANONICAL_DB


def test_mismatched_database_url_and_path_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from database.runtime import configured_database_path, configured_database_url

    url_db = (tmp_path / "url.sqlite").resolve()
    path_db = (tmp_path / "path.sqlite").resolve()
    monkeypatch.setenv("POLY_TRADER_DATABASE_URL", f"sqlite:///{url_db}")
    monkeypatch.setenv("POLY_TRADER_DATABASE_PATH", str(path_db))

    with pytest.raises(ValueError, match="different databases"):
        configured_database_url()
    with pytest.raises(ValueError, match="different databases"):
        configured_database_path()


def test_pytest_fails_during_collection_when_environment_targets_canonical_database() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["POLY_TRADER_DATABASE_URL"] = f"sqlite:///{CANONICAL_DB}"
    env["POLY_TRADER_DATABASE_PATH"] = str(CANONICAL_DB)
    env["POLY_TRADER_PYTEST_TEMP_ROOT"] = str(CANONICAL_DB.parent)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_debug.py", "--collect-only", "-q"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    output = f"{completed.stdout}\n{completed.stderr}"
    assert completed.returncode != 0
    assert "pytest database isolation" in output
