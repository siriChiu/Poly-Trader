import yaml
from pathlib import Path
from typing import Dict

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config(config_path: str = None) -> Dict:
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
