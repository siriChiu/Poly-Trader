# ADR-0008：Live Canary採保守資金與停手機制

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision ID: **R1（補充Owner風險決策）**
- Decision source: 本次BDD owner Q&A，Live Canary數值方案回答「保守方案」
- Scope: 極小額單層Live Canary資金、日損與送單失敗上限
- Related: ADR-0001 supervised Live Canary；ADR-0006 immutable bundle

## Owner接受的數值

> **每筆risk-on order與全部Live Canary gross exposure上限：`min(25 USDT, account equity × 0.5%)`。**

> **UTC單日實現虧損上限：`min(10 USDT, start-of-day account equity × 0.25%)`。**

> **連續2次真實送單失敗後停止新的risk-on order。**

若計算後的可用金額低於交易所minimum order，系統不交易，不能自行把金額調高。

## 白話邊界

這是第一階段極小額Live Canary，不是一般實盤資金配置：

- 只允許一層；
- 同一時間不得用多筆order繞過總上限；
- 上限是天花板，不是下單目標；模型可選擇HOLD；
- Owner或operator可以隨時再縮小或暫停；
- 提高任何上限需要新的Owner決策；
- Hard safety、permit、idempotency與venue lifecycle仍全部強制。

## 金額計算

每次authorization使用同一DecisionSnapshot的fresh account equity：

```text
order_and_total_cap = min(25 USDT, account_equity * 0.005)
daily_realized_loss_cap = min(10 USDT, start_of_utc_day_equity * 0.0025)
```

要求：

- account equity必須fresh且來自核准venue/account；
- `0`是合法值，不可fallback成舊的正值；
- missing、stale或負數equity時risk-on fail closed；
- order notional、estimated fees與保守slippage buffer合計不得超過cap；
- quantity/lot rounding後重新驗證，不能因向上rounding超限；
- open orders的reserved quote與existing canary position notional都計入總曝險；
- 多symbol時所有Live Canary gross exposure合計仍受25 USDT/0.5%全域cap；Q10另決定symbol policy。

## 交易所minimum order

- 先取得fresh instrument metadata與minimum notional/quantity。
- 若安全cap低於minimum order，狀態為`BELOW_VENUE_MINIMUM`。
- 不送單、不向上調金額、不把多次小單合併繞過cap。
- UI白話顯示「安全上限低於交易所最低下單額，因此沒有交易」。

## 單層與總曝險

- Risk-on最多一層。
- 若已有open risk-on order、reserved quote或spot position，不得再開第二層。
- Position因市場上漲而mark-to-market超過cap時，停止新的risk-on；不因超限本身強迫賣出。
- 取消、減倉、關閉與reconcile走risk-off path，不能被cap阻止。
- Position attribution必須引用exact bundle與order lifecycle ledger。

## 單日虧損停止

- 日界線使用UTC 00:00，符合24/7 crypto市場且容易稽核。
- Start-of-day equity固定在該UTC日第一個fresh snapshot，不在日內重算門檻。
- Daily realized PnL包含成交損益與fees；資料missing/unknown時停止新risk-on直到reconcile。
- 達到或超過`min(10 USDT, 0.25%)`時，當日新的risk-on capacity=0。
- UTC新日可重置daily counter，但若ledger/reconciliation仍不健康，保持blocked。
- Unrealized loss與mark-to-market risk由current exposure/risk policy獨立顯示；不得用daily reset隱藏。

## 連續送單失敗停止

計入真實non-dry Live Canary attempts：

- venue reject；
- authentication/permission failure；
- normalization後仍被venue拒絕；
- network/timeout且經reconciliation確認未接受；
- lifecycle進入可確認的FAILED terminal state。

規則：

- 第1次失敗：warning，仍可在問題修復且state清楚後再次嘗試。
- 第2次連續失敗：failure halt active，禁止新的risk-on。
- 一次經venue確認的successful ack可重置連續failure counter，但UNKNOWN不能當成功。
- Timeout/unknown outcome先立即停止重試並reconcile，避免duplicate；確認結果後才決定counter。
- Paper/Shadow或dry-run failure不增加live failure counter。
- Failure halt解除需operator確認問題已修復並留下audit record；不能由truthy config fallback自動清除。

## Risk-on與Risk-off不對稱

被cap、daily loss或failure halt阻止時：

- 禁止：新買單、增加曝險、第二層、retry unknown order。
- 允許且優先：cancel open orders、reduce/exit、fetch order status、reconcile、同步position與停用live。

所有risk-off行為仍需身份驗證、idempotency與venue lifecycle，但不能要求risk-on entry gate。

## 狀態與通知

DecisionSnapshot與UI顯示：

- fresh equity與as-of；
- 固定25/10 USDT與0.5%/0.25%兩邊計算值；
- 最終取較小結果；
- existing exposure、reserved amount、remaining capacity；
- daily realized loss與remaining loss budget；
- consecutive live failures；
- stable block/warning reason codes。

達日損、第二次failure或below-minimum時通知Owner，但不反覆spam。

## Executable specification

- `docs/specification/features/to-be/conservative-live-canary-risk.feature`
- As-is risk characterization：`docs/specification/features/as-is/circuit-breaker-and-risk.feature`
- As-is execution characterization：`docs/specification/features/as-is/execution-authorization.feature`
