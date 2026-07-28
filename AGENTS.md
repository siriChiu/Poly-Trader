## graphify

This project may use a graphify knowledge graph at `graphify-out/`.

Rules:
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading many raw files first.
- If `graphify-out/graph.json` exists, you may use `graphify query "<question>" --graph graphify-out/graph.json` for graph-guided retrieval.
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current.

## Poly-Trader harness map

Keep this file as a short root discovery map, not a manual. Detailed AI collaboration docs live under `docs/ai-collaboration/`.

For heartbeat work:
- Read `docs/ai-collaboration/README.md`, `docs/ai-collaboration/HEARTBEAT.md`, `docs/ai-collaboration/AI_AGENT_ROLE.md`, `ISSUES.md`, `ROADMAP.md`, and `ORID_DECISIONS.md` before acting.
- For harness-engineering/Q&A gates, read `docs/ai-collaboration/harness/README.md` and `docs/ai-collaboration/harness/heartbeat-qa.md`.
- Run `python scripts/heartbeat_governor.py --format text` before agent decision-making; its external anti-self-certification brief is binding.
- Run `python scripts/heartbeat_harness_check.py --format text` when touching heartbeat governance, docs, or agent workflow contracts.
- For product-PM arbitration heartbeat work, read `docs/ai-collaboration/PM_HEARTBEAT.md`, `docs/ai-collaboration/pm/README.md`, `docs/ai-collaboration/pm/pm-heartbeat-qa.md`, and `docs/ai-collaboration/pm/pm-status.md`.
- Run `python scripts/pm_heartbeat_check.py --format text` when touching PM heartbeat governance, PM status, or delivery-conflict contracts.
