# Poly-Trader AI 協作文件中心

> 目標：所有 AI agent / heartbeat / PM arbitration / Q&A gate / machine contract 文件集中在本資料夾，避免散落在 repo root、`docs/harness/`、`docs/pm/` 等多個位置。

## 1. 唯一入口

| 文件 | 用途 |
|---|---|
| `AGENTS.md` | **唯一保留在 repo root 的短 map**；給 agent runtime 自動發現用，不當手冊 |
| `docs/ai-collaboration/README.md` | 本文件；AI 協作文件總索引 |
| `docs/ai-collaboration/AI_AGENT_ROLE.md` | AI agent 身分、硬邊界、自主執行紀律 |
| `docs/ai-collaboration/HEARTBEAT.md` | Engineering heartbeat evergreen 操作流程 |
| `docs/ai-collaboration/strategy-decision-guide.md` | heartbeat 決策前置與策略收斂指南 |
| `docs/ai-collaboration/harness/README.md` | Engineering harness map |
| `docs/ai-collaboration/harness/heartbeat-qa.md` | Engineering heartbeat Q&A gates |
| `docs/ai-collaboration/harness/heartbeat-harness-contract.json` | Engineering machine-readable contract |
| `docs/ai-collaboration/PM_HEARTBEAT.md` | Product PM heartbeat evergreen 操作流程 |
| `docs/ai-collaboration/pm/README.md` | PM harness map |
| `docs/ai-collaboration/pm/pm-heartbeat-qa.md` | PM Q&A gates |
| `docs/ai-collaboration/pm/pm-heartbeat-contract.json` | PM machine-readable contract |
| `docs/ai-collaboration/pm/pm-status.md` | PM current-state status；由 artifact / sync script overwrite |

## 2. 不再使用的位置

下列舊位置不得新增 AI 協作文件：

- root `AI_AGENT_ROLE.md`
- root `HEARTBEAT.md`
- root `PM_HEARTBEAT.md`
- root `strategy-decision-guide.md`
- `docs/harness/`
- `docs/pm/`

例外只有 `AGENTS.md`：Hermes / agent runtime 需要 root discovery file，所以它保留在 root，但內容必須維持短 map，指向本資料夾。

## 3. Read order

### Engineering heartbeat

1. `AGENTS.md`
2. `docs/ai-collaboration/README.md`
3. `docs/ai-collaboration/AI_AGENT_ROLE.md`
4. `docs/ai-collaboration/HEARTBEAT.md`
5. `docs/ai-collaboration/harness/README.md`
6. `docs/ai-collaboration/harness/heartbeat-qa.md`
7. `ISSUES.md`, `ROADMAP.md`, `ORID_DECISIONS.md`

### Product PM heartbeat

1. `AGENTS.md`
2. `docs/ai-collaboration/README.md`
3. `docs/ai-collaboration/PM_HEARTBEAT.md`
4. `docs/ai-collaboration/pm/README.md`
5. `docs/ai-collaboration/pm/pm-heartbeat-qa.md`
6. `docs/ai-collaboration/pm/pm-status.md`
7. `docs/ai-collaboration/HEARTBEAT.md`
8. `ISSUES.md`, `ROADMAP.md`, `ORID_DECISIONS.md`

## 4. 驗證命令

修改本區任何文件後，至少跑：

```bash
python scripts/doc_topology_check.py --format text
python scripts/heartbeat_harness_check.py --format text
python scripts/pm_heartbeat_check.py --format text
python -m pytest tests/test_doc_topology.py tests/test_heartbeat_harness_contract.py tests/test_pm_heartbeat_contract.py -q
git diff --check
```

若修改 code/test files 且 `graphify-out/` 存在，最後依 `AGENTS.md` 重建 graphify。

## 5. 維護規則

1. 新的 AI 協作流程、Q&A gate、agent prompt contract、PM arbitration contract，全部放在 `docs/ai-collaboration/` 下。
2. root 只保留 `AGENTS.md` 作短 map；不要再把長流程文件放回 root。
3. `docs/ai-collaboration/*` 是 evergreen process / contract，不記錄每輪 heartbeat 流水帳。
4. current-state truth 仍留在 root `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md`，因為它們是產品狀態，不是 AI 協作手冊。
5. 每輪 run logs / generated artifacts 仍放 `data/` 或 ignored artifacts，不進本資料夾。
