from pathlib import Path
import sqlite3

from feature_engine.feature_history_policy import (
    assess_feature_quality,
    build_source_blocker_summary,
    compute_sqlite_feature_coverage,
)


def test_assess_feature_quality_marks_sparse_source_as_blocked_gap():
    result = assess_feature_quality("claw", coverage_pct=0.0, distinct=0, non_null=0, min_v=None, max_v=None)

    assert result["chart_usable"] is False
    assert result["quality_flag"] == "source_history_gap"
    assert result["history_class"] == "archive_required"
    assert "CoinGlass" in result["backfill_blocker"]


def test_compute_sqlite_feature_coverage_and_blocker_summary(tmp_path: Path):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    columns = [
        "id INTEGER PRIMARY KEY",
        "timestamp TEXT",
        "symbol TEXT",
    ]
    feature_columns = [
        "feat_eye REAL", "feat_ear REAL", "feat_nose REAL", "feat_tongue REAL", "feat_body REAL",
        "feat_pulse REAL", "feat_aura REAL", "feat_mind REAL", "feat_vix REAL", "feat_dxy REAL",
        "feat_rsi14 REAL", "feat_macd_hist REAL", "feat_atr_pct REAL", "feat_vwap_dev REAL", "feat_bb_pct_b REAL",
        "feat_nq_return_1h REAL", "feat_nq_return_24h REAL", "feat_claw REAL", "feat_claw_intensity REAL",
        "feat_fang_pcr REAL", "feat_fang_skew REAL", "feat_fin_netflow REAL", "feat_web_whale REAL",
        "feat_scales_ssr REAL", "feat_nest_pred REAL", "feat_4h_bias50 REAL", "feat_4h_bias20 REAL",
        "feat_4h_bias200 REAL", "feat_4h_rsi14 REAL", "feat_4h_macd_hist REAL", "feat_4h_bb_pct_b REAL",
        "feat_4h_dist_bb_lower REAL", "feat_4h_ma_order REAL", "feat_4h_dist_swing_low REAL", "feat_4h_vol_ratio REAL",
    ]
    conn.execute(f"CREATE TABLE features_normalized ({', '.join(columns + feature_columns)})")
    conn.execute("CREATE TABLE raw_events (id INTEGER PRIMARY KEY, subtype TEXT, timestamp TEXT)")
    conn.execute("INSERT INTO raw_events (subtype, timestamp) VALUES ('web_snapshot', '2024-04-09 00:00:00')")
    conn.execute("INSERT INTO raw_events (subtype, timestamp) VALUES ('web_snapshot', '2024-04-09 01:00:00')")
    for i in range(10):
        conn.execute(
            """
            INSERT INTO features_normalized (
                timestamp, symbol, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body,
                feat_pulse, feat_aura, feat_mind, feat_vix, feat_dxy, feat_rsi14, feat_macd_hist,
                feat_atr_pct, feat_vwap_dev, feat_bb_pct_b, feat_nq_return_1h, feat_nq_return_24h,
                feat_web_whale, feat_4h_ma_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"2026-04-09T{i:02d}:00:00", "BTCUSDT", i, i, i, i, i,
                i, i, i, i, i, i, i, i, i, i, i, i,
                1.0 if i < 2 else None, -1 if i % 2 == 0 else 1,
            ),
        )
    conn.commit()
    conn.close()

    payload = compute_sqlite_feature_coverage(db_path)
    by_key = {row["key"]: row for row in payload["features"]}

    assert by_key["eye"]["chart_usable"] is True
    assert by_key["web_whale"]["chart_usable"] is False
    assert by_key["web_whale"]["history_class"] == "short_window_public_api"
    assert by_key["web_whale"]["raw_snapshot_events"] == 2
    assert by_key["web_whale"]["forward_archive_started"] is True
    assert by_key["web_whale"]["forward_archive_ready"] is False
    assert by_key["web_whale"]["forward_archive_stale"] is True
    assert by_key["web_whale"]["forward_archive_status"] == "stale"
    assert by_key["web_whale"]["forward_archive_ready_min_events"] == 10
    assert by_key["web_whale"]["raw_snapshot_subtypes"] == ["web_snapshot"]
    assert by_key["web_whale"]["raw_snapshot_span_hours"] == 1.0
    assert by_key["web_whale"]["raw_snapshot_latest_age_min"] is not None
    assert by_key["web_whale"]["archive_window_started"] is True
    assert by_key["web_whale"]["archive_window_rows"] == 10
    assert by_key["web_whale"]["archive_window_non_null"] == 2
    assert by_key["web_whale"]["archive_window_coverage_pct"] == 20.0
    assert "Forward raw snapshot archive is stale (2/10 stored event(s)" in by_key["web_whale"]["backfill_blocker"]

    summary = build_source_blocker_summary(payload)
    assert summary["blocked_count"] >= 1
    assert any(row["key"] == "web_whale" for row in summary["blocked_features"])


def test_ready_forward_archive_changes_recommended_action_without_hiding_blocker(tmp_path: Path):
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE features_normalized (id INTEGER PRIMARY KEY, timestamp TEXT, symbol TEXT, feat_web_whale REAL)")
    conn.execute("CREATE TABLE raw_events (id INTEGER PRIMARY KEY, subtype TEXT, timestamp TEXT)")

    for i in range(12):
        hour = i % 10
        conn.execute(
            "INSERT INTO raw_events (subtype, timestamp) VALUES ('web_snapshot', ?)",
            (f"2026-04-09 {hour:02d}:00:00",),
        )
        conn.execute(
            "INSERT INTO features_normalized (timestamp, symbol, feat_web_whale) VALUES (?, 'BTCUSDT', ?)",
            (f"2026-04-09T{hour:02d}:00:00", float(i) / 10.0),
        )

    conn.commit()
    conn.close()

    payload = compute_sqlite_feature_coverage(db_path)
    web = next(row for row in payload["features"] if row["key"] == "web_whale")

    assert web["forward_archive_ready"] is True
    assert web["forward_archive_status"] == "ready"
    assert web["backfill_status"] == "blocked"
    assert web["archive_window_coverage_pct"] == 100.0
    assert "ready for recent-window diagnostics" in web["recommended_action"]
