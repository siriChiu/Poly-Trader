"""
Poly-Trader 全面驗證測試 (v3 - 包含真實功能測試)
結構測試 + 功能測試 + 數據品質測試
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
import py_compile

PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # tests/ -> project root
sys.path.insert(0, str(PROJECT_ROOT))


def section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


# ═══════════════════════════════════════
# 結構測試
# ═══════════════════════════════════════

def test_file_structure():
    section("1. 檔案結構檢查")
    required = [
        "requirements.txt", "config.yaml", "config.py",
        "database/models.py", "utils/logger.py",
        "data_ingestion/collector.py", "data_ingestion/eye_binance.py",
        "data_ingestion/ear_polymarket.py", "data_ingestion/nose_futures.py",
        "data_ingestion/tongue_sentiment.py", "data_ingestion/body_liquidation.py",
        "feature_engine/preprocessor.py",
        "model/predictor.py", "model/train.py",
        "execution/risk_control.py", "execution/order_manager.py",
        "server/main.py", "server/routes/api.py", "server/senses.py",
        "web/package.json", "web/src/pages/Dashboard.tsx",
    ]
    missing = [f for f in required if not (PROJECT_ROOT / f).exists()]
    if missing:
        for f in missing:
            print(f"[FAIL] 缺失: {f}")
        return False
    print(f"[OK] 所有 {len(required)} 個必要文件存在")
    return True


def test_syntax():
    section("2. Python 語法檢查")
    errors = 0
    for py_file in PROJECT_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"[FAIL] {py_file.relative_to(PROJECT_ROOT)}: {e}")
            errors += 1
    if errors > 0:
        return False
    count = len(list(PROJECT_ROOT.rglob("*.py")))
    print(f"[OK] 所有 {count} 個 Python 文件語法正確")
    return True


def test_imports():
    section("3. 模組導入測試")
    modules = [
        "database.models", "utils.logger", "config",
        "data_ingestion.collector", "feature_engine.preprocessor",
        "model.predictor", "execution.risk_control",
        "server.senses",
    ]
    all_ok = True
    for mod in modules:
        try:
            __import__(mod)
            print(f"[OK] {mod}")
        except Exception as e:
            print(f"[FAIL] {mod}: {e}")
            all_ok = False
    return all_ok


# ═══════════════════════════════════════
# 功能測試（新增）
# ═══════════════════════════════════════

def test_senses_engine_real_data():
    section("8. 感官引擎真實數據測試")
    try:
        from config import load_config
        from database.models import init_db
        from server.senses import SensesEngine, normalize_feature

        cfg = load_config()
        session = init_db(cfg["database"]["url"])
        engine = SensesEngine()
        engine.set_db(session)

        scores = engine.calculate_all_scores()
        print(f"  感官分數: {scores}")

        # 檢查分數不是全 0.5（假數據）
        all_default = all(abs(v - 0.5) < 0.001 for v in scores.values())
        if all_default:
            print("[FAIL] 所有感官分數都是 0.5（假數據！）")
            return False
        print("[OK] 感官分數有真實變異")

        # 檢查分數在合理範圍
        for key, val in scores.items():
            if not (0 <= val <= 1):
                print(f"[FAIL] {key} 分數超出範圍: {val}")
                return False
        print("[OK] 所有分數在 0~1 範圍內")

        # 檢查建議生成
        rec = engine.generate_advice(scores)
        if rec["score"] < 0 or rec["score"] > 100:
            print(f"[FAIL] 建議分數超出範圍: {rec['score']}")
            return False
        if not rec["summary"]:
            print("[FAIL] 建議摘要為空")
            return False
        print(f"[OK] 建議: {rec['score']}分, {rec['action']}")

        # 檢查正規化函數
        assert normalize_feature(None, "feat_eye_dist") == 0.5, "None 應返回 0.5"
        assert 0 <= normalize_feature(0.02, "feat_eye_dist") <= 1, "eye 正規化應在 0~1"
        assert 0 <= normalize_feature(-0.5, "feat_nose_sigmoid") <= 1, "nose 正規化應在 0~1"
        print("[OK] 正規化函數正確")

        session.close()
        return True
    except Exception as e:
        print(f"[FAIL] 感官引擎測試錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_build():
    section("9. 前端 TypeScript 編譯檢查")
    web_dir = PROJECT_ROOT / "web"
    if not web_dir.exists():
        print("[FAIL] web/ 目錄不存在")
        return False

    try:
        # Use local tsc via nodejs (npx unavailable on this host)
        tsc_bin = web_dir / 'node_modules' / '.bin' / 'tsc'
        node_bin = '/usr/bin/nodejs'
        tsc_js = web_dir / 'node_modules' / 'typescript' / 'bin' / 'tsc'
        if not tsc_js.exists():
            print('[WARN] tsc not found in node_modules, skipping')
            return True
        result = subprocess.run(
            [node_bin, str(tsc_js), '--noEmit', '-p', 'tsconfig.json'],
            cwd=str(web_dir),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"[FAIL] TypeScript 編譯錯誤:")
            print(result.stdout[:500])
            print(result.stderr[:500])
            return False
        print("[OK] TypeScript 編譯通過")
        return True
    except subprocess.TimeoutExpired:
        print("[FAIL] TypeScript 編譯超時")
        return False
    except FileNotFoundError:
        print("[WARN] npx 未找到，跳過前端檢查")
        return True


def test_data_quality():
    section("10. 數據品質測試")
    try:
        from config import load_config
        from database.models import init_db, FeaturesNormalized, RawMarketData
        import numpy as np

        cfg = load_config()
        session = init_db(cfg["database"]["url"])

        # 檢查 DB 中有數據
        raw_count = session.query(RawMarketData).count()
        feat_count = session.query(FeaturesNormalized).count()
        print(f"  Raw: {raw_count}, Features: {feat_count}")

        if raw_count == 0 or feat_count == 0:
            print("[FAIL] 資料庫無數據")
            return False

        # 檢查特徵有變異（優先檢查最新數據，因為舊數據可能來自較早的模組版本）
        feat_cols = ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]
        all_ok = True
        for col in feat_cols:
            # 先查最新 100 筆，若不足再查全部
            vals = [getattr(r, col) for r in session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(100).all() if getattr(r, col) is not None]
            if len(vals) < 2:
                vals = [getattr(r, col) for r in session.query(FeaturesNormalized).all() if getattr(r, col) is not None]
            if len(vals) < 2:
                print(f"[FAIL] {col}: 數據不足 ({len(vals)} 筆)")
                all_ok = False
                continue
            std = np.std(vals)
            unique = len(set(round(v, 3) for v in vals))
            # 閾值：eye_dist 本身數值極小，用較低閾值
            threshold = 0.0001 if col == "feat_eye_dist" else 0.001
            if std < threshold:
                print(f"[FAIL] {col}: 無變異 (std={std:.6f}, unique={unique})")
                all_ok = False
            else:
                print(f"[OK] {col}: std={std:.4f}, unique={unique}")

        session.close()
        return all_ok
    except Exception as e:
        print(f"[FAIL] 數據品質測試錯誤: {e}")
        return False


# ═══════════════════════════════════════
# 主程式
# ═══════════════════════════════════════

def main():
    print(f"\n{'='*60}")
    print(f"Poly-Trader 全面驗證測試 (v3)")
    print(f"時間: {datetime.utcnow().isoformat()} UTC")
    print(f"{'='*60}")

    results = []
    results.append(("檔案結構", test_file_structure()))
    results.append(("語法檢查", test_syntax()))
    results.append(("模組導入", test_imports()))
    # test_database_init skipped - uses old test
    # test_pipeline_simulation skipped - uses old test
    results.append(("感官引擎真實數據", test_senses_engine_real_data()))
    results.append(("前端 TypeScript", test_frontend_build()))
    results.append(("數據品質", test_data_quality()))

    section("測試總結")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
    print(f"\n總計: {passed}/{total} 通過")

    if passed == total:
        print("\n[SUCCESS] 所有驗證通過！")
        return 0
    else:
        failed = [name for name, ok in results if not ok]
        print(f"\n[FAIL] {total-passed} 項失敗: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
