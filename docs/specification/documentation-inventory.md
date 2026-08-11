# Poly-Trader 文件拓撲與權威審計

> 這是現況整理與遷移建議；不直接刪除原文件。任何 archive/delete 需在 BDD 核准後執行。

## 1. 文件類型必須分開

| 類型 | 代碼 | 可包含 | 不可包含 | 建議 TTL |
|---|---|---|---|---|
| Product requirement | PRD | 使用者目標、journey、non-functional requirements | 即時 rows、breaker、某次 leaderboard | 版本化 |
| Domain specification | SPEC | ubiquitous language、invariants、BDD | runtime timestamp、某次 market verdict | 版本化 |
| Safety policy | POLICY | 永久 hard gates、owner與例外規則 | 當前 support ratio或signal | 版本化 |
| Runbook | RUNBOOK | 操作步驟、失敗處置、驗證 | 特定 heartbeat 結果 | evergreen |
| Current status | STATUS | 帶 `generated_at/as_of/generation_id` 的投影 | 反向作 policy/release authority | 短 TTL |
| Analysis evidence | EVIDENCE | query/window/model/schema/metrics/provenance | 宣稱 live authorization | immutable snapshot |
| Decision record | ADR | context、decision、consequence、supersedes | 每輪重寫 | immutable |
| Implementation plan | PLAN | tasks、paths、tests、migration | 冒充現況 | 完成後 archive |
| Historical closure | HISTORY | 當時狀態與日期 | current truth | immutable |

目前主要問題不是資料夾位置，而是同一文件同時扮演多種類型。

## 2. Current inventory 與處置

### 2.1 Repository root

| File | 現況角色 | 問題 | 建議 |
|---|---|---|---|
| `AGENTS.md` | discovery map | 要求 agent 讀 generated current docs，容易框架捕獲 | 保持短；改指向 policy/spec/API snapshot，不直接把 status 當命令 |
| `README.md` | product overview + quick start + live claims | 重複 adapter描述，current/live readiness與使用指南混合 | 只留產品定位、啟動、文件入口 |
| `PRD.md` | PRD v4.1 + runtime snapshot | 把當時 Win Rate、support gate寫進 evergreen需求 | 抽出 runtime snapshot到 HISTORY/EVIDENCE；PRD只留 journeys/NFR |
| `ARCHITECTURE.md` | intended architecture | 與實際 god modules、repo外strategy store、artifact feedback loop不一致 | 由 `docs/specification/as-is-architecture.md` 取代；日後另寫 to-be |
| `ISSUES.md` | generated current issue projection | 每輪覆寫且被agent當優先級 authority | 以 `issues.json`/issue store為source；Markdown只作帶generation的view |
| `ROADMAP.md` | generated current plan | current blocker、proof、roadmap混在一起 | roadmap改為milestone/ADR；runtime next-action移到status |
| `ORID_DECISIONS.md` | generated current ORID | 名為decisions但每輪覆寫，不符合decision record不可變性 | 改名current reflection；真正決策用ADR append-only |

### 2.2 `docs/ai-collaboration/`

| File | 類型判定 | 問題 | 建議 |
|---|---|---|---|
| `README.md` | index | 把root current docs列為canonical但沒authority ranking | 加入 truth hierarchy 與禁止 status 授權規則 |
| `AI_AGENT_ROLE.md` | policy | `accuracy >90%`、`IC<0.05`硬規則與ROI/DD產品目標衝突 | 移除 metric literals；只定義證據紀律、安全與角色 |
| `HEARTBEAT.md` | runbook+policy | no-collect卻可maintenance write；每輪patch/commit壓力；fast/slow責任混合 | 拆 Scheduler runbook 與 Governance policy；material delta才發布 |
| `PM_HEARTBEAT.md` | PM policy/runbook | 與engineering heartbeat重複，forced-execution/72h容易誤當trade gate | 保留delivery policy但明示永不參與ExecutionAuthorization |
| `strategy-decision-guide.md` | runbook+historical evidence | owner名為`mia`；2026-04模型結論嵌入evergreen | generic guide保留；特定結論移dated evidence；owner identity修正 |
| `personal-release-policy.md` | safety/release policy+current snapshot | policy中寫34/50等「最新」值，已與runtime 24/50不符 | policy只留三層契約；current evidence由API/artifact提供 |
| `project-closure-2026-07-19.md` | history | 有current語氣 | 移 `docs/history/`，加「不可作current truth」banner |
| `pm/pm-status.md` | generated status | 198行/33k字，重複大量artifact欄位與next action | 用compact status DTO；detail連到artifact，不複製整份敘事 |
| harness/PM Q&A docs | harness policy | tests把特定token/copy固化，容易讓架構難簡化 | 保留安全invariant tests；移除文字token等實作細節測試 |

### 2.3 `docs/analysis/`

分成兩類：

1. **dated immutable evidence**：`2026-04-11-*`, `2026-04-14-*`。保留，但加 input/model/schema/commit provenance。
2. **generated latest companion**：q15/q35、drift、venue、customer-safe、circuit-breaker、feature coverage 等。現在檔名沒有 generation/date，會被誤認 evergreen。

建議：

```text
docs/evidence/<domain>/<YYYY-MM-DD>/<generation-id>.md
data/artifacts/<artifact-type>/<generation-id>.json
```

另提供 `latest.json` pointer，而不是覆寫內容後讓 Git diff充滿 runtime churn。

### 2.4 `docs/plans/`

目前包含 2026-04 到 2026-07 多套產品化/Execution/UI/Top-K方案；這些都是歷史設計輸入，不是current roadmap。建議：

- 未完成且仍有效：移入新的 milestone，明列 owner/status/supersedes。
- 已完成/失效：移 `docs/history/plans/`。
- 被本次BDD重構取代：加 `Superseded by docs/plans/2026-08-11-bdd-led-refactor.md`，不要直接刪除。

## 3. 已證實的矛盾/污染

| ID | 矛盾 | 影響 |
|---|---|---|
| DOC-01 | `AI_AGENT_ROLE`要求90% accuracy，策略排序實際定義ROI→低DD→DQ→PF | AI可能追錯metric並不斷加gate |
| DOC-02 | personal-release policy寫34/50，runtime artifact曾為24/50 | stale文字可能壓過request-time truth |
| DOC-03 | strategy guide含特定模型結論與錯誤owner名稱 | 歷史研究被重複當永久決策 |
| DOC-04 | PRD把當時runtime metrics放進產品需求 | requirement與status無法區分 |
| DOC-05 | ORID名為decisions但每輪overwrite | 無法追蹤真正決策與supersede chain |
| DOC-06 | heartbeat強調no-collect，runner仍可做資料maintenance write | 操作名稱與side effect不符 |
| DOC-07 | PM的72h forced-execution是delivery rule，copy容易像execution gate | AI可能把PM流程誤當交易許可/阻塞 |
| DOC-08 | generated analysis未以日期/generation命名 | 不同semantic bucket世代混用 |
| DOC-09 | docs topology checker只驗「在哪裡」，不驗「是什麼類型/權威」 | 文件放對資料夾仍可污染判斷 |
| DOC-10 | tests大量assert humanized tokens/copy | 重構投影時容易把copy穩定誤作domain contract |

## 4. Proposed documentation topology

```text
README.md                         # product entry only
PRD.md                            # evergreen product requirements
AGENTS.md                         # short discovery map

docs/
  README.md                       # authority-aware index
  specification/
    README.md
    as-is-architecture.md
    as-is-gating-lineage.md
    documentation-inventory.md
    open-questions.md
    features/as-is/*.feature
    features/to-be/*.feature      # owner批准後建立
  policy/
    execution-safety.md
    personal-release.md
    evidence-and-promotion.md
  runbooks/
    heartbeat-fast.md
    heartbeat-slow.md
    paper-shadow.md
    live-canary.md
  adr/
    ADR-0001-*.md
  evidence/<domain>/<date>/...
  status/                         # generated, short TTL, never authority
  plans/
  history/

data/
  artifacts/<type>/<generation>.json
  latest/<type>.json              # pointer/manifest
```

## 5. Authority hierarchy（proposed）

高到低：

1. **Order boundary enforcement**：ExecutionAuthorizer/DB unique invariants/venue responses。
2. **Immutable registries**：strategy release、bundle、permit、run/order lifecycle。
3. **Canonical DB facts**：帶schema/version/source的raw/features/labels/trades。
4. **Immutable DecisionSnapshot**：同generation聚合的gate results。
5. **API projections**：只能投影4，不可重算授權。
6. **Generated artifacts/status**：帶TTL/provenance，stale即unknown/reference-only。
7. **Docs/runbooks/history**：說明用途，永不授權live action。

若兩個來源衝突：高層不一定「覆蓋」低層，而是回 `inconsistent_generation` 並fail-closed；禁止用 `or` fallback靜默選一個看起來比較完整的值。

## 6. 文件整理執行順序

1. 新增specification taxonomy與index，不移動舊檔。
2. 將舊檔標上type/authority/TTL/superseded metadata。
3. 把runtime literals從policy/PRD抽出。
4. 建立ADR格式與真正decision ledger。
5. heartbeat改寫immutable artifacts + latest manifest；停止每輪大幅覆寫root docs。
6. 更新doc topology checker：除了位置，也驗type/authority frontmatter。
7. 最後才archive重複文件；保留Git history與redirect。
