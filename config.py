import yaml
from pathlib import Path
from typing import Dict

from database.runtime import configured_database_url

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config(config_path: str = None) -> Dict:
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    database = config.setdefault("database", {})
    database["url"] = configured_database_url(database.get("url", "sqlite:///poly_trader.db"))
    return config
