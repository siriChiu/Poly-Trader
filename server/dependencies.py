"""
依賴注入：DB Session、Config、OrderManager、SensesEngine 等共用實例
"""

import yaml
from pathlib import Path
from typing import Optional, Dict

from sqlalchemy.orm import Session as SASession
from database.models import init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Project root = parent of this file's parent (server/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 全局狀態
_db_session: Optional[SASession] = None
_config: Optional[Dict] = None
_automation_enabled: bool = False


def load_app_config(config_path: str = None) -> Dict:
    global _config
    path = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def get_config() -> Dict:
    global _config
    if _config is None:
        load_app_config()
    return _config


def _resolve_db_url(db_url: str) -> str:
    """將 sqlite:/// 相對路徑解析為 PROJECT_ROOT 絕對路徑，避免 CWD 差異。"""
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        rel = db_url[len("sqlite:///"):]
        abs_path = PROJECT_ROOT / rel
        return f"sqlite:///{abs_path}"
    return db_url


def init_dependencies():
    """啟動時初始化所有依賴。"""
    global _db_session, _config

    cfg = get_config()
    raw_url = cfg.get("database", {}).get("url", "sqlite:///poly_trader.db")
    db_url = _resolve_db_url(raw_url)
    logger.info(f"DB URL resolved: {db_url}")
    _db_session = init_db(db_url)

    # 注入 DB 到 SensesEngine
    from server.senses import get_engine
    engine = get_engine()
    engine.set_db(_db_session)

    logger.info("Dependencies initialized (DB + SensesEngine)")


def get_db() -> SASession:
    global _db_session
    if _db_session is None:
        init_dependencies()
    return _db_session


def is_automation_enabled() -> bool:
    return _automation_enabled


def set_automation_enabled(enabled: bool):
    global _automation_enabled
    _automation_enabled = enabled
    logger.info(f"Automation mode: {'ON' if enabled else 'OFF'}")
