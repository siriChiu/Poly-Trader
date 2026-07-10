"""Documentation topology contracts.

These tests keep product docs from drifting back into root/data clutter and keep
AI collaboration docs centralized under docs/ai-collaboration/.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_doc_topology() -> dict:
    output = subprocess.check_output(
        [sys.executable, "scripts/doc_topology_check.py", "--format", "json"],
        cwd=PROJECT_ROOT,
        text=True,
    )
    return json.loads(output)


def test_doc_topology_is_valid() -> None:
    payload = _run_doc_topology()

    assert payload["ok"] is True
    assert payload["violations"] == []
    assert "docs_index" in payload["buckets"]
    assert "docs/analysis" in payload["buckets"]
    assert "docs/ai-collaboration" in payload["buckets"]
    assert "docs/ai-collaboration/harness" in payload["buckets"]
    assert "docs/ai-collaboration/pm" in payload["buckets"]
    assert "docs/plans" in payload["buckets"]


def test_markdown_reports_do_not_live_under_data() -> None:
    payload = _run_doc_topology()

    assert "data_markdown_forbidden" not in payload["buckets"]
    assert (PROJECT_ROOT / "docs/analysis/feature_coverage_report.md").exists()
    assert not (PROJECT_ROOT / "data/feature_coverage_report.md").exists()


def test_ai_collaboration_docs_are_centralized() -> None:
    payload = _run_doc_topology()

    for rel_path in payload["ai_collaboration_required_files"]:
        assert (PROJECT_ROOT / rel_path).exists(), rel_path

    for old_root in [
        "AI_AGENT_ROLE.md",
        "HEARTBEAT.md",
        "PM_HEARTBEAT.md",
        "strategy-decision-guide.md",
    ]:
        assert not (PROJECT_ROOT / old_root).exists(), old_root

    assert not (PROJECT_ROOT / "docs/harness").exists()
    assert not (PROJECT_ROOT / "docs/pm").exists()


def test_docs_index_names_product_folders() -> None:
    text = (PROJECT_ROOT / "docs/README.md").read_text(encoding="utf-8")

    for token in [
        "docs/ai-collaboration/",
        "docs/ai-collaboration/harness/",
        "docs/ai-collaboration/pm/",
        "docs/analysis/",
        "docs/plans/",
        "data/*.json",
    ]:
        assert token in text


def test_ai_collaboration_index_names_all_canonical_docs() -> None:
    text = (PROJECT_ROOT / "docs/ai-collaboration/README.md").read_text(encoding="utf-8")

    for token in [
        "AGENTS.md",
        "docs/ai-collaboration/AI_AGENT_ROLE.md",
        "docs/ai-collaboration/HEARTBEAT.md",
        "docs/ai-collaboration/PM_HEARTBEAT.md",
        "docs/ai-collaboration/strategy-decision-guide.md",
        "docs/ai-collaboration/harness/README.md",
        "docs/ai-collaboration/pm/README.md",
    ]:
        assert token in text
