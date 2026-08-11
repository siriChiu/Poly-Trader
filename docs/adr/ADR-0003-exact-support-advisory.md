# ADR-0003：Exact Support只作信心警告

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q3回答「資料不足只警告，仍可照常做極小額Live Canary」
- Scope: Exact-support/sample-count evidence gate
- Related: ADR-0001 Live Canary；ADR-0002 permanent Owner release

## 白話背景

系統會計算：「現在這種市場情況，過去累積了多少個相似案例？」例如目標是50筆，但目前只有20筆。

案例不足只表示我們對策略表現比較沒有把握，不等於交易所、訂單或資金安全有問題。現行系統卻會在predictor、Top-K、execution overview與heartbeat多次把這個數字轉成阻塞，導致owner已核准、canary又是極小額，仍然被同一個sample gate反覆擋住。

## Decision

> **Exact support不足只顯示信心警告；不阻止Owner release，也不阻止已通過所有hard safety的極小額、單層Live Canary。**

固定50筆或其他sample target不是strategy release gate、不是deployment gate，也不是per-order execution gate。

## Product behavior

Support不足時：

- 顯示目前筆數、目標筆數、比例、資料generation與白話警告；
- 可以觸發研究review、資料品質診斷或建議繼續觀察；
- Owner release保持ACTIVE；
- Live Canary仍受ADR-0001的極小額、單層限制；
- 不因support不足把`allowed_layers`再降為0；
- 不在每筆order前重新計算固定50筆門檻。

Support達標時：

- 只把信心狀態由warning改成better-supported；
- 不自動增加層數、金額或啟用Full Auto Live；
- 不自動解除bundle、market、permit、venue或lifecycle blocker。

## Hard safety仍然強制

本決策完全不影響：

- exact released bundle binding；
- current signal/entry eligibility；
- fresh quote與同generation decision；
- kill switch、model-health breaker、daily loss/failure halt；
- explicit symbol allowlist、極小額cap與單層限制；
- signed short-lived single-use permit；
- DB-level idempotency；
- venue credentials/connectivity與order normalization；
- ack/fill/partial/cancel/reject/reconciliation；
- global/per-strategy exposure及安全risk-off path。

任一hard safety unknown/stale/mismatch時，risk-on仍fail closed。

## Evidence contract

即使只作警告，support evidence仍必須可信：

- 說明bucket/market條件與candidate identity；
- 帶`generated_at`、generation ID、source window與definition version；
- `0`是合法值，不能被舊artifact正值覆蓋；
- stale或identity mismatch顯示`unknown/stale`，不能冒充current support；
- 不同bucket、不同model或不同bundle的樣本不可無說明合併；
- 等待只能增加樣本，不能被宣稱能修正look-ahead、label mismatch、feature bug或model bias。

## Consequences

- 刪除或降級predictor、Top-K、execution overview與heartbeat中的重複support hard gate。
- API/UI把support放在Evidence/Confidence區，不放在Order Authorization區。
- Live Canary的大小由ADR-0001與hard execution policy固定，不由sample count自動調整。
- 未來若Owner希望support影響多層或Full Auto promotion，需要新的Owner決策，不能由工程自行加回。

## Executable specification

- `docs/specification/features/to-be/exact-support-advisory.feature`
- As-is characterization：`docs/specification/features/as-is/personal-release-and-runtime-binding.feature`
- Gating audit：`docs/specification/as-is-gating-lineage.md`
