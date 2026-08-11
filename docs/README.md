# Poly-Trader 文件地圖

> 目標：文件服務產品化，而不是把每輪心跳、研究輸出、runtime artifact 全部堆在 repo root。新增文件前先放進下列分類；若分類放不下，先更新本文件與 `scripts/doc_topology_check.py`。

## 1. 文件層級關係

```text
README.md / ARCHITECTURE.md / PRD.md
  └─ 產品入口、架構與需求：給人讀的 evergreen contract

AGENTS.md
  └─ root discovery stub：只做短 map，導向 docs/ai-collaboration/

docs/ai-collaboration/
  ├─ README.md                  # AI 協作文件總索引
  ├─ AI_AGENT_ROLE.md           # AI agent 身分、邊界、紀律
  ├─ HEARTBEAT.md               # engineering heartbeat 流程規範
  ├─ PM_HEARTBEAT.md            # product PM heartbeat 流程規範
  ├─ strategy-decision-guide.md # 策略決策前置與收斂指南
  ├─ harness/                   # engineering heartbeat Q&A / machine contract
  └─ pm/                        # PM heartbeat Q&A / machine contract / pm-status

ISSUES.md / ROADMAP.md / ORID_DECISIONS.md
  └─ current-state docs：由 heartbeat overwrite sync，描述「現在」而非歷史

docs/
  ├─ README.md                  # 本文件：文件分類與關聯
  ├─ adr/                       # immutable owner/architecture decision records
  ├─ ai-collaboration/          # AI 協作與 heartbeat governance 集中區
  ├─ analysis/                  # 可重跑分析、人讀摘要、artifact markdown companion
  ├─ plans/                     # 日期化設計與實作計畫
  └─ specification/             # source-backed 架構、gating lineage、as-is/to-be BDD

data/
  └─ *.json / *.db / runtime artifacts only；Markdown 報告不得放在 data/
```

## 2. 分類規則

| 區域 | 內容 | 是否 current-state | 是否可由腳本生成 | 維護規則 |
|---|---|---:|---:|---|
| Repo root evergreen | `README.md`, `ARCHITECTURE.md`, `PRD.md` | 否 | 否 | 只放穩定產品/架構/需求；不要追加 heartbeat 歷史 |
| Root agent discovery | `AGENTS.md` | 否 | 否 | 保留在 root 只為 agent runtime 自動發現；內容維持短 map，不變成手冊 |
| AI collaboration center | `docs/ai-collaboration/*` | 部分 | 部分 | 所有 agent role、heartbeat、PM heartbeat、harness、Q&A、machine contract 集中於此 |
| Current-state root | `ISSUES.md`, `ROADMAP.md`, `ORID_DECISIONS.md` | 是 | 是 | overwrite sync；不 append 歷史流水帳 |
| `docs/adr/` | owner與architecture決策、context、consequences、supersedes chain | 否 | 否 | immutable；新決策以新ADR supersede，不覆寫歷史 |
| `docs/analysis/` | 分析報告、probe markdown companion、模型/特徵摘要 | 部分 | 多數 | JSON truth 留在 `data/`，Markdown companion 放這裡 |
| `docs/plans/` | 日期化設計/實作計畫 | 否 | 否 | 檔名用 `YYYY-MM-DD-*`；完成後不再複製成多份 |
| `docs/specification/` | source-backed architecture、gate ownership、as-is/to-be BDD | 否 | 否 | as-is 與 proposed to-be 分開；spec 永不授權 live order |
| `scripts/legacy_checks/README.md` | 歷史診斷腳本說明 | 否 | 否 | 只保留 legacy 區說明，不當正式 workflow 入口 |

## 3. AI 協作文件集中規則

Canonical 入口在 [`docs/ai-collaboration/README.md`](ai-collaboration/README.md)。

子資料夾固定為：

- `docs/ai-collaboration/harness/` — engineering heartbeat harness / Q&A / machine contract。
- `docs/ai-collaboration/pm/` — PM heartbeat harness / Q&A / machine contract / `pm-status.md`。

不再新增或恢復下列舊位置：

- root `AI_AGENT_ROLE.md`
- root `HEARTBEAT.md`
- root `PM_HEARTBEAT.md`
- root `strategy-decision-guide.md`
- `docs/harness/`
- `docs/pm/`

例外：`AGENTS.md` 必須留在 root，作為 agent runtime 的短 discovery map。

## 4. Artifact ↔ Markdown companion 關係

- Machine truth：`data/*.json`。
- Operator / reviewer summary：`docs/analysis/*.md`。
- 若一個 report 同時產生 JSON 和 Markdown，預設路徑應是：
  - JSON：`data/<name>.json`
  - Markdown：`docs/analysis/<name>.md`
- 不再新增 `data/*.md`；`data/` 只放機器可讀或 runtime state。

目前已整理的例子：

| JSON artifact | Markdown companion | Producer |
|---|---|---|
| `data/feature_coverage_report.json` | `docs/analysis/feature_coverage_report.md` | `scripts/feature_coverage_report.py` |
| `data/feature_group_ablation.json` | `docs/analysis/feature_group_ablation.md` | `scripts/feature_group_ablation.py` |
| `data/bull_4h_pocket_ablation.json` | `docs/analysis/bull_4h_pocket_ablation.md` | `scripts/bull_4h_pocket_ablation.py` |
| `data/q15_support_audit.json` | `docs/analysis/q15_support_audit.md` | `scripts/hb_q15_support_audit.py` |
| `data/venue_dry_run_proof.json` | `docs/analysis/venue_dry_run_proof.md` | `scripts/venue_dry_run_proof.py` / heartbeat lane |

## 5. 新增/搬移文件前的檢查

```bash
python scripts/doc_topology_check.py --format text
python -m pytest tests/test_doc_topology.py -q
```

若要刪或搬文件，再跑：

```bash
python scripts/repo_cleanroom_audit.py --format text
python -m pytest tests/test_repo_hygiene.py -q
```

## 6. 減法原則

1. **Root 只放產品入口、current-state、AGENTS stub**：新計畫、分析、Q&A、AI 協作手冊不放 root。
2. **AI 協作集中**：agent role / heartbeat / PM heartbeat / harness / Q&A / contract 全部放 `docs/ai-collaboration/`。
3. **data 不放 Markdown**：報告 Markdown 放 `docs/analysis/`，JSON artifact 留 `data/`。
4. **plans 不複製成 docs/analysis**：計畫是意圖，analysis 是證據，兩者分離。
5. **current-state docs 只描述現在**：歷史由 git history、ignored artifacts 或 dated plans/analysis 保存。
6. **大型 runtime state 另列 protected**：DB、venv、graphify、live models 由 cleanroom audit 列出，不自動刪。

## 7. BDD 與重構規格

- [`docs/specification/README.md`](specification/README.md) — 分析邊界、閱讀順序、BDD標籤與重構啟動條件。
- [`docs/specification/as-is-architecture.md`](specification/as-is-architecture.md) — 現行bounded contexts、資料流、god modules與truth stores。
- [`docs/specification/as-is-gating-lineage.md`](specification/as-is-gating-lineage.md) — gate owner、重複projection、fallback與deadlock。
- [`docs/specification/features/as-is/`](specification/features/as-is/) — 可解析的Gherkin characterization。
- [`docs/specification/documentation-inventory.md`](specification/documentation-inventory.md) — authority/TTL分類與遷移建議。
- [`docs/specification/open-questions.md`](specification/open-questions.md) — owner decision queue；一次只確認一題。
- [`docs/plans/2026-08-11-bdd-led-refactor.md`](plans/2026-08-11-bdd-led-refactor.md) — 尚待BDD確認的strangler重構藍圖。
- [`docs/adr/ADR-0001-live-canary-product-scope.md`](adr/ADR-0001-live-canary-product-scope.md) — 已接受的近期實戰完成定義。
- [`docs/adr/ADR-0002-personal-release-lifecycle.md`](adr/ADR-0002-personal-release-lifecycle.md) — Owner release永久、manual-only revocation lifecycle。
- [`docs/adr/ADR-0003-exact-support-advisory.md`](adr/ADR-0003-exact-support-advisory.md) — Exact support只作信心警告，不阻止極小額canary。
- [`docs/adr/ADR-0004-decision-snapshot-truth.md`](adr/ADR-0004-decision-snapshot-truth.md) — API/UI/docs共用同一張完整DecisionSnapshot。
- [`docs/adr/ADR-0005-autonomous-model-improvement.md`](adr/ADR-0005-autonomous-model-improvement.md) — 自動重建、訓練、比較與shadow候選成長邊界。
- [`docs/adr/ADR-0006-immutable-deployment-bundle.md`](adr/ADR-0006-immutable-deployment-bundle.md) — Live Canary完整封裝identity與Owner-controlled switching。
- [`docs/adr/ADR-0007-exact-bundle-shadow-evidence.md`](adr/ADR-0007-exact-bundle-shadow-evidence.md) — 新bundle只用自己的Paper/Shadow成績。
- [`docs/adr/ADR-0008-conservative-live-canary-risk.md`](adr/ADR-0008-conservative-live-canary-risk.md) — 保守Live Canary資金、日損與failure halt。
- [`docs/adr/ADR-0009-docs-ai-non-authoritative.md`](adr/ADR-0009-docs-ai-non-authoritative.md) — 文件與AI不得直接授權真實下單。
- [`docs/adr/ADR-0010-manual-live-canary-permit.md`](adr/ADR-0010-manual-live-canary-permit.md) — UI雙步確認與exact single-use permit。
- [`docs/adr/ADR-0011-btc-usdt-phase-one.md`](adr/ADR-0011-btc-usdt-phase-one.md) — Phase 1只支援BTC/USDT並保留未來partition。
- [`docs/specification/features/to-be/live-canary-product-scope.feature`](specification/features/to-be/live-canary-product-scope.feature) — owner-approved Live Canary to-be BDD。
- [`docs/specification/features/to-be/personal-release-lifecycle.feature`](specification/features/to-be/personal-release-lifecycle.feature) — owner-approved permanent/manual-revoke release BDD。
- [`docs/specification/features/to-be/exact-support-advisory.feature`](specification/features/to-be/exact-support-advisory.feature) — owner-approved support advisory BDD。
- [`docs/specification/features/to-be/decision-snapshot-truth.feature`](specification/features/to-be/decision-snapshot-truth.feature) — owner-approved single-state projection BDD。
- [`docs/specification/features/to-be/autonomous-model-improvement.feature`](specification/features/to-be/autonomous-model-improvement.feature) — owner-approved autonomous model growth BDD。
- [`docs/specification/features/to-be/immutable-deployment-bundle.feature`](specification/features/to-be/immutable-deployment-bundle.feature) — owner-approved full bundle binding BDD。
- [`docs/specification/features/to-be/exact-bundle-shadow-evidence.feature`](specification/features/to-be/exact-bundle-shadow-evidence.feature) — owner-approved exact candidate evidence BDD。
- [`docs/specification/features/to-be/conservative-live-canary-risk.feature`](specification/features/to-be/conservative-live-canary-risk.feature) — owner-approved conservative canary risk BDD。
- [`docs/specification/features/to-be/docs-ai-non-authoritative.feature`](specification/features/to-be/docs-ai-non-authoritative.feature) — owner-approved docs/AI authority boundary BDD。
- [`docs/specification/features/to-be/manual-live-canary-permit.feature`](specification/features/to-be/manual-live-canary-permit.feature) — owner-approved supervised manual canary BDD。
- [`docs/specification/features/to-be/btc-usdt-phase-one.feature`](specification/features/to-be/btc-usdt-phase-one.feature) — owner-approved BTC-only Phase-1 scope BDD。

Specification只能描述與約束行為。真實order authorization仍只能由runtime enforcement、immutable bundle、permit及venue lifecycle證據產生。
