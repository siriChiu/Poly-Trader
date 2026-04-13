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
                        "null_heavy_count": 1,
                        "low_variance_examples": [
                            {"feature": "feat_eye", "std_ratio": 0.02},
                            {"feature": "feat_nose", "std_ratio": 0.05},
                        ],
                        "low_distinct_examples": [
                            {"feature": "feat_eye", "recent_distinct": 1, "baseline_distinct": 50},
                        ],
                        "null_heavy_examples": [
                            {"feature": "feat_claw", "non_null_ratio": 0.42},
                        ],
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
    assert "feature_diag=variance:4/30, distinct:3, null_heavy:1" in summary
    assert "variance_examples=feat_eye(0.02)/feat_nose(0.05)" in summary


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
    assert "feature_diag=variance:28/49, distinct:15, null_heavy:10" in pathology_issue[3]
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
    assert "TW history: #657=10/30, #656=12/30" in out
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
