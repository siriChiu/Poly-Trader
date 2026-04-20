#!/usr/bin/env python3
"""
Structured issues tracker for Poly-Trader.
Replaces the manual ISSUES.md with a machine-readable JSON file.

Usage:
    issues = IssueTracker.load()
    issues.add("P0", "#H999", "New issue description")
    issues.resolve("#H390")
    issues.save()
"""
import json
import os
from pathlib import Path
from datetime import datetime

ISSUES_JSON = Path(__file__).parent.parent / "issues.json"

# Keep current-state canonical issue IDs concise. When the structured tracker already
# carries a hand-curated canonical issue, drop the equivalent auto-proposed duplicate
# and merge its fresher machine-readable summary into the canonical record.
CANONICAL_DUPLICATE_IDS = {
    "P0_circuit_breaker_active": ["#H_AUTO_CIRCUIT_BREAKER"],
    "P0_recent_distribution_pathology": ["#H_AUTO_RECENT_PATHOLOGY"],
    "P1_q15_exact_support_stalled_under_breaker": ["#H_AUTO_CURRENT_BUCKET_SUPPORT"],
}


def _merge_issue_records(primary: dict, duplicate: dict) -> dict:
    merged = dict(primary)
    if not merged.get("title") and duplicate.get("title"):
        merged["title"] = duplicate["title"]

    primary_updated_at = merged.get("updated_at")
    duplicate_updated_at = duplicate.get("updated_at")
    duplicate_is_newer = bool(duplicate_updated_at and (not primary_updated_at or duplicate_updated_at >= primary_updated_at))
    if duplicate.get("action") and (not merged.get("action") or duplicate_is_newer):
        merged["action"] = duplicate.get("action")

    primary_summary = merged.get("summary")
    duplicate_summary = duplicate.get("summary")
    if isinstance(primary_summary, dict) and isinstance(duplicate_summary, dict):
        merged["summary"] = {**primary_summary, **duplicate_summary}
    elif duplicate_summary is not None and primary_summary in (None, "", {}):
        merged["summary"] = duplicate_summary

    for timestamp_key, chooser in (("created_at", min), ("updated_at", max)):
        primary_ts = merged.get(timestamp_key)
        duplicate_ts = duplicate.get(timestamp_key)
        if primary_ts and duplicate_ts:
            merged[timestamp_key] = chooser(primary_ts, duplicate_ts)
        elif duplicate_ts and not primary_ts:
            merged[timestamp_key] = duplicate_ts

    if merged.get("hb_detected") in (None, "") and duplicate.get("hb_detected") not in (None, ""):
        merged["hb_detected"] = duplicate.get("hb_detected")

    return merged


def _dedupe_open_issues(issues: list[dict]) -> list[dict]:
    open_issues = [dict(issue) for issue in issues if issue.get("status") == "open"]
    if not open_issues:
        return []

    issue_by_id = {issue.get("id"): issue for issue in open_issues if issue.get("id")}
    merged_canonicals: dict[str, dict] = {}
    suppressed_ids: set[str] = set()

    for canonical_id, duplicate_ids in CANONICAL_DUPLICATE_IDS.items():
        canonical = issue_by_id.get(canonical_id)
        if not canonical:
            continue
        merged = dict(canonical)
        for duplicate_id in duplicate_ids:
            duplicate = issue_by_id.get(duplicate_id)
            if not duplicate:
                continue
            merged = _merge_issue_records(merged, duplicate)
            suppressed_ids.add(duplicate_id)
        merged_canonicals[canonical_id] = merged

    deduped = []
    seen_ids = set()
    for issue in open_issues:
        issue_id = issue.get("id")
        if issue_id in suppressed_ids or issue_id in seen_ids:
            continue
        deduped_issue = merged_canonicals.get(issue_id, issue)
        deduped.append(deduped_issue)
        seen_ids.add(issue_id)
    return deduped


def _normalize_issue(issue: dict) -> dict:
    """Backfill legacy/manual issue payloads into the machine-readable action shape.

    Current-state heartbeat docs sometimes persist issues with `next_actions` only.
    Auto-propose / markdown views expect a single-line `action`, so normalize the
    loaded payload instead of printing blank arrows.
    """
    normalized = dict(issue)
    action = normalized.get("action")
    if action:
        return normalized

    next_action = normalized.get("next_action")
    if isinstance(next_action, str) and next_action.strip():
        normalized["action"] = next_action.strip()
        return normalized

    next_actions = normalized.get("next_actions")
    if isinstance(next_actions, list):
        steps = [str(step).strip() for step in next_actions if str(step).strip()]
        if steps:
            normalized["action"] = "；".join(steps)
            return normalized
    elif isinstance(next_actions, str) and next_actions.strip():
        normalized["action"] = next_actions.strip()
        return normalized

    summary = normalized.get("summary")
    if isinstance(summary, dict):
        for key in ("recommended_action", "next_action"):
            value = summary.get(key)
            if isinstance(value, str) and value.strip():
                normalized["action"] = value.strip()
                break
    return normalized


class IssueTracker:
    def __init__(self):
        self.issues = []

    @classmethod
    def load(cls):
        if ISSUES_JSON.exists():
            with open(ISSUES_JSON) as f:
                data = json.load(f)
        else:
            data = {"issues": []}
        t = cls()
        t.issues = [_normalize_issue(issue) for issue in data.get("issues", [])]
        return t

    def add(self, priority, issue_id, title, action="", status="open"):
        """Add or update an issue."""
        for i in self.issues:
            if i["id"] == issue_id:
                i["title"] = title
                i["priority"] = priority
                i["action"] = action
                i["status"] = status
                i["updated_at"] = datetime.utcnow().isoformat()
                return
        self.issues.append({
            "id": issue_id,
            "priority": priority,
            "title": title,
            "action": action,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "hb_detected": None,
        })

    def resolve(self, issue_id):
        for i in self.issues:
            if i["id"] == issue_id:
                i["status"] = "resolved"
                i["updated_at"] = datetime.utcnow().isoformat()
                return True
        return False

    def active_ids(self):
        return {i["id"] for i in _dedupe_open_issues(self.issues) if i.get("id")}

    def by_priority(self, priority):
        return [i for i in _dedupe_open_issues(self.issues) if i.get("priority") == priority]

    def save(self):
        """Persist only open issues so issues.json stays current-state-only."""
        ISSUES_JSON.parent.mkdir(parents=True, exist_ok=True)
        open_issues = _dedupe_open_issues(self.issues)
        with open(ISSUES_JSON, 'w') as f:
            json.dump({"issues": open_issues}, f, indent=2, ensure_ascii=False)

    def to_markdown(self, hb_num=None):
        """Generate ISSUES.md content from structured data."""
        lines = [
            "# ISSUES.md — 問題追蹤\n",
            f"> 最後更新：{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | 心跳 #{hb_num or '?'}\n",
        ]
        for prio in ["P0", "P1", "P2"]:
            items = self.by_priority(prio)
            if not items:
                continue
            emoji = {"P0": "🔴", "P1": "🟡", "P2": "🟢"}.get(prio, "⚪")
            lines.append(f"\n## {emoji} {prio} Issues\n")
            for item in items:
                lines.append(f"| {emoji} | **{item['id']}** | {item['title']} | {item.get('action', '')} |")
        if not any(self.by_priority(p) for p in ["P0", "P1", "P2"]):
            lines.append("\n✅ No open issues!\n")
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    tracker = IssueTracker.load()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for i in tracker.issues:
                icon = "✅" if i["status"] == "resolved" else {"P0": "🔴", "P1": "🟡", "P2": "🟢"}.get(i["priority"], "⚪")
                print(f"  {icon} {i['id']}: {i['title']}")
        elif cmd == "add" and len(sys.argv) >= 5:
            tracker.add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
            tracker.save()
            print(f"Added {sys.argv[3]}: {sys.argv[4]}")
        elif cmd == "resolve" and len(sys.argv) >= 3:
            tracker.resolve(sys.argv[2])
            tracker.save()
            print(f"Resolved {sys.argv[2]}")
    else:
        print("Usage: python issues.py [list|add <prio> <id> <title> [action]|resolve <id>]")
