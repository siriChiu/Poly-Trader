# ADR-0001：近期實戰完成定義為受監督 Live Canary

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q1回答「Live canary」
- Scope: Poly-Trader BDD-led refactor
- Supersedes: 過去文件中未分層使用的「實戰／live ready／可部署」敘事

## Context

現有文件與UI把「實戰」混用於人工訊號、Paper/Shadow、manual trade、live canary及full-auto execution。這使工程團隊無法定義何時算重構完成，也讓研究證據、owner release、runtime binding和order authorization被壓縮成同一個readiness詞彙。

截至本決策，Paper/Shadow鏈可運行；non-dry live order則由ExecutionService fail closed。系統尚未有完整production permit issuance/transport journey、exact loaded bundle attestation與真實venue lifecycle proof。

## Decision

本次重構的近期「實戰完成」定義為：

> **極小額、單層、人工監督的真實 Live Canary。**

Paper/Shadow是必要前置能力，但不是本階段最終完成條件。Full Auto Live是後續獨立里程碑，不納入本階段Definition of Done。

## Live Canary產品邊界

### In scope

- 真實venue上的極小額risk-on order；
- 最多單一pyramid layer；
- 每次risk-on order都需要operator supervision與短效single-use authorization；
- exact owner-released strategy/bundle identity；
- 明確symbol allowlist與symbol-specific quantity/notional cap；
- current market snapshot與quote freshness；
- kill switch、model-health breaker、daily loss/failure halt及global/per-strategy exposure controls；
- atomic order intent/idempotency；
- venue preview、submit acknowledgement、fill/partial fill/cancel/reject與reconciliation；
- 可用且不被risk-on gate錯誤封鎖的受控risk-off/reduce exit；
- API/UI必須清楚顯示armed、authorized、submitted、acknowledged及terminal/reconcile狀態。

### Out of scope

- 無人監督的自動risk-on下單；
- 第二或第三層自動加倉；
- 全自動出入場與全天候資金管理；
- 以historical OOS、owner personal release、support ratio或readiness projection直接代替order permit；
- 為了讓canary變綠而降低kill switch、breaker、quote freshness、曝險、idempotency、venue lifecycle或permit要求。

## Acceptance invariants

1. 若exact bundle、current decision generation、venue capability、fresh quote或hard safety任一unknown/stale/mismatch，risk-on fail closed。
2. Owner release只接受evidence risk，不簽發order authorization。
3. Live config必須明確為`mode=live`、`enable_live_trading=true`、`dry_run=false`。
4. Canary policy必須明確enabled，allowlist不得為空，且具有symbol-specific cap。
5. 每筆risk-on order必須帶綁定order、bundle、decision generation、venue、TTL與nonce的single-use permit。
6. OrderIntent必須有DB-level原子idempotency，不能只用check-then-insert。
7. 本地accepted不等於venue fill；必須持久化並投影完整lifecycle。
8. Risk-on blocked時，wait/diagnostics及安全的reduce/sell path仍可用。
9. CI與BDD verification不得送真單；真正canary只在owner明確arm、credentials配置與preflight全部通過後執行。
10. Full Auto Live不得因Live Canary完成而被自動標成ready。

## Human-supervision boundary

本ADR只決定「必須人工監督」，不決定authorization入口。以下留給Q9：

- manual UI二次確認後簽發單次permit；或
- 受管worker提出intent、operator arm/approve後簽發permit。

兩者都不得讓frontend自行簽permit，也不得繞過ExecutionAuthorizer。

## Consequences

- Refactor Definition of Done以一條可驗證的bounded live-canary journey為核心。
- API、UI與文件要分別標示Paper/Shadow、Live Canary與Full Auto，而不是共用`live_ready`。
- Permit issuer、exact bundle attestation、atomic intent與venue lifecycle從future nice-to-have升為本階段必要能力。
- 多層pyramid與無人監督automation不應阻塞Live Canary milestone。
- Q2–Q10仍需逐題確認；後續ADR不得改寫本ADR，只能supersede並說明原因。

## Executable specification

- `docs/specification/features/to-be/live-canary-product-scope.feature`
- As-is safety characterization：`docs/specification/features/as-is/execution-authorization.feature`
- Migration plan：`docs/plans/2026-08-11-bdd-led-refactor.md`
