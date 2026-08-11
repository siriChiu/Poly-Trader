# Poly-Trader BDD 與重構規格中心

> 狀態：**AS-IS CHARACTERIZATION DRAFT**
> 觀測日期：2026-08-11
> 穩定基線：`9e973bba9aa3c01aece12b18d1229f3e13c49e91`
> 文件分支：`docs/bdd-baseline-20260811`
> 這個目錄不是 live release authority，也不得用來放行真實下單。

## 1. 目的

這組文件先忠實描述 Poly-Trader **現在如何運作**，再以可測試的 Given/When/Then 契約支撐後續重構。它解決三個問題：

1. 不再把 strategy evidence、owner release、runtime binding、execution safety 與 venue readiness 混成單一 `deployable`。
2. 不再讓不同世代的 config、DB、JSON artifact、API projection 與 Markdown 同時冒充「最新真相」。
3. 保留真正保護資金的 hard gates，同時移除重複推導、歷史文件污染、隱性 fallback 與無 owner gate。

## 2. 分析邊界

本次分析刻意保留三個觀測面，不把它們混在一起：

| 觀測面 | 定義 | 用途 |
|---|---|---|
| committed baseline | `HEAD == origin/main == 9e973bba` | 可重現、可審查的穩定程式基線 |
| dirty WIP | 原 worktree 中未提交 code/docs/artifacts | 只作「候選現況」與衝突偵測，不視為產品契約 |
| runtime truth | DB、process、config/env、request-time API、帶 `generated_at` artifact | 判斷實際運行狀態；必須帶 provenance/freshness |

截至觀測時，原 worktree 有約 52 個 tracked dirty files，並混有 heartbeat code、OKX adapter、tests、current-state docs 與 runtime artifacts。這就是為何文件工作在獨立 worktree 完成。

## 3. 閱讀順序

1. [`as-is-architecture.md`](as-is-architecture.md) — bounded contexts、資料流、god modules、truth stores。
2. [`as-is-gating-lineage.md`](as-is-gating-lineage.md) — 每個 gate 的 owner、輸入、輸出、重複推導與 deadlock。
3. [`features/as-is/`](features/as-is/) — executable characterization BDD。
4. [`documentation-inventory.md`](documentation-inventory.md) — 文件分類、權威層級、歷史污染與遷移建議。
5. [`open-questions.md`](open-questions.md) — 必須由 owner 決定的產品邊界；實際對話一次只問一題。
6. [`../plans/2026-08-11-bdd-led-refactor.md`](../plans/2026-08-11-bdd-led-refactor.md) — proposed refactor，需 BDD 確認後才執行。
7. [`../adr/ADR-0001-live-canary-product-scope.md`](../adr/ADR-0001-live-canary-product-scope.md) — Q1已接受的近期實戰範圍。
8. [`features/to-be/live-canary-product-scope.feature`](features/to-be/live-canary-product-scope.feature) — 第一份owner-approved to-be BDD。

## 4. BDD coverage

| Feature | Scenarios | 核心範圍 |
|---|---:|---|
| `data-feature-lineage.feature` | 16 | symbol、4H、point-in-time backfill、missingness、feature/label versions、training join |
| `strategy-evidence-and-lab.feature` | 12 | OOS、ranking、saved strategies、cache/refresh |
| `personal-release-and-runtime-binding.feature` | 11 | owner decision、support warning、exact bundle identity |
| `current-signal-and-position-capacity.feature` | 11 | regime、entry quality、layers、DQ/technical caps |
| `circuit-breaker-and-risk.feature` | 9 | model outcome breaker vs realized execution risk |
| `execution-authorization.feature` | 16 | live triple、canary、permit、risk-off gaps |
| `venue-order-lifecycle.feature` | 14 | normalization、freshness、ack/fill/cancel/reconcile、position attribution |
| `paper-shadow-and-worker.feature` | 12 | candidate identity、outcomes、duplicates、liveness |
| `promotion-state-machine.feature` | 13 | evidence/release/binding/market/order dimensions、explicit-zero fallback |
| `heartbeat-and-artifact-freshness.feature` | 11 | fast/slow lanes、TTL/semantic freshness、publication |
| `api-ui-projection-and-performance.feature` | 13 | aggregate generation、latency、Strategy Lab/UI boundaries |
| `documentation-and-ai-truth.feature` | 12 | authority、TTL、historical isolation、agent feedback |
| **Total** | **150** | 12 bounded behavior groups |

To-be owner-approved coverage：

| Feature | Scenarios | Decision |
|---|---:|---|
| `features/to-be/live-canary-product-scope.feature` | 13 | ADR-0001 / Q1 accepted |
| `features/to-be/personal-release-lifecycle.feature` | 13 | ADR-0002 / Q2 accepted |
| `features/to-be/exact-support-advisory.feature` | 14 | ADR-0003 / Q3 accepted |
| `features/to-be/decision-snapshot-truth.feature` | 16 | ADR-0004 / Q4 accepted |
| `features/to-be/autonomous-model-improvement.feature` | 21 | ADR-0005 / Q5 accepted |
| `features/to-be/immutable-deployment-bundle.feature` | 19 | ADR-0006 / Q6 accepted |
| `features/to-be/exact-bundle-shadow-evidence.feature` | 15 | ADR-0007 / Q7 accepted |
| **Total** | **111** | 7 owner-approved feature groups |

## 5. Owner decision status

| Question | Status | Decision |
|---|---|---|
| Q1 實戰完成層級 | **ACCEPTED** | 受監督、極小額、單層Live Canary |
| Q2 Owner release生命週期 | **ACCEPTED** | 永久有效；只有Owner手動撤銷 |
| Q3 Exact support gate | **ACCEPTED** | 純信心警告；不阻止極小額單層canary |
| Q4 Current truth | **ACCEPTED** | 一張完整狀態單供API/UI/docs共同顯示 |
| Q5 Heartbeat autonomy | **ACCEPTED** | 自動資料、訓練、比較、shadow候選與狀態更新；不自動改code/live bundle |
| Q6 Runtime binding | **ACCEPTED** | 完整immutable bundle；新版本同步驗證後由Owner決定切換 |
| Q7 Shadow evidence identity | **ACCEPTED** | 只用exact bundle自己的成績；其他只能參考 |
| Q8–Q10 | `PENDING_OWNER` | 一次只問一題 |

## 6. BDD 狀態標籤

| Tag | 意義 |
|---|---|
| `@as_is` | 現行行為，重構前應先用 characterization test 固定 |
| `@safety` | 資金／訂單安全 invariant，不得因簡化 gate 而移除 |
| `@known_gap` | 程式目前缺少或只部分實作，不能冒充已滿足 |
| `@known_inconsistency` | 兩個現行 projection 或 policy 計算不一致 |
| `@generated_state` | 依賴時變 artifact；不得作 evergreen policy |
| `@owner_decision` | 需要使用者裁決後才能形成 to-be BDD |

## 7. 核心語彙

- **StrategyEvidence**：OOS、walk-forward、ROI、drawdown、profit factor、trade count 等研究證據。
- **PersonalRelease**：owner 接受策略證據風險供個人使用；不是 execution permit。
- **RuntimeBinding**：運行中的 fitted model、feature schema、target、策略參數與核准版本完全一致。
- **ExecutionAuthorization**：某一筆訂單在當下通過 live config、risk、canary、permit、quote 與 idempotency 邊界。
- **VenueReadiness**：交易所 credentials、metadata、ack/fill/cancel/reconcile 的實際能力證明。
- **DecisionSnapshot**：to-be 建議的單一、不可變、帶 provenance 的決策快照；目前尚未存在。
- **Projection**：API/UI/Markdown 對 authoritative state 的衍生呈現，不能反向成為 release authority。

## 8. 重構啟動條件

在下列事項完成前，不修改交易核心：

- as-is BDD 與 source/test 對齊；
- owner 逐題確認 `open-questions.md` 中的產品邊界；
- 產生並批准 to-be BDD；
- 對 hard safety invariants 建立可重跑測試；
- 對現有 dirty WIP 決定保留、拆分或捨棄。

重構的成功不是「讓所有 gate 變綠」，而是：**每個 gate 只有一個 owner、一個權威輸入、一個具型別輸出、一個 release condition，而且 UI/AI 只能讀 projection，不能從歷史文字猜授權。**
