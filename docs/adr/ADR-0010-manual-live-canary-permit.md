# ADR-0010：Manual Live Canary採雙步確認與單次Permit

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q9選擇「畫面顯示完整模型、金額與風險，你再次確認後取得只限這一筆的一次性許可」
- Scope: Manual supervised Live Canary正式產品旅程
- Related: ADR-0001、ADR-0004、ADR-0006、ADR-0008/R1、ADR-0009

## 白話背景

現行`/api/trade`有manual buy入口，但不傳execution permit；ExecutionService對non-dry order要求permit，因此按鈕與真正送單邊界沒有完整接通。

Owner已選擇受監督Live Canary。正式旅程必須讓Owner清楚看到「哪個模型、買什麼、多少錢、剩多少風險」，再次確認後只授權該筆order，而不是給一張可任意使用的通行證。

## Decision

> **Manual Live Canary是正式產品旅程。UI先建立只讀preview並顯示完整資料；已驗證Owner再次確認後，PermitService才可簽發綁定exact order的短效單次permit。ExecutionAuthorizer在送單前仍重新驗證所有hard safety。**

## 兩步旅程

### 第一步：Preview

Owner按「準備Live Canary」時，系統建立immutable `OrderIntentPreview`，顯示：

- exact DeploymentBundle ID、model名稱/版本與Owner release；
- active DecisionSnapshot ID、generated at與valid until；
- venue/account（mask敏感資料）、symbol、side、order type；
- fresh quote、quote as-of與允許價格偏移；
- requested notional、estimated fees、slippage buffer與normalized quantity；
- R1 order/total cap、existing exposure與remaining capacity；
- UTC daily realized loss、remaining loss budget與failure count；
- single-layer狀態、open orders/positions；
- signal/actionability與所有warning/blocker；
- permit預計TTL與「本次只授權一筆」說明。

Preview不簽permit、不送單、不保證稍後一定能交易。

### 第二步：再次確認

Owner在authenticated session明確確認preview內容後：

1. Server驗證Owner identity、session與anti-CSRF。
2. 重新讀active snapshot、fresh quote、equity、exposure、kill switch、breaker、venue與ledger。
3. 重新計算R1 cap、fees、slippage與normalized order。
4. 驗證preview與現在仍是同bundle/snapshot/order semantics。
5. 若任何重要內容改變，拒絕原確認並建立新preview。
6. 全部通過才建立persistent OrderIntent與簽發permit。
7. ExecutionAuthorizer原子消耗permit/nonce並最多呼叫venue一次。

## Permit綁定內容

Permit至少綁定：

- permit ID與single-use nonce；
- authenticated Owner/actor ID；
- exact OrderIntent ID與preview ID；
- bundle ID與content hash；
- DecisionSnapshot ID/generation；
- execution policy與R1 risk policy versions；
- venue、account ID、symbol；
- side、order type與time-in-force；
- exact normalized quantity與maximum quote notional；
- quote ID/as-of與允許price/slippage bound；
- issued at、expires at與短TTL；
- signer/key ID與signature/MAC。

不得簽發「此bundle任何order都可以」的blanket permit。

## Single-use與併發

- Permit nonce在DB中原子標記consumed。
- 同一permit的browser retry、worker retry或並發request只能有一個進入adapter。
- Permit過期、已使用、signature錯誤或order payload不同時拒絕。
- 使用失敗後不可把同一permit改給另一筆order。
- Venue timeout/UNKNOWN使用同一OrderIntent與client order ID先reconcile，不重新簽permit盲目重送。

## 狀態改變與重新確認

下列任一變化使原preview/confirmation失效：

- active bundle或snapshot改變；
- quote過期或價格偏移超過bound；
- cap/equity/exposure/daily loss/failure count改變；
- kill switch、breaker或venue health改變；
- 新open order/position令single-layer不再成立；
- instrument metadata、normalized quantity或fees改變；
- Owner release被撤銷；
- permit TTL到期。

UI顯示白話原因並要求重新preview；不能靜默套用新的內容。

## 成交與receipt

確認成功不等於成交：

- 先顯示intent created / permit issued / submitted / venue acknowledged等明確狀態；
- ack、partial fill、fill、cancel、reject與unknown分開保存；
- 每個state引用order intent、permit、bundle與venue IDs；
- 最終成交/持倉以venue reconciliation與ledger為準；
- UI提供可追蹤receipt，不用「成功」掩蓋只是local submit。

## 權限與AI邊界

- 只有authenticated Owner/被明確授權operator能作第二步確認。
- AI可以解釋preview與警告，但不能代按確認、簽permit或重放nonce。
- GET/current-state/preview endpoint沒有live side effect。
- Owner聊天決策不是permit；每筆真實risk-on仍需正式確認。

## Risk-off

Cancel、reduce、exit與reconcile必須有正式authenticated risk-off contract，但不能要求risk-on entry eligibility。Risk-off action也要exact order/position identity、idempotency與audit，避免誤操作。

## Consequences

- 取代或重構現行dead-end manual route，使UI與ExecutionService使用同一permit contract。
- Manual與未來worker path都走同一ExecutionAuthorizer，不建立繞道。
- UI需要preview、confirm、expired/reconfirm、receipt與reconciliation states。
- Live Canary可受監督、可稽核且不會因double-click重複下單。

## Executable specification

- `docs/specification/features/to-be/manual-live-canary-permit.feature`
- As-is execution characterization：`docs/specification/features/as-is/execution-authorization.feature`
- As-is lifecycle characterization：`docs/specification/features/as-is/venue-order-lifecycle.feature`
