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
