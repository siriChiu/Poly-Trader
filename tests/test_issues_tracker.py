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
