#!/usr/bin/env python3
"""
Poly-Trader 資料庫初始化腳本
建立 SQLite 資料庫與所有表結構
"""

import os
from database.models import init_db
from config import load_config

def main():
    cfg = load_config()
    db_url = cfg["database"]["url"]
    print(f"初始化資料庫：{db_url}")
    session = init_db(db_url)
    session.close()
    print("資料庫與表結構建立完成。")

if __name__ == "__main__":
    main()
