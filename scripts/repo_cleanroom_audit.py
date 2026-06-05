#!/usr/bin/env python3
"""Poly-Trader repo cleanroom audit and safe cleanup helper.

This script is intentionally conservative.  It cleans only obvious local runtime
trash that should never be promoted into source control: root one-off helper
scripts, heartbeat run logs, Python/pytest caches, frontend build output, and
CatBoost training scratch output.  It deliberately preserves venvs, databases,
model artifacts, and current-state machine artifacts such as
``data/live_predict_probe.json`` even when those paths are ignored by
``.gitignore``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROTECTED_DIR_NAMES = {
    ".git",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "web/node_modules",
    "graphify-out",
}

ROOT_TEMP_PREFIXES = ("_", "tmp_", "temp_", "debug_", "hb_")
ROOT_TEMP_EXACT = {
    "check_regime.py",
    "regime_train.py",
}

HEARTBEAT_LOG_SUFFIXES = (
    "_summary.json",
    "_progress.json",
    "_summary.md",
    "_report.md",
    "_report.txt",
    "_results.json",
)

CURRENT_STATE_ARTIFACT_PREFIXES = (
    "live_",
    "q15_",
    "q35_",
    "high_conviction_",
    "execution_metadata_",
    "customer_safe_",
    "recent_drift_",
    "feature_group_",
    "canonical_",
    "bull_",
    "full_ic_",
    "ic_regime_",
    "leaderboard_",
    "venue_",
    "paper_shadow_",
    "no_trade_",
)


@dataclass(frozen=True)
class CleanupCandidate:
    path: str
    category: str
    bytes: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "category": self.category,
            "bytes": self.bytes,
            "reason": self.reason,
        }


def _run_git(args: list[str], root: Path) -> list[str]:
    try:
        out = subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in out.splitlines() if line.strip()]


def _tracked_files(root: Path) -> set[str]:
    return set(_run_git(["ls-files"], root))


def _git_status_short(root: Path) -> list[str]:
    return _run_git(["status", "--short", "--branch"], root)


def _is_under_protected_dir(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if not rel_parts:
        return False
    if rel_parts[0] in {"venv", ".venv", "env", "node_modules", ".git", "graphify-out"}:
        return True
    if len(rel_parts) >= 2 and rel_parts[0] == "web" and rel_parts[1] == "node_modules":
        return True
    return False


def _safe_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_file() or child.is_symlink():
                try:
                    total += child.stat().st_size
                except OSError:
                    pass
    return total


def _is_root_temp_script(path: Path, root: Path) -> bool:
    if path.parent != root or path.suffix != ".py":
        return False
    if path.name in {"config.py", "main.py"}:
        return False
    return path.name.startswith(ROOT_TEMP_PREFIXES) or path.name in ROOT_TEMP_EXACT


def _is_heartbeat_run_log(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).parts
    if len(rel) != 2 or rel[0] != "data" or not path.is_file():
        return False
    name = path.name
    if name.startswith("heartbeat_") and name.endswith(HEARTBEAT_LOG_SUFFIXES):
        return True
    if name.startswith("hb_") and name.endswith(".json"):
        return True
    if len(name) > 2 and name.startswith("hb") and name[2].isdigit() and name.endswith(".json"):
        return True
    return False


def _is_current_state_artifact(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).parts
    if len(rel) != 2 or rel[0] not in {"data", "model"} or not path.is_file():
        return False
    return path.name.startswith(CURRENT_STATE_ARTIFACT_PREFIXES)


def _iter_cleanup_candidates(root: Path = PROJECT_ROOT) -> Iterable[CleanupCandidate]:
    tracked = _tracked_files(root)
    seen: set[str] = set()

    def add(path: Path, category: str, reason: str) -> CleanupCandidate | None:
        rel = _safe_relative(path, root)
        if rel in seen or rel in tracked:
            return None
        if _is_under_protected_dir(path, root):
            return None
        if _is_current_state_artifact(path, root):
            return None
        seen.add(rel)
        return CleanupCandidate(rel, category, _path_size(path), reason)

    # Root scratch helpers are the largest source of “what is this file doing?” noise.
    for child in root.iterdir():
        if _is_root_temp_script(child, root):
            candidate = add(child, "root_temp_script", "one-off root helper; formal scripts belong under scripts/ with tests")
            if candidate:
                yield candidate

    # Per-run heartbeat logs are historical runtime output; current truth is in
    # current-state docs and selected data/*.json contract artifacts.
    data_dir = root / "data"
    if data_dir.exists():
        for child in data_dir.iterdir():
            if _is_heartbeat_run_log(child, root):
                candidate = add(child, "heartbeat_run_log", "generated per-run heartbeat output")
                if candidate:
                    yield candidate

    # Source-tree caches.  Venv/node_modules caches are excluded by _is_under_protected_dir.
    for path in root.rglob("__pycache__"):
        if path.is_dir():
            candidate = add(path, "python_cache", "generated Python bytecode cache")
            if candidate:
                yield candidate

    for path in root.rglob(".pytest_cache"):
        if path.is_dir():
            candidate = add(path, "pytest_cache", "generated pytest cache")
            if candidate:
                yield candidate

    catboost_info = root / "catboost_info"
    if catboost_info.exists() and catboost_info.is_dir():
        candidate = add(catboost_info, "catboost_scratch", "generated CatBoost training scratch output")
        if candidate:
            yield candidate

    web_dist = root / "web" / "dist"
    if web_dist.exists() and web_dist.is_dir():
        candidate = add(web_dist, "frontend_build_output", "generated frontend production build output")
        if candidate:
            yield candidate


def find_cleanup_candidates(root: Path = PROJECT_ROOT) -> list[CleanupCandidate]:
    return sorted(_iter_cleanup_candidates(root), key=lambda item: (item.category, item.path))


def summarize_candidates(candidates: Iterable[CleanupCandidate]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        bucket = summary.setdefault(candidate.category, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += candidate.bytes
    return summary


def clean_candidates(candidates: Iterable[CleanupCandidate], root: Path = PROJECT_ROOT) -> list[str]:
    removed: list[str] = []
    for candidate in candidates:
        path = root / candidate.path
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(candidate.path)
    return removed


def build_audit(root: Path = PROJECT_ROOT) -> dict[str, object]:
    candidates = find_cleanup_candidates(root)
    status = _git_status_short(root)
    tracked_ignored = _run_git(["ls-files", "-ci", "--exclude-standard"], root)
    untracked_visible = _run_git(["ls-files", "--others", "--exclude-standard"], root)
    return {
        "project_root": str(root),
        "git_status_entries": status,
        "dirty_entry_count": max(0, len(status) - 1 if status and status[0].startswith("##") else len(status)),
        "tracked_ignored_count": len(tracked_ignored),
        "tracked_ignored_examples": tracked_ignored[:20],
        "untracked_visible_count": len(untracked_visible),
        "untracked_visible_examples": untracked_visible[:20],
        "cleanup_candidate_count": len(candidates),
        "cleanup_candidate_bytes": sum(candidate.bytes for candidate in candidates),
        "cleanup_summary": summarize_candidates(candidates),
        "cleanup_candidates": [candidate.as_dict() for candidate in candidates],
        "protected_policy": {
            "never_clean_by_default": sorted(PROTECTED_DIR_NAMES),
            "preserve_current_state_artifact_prefixes": CURRENT_STATE_ARTIFACT_PREFIXES,
            "why": "Do not use git clean -fdX here: it would remove venvs, DBs, model files, and contract artifacts that are intentionally ignored but operationally important.",
        },
        "closed_loop_entrypoints": [
            "AGENTS.md",
            "HEARTBEAT.md",
            "PM_HEARTBEAT.md",
            "docs/harness/README.md",
            "docs/harness/heartbeat-qa.md",
            "docs/pm/pm-status.md",
            "scripts/hb_parallel_runner.py",
            "scripts/heartbeat_harness_check.py",
            "scripts/pm_heartbeat_check.py",
            "scripts/repo_cleanroom_audit.py",
        ],
    }


def _human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{value}B"


def _as_int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return 0


def render_text(audit: dict[str, object], max_list: int = 20) -> str:
    lines: list[str] = []
    lines.append("Poly-Trader repo cleanroom audit")
    lines.append(f"root: {audit.get('project_root', '')}")
    lines.append("")
    lines.append("## Worktree shape")
    lines.append(f"dirty entries: {audit.get('dirty_entry_count', 0)}")
    lines.append(f"visible untracked entries: {audit.get('untracked_visible_count', 0)}")
    lines.append(f"tracked-but-ignored entries: {audit.get('tracked_ignored_count', 0)}")
    tracked_examples = audit.get("tracked_ignored_examples")
    if isinstance(tracked_examples, list) and tracked_examples:
        lines.append("tracked-but-ignored examples: " + ", ".join(str(item) for item in tracked_examples[:8]))
    lines.append("")
    lines.append("## Safe cleanup candidates")
    lines.append(
        f"total: {audit.get('cleanup_candidate_count', 0)} entries / {_human_bytes(_as_int_value(audit.get('cleanup_candidate_bytes', 0)))}"
    )
    summary = audit.get("cleanup_summary", {})
    if isinstance(summary, dict):
        for category, item in sorted(summary.items()):
            if isinstance(item, dict):
                lines.append(
                    f"- {category}: {item.get('count', 0)} / {_human_bytes(_as_int_value(item.get('bytes', 0)))}"
                )
    candidates = audit.get("cleanup_candidates", [])
    if isinstance(candidates, list) and candidates:
        lines.append("")
        lines.append(f"First {min(max_list, len(candidates))} candidates:")
        for item in candidates[:max_list]:
            if isinstance(item, dict):
                lines.append(
                    f"- [{item.get('category', '')}] {item.get('path', '')} ({_human_bytes(_as_int_value(item.get('bytes', 0)))})"
                )
    lines.append("")
    lines.append("## Closed-loop entrypoints")
    entrypoints = audit.get("closed_loop_entrypoints", [])
    if isinstance(entrypoints, list):
        for entry in entrypoints:
            lines.append(f"- {entry}")
    lines.append("")
    lines.append("Policy: this audit preserves venvs, DBs, model artifacts, and current-state data/*.json contracts by default.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--clean", action="store_true", help="delete safe cleanup candidates")
    parser.add_argument("--max-list", type=int, default=20)
    args = parser.parse_args(argv)

    audit = build_audit(PROJECT_ROOT)
    if args.clean:
        raw_candidates = audit.get("cleanup_candidates", [])
        candidates: list[CleanupCandidate] = []
        if isinstance(raw_candidates, list):
            for item in raw_candidates:
                if isinstance(item, dict):
                    path = item.get("path")
                    category = item.get("category")
                    reason = item.get("reason")
                    if isinstance(path, str) and isinstance(category, str) and isinstance(reason, str):
                        candidates.append(
                            CleanupCandidate(
                                path=path,
                                category=category,
                                bytes=_as_int_value(item.get("bytes", 0)),
                                reason=reason,
                            )
                        )
        removed = clean_candidates(candidates, PROJECT_ROOT)
        audit = build_audit(PROJECT_ROOT)
        audit["removed_count"] = len(removed)
        audit["removed_examples"] = removed[: args.max_list]

    if args.format == "json":
        print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.clean:
            print(f"Removed safe cleanup candidates: {audit.get('removed_count', 0)}")
            examples = audit.get("removed_examples", [])
            if examples:
                print("Removed examples:")
                for item in examples:
                    print(f"- {item}")
            print("")
        print(render_text(audit, max_list=args.max_list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
