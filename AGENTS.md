## graphify

This project may use a graphify knowledge graph at `graphify-out/`.

Rules:
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading many raw files first.
- If `graphify-out/graph.json` exists, you may use `graphify query "<question>" --graph graphify-out/graph.json` for graph-guided retrieval.
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current.

## Poly-Trader harness map

Keep this file as a short map, not a manual. For heartbeat work:
- Read `HEARTBEAT.md`, `AI_AGENT_ROLE.md`, `ISSUES.md`, `ROADMAP.md`, and `ORID_DECISIONS.md` before acting.
- For harness-engineering/Q&A gates, read `docs/harness/README.md` and `docs/harness/heartbeat-qa.md`.
- Run `python scripts/heartbeat_harness_check.py --format text` when touching heartbeat governance, docs, or agent workflow contracts.
