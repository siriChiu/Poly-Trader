import importlib.util
import sqlite3
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "auto_propose_fixes.py"
spec = importlib.util.spec_from_file_location("auto_propose_fixes_test_module", MODULE_PATH)
auto_propose_fixes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(auto_propose_fixes)


def test_check_db_uses_canonical_simulated_pyramid_win(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE raw_market_data (timestamp TEXT)")
    conn.execute("CREATE TABLE labels (id INTEGER PRIMARY KEY, simulated_pyramid_win INTEGER)")
    conn.execute("INSERT INTO raw_market_data(timestamp) VALUES ('2026-04-11 03:52:09')")
    conn.executemany(
        "INSERT INTO labels(simulated_pyramid_win) VALUES (?)",
        [(1,), (1,), (0,), (0,)],
    )
    conn.commit()
    conn.close()

    stats = auto_propose_fixes.check_db()

    assert stats["simulated_win_avg"] == 0.5
    assert stats["losing_streak"] == 2
    assert stats["raw_latest_age_min"] is not None


def test_check_db_prefers_canonical_1440m_streak_over_mixed_horizon_tail(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE raw_market_data (timestamp TEXT)")
    conn.execute(
        "CREATE TABLE labels (id INTEGER PRIMARY KEY, horizon_minutes INTEGER, simulated_pyramid_win INTEGER)"
    )
    conn.execute("INSERT INTO raw_market_data(timestamp) VALUES ('2026-04-11 03:52:09')")
    conn.executemany(
        "INSERT INTO labels(horizon_minutes, simulated_pyramid_win) VALUES (?, ?)",
        [
            (1440, 1),
            (1440, 0),
            (1440, 0),
            (240, 1),
            (1440, 0),
            (1440, 0),
        ],
    )
    conn.commit()
    conn.close()

    stats = auto_propose_fixes.check_db()

    assert stats["canonical_horizon_minutes"] == 1440
    assert stats["losing_streak"] == 4
    assert stats["all_horizon_losing_streak"] == 2


def test_check_db_does_not_truncate_canonical_streaks_beyond_200_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE raw_market_data (timestamp TEXT)")
    conn.execute(
        "CREATE TABLE labels (id INTEGER PRIMARY KEY, timestamp TEXT, horizon_minutes INTEGER, simulated_pyramid_win INTEGER)"
    )
    conn.execute("INSERT INTO raw_market_data(timestamp) VALUES ('2026-04-11 03:52:09')")
    rows = []
    for minute in range(241):
        ts = f"2026-04-11 00:{minute // 60:02d}:{minute % 60:02d}"
        simulated_win = 1 if minute == 0 else 0
        rows.append((ts, 1440, simulated_win))
    conn.executemany(
        "INSERT INTO labels(timestamp, horizon_minutes, simulated_pyramid_win) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()

    stats = auto_propose_fixes.check_db()

    assert stats["canonical_horizon_minutes"] == 1440
    assert stats["losing_streak"] == 240


def test_check_db_orders_streak_by_timestamp_not_insert_order(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    db_path = tmp_path / "poly_trader.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE raw_market_data (timestamp TEXT)")
    conn.execute(
        "CREATE TABLE labels (id INTEGER PRIMARY KEY, timestamp TEXT, horizon_minutes INTEGER, simulated_pyramid_win INTEGER)"
    )
    conn.execute("INSERT INTO raw_market_data(timestamp) VALUES ('2026-04-11 03:52:09')")
    conn.executemany(
        "INSERT INTO labels(timestamp, horizon_minutes, simulated_pyramid_win) VALUES (?, ?, ?)",
        [
            ("2026-04-11 00:00:00", 1440, 0),
            ("2026-04-11 00:10:00", 1440, 0),
            ("2026-04-11 00:20:00", 1440, 1),
            # Insert an older row after the latest win to mimic backfill/out-of-order IDs.
            ("2026-04-10 23:50:00", 1440, 0),
        ],
    )
    conn.commit()
    conn.close()

    stats = auto_propose_fixes.check_db()

    assert stats["losing_streak"] == 0


def test_upsert_issue_overwrites_summary_on_existing_issue():
    class DummyTracker:
        def __init__(self):
            self.issues = [
                {
                    "id": "#H_AUTO_CIRCUIT_BREAKER",
                    "priority": "P0",
                    "title": "old title",
                    "action": "old action",
                    "status": "open",
                    "summary": {"streak": 47, "current_recent_window_wins": 2},
                }
            ]

        def add(self, priority, issue_id, title, action="", status="open"):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["priority"] = priority
                    issue["title"] = title
                    issue["action"] = action
                    issue["status"] = status
                    return
            self.issues.append(
                {
                    "id": issue_id,
                    "priority": priority,
                    "title": title,
                    "action": action,
                    "status": status,
                }
            )

    tracker = DummyTracker()
    auto_propose_fixes.upsert_issue(
        tracker,
        "P0",
        "#H_AUTO_CIRCUIT_BREAKER",
        "canonical circuit breaker active (0/15 wins in recent 50)",
        "new action",
        summary={"streak": 71, "current_recent_window_wins": 0, "required_recent_window_wins": 15},
    )

    assert tracker.issues[0]["title"] == "canonical circuit breaker active (0/15 wins in recent 50)"
    assert tracker.issues[0]["action"] == "new action"
    assert tracker.issues[0]["summary"] == {
        "streak": 71,
        "current_recent_window_wins": 0,
        "required_recent_window_wins": 15,
    }


def test_load_recent_tw_history_reads_structured_ic_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "heartbeat_657_summary.json").write_text(
        '{"heartbeat":"657","ic_diagnostics":{"tw_pass":10,"total_features":30}}'
    )
    (data_dir / "heartbeat_656_summary.json").write_text(
        '{"heartbeat":"656","parallel_results":{"full_ic":{"stdout_preview":"TW-IC: 12/30 passing"}}}'
    )

    history = auto_propose_fixes.load_recent_tw_history(limit=2)

    assert history[0]["heartbeat"] == "657"
    assert history[0]["tw_pass"] == 10
    assert history[1]["heartbeat"] == "656"
    assert history[1]["tw_pass"] == 12


def test_load_recent_tw_history_prefers_numbered_heartbeats_over_fast_alias(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_propose_fixes, "ROOT", tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "heartbeat_fast_summary.json").write_text(
        '{"heartbeat":"fast","ic_diagnostics":{"tw_pass":12,"total_features":30}}'
    )
    (data_dir / "heartbeat_664_summary.json").write_text(
        '{"heartbeat":"664","ic_diagnostics":{"tw_pass":11,"total_features":30}}'
    )

    history = auto_propose_fixes.load_recent_tw_history(
        limit=2,
        current_entry={"heartbeat": "665", "tw_pass": 12, "total_features": 30},
    )

    assert history[0]["heartbeat"] == "665"
    assert history[1]["heartbeat"] == "664"


def test_summarize_recent_drift_formats_primary_window():
    summary = auto_propose_fixes.summarize_recent_drift(
        {
            "primary_window": {
                "window": "100",
                "alerts": ["regime_concentration", "label_imbalance"],
                "summary": {
                    "win_rate": 0.91,
                    "win_rate_delta_vs_full": 0.2641,
                    "dominant_regime": "chop",
                    "dominant_regime_share": 0.97,
                    "drift_interpretation": "distribution_pathology",
                    "quality_metrics": {
                        "avg_simulated_pnl": 0.0123,
                        "avg_simulated_quality": 0.6123,
                        "avg_drawdown_penalty": 0.1212,
                        "spot_long_win_rate": 0.55,
                    },
                    "feature_diagnostics": {
                        "feature_count": 30,
                        "low_variance_count": 4,
                        "low_distinct_count": 3,
                        "frozen_count": 1,
                        "compressed_count": 3,
                        "expected_static_count": 1,
                        "overlay_only_count": 1,
                        "unexpected_frozen_count": 0,
                        "null_heavy_count": 1,
                        "low_variance_examples": [
                            {"feature": "feat_eye", "std_ratio": 0.02},
                            {"feature": "feat_nose", "std_ratio": 0.05},
                        ],
                        "low_distinct_examples": [
                            {"feature": "feat_eye", "recent_distinct": 1, "baseline_distinct": 50},
                        ],
                        "frozen_examples": [
                            {"feature": "feat_eye", "std_ratio": 0.02, "recent_distinct": 1, "expected_static_reason": "weekend_macro_market_closed"},
                        ],
                        "compressed_examples": [
                            {"feature": "feat_nose", "std_ratio": 0.05, "recent_distinct": 42},
                        ],
                        "expected_static_examples": [
                            {"feature": "feat_eye", "expected_static_reason": "weekend_macro_market_closed"},
                        ],
                        "overlay_only_examples": [
                            {"feature": "feat_claw", "overlay_only_reason": "research_sparse_source"},
                        ],
                        "unexpected_frozen_examples": [],
                        "null_heavy_examples": [
                            {"feature": "feat_claw", "non_null_ratio": 0.42},
                        ],
                    },
                    "target_path_diagnostics": {
                        "tail_target_streak": {
                            "target": 0,
                            "count": 27,
                            "start_timestamp": "2026-04-12 00:00:00",
                            "end_timestamp": "2026-04-13 02:00:00",
                        },
                        "recent_examples": [
                            {"timestamp": "2026-04-13 00:00:00", "target": 0, "regime": "chop", "simulated_pyramid_quality": -0.18},
                            {"timestamp": "2026-04-13 01:00:00", "target": 0, "regime": "chop", "simulated_pyramid_quality": -0.22},
                            {"timestamp": "2026-04-13 02:00:00", "target": 0, "regime": "bear", "simulated_pyramid_quality": -0.31},
                        ],
                    },
                    "reference_window_comparison": {
                        "reference_quality": {
                            "win_rate": 0.98,
                            "avg_simulated_quality": 0.71,
                            "avg_simulated_pnl": 0.021,
                        },
                        "win_rate_delta_vs_reference": -0.07,
                        "avg_simulated_quality_delta_vs_reference": -0.0977,
                        "avg_simulated_pnl_delta_vs_reference": -0.0087,
                        "top_mean_shift_features": [
                            {"feature": "feat_body", "reference_mean": 0.44, "current_mean": -0.12, "delta_vs_baseline_std": 1.8},
                        ],
                        "new_unexpected_compressed_features": ["feat_body"],
                    },
                },
            }
        }
    )

    assert "recent_window=100" in summary
    assert "dominant_regime=chop(97.00%)" in summary
    assert "delta_vs_full=+0.2641" in summary
    assert "interpretation=distribution_pathology" in summary
    assert "avg_pnl=+0.0123" in summary
    assert "feature_diag=variance:4/30, frozen:1, compressed:3, expected_static:1, overlay_only:1, unexpected_frozen:0, distinct:3, null_heavy:1" in summary
    assert "tail_streak=27x0 since 2026-04-12 00:00:00 -> 2026-04-13 02:00:00" in summary
    assert "prev_win_rate=0.98" in summary
    assert "delta_vs_prev=-0.07" in summary
    assert "top_shift_examples=feat_body(0.44→-0.12,Δσ=1.8)" in summary
    assert "new_compressed=feat_body" in summary
    assert "recent_examples=2026-04-13 00:00:00:0:chop:-0.18/2026-04-13 01:00:00:0:chop:-0.22/2026-04-13 02:00:00:0:bear:-0.31" in summary
    assert "frozen_examples=feat_eye(0.02/1)" in summary
    assert "compressed_examples=feat_nose(0.05/42)" in summary
    assert "expected_static_examples=feat_eye[weekend_macro_market_closed]" in summary
    assert "overlay_only_examples=feat_claw[research_sparse_source]" in summary


def test_issue_action_text_falls_back_to_next_actions():
    action = auto_propose_fixes.issue_action_text(
        {
            "id": "P1_current_q35_exact_support",
            "title": "support under minimum",
            "next_actions": [
                "先確認 current live bucket 是否仍是 q35",
                "只追 exact support 是否累積",
            ],
        }
    )

    assert action == "先確認 current live bucket 是否仍是 q35；只追 exact support 是否累積"


def test_main_resolves_stale_issue_when_raw_is_fresh(monkeypatch, capsys):
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id, "resolved"))
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return []

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.577,
        "losing_streak": 0,
        "raw_latest_age_min": 1.3,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 14, "tw_pass": 15, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 14,
        "tw_pass": 15,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_aura", -0.35),
        "worst_ic": ("feat_eye", 0.0),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {})
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.70, "cv_accuracy": 0.72})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    _ = capsys.readouterr().out

    assert ("resolve", "#H_AUTO_STALE", "resolved") in events
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_STALE" for event in events)



def test_main_resolves_regime_drift_when_tw_gap_falls_below_threshold(monkeypatch, capsys):
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id, "resolved"))
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return []

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.577,
        "losing_streak": 0,
        "raw_latest_age_min": 0.9,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 17, "tw_pass": 19, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 17,
        "tw_pass": 19,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_vix", 0.18),
        "worst_ic": ("feat_ear", 0.001),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {})
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.70, "cv_accuracy": 0.72})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    _ = capsys.readouterr().out

    assert ("resolve", "#H_AUTO_REGIME_DRIFT", "resolved") in events
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_REGIME_DRIFT" for event in events)



def test_main_resolves_tw_drift_and_streak_when_current_run_recovers(monkeypatch, capsys):
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id, "resolved"))
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return []

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.5653,
        "losing_streak": 6,
        "raw_latest_age_min": 1.1,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 20, "tw_pass": 27, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 20,
        "tw_pass": 27,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_vix", 0.74),
        "worst_ic": ("feat_ear", 0.0014),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [
        {"heartbeat": "669", "tw_pass": 27, "total_features": 30},
        {"heartbeat": "668", "tw_pass": 12, "total_features": 30},
        {"heartbeat": "667", "tw_pass": 13, "total_features": 30},
    ])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["constant_target"],
            "summary": {
                "win_rate": 0.0,
                "win_rate_delta_vs_full": -0.6263,
                "dominant_regime": "chop",
                "dominant_regime_share": 0.75,
                "drift_interpretation": "distribution_pathology",
                "quality_metrics": {
                    "avg_simulated_pnl": -0.0108,
                    "avg_simulated_quality": -0.2809,
                    "avg_drawdown_penalty": 0.2702,
                    "spot_long_win_rate": 0.0,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.703, "cv_accuracy": 0.722})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    _ = capsys.readouterr().out

    assert ("resolve", "#H_AUTO_TW_DRIFT", "resolved") in events
    assert ("resolve", "#H_AUTO_STREAK", "resolved") in events
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_TW_DRIFT" for event in events)
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_STREAK" for event in events)


def test_main_promotes_recent_distribution_pathology_even_when_tw_ic_recovers(monkeypatch, capsys):
    added = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            added.append((priority, issue_id, title, action, status))

        def resolve(self, issue_id):
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return [
                {
                    "id": issue_id,
                    "priority": prio,
                    "title": title,
                    "action": action,
                    "status": status,
                }
                for prio, issue_id, title, action, status in added
                if prio == priority and status == "open"
            ]

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.5653,
        "losing_streak": 6,
        "raw_latest_age_min": 0.5,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 20, "tw_pass": 27, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 20,
        "tw_pass": 27,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_vix", 0.74),
        "worst_ic": ("feat_ear", 0.0014),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [
        {"heartbeat": "671", "tw_pass": 27, "total_features": 30},
        {"heartbeat": "670", "tw_pass": 27, "total_features": 30},
    ])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["constant_target"],
            "summary": {
                "win_rate": 0.0,
                "win_rate_delta_vs_full": -0.6263,
                "dominant_regime": "chop",
                "dominant_regime_share": 0.75,
                "drift_interpretation": "distribution_pathology",
                "quality_metrics": {
                    "avg_simulated_pnl": -0.0108,
                    "avg_simulated_quality": -0.2809,
                    "avg_drawdown_penalty": 0.2702,
                    "spot_long_win_rate": 0.0,
                },
                "feature_diagnostics": {
                    "feature_count": 49,
                    "low_variance_count": 28,
                    "low_distinct_count": 15,
                    "frozen_count": 5,
                    "compressed_count": 23,
                    "null_heavy_count": 10,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.703, "cv_accuracy": 0.722})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    out = capsys.readouterr().out

    pathology_issue = next(item for item in added if item[1] == "#H_AUTO_RECENT_PATHOLOGY")
    assert pathology_issue[0] == "P0"
    assert "recent canonical window 100 rows = distribution_pathology" in pathology_issue[2]
    assert "feature_diag=variance:28/49, frozen:5, compressed:23, expected_static:0, overlay_only:0, unexpected_frozen:0, distinct:15, null_heavy:10" in pathology_issue[3]
    assert "#H_AUTO_RECENT_PATHOLOGY" in out


def test_main_escalates_tw_drift_on_consecutive_low_history(monkeypatch, capsys):
    added = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            added.append((priority, issue_id, title, action, status))

        def resolve(self, issue_id):
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return [
                {
                    "id": issue_id,
                    "priority": prio,
                    "title": title,
                    "action": action,
                    "status": status,
                }
                for prio, issue_id, title, action, status in added
                if prio == priority and status == "open"
            ]

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.5748,
        "losing_streak": 0,
        "raw_latest_age_min": 0.5,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 13,
        "tw_pass": 10,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_aura", -0.35),
        "worst_ic": ("feat_eye", 0.0),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [
        {"heartbeat": "657", "tw_pass": 10, "total_features": 30},
        {"heartbeat": "656", "tw_pass": 12, "total_features": 30},
    ])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["regime_concentration"],
            "summary": {
                "win_rate": 0.91,
                "win_rate_delta_vs_full": 0.2641,
                "dominant_regime": "chop",
                "dominant_regime_share": 0.97,
                "drift_interpretation": "regime_concentration",
                "quality_metrics": {
                    "avg_simulated_pnl": 0.01,
                    "avg_simulated_quality": 0.55,
                    "avg_drawdown_penalty": 0.12,
                    "spot_long_win_rate": 0.61,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.60, "cv_accuracy": 0.55})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    out = capsys.readouterr().out

    assert any(issue_id == "#H_AUTO_TW_DRIFT" for _, issue_id, *_ in added)
    drift_issue = next(item for item in added if item[1] == "#H_AUTO_TW_DRIFT")
    assert "recent_window=100" in drift_issue[3]
    assert "TW 歷史：#657=10/30, #656=12/30" in out
    assert "dominant_regime=chop(97.00%)" in out


def test_main_tw_drift_uses_supported_extreme_trend_wording(monkeypatch, capsys):
    added = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            added.append((priority, issue_id, title, action, status))

        def resolve(self, issue_id):
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return [
                {
                    "id": issue_id,
                    "priority": prio,
                    "title": title,
                    "action": action,
                    "status": status,
                }
                for prio, issue_id, title, action, status in added
                if prio == priority and status == "open"
            ]

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.577,
        "losing_streak": 0,
        "raw_latest_age_min": 0.5,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 13,
        "tw_pass": 12,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_aura", -0.35),
        "worst_ic": ("feat_eye", 0.0),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [
        {"heartbeat": "668", "tw_pass": 12, "total_features": 30},
        {"heartbeat": "667", "tw_pass": 13, "total_features": 30},
    ])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["constant_target", "regime_concentration"],
            "summary": {
                "win_rate": 1.0,
                "win_rate_delta_vs_full": 0.3538,
                "dominant_regime": "chop",
                "dominant_regime_share": 1.0,
                "drift_interpretation": "supported_extreme_trend",
                "quality_metrics": {
                    "avg_simulated_pnl": 0.0204,
                    "avg_simulated_quality": 0.688,
                    "avg_drawdown_penalty": 0.0296,
                    "spot_long_win_rate": 0.96,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.70, "cv_accuracy": 0.72})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    _ = capsys.readouterr().out

    drift_issue = next(item for item in added if item[1] == "#H_AUTO_TW_DRIFT")
    assert "真實極端趨勢口袋" in drift_issue[3]
    assert "interpretation=supported_extreme_trend" in drift_issue[3]


def test_main_promotes_live_predictor_runtime_pathology(monkeypatch, capsys):
    added = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            added.append((priority, issue_id, title, action, status))

        def resolve(self, issue_id):
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return [
                {
                    "id": issue_id,
                    "priority": prio,
                    "title": title,
                    "action": action,
                    "status": status,
                }
                for prio, issue_id, title, action, status in added
                if prio == priority and status == "open"
            ]

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.5698,
        "losing_streak": 0,
        "raw_latest_age_min": 0.6,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 17, "tw_pass": 19, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 17,
        "tw_pass": 19,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_vix", 0.18),
        "worst_ic": ("feat_ear", 0.001),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["constant_target", "regime_concentration"],
            "summary": {
                "win_rate": 1.0,
                "win_rate_delta_vs_full": 0.3709,
                "dominant_regime": "chop",
                "dominant_regime_share": 1.0,
                "drift_interpretation": "supported_extreme_trend",
                "quality_metrics": {
                    "avg_simulated_pnl": 0.0182,
                    "avg_simulated_quality": 0.6203,
                    "avg_drawdown_penalty": 0.0454,
                    "spot_long_win_rate": 0.57,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "load_live_predict_probe", lambda: {
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "decision_quality_calibration_scope": "entry_quality_label",
        "decision_quality_sample_size": 3186,
        "decision_quality_scope_diagnostics": {
            "regime_gate+entry_quality_label": {
                "rows": 315,
                "win_rate": 0.1429,
                "avg_quality": -0.1491,
                "avg_drawdown_penalty": 0.2612,
                "avg_time_underwater": 0.7321,
                "alerts": ["label_imbalance"],
                "recent500_regime_counts": {"bull": 141, "neutral": 114, "bear": 60},
                "recent500_dominant_regime": {"regime": "bull", "count": 141, "share": 0.4476},
                "recent500_gate_counts": {"ALLOW": 315},
                "recent500_dominant_gate": {"gate": "ALLOW", "count": 315, "share": 1.0},
                "recent500_regime_gate_counts": {"bull|ALLOW": 141, "neutral|ALLOW": 114, "bear|ALLOW": 60},
                "recent500_dominant_regime_gate": {"regime_gate": "bull|ALLOW", "regime": "bull", "gate": "ALLOW", "count": 141, "share": 0.4476},
            },
            "regime_label+entry_quality_label": {
                "rows": 140,
                "win_rate": 0.05,
                "avg_quality": -0.2333,
                "avg_drawdown_penalty": 0.3111,
                "avg_time_underwater": 0.9444,
                "alerts": ["label_imbalance"],
                "recent500_regime_counts": {"bull": 140},
                "recent500_dominant_regime": {"regime": "bull", "count": 140, "share": 1.0},
                "recent500_gate_counts": {"ALLOW": 40, "CAUTION": 100},
                "recent500_dominant_gate": {"gate": "CAUTION", "count": 100, "share": 0.7143},
                "recent500_regime_gate_counts": {"bull|ALLOW": 40, "bull|CAUTION": 100},
                "recent500_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 100, "share": 0.7143},
            },
            "entry_quality_label": {
                "rows": 3186,
                "win_rate": 0.6152,
                "avg_quality": 0.2562,
                "avg_drawdown_penalty": 0.1211,
                "avg_time_underwater": 0.3112,
                "alerts": [],
                "recent500_regime_counts": {"chop": 359, "bull": 141},
                "recent500_dominant_regime": {"regime": "chop", "count": 359, "share": 0.718},
                "recent500_gate_counts": {"CAUTION": 359, "ALLOW": 141},
                "recent500_dominant_gate": {"gate": "CAUTION", "count": 359, "share": 0.718},
                "recent500_regime_gate_counts": {"chop|CAUTION": 359, "bull|ALLOW": 141},
                "recent500_dominant_regime_gate": {"regime_gate": "chop|CAUTION", "regime": "chop", "gate": "CAUTION", "count": 359, "share": 0.718},
            },
            "pathology_consensus": {
                "worst_pathology_scope": {
                    "scope": "regime_label+entry_quality_label",
                    "rows": 140,
                    "win_rate": 0.05,
                    "avg_quality": -0.2333,
                    "avg_drawdown_penalty": 0.3111,
                    "avg_time_underwater": 0.9444,
                    "recent500_regime_counts": {"bull": 140},
                    "recent500_dominant_regime": {"regime": "bull", "count": 140, "share": 1.0},
                    "recent500_gate_counts": {"ALLOW": 40, "CAUTION": 100},
                    "recent500_dominant_gate": {"gate": "CAUTION", "count": 100, "share": 0.7143},
                    "recent500_regime_gate_counts": {"bull|ALLOW": 40, "bull|CAUTION": 100},
                    "recent500_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 100, "share": 0.7143},
                },
                "shared_top_shift_features": [
                    {"feature": "feat_4h_dist_swing_low", "scope_count": 3},
                    {"feature": "feat_4h_dist_bb_lower", "scope_count": 3},
                ],
            },
        },
        "decision_quality_recent_pathology_applied": True,
        "decision_quality_recent_pathology_window": 500,
        "decision_quality_recent_pathology_alerts": ["label_imbalance"],
        "decision_quality_label": "D",
        "expected_win_rate": 0.154,
        "expected_pyramid_pnl": -0.0077,
        "expected_pyramid_quality": -0.1536,
        "allowed_layers_raw": 0,
        "allowed_layers": 0,
        "decision_quality_recent_pathology_summary": {
            "reference_window_comparison": {
                "top_mean_shift_features": [
                    {"feature": "feat_4h_dist_swing_low", "reference_mean": 8.58, "current_mean": 2.0},
                    {"feature": "feat_4h_dist_bb_lower", "reference_mean": 6.89, "current_mean": 1.33},
                ]
            }
        },
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.703, "cv_accuracy": 0.722})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    out = capsys.readouterr().out

    live_issue = next(item for item in added if item[1] == "#H_AUTO_LIVE_DQ_PATHOLOGY")
    assert live_issue[0] == "P1"
    assert "runtime-blocked by recent pathology" in live_issue[2]
    assert "live_scope=entry_quality_label" in live_issue[3]
    assert "top_shifts=feat_4h_dist_swing_low(8.58→2.0)/feat_4h_dist_bb_lower(6.89→1.33)" in live_issue[3]
    assert "scope_matrix=regime_gate+entry_quality_label:rows=315,wr=0.1429,q=-0.1491,dd=0.2612,tuw=0.7321,alerts=['label_imbalance'],recent500_dominant=bull@0.4476,recent500_gate_dominant=ALLOW@1.0,recent500_regime_gate_dominant=bull|ALLOW@0.4476,recent500_regimes=bull:141/neutral:114/bear:60,recent500_gates=ALLOW:315,recent500_regime_gates=bull|ALLOW:141/neutral|ALLOW:114/bear|ALLOW:60" in live_issue[3]
    assert "regime_label+entry_quality_label:rows=140,wr=0.05,q=-0.2333,dd=0.3111,tuw=0.9444,alerts=['label_imbalance'],recent500_dominant=bull@1.0,recent500_gate_dominant=CAUTION@0.7143,recent500_regime_gate_dominant=bull|CAUTION@0.7143,recent500_regimes=bull:140,recent500_gates=CAUTION:100/ALLOW:40,recent500_regime_gates=bull|CAUTION:100/bull|ALLOW:40" in live_issue[3]
    assert "entry_quality_label:rows=3186,wr=0.6152,q=0.2562,dd=0.1211,tuw=0.3112,alerts=[],recent500_dominant=chop@0.718,recent500_gate_dominant=CAUTION@0.718,recent500_regime_gate_dominant=chop|CAUTION@0.718,recent500_regimes=chop:359/bull:141,recent500_gates=CAUTION:359/ALLOW:141,recent500_regime_gates=chop|CAUTION:359/bull|ALLOW:141" in live_issue[3]
    assert "shared_shifts=feat_4h_dist_swing_low[x3]/feat_4h_dist_bb_lower[x3]" in live_issue[3]
    assert "worst_scope=regime_label+entry_quality_label(wr=0.05,q=-0.2333,rows=140,dd=0.3111,tuw=0.9444,recent500_dominant=bull@1.0,recent500_gate_dominant=CAUTION@0.7143,recent500_regime_gate_dominant=bull|CAUTION@0.7143,recent500_regimes=bull:140,recent500_gates=CAUTION:100/ALLOW:40,recent500_regime_gates=bull|CAUTION:100/bull|ALLOW:40)" in live_issue[3]
    assert "#H_AUTO_LIVE_DQ_PATHOLOGY" in out
    assert "📊 Live probe：live_scope=entry_quality_label" in out


def test_main_promotes_live_dq_pathology_from_narrowed_scope_even_when_broad_scope_is_healthy(monkeypatch, capsys):
    added = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            added.append((priority, issue_id, title, action, status))

        def resolve(self, issue_id):
            return True

        def save(self):
            return None

        def by_priority(self, priority):
            return [
                {
                    "id": issue_id,
                    "priority": prio,
                    "title": title,
                    "action": action,
                    "status": status,
                }
                for prio, issue_id, title, action, status in added
                if prio == priority and status == "open"
            ]

    monkeypatch.setattr(auto_propose_fixes, "check_db", lambda: {
        "simulated_win_avg": 0.5702,
        "losing_streak": 0,
        "raw_latest_age_min": 0.7,
    })
    monkeypatch.setattr(auto_propose_fixes, "load_full_ic_data", lambda: {"global_pass": 17, "tw_pass": 22, "total_features": 30})
    monkeypatch.setattr(auto_propose_fixes, "check_ic", lambda ic_data, full_ic_data=None: {
        "global_pass": 17,
        "tw_pass": 22,
        "total_core": 15,
        "total_features": 30,
        "no_data": [],
        "low_data": [],
        "best_ic": ("feat_vwap_dev", -0.18),
        "worst_ic": ("feat_ear", 0.001),
    })
    monkeypatch.setattr(auto_propose_fixes, "load_recent_tw_history", lambda limit=3, current_entry=None: [
        {"heartbeat": "696", "tw_pass": 22, "total_features": 30},
        {"heartbeat": "695", "tw_pass": 22, "total_features": 30},
        {"heartbeat": "694", "tw_pass": 20, "total_features": 30},
    ])
    monkeypatch.setattr(auto_propose_fixes, "load_recent_drift_report", lambda: {
        "primary_window": {
            "window": "100",
            "alerts": ["constant_target", "regime_concentration"],
            "summary": {
                "win_rate": 1.0,
                "win_rate_delta_vs_full": 0.3708,
                "dominant_regime": "chop",
                "dominant_regime_share": 1.0,
                "drift_interpretation": "supported_extreme_trend",
                "quality_metrics": {
                    "avg_simulated_pnl": 0.0184,
                    "avg_simulated_quality": 0.6220,
                    "avg_drawdown_penalty": 0.0476,
                    "spot_long_win_rate": 0.59,
                },
            },
        }
    })
    monkeypatch.setattr(auto_propose_fixes, "load_live_predict_probe", lambda: {
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "decision_quality_calibration_scope": "entry_quality_label",
        "decision_quality_sample_size": 3610,
        "decision_quality_scope_diagnostics": {
            "regime_gate+entry_quality_label": {
                "rows": 272,
                "win_rate": 0.1728,
                "avg_quality": -0.1385,
                "avg_drawdown_penalty": 0.2422,
                "avg_time_underwater": 0.7011,
                "alerts": ["label_imbalance"],
                "recent500_regime_counts": {"bull": 134, "neutral": 102, "bear": 36},
                "recent500_dominant_regime": {"regime": "bull", "count": 134, "share": 0.4926},
                "recent500_gate_counts": {"ALLOW": 272},
                "recent500_dominant_gate": {"gate": "ALLOW", "count": 272, "share": 1.0},
                "recent500_regime_gate_counts": {"bull|ALLOW": 134, "neutral|ALLOW": 102, "bear|ALLOW": 36},
                "recent500_dominant_regime_gate": {"regime_gate": "bull|ALLOW", "regime": "bull", "gate": "ALLOW", "count": 134, "share": 0.4926},
                "spillover_vs_exact_live_lane": {
                    "extra_rows": 248,
                    "extra_row_share": 0.9118,
                    "extra_gate_counts": {"ALLOW": 248},
                    "extra_dominant_gate": {"gate": "ALLOW", "count": 248, "share": 1.0},
                    "extra_regime_gate_counts": {"neutral|ALLOW": 102, "bear|ALLOW": 36, "bull|ALLOW": 110},
                    "extra_dominant_regime_gate": {"regime_gate": "bull|ALLOW", "regime": "bull", "gate": "ALLOW", "count": 110, "share": 0.4435},
                    "worst_extra_regime_gate": {"regime_gate": "neutral|ALLOW", "regime": "neutral", "gate": "ALLOW", "rows": 102, "win_rate": 0.08, "avg_pnl": -0.0046, "avg_quality": -0.1821, "avg_drawdown_penalty": 0.2611, "avg_time_underwater": 0.7444},
                    "win_rate_delta_vs_exact": -0.1189,
                    "avg_pnl_delta_vs_exact": -0.0034,
                    "avg_quality_delta_vs_exact": -0.1335,
                },
            },
            "regime_label+entry_quality_label": {
                "rows": 147,
                "win_rate": 0.0748,
                "avg_quality": -0.2098,
                "avg_drawdown_penalty": 0.2877,
                "avg_time_underwater": 0.8811,
                "alerts": ["label_imbalance"],
                "recent500_regime_counts": {"bull": 147},
                "recent500_dominant_regime": {"regime": "bull", "count": 147, "share": 1.0},
                "recent500_gate_counts": {"CAUTION": 123, "ALLOW": 24},
                "recent500_dominant_gate": {"gate": "CAUTION", "count": 123, "share": 0.8367},
                "recent500_regime_gate_counts": {"bull|CAUTION": 123, "bull|ALLOW": 24},
                "recent500_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 123, "share": 0.8367},
                "spillover_vs_exact_live_lane": {
                    "extra_rows": 123,
                    "extra_row_share": 0.8367,
                    "extra_gate_counts": {"CAUTION": 123},
                    "extra_dominant_gate": {"gate": "CAUTION", "count": 123, "share": 1.0},
                    "extra_regime_gate_counts": {"bull|CAUTION": 123},
                    "extra_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 123, "share": 1.0},
                    "worst_extra_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "rows": 123, "win_rate": 0.0, "avg_pnl": -0.0112, "avg_quality": -0.3011, "avg_drawdown_penalty": 0.3122, "avg_time_underwater": 0.9555},
                    "worst_extra_regime_gate_feature_contrast": {
                        "top_mean_shift_features": [
                            {"feature": "feat_4h_bias200", "reference_mean": 2.4, "current_mean": 0.9, "mean_delta": -1.5},
                            {"feature": "feat_4h_dist_bb_lower", "reference_mean": 7.4, "current_mean": 0.4, "mean_delta": -7.0},
                            {"feature": "feat_4h_dist_swing_low", "reference_mean": 9.3, "current_mean": 1.7, "mean_delta": -7.6},
                            {"feature": "feat_4h_bb_pct_b", "reference_mean": 0.87, "current_mean": 0.13, "mean_delta": -0.74},
                        ]
                    },
                    "worst_extra_regime_gate_feature_snapshot": {
                        "feat_4h_bias200": {"reference_mean": 2.4, "current_mean": 0.9, "mean_delta": -1.5},
                        "feat_4h_bb_pct_b": {"reference_mean": 0.87, "current_mean": 0.13, "mean_delta": -0.74},
                        "feat_4h_dist_bb_lower": {"reference_mean": 7.4, "current_mean": 0.4, "mean_delta": -7.0},
                        "feat_4h_dist_swing_low": {"reference_mean": 9.3, "current_mean": 1.7, "mean_delta": -7.6}
                    },
                    "worst_extra_regime_gate_path_summary": {
                        "rows": 123,
                        "final_gate_counts": {"CAUTION": 123},
                        "final_reason_counts": {"structure_quality_caution": 123},
                        "base_gate_counts": {"ALLOW": 123},
                        "avg_structure_quality": 0.2214,
                        "structure_quality_distribution": {"min": 0.2214, "p25": 0.2214, "p50": 0.2214, "p75": 0.2214, "max": 0.2214},
                        "structure_quality_gate_bands": {"block_lt_0.15": 0, "caution_0.15_to_0.35": 123, "allow_ge_0.35": 0},
                        "avg_bias200": 0.9,
                        "target_counts": {"loss": 123},
                        "pnl_sign_counts": {"positive": 0, "zero": 0, "negative": 123},
                        "quality_sign_counts": {"positive": 0, "zero": 0, "negative": 123},
                        "canonical_true_negative_rows": 123,
                        "canonical_true_negative_share": 1.0,
                        "missing_input_rows": 0,
                        "missing_input_feature_counts": {},
                    },
                    "exact_live_gate_path_summary": {
                        "rows": 24,
                        "final_gate_counts": {"ALLOW": 24},
                        "final_reason_counts": {"base_allow": 24},
                        "base_gate_counts": {"ALLOW": 24},
                        "avg_structure_quality": 0.8125,
                        "structure_quality_distribution": {"min": 0.8125, "p25": 0.8125, "p50": 0.8125, "p75": 0.8125, "max": 0.8125},
                        "structure_quality_gate_bands": {"block_lt_0.15": 0, "caution_0.15_to_0.35": 0, "allow_ge_0.35": 24},
                        "avg_bias200": 2.4,
                        "target_counts": {"win": 24},
                        "pnl_sign_counts": {"positive": 24, "zero": 0, "negative": 0},
                        "quality_sign_counts": {"positive": 24, "zero": 0, "negative": 0},
                        "canonical_true_negative_rows": 0,
                        "canonical_true_negative_share": 0.0,
                        "missing_input_rows": 0,
                        "missing_input_feature_counts": {},
                    },
                    "win_rate_delta_vs_exact": -0.5709,
                    "avg_pnl_delta_vs_exact": -0.0098,
                    "avg_quality_delta_vs_exact": -0.5003,
                },
            },
            "entry_quality_label": {
                "rows": 3610,
                "win_rate": 0.6457,
                "avg_quality": 0.2905,
                "avg_drawdown_penalty": 0.1181,
                "avg_time_underwater": 0.2994,
                "alerts": [],
                "recent500_regime_counts": {"chop": 390, "bull": 110},
                "recent500_dominant_regime": {"regime": "chop", "count": 390, "share": 0.78},
                "recent500_gate_counts": {"CAUTION": 390, "ALLOW": 110},
                "recent500_dominant_gate": {"gate": "CAUTION", "count": 390, "share": 0.78},
                "recent500_regime_gate_counts": {"chop|CAUTION": 390, "bull|ALLOW": 110},
                "recent500_dominant_regime_gate": {"regime_gate": "chop|CAUTION", "regime": "chop", "gate": "CAUTION", "count": 390, "share": 0.78},
            },
            "pathology_consensus": {
                "worst_pathology_scope": {
                    "scope": "regime_label+entry_quality_label",
                    "rows": 147,
                    "win_rate": 0.0748,
                    "avg_quality": -0.2098,
                    "avg_drawdown_penalty": 0.2877,
                    "avg_time_underwater": 0.8811,
                    "recent500_regime_counts": {"bull": 147},
                    "recent500_dominant_regime": {"regime": "bull", "count": 147, "share": 1.0},
                    "recent500_gate_counts": {"CAUTION": 123, "ALLOW": 24},
                    "recent500_dominant_gate": {"gate": "CAUTION", "count": 123, "share": 0.8367},
                    "recent500_regime_gate_counts": {"bull|CAUTION": 123, "bull|ALLOW": 24},
                    "recent500_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 123, "share": 0.8367},
                    "spillover_vs_exact_live_lane": {
                        "extra_rows": 123,
                        "extra_row_share": 0.8367,
                        "extra_gate_counts": {"CAUTION": 123},
                        "extra_dominant_gate": {"gate": "CAUTION", "count": 123, "share": 1.0},
                        "extra_regime_gate_counts": {"bull|CAUTION": 123},
                        "extra_dominant_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "count": 123, "share": 1.0},
                        "worst_extra_regime_gate": {"regime_gate": "bull|CAUTION", "regime": "bull", "gate": "CAUTION", "rows": 123, "win_rate": 0.0, "avg_pnl": -0.0112, "avg_quality": -0.3011, "avg_drawdown_penalty": 0.3122, "avg_time_underwater": 0.9555},
                        "worst_extra_regime_gate_feature_contrast": {
                            "top_mean_shift_features": [
                                {"feature": "feat_4h_bias200", "reference_mean": 2.4, "current_mean": 0.9, "mean_delta": -1.5},
                                {"feature": "feat_4h_dist_bb_lower", "reference_mean": 7.4, "current_mean": 0.4, "mean_delta": -7.0},
                                {"feature": "feat_4h_dist_swing_low", "reference_mean": 9.3, "current_mean": 1.7, "mean_delta": -7.6},
                                {"feature": "feat_4h_bb_pct_b", "reference_mean": 0.87, "current_mean": 0.13, "mean_delta": -0.74},
                            ]
                        },
                        "worst_extra_regime_gate_feature_snapshot": {
                            "feat_4h_bias200": {"reference_mean": 2.4, "current_mean": 0.9, "mean_delta": -1.5},
                            "feat_4h_bb_pct_b": {"reference_mean": 0.87, "current_mean": 0.13, "mean_delta": -0.74},
                            "feat_4h_dist_bb_lower": {"reference_mean": 7.4, "current_mean": 0.4, "mean_delta": -7.0},
                            "feat_4h_dist_swing_low": {"reference_mean": 9.3, "current_mean": 1.7, "mean_delta": -7.6}
                        },
                        "worst_extra_regime_gate_path_summary": {
                            "rows": 123,
                            "final_gate_counts": {"CAUTION": 123},
                            "final_reason_counts": {"structure_quality_caution": 123},
                            "base_gate_counts": {"ALLOW": 123},
                            "avg_structure_quality": 0.2214,
                            "structure_quality_distribution": {"min": 0.2214, "p25": 0.2214, "p50": 0.2214, "p75": 0.2214, "max": 0.2214},
                            "structure_quality_gate_bands": {"block_lt_0.15": 0, "caution_0.15_to_0.35": 123, "allow_ge_0.35": 0},
                            "avg_bias200": 0.9,
                            "missing_input_rows": 0,
                            "missing_input_feature_counts": {},
                        },
                        "exact_live_gate_path_summary": {
                            "rows": 24,
                            "final_gate_counts": {"ALLOW": 24},
                            "final_reason_counts": {"base_allow": 24},
                            "base_gate_counts": {"ALLOW": 24},
                            "avg_structure_quality": 0.8125,
                            "structure_quality_distribution": {"min": 0.8125, "p25": 0.8125, "p50": 0.8125, "p75": 0.8125, "max": 0.8125},
                            "structure_quality_gate_bands": {"block_lt_0.15": 0, "caution_0.15_to_0.35": 0, "allow_ge_0.35": 24},
                            "avg_bias200": 2.4,
                            "missing_input_rows": 0,
                            "missing_input_feature_counts": {},
                        },
                        "win_rate_delta_vs_exact": -0.5709,
                        "avg_pnl_delta_vs_exact": -0.0098,
                        "avg_quality_delta_vs_exact": -0.5003,
                    },
                },
                "shared_top_shift_features": [
                    {"feature": "feat_4h_dist_swing_low", "scope_count": 2},
                    {"feature": "feat_4h_dist_bb_lower", "scope_count": 2},
                ],
            },
        },
        "decision_quality_recent_pathology_applied": False,
        "decision_quality_recent_pathology_window": 100,
        "decision_quality_recent_pathology_alerts": [],
        "decision_quality_label": "D",
        "expected_win_rate": 0.6457,
        "expected_pyramid_pnl": 0.0084,
        "expected_pyramid_quality": 0.2905,
        "allowed_layers_raw": 0,
        "allowed_layers": 0,
        "decision_quality_recent_pathology_summary": {},
    })
    monkeypatch.setattr(auto_propose_fixes, "check_metrics", lambda: {"train_accuracy": 0.703, "cv_accuracy": 0.722})
    monkeypatch.setattr(auto_propose_fixes, "IssueTracker", type("IssueTrackerProxy", (), {"load": staticmethod(lambda: DummyTracker())}))

    auto_propose_fixes.main()
    out = capsys.readouterr().out

    live_issue = next(item for item in added if item[1] == "#H_AUTO_LIVE_DQ_PATHOLOGY")
    assert live_issue[0] == "P1"
    assert "runtime-blocked by recent pathology, a toxic exact live lane, or a severe narrowed pathology lane" in live_issue[2]
    assert "live_scope=entry_quality_label" in live_issue[3]
    assert "shared_shifts=feat_4h_dist_swing_low[x2]/feat_4h_dist_bb_lower[x2]" in live_issue[3]
    assert "spillover_rows=123" in live_issue[3]
    assert "spillover_regime_gate_dominant=bull|CAUTION@1.0" in live_issue[3]
    assert "spillover_regime_gates=bull|CAUTION:123" in live_issue[3]
    assert "spillover_worst=bull|CAUTION(rows=123,wr=0.0,q=-0.3011,pnl=-0.0112,dd=0.3122,tuw=0.9555)" in live_issue[3]
    assert "spillover_feature_shift=feat_4h_bias200(2.4→0.9,Δ=-1.5)/feat_4h_dist_bb_lower(7.4→0.4,Δ=-7.0)/feat_4h_dist_swing_low(9.3→1.7,Δ=-7.6)/feat_4h_bb_pct_b(0.87→0.13,Δ=-0.74)" in live_issue[3]
    assert "spillover_gate_inputs=feat_4h_bias200(2.4→0.9,Δ=-1.5)/feat_4h_bb_pct_b(0.87→0.13,Δ=-0.74)/feat_4h_dist_bb_lower(7.4→0.4,Δ=-7.0)/feat_4h_dist_swing_low(9.3→1.7,Δ=-7.6)" in live_issue[3]
    assert "spillover_gate_path=final[CAUTION:123]|reason[structure_quality_caution:123]|base[ALLOW:123]|avg_structure=0.2214|structure_q[min:0.2214,p25:0.2214,p50:0.2214,p75:0.2214,max:0.2214]|structure_bands[block:0,caution:123,allow:0]|targets[loss:123]|pnl_signs[negative:123/positive:0/zero:0]|quality_signs[negative:123/positive:0/zero:0]|true_negative_rows=123@1.0|avg_bias200=0.9|missing_rows=0" in live_issue[3]
    assert "exact_gate_path=final[ALLOW:24]|reason[base_allow:24]|base[ALLOW:24]|avg_structure=0.8125|structure_q[min:0.8125,p25:0.8125,p50:0.8125,p75:0.8125,max:0.8125]|structure_bands[block:0,caution:0,allow:24]|targets[win:24]|pnl_signs[negative:0/positive:24/zero:0]|quality_signs[negative:0/positive:24/zero:0]|true_negative_rows=0@0.0|avg_bias200=2.4|missing_rows=0" in live_issue[3]
    assert "worst_scope=regime_label+entry_quality_label(wr=0.0748,q=-0.2098,rows=147,dd=0.2877,tuw=0.8811,recent500_dominant=bull@1.0,recent500_gate_dominant=CAUTION@0.8367,recent500_regime_gate_dominant=bull|CAUTION@0.8367,recent500_regimes=bull:147,recent500_gates=CAUTION:123/ALLOW:24,recent500_regime_gates=bull|CAUTION:123/bull|ALLOW:24,spillover_rows=123,spillover_share=0.8367,spillover_wr_delta=-0.5709,spillover_q_delta=-0.5003,spillover_pnl_delta=-0.0098,spillover_gate_dominant=CAUTION@1." in live_issue[3]

    assert "#H_AUTO_LIVE_DQ_PATHOLOGY" in out
    assert "📊 Live probe：live_scope=entry_quality_label" in out


def test_summarize_live_predict_probe_flags_toxic_exact_live_lane():
    summary = auto_propose_fixes.summarize_live_predict_probe({
        "decision_quality_calibration_scope": "regime_gate+entry_quality_label",
        "decision_quality_label": "D",
        "decision_quality_recent_pathology_window": 100,
        "decision_quality_recent_pathology_alerts": ["label_imbalance"],
        "expected_win_rate": 0.0,
        "expected_pyramid_pnl": -0.0108,
        "expected_pyramid_quality": -0.2789,
        "allowed_layers_raw": 0,
        "allowed_layers": 0,
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "decision_quality_sample_size": 127,
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "rows": 24,
                "win_rate": 0.2917,
                "avg_quality": -0.005,
                "avg_drawdown_penalty": 0.2986,
                "avg_time_underwater": 0.6147,
                "recent500_dominant_regime_gate": {"regime_gate": "bull|ALLOW", "share": 1.0},
                "spillover_vs_exact_live_lane": {
                    "exact_live_gate_path_summary": {
                        "target_counts": {"loss": 17, "win": 7},
                        "canonical_true_negative_rows": 17,
                        "canonical_true_negative_share": 0.7083,
                        "final_gate_counts": {"ALLOW": 24},
                    }
                },
            }
        },
        "decision_quality_recent_pathology_summary": {},
    })

    assert "exact_live_lane=(rows=24,wr=0.2917,q=-0.005,dd=0.2986,tuw=0.6147,recent500_dom=bull|ALLOW@1.0,targets=loss:17/win:7,true_negative_rows=17@0.7083,final_gate=ALLOW:24)" in summary
    assert "exact_lane_status=toxic_allow_lane" in summary


def test_sync_current_state_governance_issues_replaces_stale_q35_support_issue():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 2,
                    "support_progress": {
                        "current_rows": 2,
                        "minimum_support_rows": 50,
                        "history": [
                            {
                                "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15"
                            }
                        ],
                    },
                },
            }
        },
        {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 2,
            "allowed_layers_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    assert ("resolve", "P1_q35_exact_support_under_minimum") in events
    assert ("resolve", "P1_current_q35_exact_support") in events
    assert ("resolve", "P1_q35_redesign_support_blocked") in events
    support_add = next(event for event in events if event[0] == "add" and event[1] == "#H_AUTO_CURRENT_BUCKET_SUPPORT")
    assert "q15" in support_add[2]
    assert "2/50" in support_add[2]


def test_sync_current_state_governance_issues_uses_live_probe_bucket_when_alignment_snapshot_is_stale():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 0,
                    "support_progress": {
                        "current_rows": 0,
                        "minimum_support_rows": 50,
                        "history": [
                            {
                                "live_current_structure_bucket": None,
                            }
                        ],
                    },
                },
            }
        },
        {
            "current_live_structure_bucket": "ALLOW|base_allow|q65",
            "current_live_structure_bucket_rows": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade",
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    support_add = next(event for event in events if event[0] == "add" and event[1] == "#H_AUTO_CURRENT_BUCKET_SUPPORT")
    assert "ALLOW|base_allow|q65" in support_add[2]
    assert "0/50" in support_add[2]
    assert ("resolve", "P1_current_q35_exact_support") in events
    assert ("resolve", "P1_q35_redesign_support_blocked") in events


def test_sync_current_state_governance_issues_prefers_live_supported_bucket_over_stale_proxy_route():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 0,
                    "support_progress": {
                        "current_rows": 0,
                        "minimum_support_rows": 50,
                        "history": [
                            {
                                "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                            }
                        ],
                    },
                },
            }
        },
        {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 139,
            "allowed_layers_reason": "decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade",
            "execution_guardrail_reason": "decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade",
            "deployment_blocker": "exact_live_lane_toxic_sub_bucket_current_bucket",
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    assert ("resolve", "#H_AUTO_CURRENT_BUCKET_SUPPORT") in events
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_CURRENT_BUCKET_SUPPORT" for event in events)
    toxic_add = next(event for event in events if event[0] == "add" and event[1] == "#H_AUTO_CURRENT_BUCKET_TOXICITY")
    assert "CAUTION|structure_quality_caution|q35" in toxic_add[2]
    assert "139 rows" in toxic_add[2]


def test_sync_current_state_governance_issues_refreshes_leaderboard_recent_window_issue_summary():
    class DummyTracker:
        def __init__(self):
            self.issues = [
                {
                    "id": "P1_leaderboard_recent_window_contract",
                    "priority": "P1",
                    "title": "leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe",
                    "action": "old action",
                    "status": "open",
                    "summary": {
                        "leaderboard_count": 1,
                        "comparable_count": 1,
                        "placeholder_count": 0,
                        "top_model": "rule_baseline",
                        "top_profile": "current_full",
                    },
                }
            ]

        def add(self, priority, issue_id, title, action="", status="open"):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["priority"] = priority
                    issue["title"] = title
                    issue["action"] = action
                    issue["status"] = status
                    return
            self.issues.append(
                {
                    "id": issue_id,
                    "priority": priority,
                    "title": title,
                    "action": action,
                    "status": status,
                }
            )

        def resolve(self, issue_id):
            return True

    tracker = DummyTracker()
    auto_propose_fixes.sync_current_state_governance_issues(
        tracker,
        {
            "leaderboard_count": 6,
            "top_model": {
                "model_name": "random_forest",
                "selected_feature_profile": "core_only",
                "selected_deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
            },
            "leaderboard_current_state": {
                "comparable_count": 6,
                "placeholder_count": 0,
            },
            "alignment": {
                "current_alignment_inputs_stale": False,
                "leaderboard_selected_profile": "core_only",
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "verdict": "dual_role_governance_active",
                    "current_closure": "global_ranking_vs_support_aware_production_split",
                    "production_profile": "core_plus_macro",
                },
            },
        },
        {},
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    issue = next(issue for issue in tracker.issues if issue["id"] == "P1_leaderboard_recent_window_contract")
    assert issue["summary"]["leaderboard_count"] == 6
    assert issue["summary"]["comparable_count"] == 6
    assert issue["summary"]["placeholder_count"] == 0
    assert issue["summary"]["top_model"] == "random_forest"
    assert issue["summary"]["top_profile"] == "core_only"
    assert issue["summary"]["top_deployment_profile"] == "stable_turning_point_all_regimes_relaxed_v1"
    assert issue["summary"]["governance_contract"] == "dual_role_governance_active"


def test_sync_current_state_governance_issues_reads_comparable_rows_from_top_model_probe_shape():
    class DummyTracker:
        def __init__(self):
            self.issues = [
                {
                    "id": "P1_leaderboard_recent_window_contract",
                    "priority": "P1",
                    "title": "leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe",
                    "action": "old action",
                    "status": "open",
                    "summary": {},
                }
            ]

        def add(self, priority, issue_id, title, action="", status="open"):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["priority"] = priority
                    issue["title"] = title
                    issue["action"] = action
                    issue["status"] = status
                    return
            self.issues.append(
                {
                    "id": issue_id,
                    "priority": priority,
                    "title": title,
                    "action": action,
                    "status": status,
                }
            )

        def resolve(self, issue_id):
            return True

    tracker = DummyTracker()
    auto_propose_fixes.sync_current_state_governance_issues(
        tracker,
        {
            "leaderboard_count": 6,
            "top_model": {
                "model_name": "random_forest",
                "selected_feature_profile": "core_only",
                "selected_deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
                "comparable_count": 6,
                "placeholder_count": 0,
            },
            "alignment": {
                "current_alignment_inputs_stale": False,
                "leaderboard_selected_profile": "core_only",
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "verdict": "dual_role_governance_active",
                    "current_closure": "global_ranking_vs_support_aware_production_split",
                    "production_profile": "core_plus_macro",
                },
            },
        },
        {},
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    issue = next(issue for issue in tracker.issues if issue["id"] == "P1_leaderboard_recent_window_contract")
    assert issue["title"] == "leaderboard comparable rows are back; keep the recent-window contract stable and cron-safe"
    assert issue["summary"]["comparable_count"] == 6
    assert issue["summary"]["placeholder_count"] == 0


def test_sync_current_state_governance_issues_resolves_stale_q15_issue_when_circuit_breaker_is_active():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "support_governance_route": "exact_live_bucket_supported",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 95,
                    "support_progress": {
                        "current_rows": 95,
                        "minimum_support_rows": 50,
                        "history": [
                            {
                                "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15"
                            }
                        ],
                    },
                },
            }
        },
        {
            "signal": "CIRCUIT_BREAKER",
            "current_live_structure_bucket": None,
            "current_live_structure_bucket_rows": None,
            "runtime_closure_state": "circuit_breaker_active",
            "deployment_blocker": "circuit_breaker_active",
            "deployment_blocker_details": {
                "release_condition": {
                    "current_recent_window_wins": 5,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 10,
                    "recent_window": 50,
                    "streak_must_be_below": 50,
                }
            },
            "allowed_layers_reason": "circuit_breaker_blocks_trade",
            "execution_guardrail_reason": "circuit_breaker_blocks_trade",
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    assert ("resolve", "P0_q15_patch_active_but_execution_blocked") in events
    assert ("resolve", "#H_AUTO_CURRENT_BUCKET_SUPPORT") in events
    breaker_add = next(event for event in events if event[0] == "add" and event[1] == "#H_AUTO_CIRCUIT_BREAKER")
    assert "5/15" in breaker_add[2]
    assert "recent 50" in breaker_add[2]
    assert "還差 10 勝" in breaker_add[3]
    assert not any(event[0] == "add" and event[1] == "#H_AUTO_CURRENT_BUCKET_SUPPORT" for event in events)


def test_sync_current_state_governance_issues_refreshes_canonical_q15_and_patch_issues_from_live_probe():
    class DummyTracker:
        def __init__(self):
            self.issues = [
                {
                    "id": "P1_q15_exact_support_stalled_under_breaker",
                    "priority": "P1",
                    "title": "q15 exact support remains 0/50 and stalled under breaker",
                    "action": "old q15 action",
                    "status": "open",
                    "summary": {
                        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                        "live_current_structure_bucket_rows": 0,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 50,
                        "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
                    },
                },
                {
                    "id": "P1_reference_only_patch_visibility",
                    "priority": "P1",
                    "title": "legacy reference-only patch visibility issue",
                    "action": "legacy patch action",
                    "status": "open",
                    "summary": {
                        "recommended_patch": "core_plus_macro",
                        "recommended_patch_status": "reference_only_until_exact_support_ready",
                    },
                },
                {
                    "id": "P1_bull_caution_spillover_patch_reference_only",
                    "priority": "P1",
                    "title": "bull|CAUTION spillover patch is productized, but must remain reference-only until exact support recovers",
                    "action": "old patch action",
                    "status": "open",
                    "summary": {
                        "recommended_patch": "core_plus_macro",
                        "recommended_patch_status": "reference_only_until_exact_support_ready",
                        "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
                        "gap_to_minimum": 50,
                    },
                },
            ]

        def add(self, priority, issue_id, title, action="", status="open"):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["priority"] = priority
                    issue["title"] = title
                    issue["action"] = action
                    issue["status"] = status
                    return
            self.issues.append(
                {
                    "id": issue_id,
                    "priority": priority,
                    "title": title,
                    "action": action,
                    "status": status,
                }
            )

        def resolve(self, issue_id):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["status"] = "resolved"
            return True

    tracker = DummyTracker()
    auto_propose_fixes.sync_current_state_governance_issues(
        tracker,
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "selected_feature_profile": "core_only",
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "verdict": "dual_role_governance_active",
                    "production_profile": "core_plus_macro",
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 1,
                    "support_progress": {
                        "current_rows": 1,
                        "minimum_support_rows": 50,
                        "status": "present_but_below_minimum",
                        "history": [
                            {
                                "live_current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15"
                            }
                        ],
                    },
                },
            }
        },
        {
            "signal": "CIRCUIT_BREAKER",
            "deployment_blocker": "circuit_breaker_active",
            "runtime_closure_state": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket_rows": 1,
            "minimum_support_rows": 50,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "decision_quality_scope_pathology_summary": {
                "spillover": {
                    "worst_extra_regime_gate": {
                        "regime_gate": "bull|BLOCK",
                    }
                },
                "exact_live_lane": {
                    "rows": 199,
                },
                "recommended_patch": {
                    "status": "reference_only_until_exact_support_ready",
                    "recommended_profile": "core_plus_macro",
                    "spillover_regime_gate": "bull|BLOCK",
                    "reference_patch_scope": "bull|CAUTION",
                    "support_route_verdict": "exact_bucket_present_but_below_minimum",
                    "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                    "current_live_structure_bucket_rows": 1,
                    "minimum_support_rows": 50,
                    "gap_to_minimum": 49,
                    "reference_source": "bull_4h_pocket_ablation.bull_collapse_q35",
                    "collapse_features": [
                        "feat_4h_dist_swing_low",
                        "feat_4h_dist_bb_lower",
                        "feat_4h_bb_pct_b",
                    ],
                },
            },
            "deployment_blocker_details": {
                "release_condition": {
                    "current_recent_window_wins": 0,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 15,
                    "recent_window": 50,
                    "streak_must_be_below": 50,
                }
            },
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    q15_issue = next(issue for issue in tracker.issues if issue["id"] == "P1_q15_exact_support_stalled_under_breaker")
    assert q15_issue["status"] == "open"
    assert "1/50" in q15_issue["title"]
    assert q15_issue["summary"]["live_current_structure_bucket_rows"] == 1
    assert q15_issue["summary"]["gap_to_minimum"] == 49
    assert q15_issue["summary"]["support_route_verdict"] == "exact_bucket_present_but_below_minimum"
    assert q15_issue["summary"]["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert q15_issue["summary"]["leaderboard_selected_profile"] == "core_only"
    assert q15_issue["summary"]["train_selected_profile"] == "core_plus_macro"
    assert q15_issue["summary"]["governance_contract"] == "dual_role_governance_active"

    patch_issue = next(issue for issue in tracker.issues if issue["id"] == "P1_bull_caution_spillover_patch_reference_only")
    assert patch_issue["status"] == "open"
    assert patch_issue["title"] == "support-aware core_plus_macro patch must stay visible but reference-only"
    assert patch_issue["summary"]["actual_live_spillover_scope"] == "bull|BLOCK"
    assert patch_issue["summary"]["reference_patch_scope"] == "bull|CAUTION"
    assert patch_issue["summary"]["current_live_structure_bucket_rows"] == 1
    assert patch_issue["summary"]["gap_to_minimum"] == 49
    assert patch_issue["summary"]["reference_source"] == "bull_4h_pocket_ablation.bull_collapse_q35"
    assert patch_issue["summary"]["collapse_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
        "feat_4h_bb_pct_b",
    ]

    legacy_patch_issue = next(issue for issue in tracker.issues if issue["id"] == "P1_reference_only_patch_visibility")
    assert legacy_patch_issue["status"] == "resolved"


def test_sync_current_state_governance_issues_prefers_live_support_route_and_refreshes_breaker_context():
    class DummyTracker:
        def __init__(self):
            self.issues = [
                {
                    "id": "P1_q15_exact_support_stalled_under_breaker",
                    "priority": "P1",
                    "title": "old q15 support title",
                    "action": "old q15 action",
                    "status": "open",
                    "summary": {
                        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                        "live_current_structure_bucket_rows": 1,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 49,
                        "support_route_verdict": "exact_bucket_present_but_below_minimum",
                    },
                }
            ]

        def add(self, priority, issue_id, title, action="", status="open"):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["priority"] = priority
                    issue["title"] = title
                    issue["action"] = action
                    issue["status"] = status
                    return
            self.issues.append(
                {
                    "id": issue_id,
                    "priority": priority,
                    "title": title,
                    "action": action,
                    "status": status,
                }
            )

        def resolve(self, issue_id):
            for issue in self.issues:
                if issue["id"] == issue_id:
                    issue["status"] = "resolved"
            return True

    tracker = DummyTracker()
    auto_propose_fixes.sync_current_state_governance_issues(
        tracker,
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "selected_feature_profile": "core_only",
                "governance_contract": {
                    "treat_as_parity_blocker": False,
                    "verdict": "dual_role_governance_active",
                    "production_profile": "core_plus_macro",
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_rows": 0,
                    "support_progress": {
                        "current_rows": 0,
                        "minimum_support_rows": 50,
                        "status": "no_recent_comparable_history",
                        "history": [
                            {
                                "live_current_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15"
                            }
                        ],
                    },
                },
            }
        },
        {
            "signal": "CIRCUIT_BREAKER",
            "deployment_blocker": "circuit_breaker_active",
            "runtime_closure_state": "circuit_breaker_active",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
            "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "horizon_minutes": 1440,
            "streak": 240,
            "deployment_blocker_details": {
                "release_condition": {
                    "current_recent_window_wins": 0,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 15,
                    "recent_window": 50,
                    "streak_must_be_below": 50,
                }
            },
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    q15_issue = next(issue for issue in tracker.issues if issue["id"] == "P1_q15_exact_support_stalled_under_breaker")
    assert q15_issue["summary"]["support_route_verdict"] == "exact_bucket_missing_exact_lane_proxy_only"
    assert q15_issue["summary"]["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert q15_issue["summary"]["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert q15_issue["summary"]["live_current_structure_bucket_rows"] == 0
    assert q15_issue["summary"]["gap_to_minimum"] == 50

    breaker_issue = next(issue for issue in tracker.issues if issue["id"] == "#H_AUTO_CIRCUIT_BREAKER")
    assert breaker_issue["summary"]["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert breaker_issue["summary"]["runtime_closure_state"] == "circuit_breaker_active"
    assert breaker_issue["summary"]["support_route_verdict"] == "exact_bucket_missing_exact_lane_proxy_only"



def test_sync_current_state_governance_issues_adds_alignment_blocker_when_current_inputs_stale():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": True,
                "governance_contract": {
                    "current_closure": "alignment_snapshot_stale",
                    "recommended_action": "refresh alignment artifacts",
                    "treat_as_parity_blocker": False,
                },
            }
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    align_add = next(event for event in events if event[0] == "add" and event[1] == "#H_AUTO_ALIGNMENT_GOVERNANCE")
    assert "alignment_snapshot_stale" in align_add[2]
    assert align_add[3] == "refresh alignment artifacts"


def test_sync_current_state_governance_issues_resolves_legacy_alignment_issue_when_alignment_is_current():
    events = []

    class DummyTracker:
        def add(self, priority, issue_id, title, action="", status="open"):
            events.append(("add", issue_id, title, action, status))

        def resolve(self, issue_id):
            events.append(("resolve", issue_id))
            return True

    auto_propose_fixes.sync_current_state_governance_issues(
        DummyTracker(),
        {
            "alignment": {
                "current_alignment_inputs_stale": False,
                "governance_contract": {
                    "current_closure": "global_ranking_vs_support_aware_production_split",
                    "treat_as_parity_blocker": False,
                },
            }
        },
        {"cv_accuracy": 0.71, "cv_std": 0.05, "cv_worst": 0.66},
    )

    assert ("resolve", "P1_leaderboard_alignment_snapshot_stale") in events
    assert not any(
        event[0] == "add" and event[1] == "#H_AUTO_ALIGNMENT_GOVERNANCE"
        for event in events
    )
