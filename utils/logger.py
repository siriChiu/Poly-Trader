import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logger(
    name: str = "poly_trader",
    log_file: Optional[str] = "poly_trader.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    level: int = logging.INFO
) -> logging.Logger:
    """
    設置同時輸出到終端機與旋轉檔案的 Logger。

    Args:
        name: logger 名稱。
        log_file: log 檔案路徑（相對於專案根目錄）。
        max_bytes: 單個 log 檔案最大大小。
        backup_count: 保留的備份檔案數量。
        level: 日誌等級。

    Returns:
        配置好的 Logger 實例。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重複添加 handlers
    if logger.hasHandlers():
        return logger

    # 格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 終端機 handler（nohup 環境 stdout 已重定向至 log 檔，避免重複記錄）
    if sys.stdout.isatty():
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

    # 檔案 handler (可選)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
