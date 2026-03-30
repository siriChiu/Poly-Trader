#!/usr/bin/env python3
"""
開發進度 Heartbeat 檢查腳本
定期執行以確保開發按計劃進行，並報告遺漏的文件與步驟。
"""

import os
import sys
import py_compile
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.resolve()

# 必需的目錄結構
REQUIRED_DIRS = [
    "data_ingestion",
    "feature_engine",
    "model",
    "execution",
    "database",
    "utils"
]

# Phase 1 必需文件
PHASE1_FILES = [
    "requirements.txt",
    "config.yaml",
    "database/models.py",
    "utils/logger.py"
]

# Phase 2 五感模組
PHASE2_FILES = [
    "data_ingestion/body_defillama.py",
    "data_ingestion/tongue_sentiment.py",
    "data_ingestion/nose_futures.py",
    "data_ingestion/eye_binance.py",
    "data_ingestion/ear_polymarket.py"
]

# Phase 3
PHASE3_FILES = [
    "feature_engine/preprocessor.py"
]

# Phase 4
PHASE4_FILES = [
    "model/predictor.py",
    "model/train.py"
]

# Phase 5
PHASE5_FILES = [
    "execution/risk_control.py",
    "execution/order_manager.py",
    "main.py"
]

# Phase 6 (Backtesting)
PHASE6_FILES = [
    "backtesting/__init__.py",
    "backtesting/metrics.py",
    "backtesting/engine.py",
    "backtesting/optimizer.py"
]

# Phase 7 (Dashboard) - already in dashboard/
PHASE7_FILES = [
    "dashboard/__init__.py",
    "dashboard/app.py",
    "dashboard/requirements.txt"
]

ALL_FILES = PHASE1_FILES + PHASE2_FILES + PHASE3_FILES + PHASE4_FILES + PHASE5_FILES + PHASE6_FILES + PHASE7_FILES

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
    """
    使用 py_compile 检查 Python 文件语法，不执行 import。
    返回语法错误的文件列表。
    """
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

def main():
    from datetime import datetime
    print(f"\n=== Poly-Trader 開發進度心跳檢查 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===")

    # 檢查目錄
    missing_dirs = check_dirs()
    if missing_dirs:
        print(f"[ERROR] 缺失目錄: {missing_dirs}")
    else:
        print("[OK] 所有必要目錄存在")

    # 檢查 Phase 1
    missing_p1 = check_files(PHASE1_FILES)
    if missing_p1:
        print(f"[WARN] Phase 1 缺失文件: {missing_p1}")
    else:
        print("[OK] Phase 1 完成")

    # 檢查 Phase 2
    missing_p2 = check_files(PHASE2_FILES)
    if missing_p2:
        print(f"[WARN] Phase 2 缺失文件: {missing_p2}")
    else:
        print("[OK] Phase 2 完成 (五感模組)")

    # 檢查 Phase 3
    missing_p3 = check_files(PHASE3_FILES)
    if missing_p3:
        print(f"[WARN] Phase 3 缺失文件: {missing_p3}")
    else:
        print("[OK] Phase 3 完成")

    # 檢查 Phase 4
    missing_p4 = check_files(PHASE4_FILES)
    if missing_p4:
        print(f"[WARN] Phase 4 缺失文件: {missing_p4}")
    else:
        print("[OK] Phase 4 完成")

    # 檢查 Phase 5
    missing_p5 = check_files(PHASE5_FILES)
    if missing_p5:
        print(f"[WARN] Phase 5 缺失文件: {missing_p5}")
    else:
        print("[OK] Phase 5 完成")

    # 檢查 Phase 6
    missing_p6 = check_files(PHASE6_FILES)
    if missing_p6:
        print(f"[WARN] Phase 6 缺失文件: {missing_p6}")
    else:
        print("[OK] Phase 6 完成 (Backtesting)")

    # 檢查 Phase 7
    missing_p7 = check_files(PHASE7_FILES)
    if missing_p7:
        print(f"[WARN] Phase 7 缺失文件: {missing_p7}")
    else:
        print("[OK] Phase 7 完成 (Dashboard)")

    # 語法檢查 (僅檢查 Python 檔案)
    py_files = [f for f in ALL_FILES if f.endswith(".py")]
    syntax_errors = check_syntax(py_files)
    if syntax_errors:
        print("[ERROR] 語法錯誤:")
        for err in syntax_errors:
            print(f"  - {err}")
    else:
        print("[OK] 所有 Python 模組語法檢查通過")

    print("=== 檢查完成 ===\n")

if __name__ == "__main__":
    main()
