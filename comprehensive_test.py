#!/usr/bin/env python3
"""
Poly-Trader  Comprehensive Verification Suite
嚴格按照規格書 (PRD_v2.md, architecture.md) 逐項驗證
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import py_compile
from datetime import datetime

def section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)

def test_file_structure():
    """驗證檔案結構是否符合 architecture.md"""
    section("1. 檔案結構檢查")
    required = [
        "requirements.txt", "config.yaml", "config.py", "init_db.py",
        "database/models.py", "utils/logger.py",
        "data_ingestion/__init__.py",
        "data_ingestion/body_defillama.py",
        "data_ingestion/tongue_sentiment.py",
        "data_ingestion/nose_futures.py",
        "data_ingestion/eye_binance.py",
        "data_ingestion/ear_polymarket.py",
        "data_ingestion/collector.py",
        "feature_engine/__init__.py", "feature_engine/preprocessor.py",
        "model/__init__.py", "model/predictor.py", "model/train.py",
        "execution/__init__.py", "execution/risk_control.py", "execution/order_manager.py",
        "backtesting/__init__.py", "backtesting/metrics.py", "backtesting/engine.py", "backtesting/optimizer.py",
        "dashboard/__init__.py", "dashboard/app.py",
        "main.py", "test_pipeline.py", "dev_heartbeat.py"
    ]
    missing = []
    for f in required:
        p = PROJECT_ROOT / f
        if not p.exists():
            missing.append(f)
        else:
            print(f"[OK] {f}")
    if missing:
        print(f"[FAIL] 缺失文件: {missing}")
        return False
    return True

def test_syntax():
    """檢查所有 Python 文件語法"""
    section("2. Python 語法檢查")
    errors = []
    py_files = list(PROJECT_ROOT.rglob("*.py"))
    for pyf in py_files:
        try:
            py_compile.compile(str(pyf), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{pyf.relative_to(PROJECT_ROOT)}: {e.msg} (line {e.lineno})")
    if errors:
        print("[FAIL] 語法錯誤:")
        for err in errors:
            print(f"  {err}")
        return False
    print(f"[OK] 所有 {len(py_files)} 個 Python 文件語法檢查通過")
    return True

def test_imports():
    """測試關鍵模組是否能正確導入"""
    section("3. 模組導入測試")
    errors = []
    tests = [
        ("database.models", "from database.models import RawMarketData, init_db"),
        ("utils.logger", "from utils.logger import setup_logger"),
        ("config", "from config import load_config"),
        ("data_ingestion.collector", "from data_ingestion.collector import collect_all_senses"),
        ("feature_engine.preprocessor", "from feature_engine.preprocessor import run_preprocessor"),
        ("model.predictor", "from model.predictor import predict, DummyPredictor"),
        ("execution.risk_control", "from execution.risk_control import validate_order"),
        ("backtesting.engine", "from backtesting.engine import run_backtest"),
        ("backtesting.metrics", "from backtesting.metrics import calculate_metrics"),
        ("backtesting.optimizer", "from backtesting.optimizer import grid_search"),
    ]
    for mod, stmt in tests:
        try:
            exec(stmt, {})
            print(f"[OK] {mod}")
        except Exception as e:
            errors.append(f"{mod}: {e}")
            print(f"[FAIL] {mod}: {e}")
    return len(errors) == 0

def test_database_init():
    """測試資料庫初始化與 Schema"""
    section("4. 資料庫初始化")
    try:
        from database.models import init_db, Base
        from sqlalchemy import create_engine
        import tempfile
        db_path = Path(tempfile.mktemp(suffix=".db"))
        engine = create_engine(f"sqlite:///{db_path}")
        # 檢查表是否存在
        Base.metadata.create_all(engine)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected = ["raw_market_data", "features_normalized", "trade_history"]
        missing_tables = [t for t in expected if t not in tables]
        if missing_tables:
            print(f"[FAIL] 缺失表: {missing_tables}")
            return False
        print(f"[OK] 所有表已建立: {tables}")
        try:
            db_path.unlink(missing_ok=True)
        except Exception:
            pass  # Windows 文件锁，忽略
        return True
    except Exception as e:
        print(f"[FAIL] DB 初始化錯誤: {e}")
        return False

def test_pipeline_simulation():
    """模擬完整 pipeline（不使用實際 API）"""
    section("5. Pipeline 模擬測試")
    try:
        from config import load_config
        from database.models import init_db, RawMarketData, FeaturesNormalized
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        import tempfile
        from datetime import datetime

        # 1. 初始化臨時 DB
        db_file = Path(tempfile.mktemp(suffix=".db"))
        engine = create_engine(f"sqlite:///{db_file}")
        Session = sessionmaker(bind=engine)
        session = Session()
        # 建立表
        from database.models import Base
        Base.metadata.create_all(engine)

        # 2. 插入模擬 Raw Data
        raw = RawMarketData(
            timestamp=datetime.utcnow(),
            symbol="BTCUSDT",
            close_price=50000.0,
            volume=1000.0,
            funding_rate=0.0001,
            fear_greed_index=50,
            stablecoin_mcap=0.01,  # ROC 計算用
            polymarket_prob=0.65
        )
        session.add(raw)
        session.commit()

        # 3. 執行特徵工程（依賴 raw data）
        from feature_engine.preprocessor import run_preprocessor
        feat = run_preprocessor(session, "BTCUSDT")
        if not feat:
            print("[FAIL] 特徵計算失敗")
            return False
        print(f"[OK] 特徵計算成功: {list(feat.keys())}")

        # 4. 模型預測
        from model.predictor import predict
        pred = predict(session)
        if not pred:
            print("[FAIL] 預測失敗")
            return False
        print(f"[OK] 預測成功: confidence={pred['confidence']:.2%}, signal={pred['signal']}")

        # 5. 回測引擎載入數據
        from backtesting.engine import BacktestEngine
        engine_bt = BacktestEngine(session, initial_capital=10000.0)
        # 手動插入第二條 raw data 以計算 ROC
        raw2 = RawMarketData(
            timestamp=datetime.utcnow(),
            symbol="BTCUSDT",
            close_price=50500.0,
            volume=1100.0,
            funding_rate=0.00011,
            fear_greed_index=52,
            stablecoin_mcap=0.0105,
            polymarket_prob=0.66
        )
        session.add(raw2)
        session.commit()
        # 重新載入特徵
        from feature_engine.preprocessor import load_latest_raw_data
        df_raw = load_latest_raw_data(session, "BTCUSDT", limit=10)
        # 這裡應該能計算 body_roc
        print("[OK] Pipeline 模擬完成")

        session.close()
        try:
            db_file.unlink(missing_ok=True)
        except Exception:
            pass
        return True
    except Exception as e:
        import traceback
        print(f"[FAIL] Pipeline 錯誤: {e}")
        traceback.print_exc()
        return False

def test_backtesting_components():
    """驗證回測組件"""
    section("6. 回測組件測試")
    try:
        from backtesting.metrics import calculate_metrics
        from backtesting.engine import BacktestEngine
        import pandas as pd
        import numpy as np

        # 模擬 equity curve
        eq = pd.Series([10000, 10200, 10100, 10500, 11000], index=pd.date_range("2025-01-01", periods=5, freq="H"))
        trades = pd.DataFrame({"pnl": [200, -100, 400]})
        metrics = calculate_metrics(eq, trades)
        required_keys = ["total_return", "annual_return", "sharpe_ratio", "max_drawdown", "win_rate"]
        missing_keys = [k for k in required_keys if k not in metrics]
        if missing_keys:
            print(f"[FAIL] 缺失指標: {missing_keys}")
            return False
        print(f"[OK] Metrics 計算正常: {list(metrics.keys())}")

        # BacktestEngine 類是否存在必要方法
        required_methods = ["__init__", "load_historical_features", "run"]
        missing_methods = [m for m in required_methods if not hasattr(BacktestEngine, m)]
        if missing_methods:
            print(f"[FAIL] BacktestEngine 缺失方法: {missing_methods}")
            return False
        print(f"[OK] BacktestEngine 結構完整")

        # Optimizer
        from backtesting.optimizer import grid_search, find_best_params
        print(f"[OK] Optimizer module loaded")
        return True
    except Exception as e:
        print(f"[FAIL] 回測組件錯誤: {e}")
        return False

def test_dashboard():
    """檢查dashboard是否可以導入"""
    section("7. Dashboard 檢查")
    try:
        # 檢查 app.py 語法
        py_compile.compile(str(PROJECT_ROOT / "dashboard" / "app.py"), doraise=True)
        print("[OK] dashboard/app.py 語法正確")
        # 檢查是否有關鍵函數
        with open(PROJECT_ROOT / "dashboard" / "app.py", "r", encoding="utf-8") as f:
            content = f.read()
        required = ["load_features", "load_trades", "run_backtest", "grid_search"]
        missing = [r for r in required if r not in content]
        if missing:
            print(f"[FAIL] Dashboard 缺失功能: {missing}")
            return False
        print(f"[OK] Dashboard 包含所有關鍵功能")
        return True
    except Exception as e:
        print(f"[FAIL] Dashboard 錯誤: {e}")
        return False

def main():
    print(f"\n{'='*60}")
    print(f"Poly-Trader 全面驗證測試")
    print(f"時間: {datetime.utcnow().isoformat()} UTC")
    print(f"{'='*60}")

    results = []
    results.append(("檔案結構", test_file_structure()))
    results.append(("語法檢查", test_syntax()))
    results.append(("模組導入", test_imports()))
    results.append(("資料庫初始化", test_database_init()))
    results.append(("Pipeline 模擬", test_pipeline_simulation()))
    results.append(("回測組件", test_backtesting_components()))
    results.append(("Dashboard", test_dashboard()))

    section("測試總結")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"{status}: {name}")
    print(f"\n總計: {passed}/{total} 通過")

    if passed == total:
        print("\n[SUCCESS] 所有驗證通過！專案符合規格書要求。")
        return 0
    else:
        print(f"\n[WARN] 有 {total-passed} 項測試失敗，請檢查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
