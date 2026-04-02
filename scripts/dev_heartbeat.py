#!/usr/bin/env python3
"""
Poly-Trader 開發進度 Heartbeat 檢查
自動驗證專案結構、模組語法、系統健康
"""

import os
import sys
import py_compile
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 必需目錄（動態檢查，不硬編碼特定感官檔案）
REQUIRED_DIRS = [
    "data_ingestion",
    "feature_engine",
    "model",
    "execution",
    "database",
    "utils",
    "server",
    "web",
    "scripts",
    "tests",
]

# 核心檔案（只要求關鍵入口點，不檢查每個感官模組）
CORE_FILES = [
    # Config
    "config.py",
    "config.yaml",
    "requirements.txt",
    # Database
    "database/models.py",
    "utils/logger.py",
    # Feature engine
    "feature_engine/preprocessor.py",
    # Model
    "model/predictor.py",
    "model/train.py",
    # Server
    "server/main.py",
    "server/senses.py",
    "server/routes/api.py",
    "server/routes/ws.py",
    "server/dependencies.py",
    # Scripts
    "scripts/dev_heartbeat.py",
]

# 感官模組目錄（只檢查目錄存在，不硬編碼檔案名）
SENSE_MODULES_DIR = "data_ingestion"


def check_dirs() -> List[str]:
    missing = []
    for d in REQUIRED_DIRS:
        if not (PROJECT_ROOT / d).is_dir():
            missing.append(d)
    return missing


def check_files(file_list: List[str]) -> List[str]:
    missing = []
    for f in file_list:
        if not (PROJECT_ROOT / f).exists():
            missing.append(f)
    return missing


def check_syntax(file_list: List[str]) -> List[str]:
    errors = []
    for f in file_list:
        path = PROJECT_ROOT / f
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{f}: {e.msg} (line {e.lineno})")
    return errors


def check_sense_modules() -> dict:
    """動態檢查 data_ingestion 目錄下的感官模組"""
    sense_dir = PROJECT_ROOT / SENSE_MODULES_DIR
    if not sense_dir.is_dir():
        return {"status": "ERROR", "modules": [], "count": 0}
    
    modules = [f.stem for f in sense_dir.glob("*.py") 
               if f.stem not in ("__init__", "collector", "backfill_historical", "labeling")]
    return {"status": "OK", "modules": modules, "count": len(modules)}


def check_db() -> dict:
    """檢查資料庫狀態"""
    db_path = PROJECT_ROOT / "poly_trader.db"
    if not db_path.exists():
        return {"status": "MISSING"}
    try:
        import sqlite3
        db = sqlite3.connect(str(db_path))
        raw = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
        feat = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
        labels = db.execute("SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL").fetchone()[0]
        db.close()
        return {"status": "OK", "raw": raw, "features": feat, "labels": labels}
    except Exception as e:
        return {"status": f"ERROR: {e}"}


def main():
    from datetime import datetime
    print(f"\n=== Poly-Trader Heartbeat [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===")

    # 檢查目錄
    missing_dirs = check_dirs()
    if missing_dirs:
        print(f"[ERROR] 缺失目錄: {missing_dirs}")
    else:
        print(f"[OK] 所有 {len(REQUIRED_DIRS)} 個目錄存在")

    # 檢查核心檔案
    missing_files = check_files(CORE_FILES)
    if missing_files:
        print(f"[WARN] 缺失核心檔案: {missing_files}")
    else:
        print(f"[OK] 所有 {len(CORE_FILES)} 個核心檔案存在")

    # 感官模組（動態）
    senses = check_sense_modules()
    print(f"[OK] 感官模組: {senses['count']} 個 ({', '.join(senses['modules'][:5])}{'...' if senses['count']>5 else ''})")

    # 資料庫
    db = check_db()
    if db["status"] == "OK":
        print(f"[OK] 資料庫: raw={db['raw']}, features={db['features']}, labels={db['labels']}")
    else:
        print(f"[WARN] 資料庫: {db['status']}")

    # 語法檢查
    py_files = [f for f in CORE_FILES if f.endswith(".py")]
    # 加上所有 data_ingestion/*.py
    for f in (PROJECT_ROOT / "data_ingestion").glob("*.py"):
        py_files.append(f"data_ingestion/{f.name}")
    for f in (PROJECT_ROOT / "feature_engine").glob("*.py"):
        py_files.append(f"feature_engine/{f.name}")
    for f in (PROJECT_ROOT / "model").glob("*.py"):
        py_files.append(f"model/{f.name}")
    
    syntax_errors = check_syntax(py_files)
    if syntax_errors:
        print(f"[ERROR] 語法錯誤:")
        for err in syntax_errors:
            print(f"  - {err}")
    else:
        print(f"[OK] 所有 Python 模組語法檢查通過 ({len(py_files)} files)")

    print("=== 檢查完成 ===\n")


if __name__ == "__main__":
    main()
