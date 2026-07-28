from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

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


def test_compute_missing_range_flags_newer_history_gap():
    coverage = {
        "raw": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 10},
        "features": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 9},
        "labels": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 8},
    }

    plan = backfill_backtest_range.compute_missing_range(
        coverage,
        target_start="2024-05-29T00:00:00Z",
        target_end="2026-05-29T00:00:00Z",
    )

    assert plan["needs_backfill"] is True
    assert plan["missing_raw_start"] is False
    assert plan["missing_feature_start"] is False
    assert plan["missing_label_start"] is False
    assert plan["missing_raw_end"] is True
    assert plan["missing_feature_end"] is True
    assert plan["missing_label_end"] is True


def test_fetch_okx_klines_for_range_paginates_and_honors_bounds(monkeypatch):
    start = int(datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    hour = 3_600_000
    calls = []

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, since, limit):
            calls.append((symbol, timeframe, since, limit))
            if since == start:
                return [[start, 1, 2, 0, 1.5, 10], [start + hour, 2, 3, 1, 2.5, 20]]
            if since == start + 2 * hour:
                return [[start + 2 * hour, 3, 4, 2, 3.5, 30], [start + 3 * hour, 4, 5, 3, 4.5, 40]]
            return []

    monkeypatch.setitem(__import__("sys").modules, "ccxt", SimpleNamespace(okx=lambda config: FakeExchange()))

    frame = backfill_backtest_range.fetch_okx_klines_for_range(
        symbol="BTCUSDT",
        target_start="2026-06-01T00:00:00Z",
        target_end="2026-06-01T03:00:00Z",
    )

    assert len(frame) == 4
    assert [int(item[2]) for item in calls] == [start, start + 2 * hour]
    assert all(item[0] == "BTC/USDT" and item[1] == "1h" for item in calls)


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


def test_run_backfill_pipeline_apply_executes_newer_gap_steps(monkeypatch):
    calls = {"fetch": 0, "feature": 0, "4h": 0, "label": 0, "save": 0}

    monkeypatch.setattr(
        backfill_backtest_range,
        "collect_coverage",
        lambda session, symbol="BTCUSDT", horizon_hours=24: {
            "raw": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 10},
            "features": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 9},
            "labels": {"start": "2024-04-16T00:00:00Z", "end": "2026-05-28T08:00:00Z", "count": 8},
        },
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "fetch_and_store_raw_history",
        lambda session, symbol, days: calls.__setitem__("fetch", calls["fetch"] + 1) or 12,
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "backfill_missing_feature_rows",
        lambda session, symbol="BTCUSDT", lookback_days=None: calls.__setitem__("feature", calls["feature"] + 1) or 10,
    )
    monkeypatch.setattr(
        backfill_backtest_range.backfill_4h_distance_module,
        "main",
        lambda: calls.__setitem__("4h", calls["4h"] + 1) or 0,
    )

    class DummyLabels:
        empty = False
        def __len__(self):
            return 11

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
        target_start="2024-05-29T00:00:00Z",
        target_end="2026-05-29T00:00:00Z",
        apply_changes=True,
    )

    assert result["dry_run"] is False
    assert result["plan"]["missing_raw_end"] is True
    assert result["actions"]["raw_rows_inserted"] == 12
    assert result["actions"]["feature_rows_inserted"] == 10
    assert result["actions"]["four_h_distance_refreshed"] is True
    assert result["actions"]["labels_saved"] == 11
    assert calls == {"fetch": 1, "feature": 1, "4h": 1, "label": 1, "save": 1}


def test_run_backfill_pipeline_apply_executes_fetch_feature_and_label_steps(monkeypatch):
    calls = {"fetch": 0, "feature": 0, "4h": 0, "label": 0, "save": 0}

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
    monkeypatch.setattr(
        backfill_backtest_range.backfill_4h_distance_module,
        "main",
        lambda: calls.__setitem__("4h", calls["4h"] + 1) or 0,
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
    assert result["actions"]["four_h_distance_refreshed"] is True
    assert result["actions"]["labels_saved"] == 30
    assert calls == {"fetch": 1, "feature": 1, "4h": 1, "label": 1, "save": 1}


def test_run_backfill_pipeline_repairs_explicit_interior_gap(monkeypatch):
    calls = {"gap": [], "feature": 0, "4h": 0, "label": 0, "save": 0}
    monkeypatch.setattr(
        backfill_backtest_range,
        "collect_coverage",
        lambda session, symbol="BTCUSDT", horizon_hours=24: {
            "raw": {"start": "2026-06-01T00:00:00Z", "end": "2026-07-01T00:00:00Z", "count": 100},
            "features": {"start": "2026-06-01T00:00:00Z", "end": "2026-07-01T00:00:00Z", "count": 100},
            "labels": {"start": "2026-06-01T00:00:00Z", "end": "2026-07-01T00:00:00Z", "count": 100},
        },
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "fetch_and_store_raw_gap_range",
        lambda session, *, symbol, target_start, target_end: calls["gap"].append((symbol, target_start, target_end)) or 24,
    )
    monkeypatch.setattr(
        backfill_backtest_range,
        "backfill_missing_feature_rows",
        lambda session, symbol="BTCUSDT", lookback_days=None: calls.__setitem__("feature", calls["feature"] + 1) or 24,
    )
    monkeypatch.setattr(
        backfill_backtest_range.backfill_4h_distance_module,
        "main",
        lambda: calls.__setitem__("4h", calls["4h"] + 1),
    )

    class DummyLabels:
        empty = False
        def __len__(self):
            return 24

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
        target_start="2026-06-01T00:00:00Z",
        target_end="2026-07-01T00:00:00Z",
        interior_gap_ranges=[{"start": "2026-06-05T04:00:00Z", "end": "2026-06-26T00:00:00Z"}],
        apply_changes=True,
    )

    assert result["plan"]["interior_gap_count"] == 1
    assert result["actions"]["raw_rows_inserted"] == 24
    assert calls["gap"] == [("BTCUSDT", "2026-06-05T04:00:00Z", "2026-06-26T00:00:00Z")]
    assert calls["feature"] == calls["4h"] == calls["label"] == calls["save"] == 1


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


def test_collect_coverage_accepts_symbol_alias_and_excludes_strategy_unready_features(tmp_path: Path):
    session = init_db(f"sqlite:///{tmp_path / 'coverage_alias.db'}")
    assert isinstance(session, Session)
    try:
        session.add_all([
            RawMarketData(timestamp=datetime(2026, 6, 27, 0, 0), symbol="BTCUSDT", close_price=100.0, volume=1.0),
            FeaturesNormalized(timestamp=datetime(2026, 6, 27, 0, 0), symbol="BTC/USDT", feat_4h_bias50=None),
            FeaturesNormalized(timestamp=datetime(2026, 6, 27, 1, 0), symbol="BTC/USDT", feat_4h_bias50=0.5),
            Labels(timestamp=datetime(2026, 6, 27, 0, 0), symbol="BTCUSDT", horizon_minutes=1440, label_spot_long_win=1, label_sell_win=0, label_up=1),
        ])
        session.commit()
        coverage = backfill_backtest_range.collect_coverage(session, symbol="BTCUSDT", horizon_hours=24)
    finally:
        session.close()

    assert coverage["features"]["count"] == 1
    assert coverage["features"]["start"].startswith("2026-06-27T01:00:00")
