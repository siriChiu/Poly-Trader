# ADR-0004：用單一完整狀態單作為當前顯示基準

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q4回答「每次先產生一張完整狀態單，API、畫面與文件都只顯示同一張」
- Scope: Current state truth與projection generation
- Technical name: Immutable `DecisionSnapshot`

## 白話背景

目前同一個狀態可能來自設定檔、資料庫、JSON報告、即時probe或API臨時計算。這些來源的時間與版本不同，系統卻可能把它們拼在一起，造成：

- 畫面說可以，送單邊界說不行；
- 新的0被舊的正值覆蓋；
- 新模型配到舊support；
- 舊venue proof被顯示為現在正常；
- 每次刷新API都得到不同generation的混合答案。

## Decision

> **每次決策先產生一張完整、不可修改、有唯一編號與時間的狀態單。API、UI與generated docs只顯示同一張狀態單。**

狀態單技術名稱為`DecisionSnapshot`。它是「目前整體狀態的統一投影」，不是永久資料來源，也不是單筆order permit。

## 狀態單必備內容

每張狀態單至少包含：

- `snapshot_id`與`generation_id`；
- `generated_at`、`valid_until`與建置程式版本；
- symbol、market data as-of、feature schema/target/label versions；
- strategy/release/model/bundle identity；
- owner release狀態；
- evidence與exact support（只作Q3 warning）；
- current signal、market actionability與layer capacity；
- hard risk、kill switch與breaker狀態；
- venue capability、quote/reconciliation freshness；
- 每個輸入來源的identity、as-of與provenance；
- typed reason codes、warning與blocking reasons。

合法的`0`、`false`與空集合必須被保留，不能被truthy fallback換成舊值。

## 產生與發布方式

1. Builder先取得明確版本的所有輸入。
2. 在未公開區完整組裝candidate snapshot。
3. 驗證identity、generation、freshness與schema。
4. 驗證成功後寫入immutable snapshot。
5. 以單一atomic pointer切換`active_snapshot_id`。
6. API/UI/docs只讀active snapshot，不自行再拼資料。

如果建置失敗：

- 不發布半張狀態單；
- 不把candidate部分欄位覆蓋到舊active snapshot；
- 可以繼續顯示上一張，但必須保留原snapshot ID並清楚顯示年齡；
- 上一張超過`valid_until`後顯示STALE/UNKNOWN，risk-on fail closed；
- 不以其他artifact補洞冒充最新。

## 權威邊界

狀態單統一「現在顯示什麼」，但不取代底層正式記錄：

- release registry仍負責Owner release/revocation；
- model/bundle registry仍負責不可變identity；
- order/position ledger仍負責訂單與持倉；
- venue response仍負責ack/fill/cancel truth；
- ExecutionAuthorizer仍負責每筆order的last-mile安全檢查。

因此，狀態單不是permit，也不能因畫面顯示READY就繞過fresh quote、kill switch、single-use permit與idempotency。

## API、UI與文件規則

- 所有current-state API response都帶同一`active_snapshot_id`。
- 同一頁面的卡片、圖表與按鈕不得來自不同snapshot。
- UI若拿到generation不一致的response，顯示refresh required，不合併。
- Generated docs必須標snapshot ID與as-of；evergreen docs不得複製current數字。
- Request-time read endpoint不可順便訓練、回填、刷新probe或改DB。
- 即時probe若不是同一snapshot generation，只能標為「較新的獨立觀測」，不能覆寫主狀態。

## Execution規則

ExecutionAuthorizer收到intent時必須：

- 引用active snapshot ID；
- 驗證snapshot未過期且identity一致；
- 再做last-mile fresh quote、kill switch、permit replay與current exposure檢查；
- 任一檢查失敗則拒絕risk-on；
- 不允許caller只傳一個`ready=true`。

## Consequences

- API與前端會變簡單，因為只讀一個完整物件。
- Snapshot builder成為明確domain service，但不能變成新的god module。
- heartbeat只觸發建置與觀測，不重算另一套政策。
- 新舊狀態差異可用snapshot ID完整追蹤。
- 需要migration期間的dual-read比較，但公開projection只能選一個active generation。

## Executable specification

- `docs/specification/features/to-be/decision-snapshot-truth.feature`
- As-is characterization：`docs/specification/features/as-is/promotion-state-machine.feature`
- API characterization：`docs/specification/features/as-is/api-ui-projection-and-performance.feature`
