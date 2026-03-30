"""
依賴注入：DB Session、Config、OrderManager 等共用實例
"""

import yaml
from pathlib import Path
from typing import Optional, Dict

from sqlalchemy.orm import Session as SASession
from database.models import init_db
from execution.order_manager import OrderManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 全局狀態
_db_session: Optional[SASession] = None
_config: Optional[Dict] = None
_order_manager: Optional[OrderManager] = None
_automation_enabled: bool = False  # 預設手動模式


def load_app_config(config_path: str = None) -> Dict:
    global _config
    path = Path(config_path) if config_path else Path(__file__).parent.parent / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config


def get_config() -> Dict:
    global _config
    if _config is None:
        load_app_config()
    return _config


def init_dependencies():
    """啟動時初始化所有依賴。"""
    global _db_session, _order_manager, _config

    cfg = get_config()
    db_url = cfg["database"]["url"]
    _db_session = init_db(db_url)
    _order_manager = OrderManager(cfg, _db_session)
    logger.info("Dependencies initialized (DB + OrderManager)")


def get_db() -> SASession:
    global _db_session
    if _db_session is None:
        init_dependencies()
    return _db_session


def get_order_manager() -> OrderManager:
    global _order_manager
    if _order_manager is None:
        init_dependencies()
    return _order_manager


def is_automation_enabled() -> bool:
    return _automation_enabled


def set_automation_enabled(enabled: bool):
    global _automation_enabled
    _automation_enabled = enabled
    logger.info(f"Automation mode: {'ON' if enabled else 'OFF'}")
