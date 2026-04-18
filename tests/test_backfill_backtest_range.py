from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from database.models import RawMarketData, FeaturesNormalized, Labels, init_db
from scripts import backfill_backtest_range


def test_compute_missing_range_flags_older_history_gap():
    coverage = {
        "raw": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 10},
        "features": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 9},
        "labels": {"start": "2025-04-04T13:00:00Z", "end": "2026-04-15T00:40:26Z", "count": 8},
    }

    plan = backfill_backtest_range.compute_missing_range(
        coverage,
        target_start="2024-04-16T00:00:00Z",
        target_end="2026-04-16T00:40:26Z",
    )

    assert plan["needs_backfill"] is True
    assert plan["missing_raw_start"] is True
    assert plan["missing_feature_start"] is True
    assert plan["requested_days"] > 700


def test_run_backfill_pipeline_dry_run_reports_plan_only(monkeypatch):
    monkeypatch.setattr(
        backfill_backtest_range,
        "collect_coverage",
        lambda session, symbol="BTCUSDT", horizon_hours=24: {
            "raw": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 10},
            "features": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 9},
            "labels": {"start": "2025-04-04T13:00:00Z", "end": "2026-04-15T00:40:26Z", "count": 8},
        },
    )

    result = backfill_backtest_range.run_backfill_pipeline(
        session=None,
        symbol="BTCUSDT",
        target_start="2024-04-16T00:00:00Z",
        target_end="2026-04-16T00:40:26Z",
        apply_changes=False,
    )

    assert result["dry_run"] is True
    assert result["plan"]["needs_backfill"] is True
    assert result["actions"]["raw_rows_inserted"] == 0
    assert result["actions"]["feature_rows_inserted"] == 0
    assert result["actions"]["labels_saved"] == 0


def test_run_backfill_pipeline_apply_executes_fetch_feature_and_label_steps(monkeypatch):
    calls = {"fetch": 0, "feature": 0, "label": 0, "save": 0}

    monkeypatch.setattr(
        backfill_backtest_range,
        "collect_coverage",
        lambda session, symbol="BTCUSDT", horizon_hours=24: {
            "raw": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 10},
            "features": {"start": "2025-04-03T13:00:00Z", "end": "2026-04-16T00:40:26Z", "count": 9},
            "labels": {"start": "2025-04-04T13:00:00Z", "end": "2026-04-15T00:40:26Z", "count": 8},
        },
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "fetch_and_store_raw_history",
        lambda session, symbol, days: calls.__setitem__("fetch", calls["fetch"] + 1) or 25,
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "backfill_missing_feature_rows",
        lambda session, symbol="BTCUSDT", lookback_days=None: calls.__setitem__("feature", calls["feature"] + 1) or 22,
    )

    class DummyLabels:
        empty = False
        def __len__(self):
            return 30

    monkeypatch.setattr(
        backfill_backtest_range,
        "generate_future_return_labels",
        lambda session, symbol="BTCUSDT", horizon_hours=24: calls.__setitem__("label", calls["label"] + 1) or DummyLabels(),
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "save_labels_to_db",
        lambda session, labels_df, symbol="BTCUSDT", horizon_hours=24, force_update_all=False: calls.__setitem__("save", calls["save"] + 1),
    )

    result = backfill_backtest_range.run_backfill_pipeline(
        session=None,
        symbol="BTCUSDT",
        target_start="2024-04-16T00:00:00Z",
        target_end="2026-04-16T00:40:26Z",
        apply_changes=True,
    )

    assert result["dry_run"] is False
    assert result["actions"]["raw_rows_inserted"] == 25
    assert result["actions"]["feature_rows_inserted"] == 22
    assert result["actions"]["labels_saved"] == 30
    assert calls == {"fetch": 1, "feature": 1, "label": 1, "save": 1}


def test_collect_coverage_reads_min_max_counts(tmp_path: Path):
    session = init_db(f"sqlite:///{tmp_path / 'coverage.db'}")
    assert isinstance(session, Session)
    try:
        session.add_all([
            RawMarketData(timestamp=datetime(2025, 1, 1, 0, 0), symbol="BTCUSDT", close_price=100.0, volume=1.0),
            RawMarketData(timestamp=datetime(2025, 1, 2, 0, 0), symbol="BTCUSDT", close_price=101.0, volume=1.0),
            FeaturesNormalized(timestamp=datetime(2025, 1, 1, 0, 0), symbol="BTCUSDT", feat_4h_bias50=-1.0),
            FeaturesNormalized(timestamp=datetime(2025, 1, 2, 0, 0), symbol="BTCUSDT", feat_4h_bias50=-0.5),
            Labels(timestamp=datetime(2025, 1, 1, 0, 0), symbol="BTCUSDT", horizon_minutes=1440, label_spot_long_win=1, label_sell_win=0, label_up=1),
        ])
        session.commit()

        coverage = backfill_backtest_range.collect_coverage(session, symbol="BTCUSDT", horizon_hours=24)
    finally:
        session.close()

    assert coverage["raw"]["count"] == 2
    assert coverage["features"]["count"] == 2
    assert coverage["labels"]["count"] == 1
    assert coverage["raw"]["start"].startswith("2025-01-01")
