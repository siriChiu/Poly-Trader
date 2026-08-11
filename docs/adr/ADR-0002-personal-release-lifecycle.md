# ADR-0002：Owner Personal Release永久有效且只可手動撤銷

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q2回答「永久有效，只有你手動撤銷」
- Scope: Owner personal-use strategy release lifecycle
- Related: ADR-0001 Live Canary product scope

## Context

現行系統會把strategy evidence、rolling support、runtime binding、current market eligibility與execution safety投影到同一組readiness欄位。若任一runtime artifact或rolling metric能撤銷owner release，owner的治理決策就會被heartbeat、fallback或市場狀態反覆覆寫。

另一方面，永久release不能被誤讀為永久live authorization。Strategy release、runtime binding與每筆order permit必須保持獨立。

## Decision

> **Owner personal release永久有效，只有Owner能以明確手動決策撤銷。**

沒有自動到期日。Support不足、模型近期表現惡化、circuit breaker、stale artifact、runtime binding失敗、venue unavailable或current market HOLD都不得把release record改成revoked。

## Scope boundaries

本ADR決定release的**生命週期與撤銷權限**，不決定完整identity欄位；runtime binding identity由Q6另行確認。

安全邊界如下：

- Release必須有明確subject/selector；不得因「永久」而自動套用到不同strategy/model identity。
- Identity改變且不符合原subject時，結果是`release_not_applicable`或`runtime_binding_mismatch`，不是把舊release撤銷，也不是讓新identity繼承release。
- Owner若要核准新identity，建立新的release decision record。

## Required state model

Release lifecycle至少包含：

- `ACTIVE`：owner release有效；
- `REVOKED`：owner明確撤銷；
- `NOT_APPLICABLE`：查詢subject與release identity不符；
- `UNKNOWN`：record無法驗證，execution fail closed。

Evidence與technical runtime狀態使用獨立欄位：

- `evidence_status`；
- `runtime_binding_status`；
- `market_actionability`；
- `execution_authorization`。

它們不得反向改寫`release_status`。

## Manual revocation contract

撤銷必須：

1. 由已驗證Owner identity明確觸發；
2. 引用原release decision ID；
3. 寫入append-only revocation record；
4. 包含`revoked_at`、actor、reason與new generation ID；
5. 立即阻止該release的新risk-on authorization；
6. 保留wait/diagnostics與安全risk-off/reduce path；
7. 不刪除原release record與historical audit trail。

Heartbeat、PM agent、runtime probe、UI、support artifact、model retraining job與venue adapter都無權撤銷。

## Technical blockers while release remains active

以下可以令`allowed_layers/final_capacity=0`或阻止order，但release仍保持`ACTIVE`：

- exact bundle mismatch；
- stale/inconsistent decision generation；
- model-health breaker；
- kill switch/daily loss/failure halt；
- current signal HOLD或entry ineligible；
- live canary policy不完整；
- quote/venue stale；
- credentials或connectivity unavailable；
- permit missing/expired/replayed；
- order lifecycle/reconciliation unhealthy。

## Persistence and projection

- To-be以immutable release registry與append-only revocation records作authority。
- Config可提供migration/default intent，但不能讓舊config覆蓋較新的revocation。
- API/UI/docs只投影registry state與獨立technical blockers。
- Generated artifacts不得把`ACTIVE`改成`REVOKED`，也不得在revoked後以stale cache復活release。

## Consequences

- Rolling evidence惡化只形成warning、review request或owner-approved capacity policy，不自動撤銷。
- 技術安全仍fail closed，因此永久release不會降低Live Canary gate。
- Owner撤銷需要正式、可稽核的產品旅程。
- 未來若需要expiry，只能由新的Owner ADR supersede本決策。

## Executable specification

- `docs/specification/features/to-be/personal-release-lifecycle.feature`
- As-is characterization：`docs/specification/features/as-is/personal-release-and-runtime-binding.feature`
