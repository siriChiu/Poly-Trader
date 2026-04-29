import importlib.util
import sqlite3
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "recent_drift_report.py"
spec = importlib.util.spec_from_file_location("recent_drift_report_test_module", MODULE_PATH)
recent_drift_report = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(recent_drift_report)


def test_build_report_includes_feature_diagnostics(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_constant REAL,
            feat_live REAL,
            feat_sparse REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    for i in range(10):
        ts = f"2026-04-11 00:{i:02d}:00"
        label_rows.append(
            (
                i + 1,
                ts,
                "BTCUSDT",
                1440,
                1 if i >= 5 else 0,
                0.6,
                0.01,
                0.55,
                0.12,
                0.2,
                0.01,
                -0.02,
                0.03,
                "bull",
            )
        )
        recent_value = (5.0 + i * 0.0001) if i >= 5 else float(i)
        sparse_value = None if i >= 5 and i % 2 == 0 else float(i)
        feature_rows.append((ts, "BTCUSDT", "bull", 1.0, recent_value, sparse_value))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()

    summary = report["windows"]["5"]
    feature_diag = summary["feature_diagnostics"]
    target_path = summary["target_path_diagnostics"]
    reference = summary["reference_window_comparison"]
    assert report["full_sample"]["feature_count"] == 3
    assert feature_diag["feature_count"] == 3
    assert feature_diag["low_variance_count"] >= 2
    assert feature_diag["low_distinct_count"] >= 1
    assert feature_diag["frozen_count"] >= 1
    assert feature_diag["compressed_count"] >= 1
    assert feature_diag["null_heavy_count"] >= 1
    assert any(row["feature"] == "feat_constant" for row in feature_diag["low_variance_examples"])
    assert any(row["feature"] == "feat_constant" for row in feature_diag["low_distinct_examples"])
    assert any(row["feature"] == "feat_constant" for row in feature_diag["frozen_examples"])
    assert any(row["feature"] == "feat_live" for row in feature_diag["compressed_examples"])
    assert any(row["feature"] == "feat_sparse" for row in feature_diag["null_heavy_examples"])
    assert target_path["window_start_timestamp"] == "2026-04-11 00:05:00"
    assert target_path["window_end_timestamp"] == "2026-04-11 00:09:00"
    assert target_path["tail_target_streak"]["target"] == 1
    assert target_path["tail_target_streak"]["count"] == 5
    assert target_path["tail_target_streak"]["start_timestamp"] == "2026-04-11 00:05:00"
    assert target_path["target_regime_breakdown"]["bull:1"] == 5
    assert len(target_path["recent_examples"]) == 5
    assert target_path["recent_examples"][-1]["label_id"] == 10
    assert reference["reference_rows"] == 5
    assert reference["reference_quality"]["win_rate"] == 0.0
    assert reference["current_quality"]["win_rate"] == 1.0
    assert reference["win_rate_delta_vs_reference"] == 1.0
    assert reference["avg_simulated_quality_delta_vs_reference"] == 0.0
    assert any(row["feature"] == "feat_live" for row in reference["top_mean_shift_features"])


def test_build_report_marks_expected_static_weekend_and_discrete_features(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_vix REAL,
            feat_dxy REAL,
            feat_nq_return_1h REAL,
            feat_4h_ma_order REAL,
            feat_eye REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    for i in range(8):
        ts = f"2026-04-12 0{i}:00:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 0, 0.0, -0.01, -0.2, 0.3, 0.9, -0.01, -0.02, 0.01, "chop"))
        feature_rows.append((ts, "BTCUSDT", "chop", 19.23, 98.69, 0.0, 1.0, float(i)))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [8])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["8"]["feature_diagnostics"]

    assert feature_diag["time_context"]["weekend_dominant"] is True
    assert feature_diag["expected_static_count"] >= 4
    reasons = {row["feature"]: row["expected_static_reason"] for row in feature_diag["expected_static_examples"]}
    assert reasons["feat_4h_ma_order"] == "discrete_regime_feature"
    assert reasons["feat_vix"] == "weekend_macro_market_closed"
    assert reasons["feat_dxy"] == "weekend_macro_market_closed"
    assert reasons["feat_nq_return_1h"] == "weekend_macro_market_closed"


def test_build_report_marks_weekday_macro_features_as_expected_static_outside_us_market_hours(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_vix REAL,
            feat_dxy REAL,
            feat_eye REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    for i in range(6):
        ts = f"2026-04-15 0{i}:15:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 1.0, 0.01, 0.4, 0.1, 0.2, 0.01, -0.02, 0.03, "bull"))
        feature_rows.append((ts, "BTCUSDT", "bull", 22.5, 101.2, float(i)))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [6])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["6"]["feature_diagnostics"]

    assert feature_diag["time_context"]["weekend_dominant"] is False
    assert feature_diag["time_context"]["weekday_market_closed_dominant"] is True
    reasons = {row["feature"]: row["expected_static_reason"] for row in feature_diag["expected_static_examples"]}
    assert reasons["feat_vix"] == "weekday_macro_market_closed"
    assert reasons["feat_dxy"] == "weekday_macro_market_closed"
    unexpected = {row["feature"] for row in feature_diag["unexpected_frozen_examples"]}
    assert "feat_vix" not in unexpected
    assert "feat_dxy" not in unexpected


def test_build_report_marks_expected_compressed_features_when_underlying_raw_proxy_compresses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_atr_pct REAL,
            feat_eye REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            volatility REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    raw_rows = []
    for i in range(10):
        ts = f"2026-04-15 0{i}:00:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 1.0, 0.01, 0.4, 0.1, 0.2, 0.01, -0.02, 0.03, "bull"))
        atr_val = (0.0100 + i * 0.0020) if i < 5 else (0.0030 + (i - 5) * 0.00005)
        raw_vol = (0.0400 + i * 0.0100) if i < 5 else (0.0080 + (i - 5) * 0.0002)
        feature_rows.append((ts, "BTCUSDT", "bull", atr_val, float(i)))
        raw_rows.append((ts, "BTCUSDT", raw_vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?)",
        raw_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    reasons = {row["feature"]: row.get("expected_compressed_reason") for row in feature_diag["expected_compressed_examples"]}
    assert reasons["feat_atr_pct"] == "underlying_raw_volatility_compression"
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_atr_pct" not in unexpected


def test_build_report_keeps_atr_expected_compression_when_raw_volatility_mean_rises_but_dispersion_collapses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_atr_pct REAL,
            feat_eye REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            volatility REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    raw_rows = []
    for i in range(10):
        ts = f"2026-04-16 0{i}:00:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 1.0, 0.01, 0.4, 0.1, 0.2, 0.01, -0.02, 0.03, "bull"))
        atr_val = (0.0200 + i * 0.0025) if i < 5 else (0.0100 + (i - 5) * 0.00004)
        # Recent volatility mean is slightly HIGHER than baseline, but dispersion collapses sharply.
        raw_vol = (0.0040 + i * 0.0002) if i < 5 else (0.0050 + (i - 5) * 0.00001)
        feature_rows.append((ts, "BTCUSDT", "bull", atr_val, float(i)))
        raw_rows.append((ts, "BTCUSDT", raw_vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?)",
        raw_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    reasons = {row["feature"]: row.get("expected_compressed_reason") for row in feature_diag["expected_compressed_examples"]}
    assert reasons["feat_atr_pct"] == "underlying_raw_volatility_compression"
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_atr_pct" not in unexpected


def test_build_report_marks_4h_bias200_expected_compression_when_price_and_volatility_both_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_bias200 REAL,
            feat_eye REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            volatility REAL,
            close_price REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    raw_rows = []
    for i in range(10):
        ts = f"2026-04-16 1{i}:00:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 1.0, 0.01, 0.4, 0.1, 0.2, 0.01, -0.02, 0.03, "bull"))
        bias200_val = (1.0 + i * 1.0) if i < 5 else (6.0 + (i - 5) * 0.03)
        raw_vol = (0.0200 + i * 0.0050) if i < 5 else (0.0040 + (i - 5) * 0.00005)
        close_price = (70000.0 + i * 500.0) if i < 5 else (74000.0 + (i - 5) * 5.0)
        feature_rows.append((ts, "BTCUSDT", "bull", bias200_val, float(i)))
        raw_rows.append((ts, "BTCUSDT", raw_vol, close_price))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_bias200"]["expected_compressed_reason"] == "underlying_price_and_volatility_compression"
    details = expected["feat_4h_bias200"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] == 2
    assert details["min_required_proxies"] == 2
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_bias200" not in unexpected



def test_build_report_marks_4h_swing_low_as_expected_compression_when_support_cluster_compresses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volatility REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_dist_swing_low REAL,
            feat_4h_dist_bb_lower REAL,
            feat_4h_bb_pct_b REAL,
            feat_eye REAL
        )
        """
    )

    label_rows = []
    raw_rows = []
    feature_rows = []
    baseline_swing = [6.0, 6.8, 7.5, 5.9, 7.2]
    baseline_bb_lower = [2.1, 2.8, 3.0, 2.4, 2.9]
    baseline_bb_pct_b = [0.62, 0.85, 0.74, 0.93, 0.68]
    baseline_close = [74200.0, 74650.0, 75120.0, 73980.0, 74810.0]
    baseline_vol = [0.0060, 0.0052, 0.0066, 0.0054, 0.0061]
    recent_swing = [5.02, 5.09, 5.12, 4.98, 5.05]
    recent_bb_lower = [1.49, 1.55, 1.58, 1.51, 1.54]
    recent_bb_pct_b = [0.47, 0.49, 0.5, 0.48, 0.46]
    recent_close = [74240.0, 74285.0, 74210.0, 74305.0, 74260.0]
    recent_vol = [0.0048, 0.0049, 0.0049, 0.0048, 0.0049]

    for i in range(10):
        ts = f"2026-04-17 00:{i:02d}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1 if i >= 5 else 0, 0.5, 0.01, 0.4, 0.12, 0.3, 0.01, -0.02, 0.03, "bull"))
        if i < 5:
            swing = baseline_swing[i]
            bb_lower = baseline_bb_lower[i]
            bb_pct_b = baseline_bb_pct_b[i]
            close = baseline_close[i]
            vol = baseline_vol[i]
        else:
            idx = i - 5
            swing = recent_swing[idx]
            bb_lower = recent_bb_lower[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            close = recent_close[idx]
            vol = recent_vol[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", swing, bb_lower, bb_pct_b, float(i)))
        raw_rows.append((ts, "BTCUSDT", close, vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_dist_swing_low"]["expected_compressed_reason"] == "coherent_4h_support_cluster_compression"
    details = expected["feat_4h_dist_swing_low"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 3
    assert details["min_required_proxies"] == 3
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_dist_bb_lower"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_dist_swing_low" not in unexpected


def test_build_report_marks_4h_macd_hist_as_expected_compression_when_4h_momentum_cluster_cools_coherently(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volatility REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_macd_hist REAL,
            feat_4h_bias50 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_bb_pct_b REAL,
            feat_eye REAL
        )
        """
    )

    label_rows = []
    raw_rows = []
    feature_rows = []
    baseline_macd = [220.0, 255.0, 290.0, 245.0, 310.0]
    baseline_bias50 = [3.8, 4.1, 4.4, 3.9, 4.3]
    baseline_rsi14 = [63.5, 66.2, 68.4, 64.1, 67.0]
    baseline_bb_pct_b = [0.63, 0.75, 0.88, 0.69, 0.81]
    baseline_close = [74200.0, 74580.0, 74990.0, 74320.0, 74860.0]
    baseline_vol = [0.0051, 0.0055, 0.0062, 0.0054, 0.0059]
    recent_macd = [144.8, 145.4, 146.2, 145.1, 145.7]
    recent_bias50 = [3.24, 3.27, 3.31, 3.28, 3.3]
    recent_rsi14 = [61.4, 61.6, 61.8, 61.5, 61.7]
    recent_bb_pct_b = [0.48, 0.49, 0.5, 0.49, 0.48]
    recent_close = [74272.0, 74286.0, 74305.0, 74291.0, 74280.0]
    recent_vol = [0.0049, 0.0049, 0.0049, 0.0048, 0.0049]

    for i in range(10):
        ts = f"2026-04-17 01:{i:02d}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1 if i >= 5 else 0, 0.5, 0.01, 0.4, 0.12, 0.3, 0.01, -0.02, 0.03, "bull"))
        if i < 5:
            macd = baseline_macd[i]
            bias50 = baseline_bias50[i]
            rsi14 = baseline_rsi14[i]
            bb_pct_b = baseline_bb_pct_b[i]
            close = baseline_close[i]
            vol = baseline_vol[i]
        else:
            idx = i - 5
            macd = recent_macd[idx]
            bias50 = recent_bias50[idx]
            rsi14 = recent_rsi14[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            close = recent_close[idx]
            vol = recent_vol[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", macd, bias50, rsi14, bb_pct_b, float(i)))
        raw_rows.append((ts, "BTCUSDT", close, vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_macd_hist"]["expected_compressed_reason"] == "coherent_4h_momentum_compression"
    details = expected["feat_4h_macd_hist"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 4
    assert details["min_required_proxies"] == 4
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bias50"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_rsi14"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_macd_hist" not in unexpected


def test_build_report_marks_4h_bias50_as_expected_compression_when_trend_proxies_compress(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volatility REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_macd_hist REAL,
            feat_4h_bias50 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_bb_pct_b REAL,
            feat_eye REAL
        )
        """
    )

    baseline_bias50 = [0.2, 1.5, -1.8, 2.7, -2.2]
    recent_bias50 = [2.95, 2.98, 3.0, 3.02, 3.01]
    baseline_rsi14 = [44.0, 48.0, 55.0, 61.0, 38.0]
    recent_rsi14 = [62.0, 62.2, 62.4, 62.3, 62.1]
    baseline_bb_pct_b = [0.21, 0.35, 0.68, 0.84, 0.48]
    recent_bb_pct_b = [0.47, 0.48, 0.49, 0.5, 0.48]
    baseline_macd = [-120.0, 80.0, -60.0, 150.0, -30.0]
    recent_macd = [140.0, 141.0, 142.0, 141.5, 140.5]
    baseline_close = [64000.0, 66000.0, 62000.0, 67500.0, 61000.0]
    recent_close = [74200.0, 74280.0, 74320.0, 74290.0, 74260.0]
    baseline_vol = [0.0010, 0.0018, 0.0031, 0.0024, 0.0014]
    recent_vol = [0.0048, 0.0049, 0.00485, 0.00488, 0.00486]

    label_rows = []
    raw_rows = []
    feature_rows = []
    for i in range(10):
        ts = f"2026-04-15 00:0{i}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 0.0, 0.01, 0.5, 0.1, 0.4, 0.01, -0.01, 0.02, "bull"))
        if i < 5:
            idx = i
            bias50 = baseline_bias50[idx]
            rsi14 = baseline_rsi14[idx]
            bb_pct_b = baseline_bb_pct_b[idx]
            macd = baseline_macd[idx]
            close = baseline_close[idx]
            vol = baseline_vol[idx]
        else:
            idx = i - 5
            bias50 = recent_bias50[idx]
            rsi14 = recent_rsi14[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            macd = recent_macd[idx]
            close = recent_close[idx]
            vol = recent_vol[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", macd, bias50, rsi14, bb_pct_b, float(i)))
        raw_rows.append((ts, "BTCUSDT", close, vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_bias50"]["expected_compressed_reason"] == "coherent_4h_trend_compression"
    details = expected["feat_4h_bias50"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 4
    assert details["min_required_proxies"] == 4
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_rsi14"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bb_pct_b"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_macd_hist"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_bias50" not in unexpected


def test_build_report_marks_4h_bias20_as_expected_compression_when_short_trend_cluster_compresses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_bias20 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_macd_hist REAL,
            feat_eye REAL
        )
        """
    )

    baseline_bias20 = [0.1, 1.8, -1.4, 2.2, -2.0]
    recent_bias20 = [2.84, 2.88, 2.91, 2.89, 2.9]
    baseline_rsi14 = [42.0, 47.0, 54.0, 60.0, 39.0]
    recent_rsi14 = [61.8, 61.9, 62.1, 62.0, 61.9]
    baseline_bb_pct_b = [0.18, 0.31, 0.65, 0.82, 0.44]
    recent_bb_pct_b = [0.46, 0.47, 0.49, 0.48, 0.47]
    baseline_macd = [-140.0, 70.0, -55.0, 130.0, -20.0]
    recent_macd = [138.0, 139.5, 141.0, 140.2, 139.0]

    label_rows = []
    feature_rows = []
    for i in range(10):
        ts = f"2026-04-15 02:0{i}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 0.0, 0.01, 0.5, 0.1, 0.4, 0.01, -0.01, 0.02, "bull"))
        if i < 5:
            idx = i
            bias20 = baseline_bias20[idx]
            rsi14 = baseline_rsi14[idx]
            bb_pct_b = baseline_bb_pct_b[idx]
            macd = baseline_macd[idx]
        else:
            idx = i - 5
            bias20 = recent_bias20[idx]
            rsi14 = recent_rsi14[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            macd = recent_macd[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", bias20, rsi14, bb_pct_b, macd, float(i)))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_bias20"]["expected_compressed_reason"] == "coherent_4h_short_trend_compression"
    details = expected["feat_4h_bias20"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 3
    assert details["min_required_proxies"] == 3
    assert details["proxy_stats"]["feat_4h_rsi14"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bb_pct_b"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_macd_hist"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_bias20" not in unexpected


def test_build_report_marks_4h_rsi14_as_expected_compression_when_short_trend_cluster_compresses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volatility REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_bias20 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_macd_hist REAL,
            feat_eye REAL
        )
        """
    )

    baseline_bias20 = [-2.4, -1.8, 0.2, 1.6, 2.3]
    recent_bias20 = [2.86, 2.88, 2.91, 2.89, 2.9]
    baseline_rsi14 = [33.0, 41.0, 52.0, 64.0, 71.0]
    recent_rsi14 = [62.0, 62.2, 62.1, 61.9, 62.05]
    baseline_bb_pct_b = [0.12, 0.28, 0.51, 0.76, 0.91]
    recent_bb_pct_b = [0.46, 0.47, 0.48, 0.49, 0.48]
    baseline_macd = [-180.0, -75.0, 10.0, 105.0, 190.0]
    recent_macd = [139.0, 140.2, 141.1, 140.5, 139.8]
    baseline_close = [68100.0, 69450.0, 70820.0, 72130.0, 73420.0]
    recent_close = [74210.0, 74255.0, 74295.0, 74260.0, 74235.0]
    baseline_vol = [0.0014, 0.0022, 0.0031, 0.0028, 0.0019]
    recent_vol = [0.00482, 0.00486, 0.00488, 0.00485, 0.00484]

    label_rows = []
    raw_rows = []
    feature_rows = []
    for i in range(10):
        ts = f"2026-04-15 03:0{i}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1, 0.0, 0.01, 0.5, 0.1, 0.4, 0.01, -0.01, 0.02, "bull"))
        if i < 5:
            idx = i
            bias20 = baseline_bias20[idx]
            rsi14 = baseline_rsi14[idx]
            bb_pct_b = baseline_bb_pct_b[idx]
            macd = baseline_macd[idx]
            close = baseline_close[idx]
            vol = baseline_vol[idx]
        else:
            idx = i - 5
            bias20 = recent_bias20[idx]
            rsi14 = recent_rsi14[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            macd = recent_macd[idx]
            close = recent_close[idx]
            vol = recent_vol[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", bias20, rsi14, bb_pct_b, macd, float(i)))
        raw_rows.append((ts, "BTCUSDT", close, vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_rsi14"]["expected_compressed_reason"] == "coherent_4h_short_trend_oscillator_compression"
    details = expected["feat_4h_rsi14"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 4
    assert details["min_required_proxies"] == 4
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bias20"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bb_pct_b"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_macd_hist"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_rsi14" not in unexpected


def test_build_report_marks_4h_dist_bb_lower_as_expected_compression_when_band_floor_cluster_compresses(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volatility REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_dist_swing_low REAL,
            feat_4h_dist_bb_lower REAL,
            feat_4h_bb_pct_b REAL,
            feat_eye REAL
        )
        """
    )

    label_rows = []
    raw_rows = []
    feature_rows = []
    baseline_swing = [6.0, 6.8, 7.5, 5.9, 7.2]
    baseline_bb_lower = [2.1, 2.8, 3.0, 2.4, 2.9]
    baseline_bb_pct_b = [0.62, 0.85, 0.74, 0.93, 0.68]
    baseline_close = [74200.0, 74650.0, 75120.0, 73980.0, 74810.0]
    baseline_vol = [0.0060, 0.0052, 0.0066, 0.0054, 0.0061]
    recent_swing = [5.02, 5.09, 5.12, 4.98, 5.05]
    recent_bb_lower = [1.49, 1.55, 1.58, 1.51, 1.54]
    recent_bb_pct_b = [0.47, 0.49, 0.5, 0.48, 0.46]
    recent_close = [74240.0, 74285.0, 74210.0, 74305.0, 74260.0]
    recent_vol = [0.0048, 0.0049, 0.0049, 0.0048, 0.0049]

    for i in range(10):
        ts = f"2026-04-17 01:{i:02d}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1 if i >= 5 else 0, 0.5, 0.01, 0.4, 0.12, 0.3, 0.01, -0.02, 0.03, "bull"))
        if i < 5:
            swing = baseline_swing[i]
            bb_lower = baseline_bb_lower[i]
            bb_pct_b = baseline_bb_pct_b[i]
            close = baseline_close[i]
            vol = baseline_vol[i]
        else:
            idx = i - 5
            swing = recent_swing[idx]
            bb_lower = recent_bb_lower[idx]
            bb_pct_b = recent_bb_pct_b[idx]
            close = recent_close[idx]
            vol = recent_vol[idx]
        feature_rows.append((ts, "BTCUSDT", "bull", swing, bb_lower, bb_pct_b, float(i)))
        raw_rows.append((ts, "BTCUSDT", close, vol))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO raw_market_data VALUES (?, ?, ?, ?)",
        raw_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    feature_diag = report["windows"]["5"]["feature_diagnostics"]

    expected = {row["feature"]: row for row in feature_diag["expected_compressed_examples"]}
    assert expected["feat_4h_dist_bb_lower"]["expected_compressed_reason"] == "coherent_4h_band_floor_compression"
    details = expected["feat_4h_dist_bb_lower"]["expected_compressed_details"]
    assert details["compressed_proxy_count"] >= 3
    assert details["min_required_proxies"] == 3
    assert details["proxy_stats"]["raw_close_price"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["raw_volatility"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_bb_pct_b"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    assert details["proxy_stats"]["feat_4h_dist_swing_low"]["std_ratio"] <= recent_drift_report.LOW_VARIANCE_STD_RATIO_THRESHOLD
    unexpected = {row["feature"] for row in feature_diag["unexpected_compressed_examples"]}
    assert "feat_4h_dist_bb_lower" not in unexpected


def test_build_report_keeps_sparse_research_features_out_of_primary_shift_and_unexpected_freeze_lists(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_eye REAL,
            feat_claw REAL,
            feat_nest_pred REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    for i in range(10):
        ts = f"2026-04-11 01:{i:02d}:00"
        label_rows.append((i + 1, ts, "BTCUSDT", 1440, 1 if i >= 5 else 0, 0.6, 0.01, 0.55, 0.12, 0.2, 0.01, -0.02, 0.03, "chop"))
        if i < 5:
            feat_eye = float(i)
            feat_claw = float(i)
            feat_nest_pred = float(i)
        else:
            feat_eye = 50.0 + i
            feat_claw = 0.0
            feat_nest_pred = 0.5
        feature_rows.append((ts, "BTCUSDT", "chop", feat_eye, feat_claw, feat_nest_pred))

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [5])

    report = recent_drift_report.build_report()
    summary = report["windows"]["5"]
    feature_diag = summary["feature_diagnostics"]
    reference = summary["reference_window_comparison"]

    assert feature_diag["overlay_only_count"] >= 2
    assert {row["feature"] for row in feature_diag["overlay_only_examples"]} >= {"feat_claw", "feat_nest_pred"}
    assert feature_diag["unexpected_frozen_count"] == 0
    assert reference["top_mean_shift_features"]
    assert all(row["feature"] == "feat_eye" for row in reference["top_mean_shift_features"])


def test_target_path_diagnostics_exposes_longest_adverse_streak_even_when_tail_recovers():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE sample (
            label_id INTEGER,
            timestamp TEXT,
            symbol TEXT,
            target INTEGER,
            regime TEXT,
            spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL
        )
        """
    )
    rows = []
    for i in range(12):
        target = 0 if 2 <= i <= 7 else 1
        rows.append(
            (
                i + 1,
                f"2026-04-12 00:{i:02d}:00",
                "BTCUSDT",
                target,
                "chop",
                float(target),
                0.01 if target else -0.02,
                0.4 if target else -0.3,
                0.1 if target else 0.25,
                0.2 if target else 0.6,
                0.01 if target else -0.01,
                -0.02,
                0.03,
            )
        )
    conn.executemany("INSERT INTO sample VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    query_rows = conn.execute("SELECT * FROM sample ORDER BY timestamp").fetchall()
    conn.close()

    diagnostics = recent_drift_report._target_path_diagnostics(query_rows)

    assert diagnostics["tail_target_streak"]["target"] == 1
    assert diagnostics["tail_target_streak"]["count"] == 4
    assert diagnostics["longest_zero_target_streak"]["target"] == 0
    assert diagnostics["longest_zero_target_streak"]["count"] == 6
    assert diagnostics["longest_zero_target_streak"]["start_timestamp"] == "2026-04-12 00:02:00"
    assert diagnostics["longest_zero_target_streak"]["end_timestamp"] == "2026-04-12 00:07:00"


def test_select_adverse_target_streak_tracks_losses_not_all_win_tail():
    adverse = recent_drift_report._select_adverse_target_streak(
        {
            "longest_zero_target_streak": {
                "target": 0,
                "count": 0,
                "start_timestamp": None,
                "end_timestamp": None,
                "examples": [],
            },
            "longest_one_target_streak": {
                "target": 1,
                "count": 100,
                "start_timestamp": "2026-04-19 15:30:25",
                "end_timestamp": "2026-04-20 09:12:33",
                "examples": [{"timestamp": "2026-04-20 09:12:33", "target": 1}],
            },
        }
    )

    assert adverse["target"] == 0
    assert adverse["count"] == 0
    assert adverse["examples"] == []


def test_classify_window_marks_high_quality_label_imbalance_as_supported_extreme_trend_even_if_legacy_compare_is_weaker():
    interpretation = recent_drift_report._classify_window(
        ["label_imbalance", "regime_concentration"],
        {
            "simulated_win_rate": 0.97,
            "avg_simulated_pnl": 0.0153,
            "avg_simulated_quality": 0.5770,
            "avg_drawdown_penalty": 0.0425,
            "avg_time_underwater": 0.18,
            "spot_long_win_rate": 0.38,
        },
    )

    assert interpretation == "supported_extreme_trend"


def test_classify_window_keeps_supported_extreme_trend_for_near_threshold_time_underwater_when_other_canonical_metrics_are_strong():
    interpretation = recent_drift_report._classify_window(
        ["constant_target", "regime_concentration"],
        {
            "simulated_win_rate": 1.0,
            "avg_simulated_pnl": 0.0181,
            "avg_simulated_quality": 0.6207,
            "avg_drawdown_penalty": 0.0444,
            "avg_time_underwater": 0.4713,
            "spot_long_win_rate": 0.57,
        },
    )

    assert interpretation == "supported_extreme_trend"


def test_classify_window_marks_strong_nonconstant_label_imbalance_as_supported_extreme_trend_when_drawdown_is_low():
    interpretation = recent_drift_report._classify_window(
        ["label_imbalance", "regime_shift"],
        {
            "simulated_win_rate": 0.88,
            "avg_simulated_pnl": 0.0148,
            "avg_simulated_quality": 0.5503,
            "avg_drawdown_penalty": 0.0703,
            "avg_time_underwater": 0.1642,
            "spot_long_win_rate": 0.61,
        },
    )

    assert interpretation == "supported_extreme_trend"


def test_compact_window_summary_describes_positive_label_imbalance_as_concentration_risk():
    compact = recent_drift_report._compact_window_summary(
        window_rows=100,
        alerts=["label_imbalance", "regime_concentration", "regime_shift"],
        interpretation="distribution_pathology",
        win_rate=0.81,
        dominant_regime="bull",
        dominant_share=1.0,
        quality_metrics={
            "avg_simulated_pnl": 0.0046,
            "avg_simulated_quality": 0.3429,
            "avg_drawdown_penalty": 0.2043,
        },
        target_path_diagnostics={
            "tail_target_streak": {
                "target": 0,
                "count": 19,
                "start_timestamp": "2026-04-23 12:00:00",
                "end_timestamp": "2026-04-24 06:00:00",
            },
            "longest_zero_target_streak": {
                "target": 0,
                "count": 19,
                "start_timestamp": "2026-04-23 12:00:00",
                "end_timestamp": "2026-04-24 06:00:00",
            },
        },
        reference_comparison={
            "top_mean_shift_features": [
                {"feature": "feat_bb_pct_b"},
                {"feature": "feat_4h_dist_bb_lower"},
            ]
        },
    )

    assert compact["severity"] == "medium"
    assert compact["actionable_summary"] == "distribution concentration with adverse tail risk; canonical quality remains positive"
    assert compact["top_shift_features"] == ["feat_bb_pct_b", "feat_4h_dist_bb_lower"]
    assert compact["tail_streak"]["count"] == 19
    assert compact["adverse_streak"]["count"] == 19


def test_find_primary_window_prefers_more_persistent_pathology_when_severity_and_delta_tie():
    label, summary = recent_drift_report._find_primary_window(
        {
            "100": {
                "rows": 100,
                "alerts": ["constant_target"],
                "win_rate_delta_vs_full": -0.6261,
            },
            "250": {
                "rows": 250,
                "alerts": ["constant_target"],
                "win_rate_delta_vs_full": -0.6261,
            },
            "500": {
                "rows": 500,
                "alerts": ["label_imbalance"],
                "win_rate_delta_vs_full": -0.4781,
            }
        }
    )

    assert label == "250"
    assert summary["rows"] == 250


def test_find_blocking_window_prefers_negative_pathology_over_supported_extreme_trend():
    label, summary = recent_drift_report._find_blocking_window(
        {
            "100": {
                "rows": 100,
                "alerts": ["constant_target", "regime_concentration", "regime_shift"],
                "win_rate": 1.0,
                "drift_interpretation": "supported_extreme_trend",
                "quality_metrics": {
                    "avg_simulated_pnl": 0.0191,
                    "avg_simulated_quality": 0.6332,
                    "spot_long_win_rate": 0.74,
                },
            },
            "500": {
                "rows": 500,
                "alerts": ["regime_shift"],
                "win_rate": 0.25,
                "drift_interpretation": "regime_concentration",
                "quality_metrics": {
                    "avg_simulated_pnl": -0.0015,
                    "avg_simulated_quality": -0.0335,
                    "spot_long_win_rate": 0.14,
                },
            },
        }
    )

    assert label == "500"
    assert summary["drift_interpretation"] == "regime_concentration"


def test_build_report_includes_canonical_tail_root_cause_loss_path_breakdown(tmp_path, monkeypatch):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            simulated_pyramid_win INTEGER,
            label_spot_long_win REAL,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL,
            future_return_pct REAL,
            future_max_drawdown REAL,
            future_max_runup REAL,
            regime_label TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_4h_bias200 REAL,
            feat_4h_dist_swing_low REAL,
            feat_4h_dist_swing_high REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_rsi14 REAL,
            feat_4h_bias50 REAL
        )
        """
    )

    label_rows = []
    feature_rows = []
    for i in range(200):
        recent = i >= 100
        recent_idx = i - 100 if recent else i
        target = 0 if recent and recent_idx < 80 else 1
        regime = "chop" if recent_idx < 50 else ("bull" if recent_idx < 70 else "bear")
        if not recent:
            target = 1 if i % 3 else 0
            regime = "bull" if i < 60 else "chop"
        tp_miss_runup = 0.012 if target == 0 and recent_idx < 60 else 0.028
        max_drawdown = -0.061 if target == 0 and 30 <= recent_idx < 48 else (-0.028 if target == 0 else -0.014)
        time_underwater = 0.86 if target == 0 and recent_idx < 45 else (0.42 if target == 0 else 0.16)
        ts = f"2026-04-12 00:{i:03d}:00"
        label_rows.append(
            (
                i + 1,
                ts,
                "BTCUSDT",
                1440,
                target,
                float(target),
                0.014 if target else -0.012,
                0.58 if target else -0.22,
                0.08 if target else 0.31,
                time_underwater,
                0.014 if target else -0.012,
                max_drawdown,
                tp_miss_runup,
                regime,
            )
        )
        bias200 = 2.0 + (0.02 * i) + (4.0 if recent and target == 0 else 0.0)
        feature_rows.append(
            (
                ts,
                "BTCUSDT",
                regime,
                bias200,
                -0.8 if recent and target == 0 else 1.4,
                1.1 if recent and target == 0 else -0.2,
                0.91 if recent and target == 0 else 0.42,
                72.0 if recent and target == 0 else 48.0,
                6.0 if recent and target == 0 else 1.0,
            )
        )

    conn.executemany(
        "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        label_rows,
    )
    conn.executemany(
        "INSERT INTO features_normalized VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        feature_rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(recent_drift_report, "DB_PATH", db_path)
    monkeypatch.setattr(recent_drift_report, "WINDOWS", [100])

    report = recent_drift_report.build_report()
    root_cause = report["canonical_tail_root_cause"]

    assert root_cause["window"] == 100
    assert root_cause["rows"] == 100
    assert root_cause["losses"] == 80
    assert root_cause["wins"] == 20
    assert root_cause["loss_path_breakdown"]["tp_miss_count"] == 60
    assert root_cause["loss_path_breakdown"]["dd_breach_count"] == 18
    assert root_cause["loss_path_breakdown"]["high_underwater_count"] == 45
    assert root_cause["loss_path_breakdown"]["avg_time_underwater"] > 0.5
    assert root_cause["regime_breakdown"]["chop"]["losses"] == 50
    assert root_cause["regime_breakdown"]["bull"]["losses"] == 20
    assert root_cause["regime_breakdown"]["bear"]["losses"] == 10
    assert root_cause["dominant_loss_regime"] == "chop"
    assert root_cause["feature_shift"]["loss_vs_reference"]["feat_4h_bias200"]["current_loss_mean"] > root_cause["feature_shift"]["loss_vs_reference"]["feat_4h_bias200"]["reference_mean"]
    assert root_cause["feature_shift"]["loss_vs_recent_wins"]["feat_4h_bb_pct_b"]["loss_mean"] > root_cause["feature_shift"]["loss_vs_recent_wins"]["feat_4h_bb_pct_b"]["win_mean"]
    assert "feat_4h_bias200" in root_cause["top_4h_shift_features"]
    assert root_cause["key_findings"]
