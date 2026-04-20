import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "issues.py"
spec = importlib.util.spec_from_file_location("issues_test_module", MODULE_PATH)
issues_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issues_module)


def test_issue_tracker_save_persists_only_open_issues(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)

    tracker = issues_module.IssueTracker()
    tracker.issues = [
        {"id": "open-1", "priority": "P1", "status": "open", "title": "keep"},
        {"id": "resolved-1", "priority": "P1", "status": "resolved", "title": "drop"},
    ]

    tracker.save()

    payload = json.loads(target.read_text())
    assert payload == {
        "issues": [
            {"id": "open-1", "priority": "P1", "status": "open", "title": "keep"}
        ]
    }


def test_issue_tracker_load_backfills_action_from_next_actions(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)
    target.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "id": "P1_current_q35_exact_support",
                        "priority": "P1",
                        "status": "open",
                        "title": "support under minimum",
                        "next_actions": [
                            "先確認 current live bucket 是否仍是 q35",
                            "只追 exact support 是否累積",
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tracker = issues_module.IssueTracker.load()

    assert tracker.issues[0]["action"] == "先確認 current live bucket 是否仍是 q35；只追 exact support 是否累積"


def test_issue_tracker_load_backfills_action_from_next_action(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)
    target.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "id": "P1_execution_venue_readiness_unverified",
                        "priority": "P1",
                        "status": "open",
                        "title": "venue readiness is still unverified",
                        "next_action": "Keep venue blockers visible on operator-facing surfaces.",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tracker = issues_module.IssueTracker.load()

    assert tracker.issues[0]["action"] == "Keep venue blockers visible on operator-facing surfaces."


def test_issue_tracker_add_updates_stale_next_action_for_existing_issue(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)

    tracker = issues_module.IssueTracker()
    tracker.issues = [
        {
            "id": "P0_circuit_breaker_active",
            "priority": "P0",
            "status": "open",
            "title": "old blocker title",
            "action": "old blocker action",
            "next_action": "stale breaker-only next action",
        }
    ]

    tracker.add(
        "P0",
        "P0_circuit_breaker_active",
        "current live bucket q35 exact support is missing",
        "Track exact-support truth instead of stale breaker copy.",
    )
    tracker.save()

    payload = json.loads(target.read_text())
    saved = payload["issues"][0]
    assert saved["title"] == "current live bucket q35 exact support is missing"
    assert saved["action"] == "Track exact-support truth instead of stale breaker copy."
    assert saved["next_action"] == "Track exact-support truth instead of stale breaker copy."



def test_issue_tracker_save_merges_auto_breaker_duplicate_into_canonical_issue(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)

    tracker = issues_module.IssueTracker()
    tracker.issues = [
        {
            "id": "P0_circuit_breaker_active",
            "priority": "P0",
            "status": "open",
            "title": "canonical circuit breaker remains the only current-live deployment blocker",
            "action": "Keep breaker-first truth on all operator surfaces.",
            "summary": {"streak": 235, "current_recent_window_wins": 0},
            "created_at": "2026-04-18T21:16:34",
            "updated_at": "2026-04-18T21:16:34",
        },
        {
            "id": "#H_AUTO_CIRCUIT_BREAKER",
            "priority": "P0",
            "status": "open",
            "title": "canonical circuit breaker active (0/15 wins in recent 50)",
            "action": "recent 50 still needs 15 wins",
            "summary": {
                "recent_window": 50,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
            },
            "created_at": "2026-04-18T21:36:01",
            "updated_at": "2026-04-18T21:36:01",
            "hb_detected": "fast",
        },
    ]

    tracker.save()

    payload = json.loads(target.read_text())
    assert [issue["id"] for issue in payload["issues"]] == ["P0_circuit_breaker_active"]
    saved = payload["issues"][0]
    assert saved["title"] == "canonical circuit breaker remains the only current-live deployment blocker"
    assert saved["action"] == "recent 50 still needs 15 wins"
    assert saved["summary"]["recent_window"] == 50
    assert saved["summary"]["required_recent_window_wins"] == 15
    assert saved["summary"]["streak"] == 235
    assert saved["hb_detected"] == "fast"


def test_issue_tracker_save_merges_recent_pathology_duplicate_into_canonical_issue(tmp_path, monkeypatch):
    target = tmp_path / "issues.json"
    monkeypatch.setattr(issues_module, "ISSUES_JSON", target)

    tracker = issues_module.IssueTracker()
    tracker.issues = [
        {
            "id": "P0_recent_distribution_pathology",
            "priority": "P0",
            "status": "open",
            "title": "recent canonical 250 rows remains a distribution pathology",
            "action": "Keep drilling the pathological slice itself.",
            "summary": {"window": 250, "win_rate": 0.0, "dominant_regime": "bull"},
            "created_at": "2026-04-19T17:05:36",
            "updated_at": "2026-04-19T17:05:36",
        },
        {
            "id": "#H_AUTO_RECENT_PATHOLOGY",
            "priority": "P0",
            "status": "open",
            "title": "recent canonical window 500 rows = distribution_pathology",
            "action": "Use the fresh drift artifact instead of stale manual stats.",
            "summary": {
                "window": "500",
                "win_rate": 0.016,
                "dominant_regime_share": 0.988,
                "avg_quality": -0.2188,
                "alerts": ["label_imbalance", "regime_concentration", "regime_shift"],
            },
            "created_at": "2026-04-20T01:56:34",
            "updated_at": "2026-04-20T01:56:34",
            "hb_detected": "fast",
        },
    ]

    tracker.save()

    payload = json.loads(target.read_text())
    assert [issue["id"] for issue in payload["issues"]] == ["P0_recent_distribution_pathology"]
    saved = payload["issues"][0]
    assert saved["title"] == "recent canonical window 500 rows = distribution_pathology"
    assert saved["action"] == "Use the fresh drift artifact instead of stale manual stats."
    assert saved["summary"]["window"] == "500"
    assert saved["summary"]["win_rate"] == 0.016
    assert saved["summary"]["dominant_regime"] == "bull"
    assert saved["summary"]["avg_quality"] == -0.2188
    assert saved["summary"]["alerts"] == ["label_imbalance", "regime_concentration", "regime_shift"]
    assert saved["hb_detected"] == "fast"


def test_issue_tracker_by_priority_hides_duplicate_support_issue_when_canonical_exists():
    tracker = issues_module.IssueTracker()
    tracker.issues = [
        {
            "id": "P1_q15_exact_support_stalled_under_breaker",
            "priority": "P1",
            "status": "open",
            "title": "q15 exact support remains 0/50 and stalled, but support-aware governance is now visible under breaker",
            "action": "Keep support metadata visible under breaker.",
            "summary": {"current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15"},
        },
        {
            "id": "#H_AUTO_CURRENT_BUCKET_SUPPORT",
            "priority": "P1",
            "status": "open",
            "title": "current live bucket BLOCK|bull_q15_bias50_overextended_block|q15 exact support is missing (0/50)",
            "action": "Track the current live bucket support gap.",
            "summary": {"minimum_support_rows": 50, "gap_to_minimum": 50},
        },
    ]

    ids = [issue["id"] for issue in tracker.by_priority("P1")]

    assert ids == ["P1_q15_exact_support_stalled_under_breaker"]
    merged = tracker.by_priority("P1")[0]
    assert merged["summary"]["minimum_support_rows"] == 50
    assert merged["summary"]["gap_to_minimum"] == 50
