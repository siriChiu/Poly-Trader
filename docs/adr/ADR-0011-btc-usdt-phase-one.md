# ADR-0011：第一階段只支援BTC/USDT並保留Multi-Symbol擴充能力

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q10選擇「第一階段只允許BTC/USDT；其他幣明確拒絕，保留未來擴充能力」
- Scope: Phase-1 symbol policy、data partition與Live Canary venue scope
- Related: ADR-0006 DeploymentBundle；ADR-0008/R1 Live Canary risk

## 白話背景

目前程式部分API與schema看似接受任意symbol，但4H fetch硬寫BTC/USDT，training merge也可能沒有按symbol分區。這會造成最危險的假支援：使用者填ETH，系統卻拿BTC的4H資料、label或模型做決策。

第一階段先把一個symbol從資料、模型、決策到order lifecycle完整做對，比同時假裝支援多幣安全且可驗證。

## Decision

> **Phase 1唯一允許的交易symbol是`BTC/USDT` spot。任何其他symbol在進入fetch、feature、training、prediction、bundle、permit或venue order前都要明確拒絕。Schema與所有identity仍保留symbol欄位與partition key，未來可新增真正multi-symbol能力。**

## Canonical symbol

內部canonical identity：

```text
base_asset = BTC
quote_asset = USDT
market_type = spot
canonical_symbol = BTC/USDT
```

可在輸入邊界接受明確alias，例如`BTC-USDT`或venue instrument ID，normalize後必須得到同一canonical identity。模糊、未知或不同market type不得猜測。

## 明確拒絕規則

下列任一收到非BTC/USDT時，回傳stable `UNSUPPORTED_SYMBOL_PHASE_1`或等價typed error，且不得執行後續side effect：

- market data/4H fetch；
- historical backfill；
- feature與label materialization；
- training dataset selection；
- automatic model-improvement job；
- prediction/current signal；
- strategy save/deployment bundle build；
- DecisionSnapshot publication；
- manual preview與permit issuance；
- ExecutionAuthorizer與venue adapter。

不得：

- fallback到BTC；
- 回傳BTC數值但保留request symbol；
- 把不同symbol rows merge/forward-fill；
- 用BTC model或support替其他symbol放行；
- 在UI顯示可選但後端偷偷normalize成BTC。

## Data與training contract

即使只有BTC，所有facts仍顯式帶：

- canonical symbol；
- venue/instrument ID；
- market type；
- event time與as-of；
- source與generation。

Join/partition keys必須含symbol：

- 1min與4H as-of join；
- features與labels；
- training rows與walk-forward splits；
- predictions/intents/outcomes；
- leaderboard metrics與support。

這可防止未來擴充時沿用現在的cross-symbol bug。

## 4H與Backfill

- 4H fetcher接收canonical symbol parameter，不在深層helper硬寫BTC。
- Phase-1 guard只允許BTC/USDT通過。
- Historical 4H features使用每個row當時可知的closed candles，不能用目前最新4H snapshot回填過去。
- Non-BTC request在任何network call或DB write前拒絕。

## Bundle、Snapshot與Order

以下identity都必須明確包含BTC/USDT spot：

- dataset snapshot；
- DeploymentBundle manifest；
- Owner release subject；
- Paper/Shadow evidence；
- DecisionSnapshot；
- OrderIntentPreview、permit與OrderIntent；
- venue client order ID mapping；
- order/position ledger attribution。

任何symbol mismatch risk-on fail closed；permit不得被改成其他symbol。

## API與UI

- UI Phase 1只提供BTC/USDT，不顯示可用的ETH或其他選項。
- API收到其他symbol回傳4xx typed error與白話說明。
- Strategy Lab可以保留未來symbol欄位，但只允許BTC/USDT experiment進正式pipeline。
- Historical non-BTC資料可保留作研究/遷移，不刪除；不得冒充Phase-1 supported evidence。
- Docs清楚標示「目前只支援BTC/USDT spot」。

## R1全域風險

即使未來開放multi-symbol，ADR-0008/R1的25 USDT/0.5%是全部Live Canary合計上限，不會自動變成每個symbol各一份。未來擴充需要新的Owner風險決策。

## 未來擴充條件

新增第二個symbol前必須有新的ADR與BDD，至少驗證：

- symbol-aware fetch與point-in-time data；
- per-symbol features/labels/training；
- independent bundle/evidence/position attribution；
- portfolio-level exposure與correlation policy；
- venue instrument metadata與minimums；
- UI、API、worker與reconciliation end-to-end；
- 不同symbol並行時的R1替代或擴充風險上限。

不需要移除symbol abstraction；目前就用正確partitioning為未來鋪路。

## Consequences

- 第一階段scope縮小但真實journey更可信。
- ETH等request不再得到混入BTC資料的假結果。
- 現行hard-coded BTC helper要改成「參數化fetcher＋明確Phase-1 guard」。
- 所有新table/records/contracts保留symbol identity。
- Multi-symbol是後續產品milestone，不是隱性半支援。

## Executable specification

- `docs/specification/features/to-be/btc-usdt-phase-one.feature`
- As-is data characterization：`docs/specification/features/as-is/data-feature-lineage.feature`
- As-is venue characterization：`docs/specification/features/as-is/venue-order-lifecycle.feature`
