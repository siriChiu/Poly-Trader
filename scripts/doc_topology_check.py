#!/usr/bin/env python3
"""Validate Poly-Trader documentation folder topology.

The goal is productization hygiene: root docs stay navigational/current-state,
`docs/` owns human-readable documentation, AI collaboration docs are centralized
under `docs/ai-collaboration/`, and `data/` stays machine/runtime state only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Hermes stores session-local plans and metadata under this hidden directory.
# It is not product documentation and must not be classified by the repo's
# documentation topology contract when it is present as an untracked workspace.
IGNORED_VISIBLE_PREFIXES = (".hermes/",)

ROOT_MARKDOWN_ALLOWLIST = {
    "AGENTS.md",  # root discovery stub for agent runtimes; detailed AI docs live in docs/ai-collaboration/
    "ARCHITECTURE.md",
    "ISSUES.md",
    "ORID_DECISIONS.md",
    "PRD.md",
    "README.md",
    "ROADMAP.md",
}

AI_COLLAB_REQUIRED_FILES = [
    "docs/ai-collaboration/README.md",
    "docs/ai-collaboration/AI_AGENT_ROLE.md",
    "docs/ai-collaboration/HEARTBEAT.md",
    "docs/ai-collaboration/PM_HEARTBEAT.md",
    "docs/ai-collaboration/strategy-decision-guide.md",
    "docs/ai-collaboration/harness/README.md",
    "docs/ai-collaboration/harness/heartbeat-qa.md",
    "docs/ai-collaboration/harness/heartbeat-harness-contract.json",
    "docs/ai-collaboration/pm/README.md",
    "docs/ai-collaboration/pm/pm-heartbeat-qa.md",
    "docs/ai-collaboration/pm/pm-heartbeat-contract.json",
    "docs/ai-collaboration/pm/pm-status.md",
]

AI_COLLAB_FORBIDDEN_ROOT_FILES = {
    "AI_AGENT_ROLE.md",
    "HEARTBEAT.md",
    "PM_HEARTBEAT.md",
    "strategy-decision-guide.md",
}

FORBIDDEN_AI_COLLAB_LEGACY_PREFIXES = (
    "docs/harness/",
    "docs/pm/",
)

DOCS_DIRS = {
    "docs/ai-collaboration/harness": "engineering heartbeat harness map, Q&A gate, and machine contract",
    "docs/ai-collaboration/pm": "PM heartbeat harness and current PM status",
    "docs/ai-collaboration": "AI agent role, heartbeat governance, PM arbitration, and collaboration contracts",
    "docs/analysis": "analysis reports and markdown companions for data/*.json artifacts",
    "docs/plans": "dated implementation plans and design blueprints",
}

REQUIRED_DOCS_README_TOKENS = [
    "docs/ai-collaboration/",
    "docs/ai-collaboration/harness/",
    "docs/ai-collaboration/pm/",
    "docs/analysis/",
    "docs/plans/",
    "data/*.json",
    "data/*.md",
    "scripts/doc_topology_check.py",
]

REQUIRED_AI_COLLAB_INDEX_TOKENS = [
    "AGENTS.md",
    "docs/ai-collaboration/AI_AGENT_ROLE.md",
    "docs/ai-collaboration/HEARTBEAT.md",
    "docs/ai-collaboration/PM_HEARTBEAT.md",
    "docs/ai-collaboration/strategy-decision-guide.md",
    "docs/ai-collaboration/harness/README.md",
    "docs/ai-collaboration/pm/README.md",
]


def _filter_visible_paths(lines: Iterable[str]) -> list[str]:
    return sorted(
        {
            line
            for line in lines
            if line.strip() and not line.startswith(IGNORED_VISIBLE_PREFIXES)
        }
    )


def _git_visible_files(*patterns: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", *patterns],
        cwd=PROJECT_ROOT,
        text=True,
    )
    return _filter_visible_paths(output.splitlines())


def _classify_markdown(path: str) -> str:
    if path in ROOT_MARKDOWN_ALLOWLIST:
        return "root"
    if path == "docs/README.md":
        return "docs_index"
    for prefix in sorted(DOCS_DIRS, key=len, reverse=True):
        if path.startswith(f"{prefix}/"):
            return prefix
    if path == "scripts/legacy_checks/README.md":
        return "legacy_readme"
    if path.startswith("data/"):
        return "data_markdown_forbidden"
    if "/" not in path:
        return "root_unclassified"
    return "unclassified"


def build_report() -> dict[str, Any]:
    visible_files = set(_git_visible_files("*"))
    markdown_files = _git_visible_files("*.md")
    docs_json_files = _git_visible_files("docs/*.json", "docs/**/*.json")
    buckets: dict[str, list[str]] = {}
    violations: list[dict[str, str]] = []

    for path in markdown_files:
        category = _classify_markdown(path)
        buckets.setdefault(category, []).append(path)
        if category == "data_markdown_forbidden":
            violations.append(
                {
                    "path": path,
                    "rule": "data_markdown_forbidden",
                    "message": "Markdown reports belong under docs/analysis/; data/ is machine/runtime state.",
                }
            )
        elif category in {"root_unclassified", "unclassified"}:
            violations.append(
                {
                    "path": path,
                    "rule": "unclassified_markdown",
                    "message": "Add this file to the documented topology or move it into docs/{analysis,ai-collaboration,plans}.",
                }
            )

    for path in buckets.get("docs/plans", []):
        name = Path(path).name
        if not re.match(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$", name):
            violations.append(
                {
                    "path": path,
                    "rule": "dated_plan_filename",
                    "message": "Plan files should use YYYY-MM-DD-kebab-case.md.",
                }
            )

    for path in sorted(AI_COLLAB_FORBIDDEN_ROOT_FILES & visible_files):
        violations.append(
            {
                "path": path,
                "rule": "ai_collaboration_root_file_forbidden",
                "message": "AI collaboration manuals belong under docs/ai-collaboration/; keep only AGENTS.md as the root discovery stub.",
            }
        )

    for prefix in FORBIDDEN_AI_COLLAB_LEGACY_PREFIXES:
        for path in sorted(item for item in visible_files if item.startswith(prefix)):
            violations.append(
                {
                    "path": path,
                    "rule": "ai_collaboration_legacy_folder_forbidden",
                    "message": "Move legacy AI collaboration docs to docs/ai-collaboration/{harness,pm}/.",
                }
            )

    for path in AI_COLLAB_REQUIRED_FILES:
        if path not in visible_files:
            violations.append(
                {
                    "path": path,
                    "rule": "missing_ai_collaboration_file",
                    "message": "Required AI collaboration file is missing from the centralized docs/ai-collaboration/ tree.",
                }
            )

    docs_readme = PROJECT_ROOT / "docs" / "README.md"
    docs_readme_text = docs_readme.read_text(encoding="utf-8") if docs_readme.exists() else ""
    if not docs_readme.exists():
        violations.append(
            {"path": "docs/README.md", "rule": "missing_docs_index", "message": "docs/README.md is required."}
        )
    else:
        for token in REQUIRED_DOCS_README_TOKENS:
            if token not in docs_readme_text:
                violations.append(
                    {
                        "path": "docs/README.md",
                        "rule": "docs_index_missing_token",
                        "message": f"Missing topology token: {token}",
                    }
                )

    ai_index = PROJECT_ROOT / "docs" / "ai-collaboration" / "README.md"
    ai_index_text = ai_index.read_text(encoding="utf-8") if ai_index.exists() else ""
    if not ai_index.exists():
        violations.append(
            {
                "path": "docs/ai-collaboration/README.md",
                "rule": "missing_ai_collaboration_index",
                "message": "AI collaboration index is required.",
            }
        )
    else:
        for token in REQUIRED_AI_COLLAB_INDEX_TOKENS:
            if token not in ai_index_text:
                violations.append(
                    {
                        "path": "docs/ai-collaboration/README.md",
                        "rule": "ai_collaboration_index_missing_token",
                        "message": f"Missing AI collaboration token: {token}",
                    }
                )

    feature_coverage_script = PROJECT_ROOT / "scripts" / "feature_coverage_report.py"
    if feature_coverage_script.exists():
        text = feature_coverage_script.read_text(encoding="utf-8")
        if "docs' / 'analysis' / 'feature_coverage_report.md'" not in text:
            violations.append(
                {
                    "path": "scripts/feature_coverage_report.py",
                    "rule": "feature_coverage_markdown_location",
                    "message": "Feature coverage Markdown companion should be written to docs/analysis/.",
                }
            )

    return {
        "ok": not violations,
        "markdown_count": len(markdown_files),
        "docs_json_count": len(docs_json_files),
        "buckets": {key: sorted(value) for key, value in sorted(buckets.items())},
        "docs_dirs": DOCS_DIRS,
        "ai_collaboration_required_files": AI_COLLAB_REQUIRED_FILES,
        "violations": violations,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = ["Poly-Trader doc topology check", ""]
    lines.append(f"markdown files: {report['markdown_count']}")
    lines.append(f"docs json files: {report['docs_json_count']}")
    lines.append("")
    lines.append("## Buckets")
    buckets = report.get("buckets", {})
    if isinstance(buckets, dict):
        for bucket, paths in buckets.items():
            if isinstance(paths, list):
                lines.append(f"- {bucket}: {len(paths)}")
    violations = report.get("violations", [])
    lines.append("")
    if violations:
        lines.append("## Violations")
        for item in violations:
            if isinstance(item, dict):
                lines.append(f"- {item.get('path')}: {item.get('rule')} — {item.get('message')}")
        lines.append("")
        lines.append("RESULT: FAIL")
    else:
        lines.append("RESULT: PASS")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    report = build_report()
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
