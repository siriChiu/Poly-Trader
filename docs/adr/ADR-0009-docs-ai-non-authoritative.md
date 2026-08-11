# ADR-0009：文件與AI不得直接授權下單

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q8選擇「不可以；文件與AI只能解釋、提醒和提出修改，真正下單只相信正式設定、核准紀錄與單次許可」
- Scope: Docs、AI、chat instruction與execution authority邊界
- Related: ADR-0002 Owner release；ADR-0004 DecisionSnapshot；ADR-0006 DeploymentBundle

## 白話背景

文件、AI回答與聊天內容可能過期、被誤讀或缺少完整上下文。如果一句「可以交易」就能直接放行真實訂單，舊PRD、generated report、AI summary或聊天誤會都可能影響資金。

另一方面，AI仍應幫忙分析、提醒、提出修改與執行經核准的工程工作。因此要把「說明／建議」和「正式機器授權」分開。

## Decision

> **文件、Markdown、AI文字與一般聊天指令都不是execution authority。真正的risk-on order只接受有版本的machine policy、可驗證Owner decision record、exact DeploymentBundle、fresh DecisionSnapshot與短效單次permit。**

## 三層責任

### 1. 文件與AI：說明、提醒、提案

可以：

- 解釋目前狀態與blocked reasons；
- 比較模型與產生白話報告；
- 提醒資料過期、風險或模型改善；
- 撰寫ADR、BDD、runbook與change proposal；
- 經正常review/test/deploy流程修改code或machine policy；
- 引導Owner進入正式核准、撤銷、切換或permit UI。

不可以：

- 解析Markdown中的`READY`、`approved`或數字直接放行；
- 把AI summary當release record；
- 用聊天句子直接切live bundle、提高cap或簽permit；
- 以generated report覆蓋runtime gate；
- 取得或展示交易所secret。

### 2. 正式治理記錄：Owner決策

Owner release、revocation、bundle switch、風險上限變更必須經authenticated product action或等價正式workflow，產生：

- stable decision ID；
- actor identity；
- target bundle/policy ID；
- decision type與reason；
- timestamp與generation；
- append-only audit record。

聊天可作決策來源與提案，但在execution system中必須轉成上述record；未轉換前不具live authority。

### 3. 每筆order：ExecutionAuthorizer

Risk-on order必須同時驗證：

- versioned machine-readable execution policy；
- active Owner release/switch record；
- exact bundle binding；
- fresh active DecisionSnapshot；
- current signal與entry eligibility；
- R1 capital/daily-loss/failure limits；
- fresh quote、venue/account/instrument capability；
- kill switch、breaker、exposure與lifecycle health；
- signed、short-lived、exact-order-bound、single-use permit；
- DB-level idempotency。

任何AI文字、文件內容或單一`ready=true`都不能替代其中一項。

## Authority優先順序

Execution authority：

```text
Venue/order ledger truth
  > ExecutionAuthorizer + versioned machine policy
  > authenticated Owner decision registry
  > active immutable DecisionSnapshot projection
  > generated reports / AI summaries / evergreen docs
```

這不是說文件不重要；文件定義應有行為並支撐review，但runtime不能靠自然語言猜測授權。

## 衝突處理

若文件或AI說READY，但machine state說BLOCKED：

- risk-on保持BLOCKED；
- UI顯示source conflict與兩邊as-of；
- 建立文件或projection修正工作；
- 不修改machine state來配合文字。

若文件說BLOCKED但machine state READY：

- 不因舊文字改寫runtime；
- UI不把舊文件當current truth；
- generated current-state docs應從同一DecisionSnapshot重建。

## AI提出修改的正式流程

1. AI建立清楚proposal、原因、風險與BDD。
2. 變更machine policy/code時加入tests與version bump。
3. Owner在適當層級review/approve。
4. CI與safety tests通過。
5. 以可回復deployment發布。
6. 新DecisionSnapshot引用新的policy version。
7. Live order仍需每筆permit。

AI不能跳過中間步驟直接改正在運作的gate。Heartbeat依ADR-0005也不能自動patch code或交易規則。

## 緊急停止

Kill switch是例外方向但仍是machine action：

- Docs/AI可以強烈建議停止；
- Owner或受權系統可透過authenticated command啟動kill switch；
- 啟動後立即阻止risk-on；
- 單靠文字不改runtime；
- 解除kill switch需要正式、可稽核且不低於啟動權限的action。

## API與UI

- Current-state GET endpoints只讀DecisionSnapshot，不解析docs或呼叫LLM決定gate。
- UI把「AI建議」、「Owner核准」、「Machine blocker」、「Permit狀態」分開顯示。
- 所有AI內容標generated at、source snapshot ID與`non-authoritative`。
- Owner action UI顯示實際會建立的record與影響範圍，再要求明確確認。

## Consequences

- 移除PRD literal、Markdown與AI summary對runtime gate的隱性依賴。
- AI仍能幫助系統成長，但無法用自然語言繞過hard safety。
- 正式Owner journey與permit service成為必要產品能力。
- 文件錯誤會造成觀測問題，但不直接造成真實order authorization。

## Executable specification

- `docs/specification/features/to-be/docs-ai-non-authoritative.feature`
- As-is characterization：`docs/specification/features/as-is/documentation-and-ai-truth.feature`
- Execution characterization：`docs/specification/features/as-is/execution-authorization.feature`
