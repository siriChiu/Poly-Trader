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
        t.issues = data.get("issues", [])
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
        return {i["id"] for i in self.issues if i["status"] == "open"}

    def by_priority(self, priority):
        return [i for i in self.issues if i["priority"] == priority and i["status"] == "open"]

    def save(self):
        ISSUES_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(ISSUES_JSON, 'w') as f:
            json.dump({"issues": self.issues}, f, indent=2, ensure_ascii=False)

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
