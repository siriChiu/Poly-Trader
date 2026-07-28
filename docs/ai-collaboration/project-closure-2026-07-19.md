# Poly-Trader 專案收尾與個人策略放行決策

**決策日期：** 2026-07-19
**專案狀態：** Maintenance / 非 Major
**策略狀態：** `RELEASED_FOR_PERSONAL_USE`
**決策人：** 專案擁有者（Kazuha）

---

## 1. 最終決策

Poly-Trader 至此完成主要研發階段，正式由 Major 專案降為維護模式。

本專案不是對外商品，也不承擔商業產品的部署認證流程。依專案擁有者的明確決定，系統最新回測證據中最符合「低頻、高信念、低回撤」偏好的策略，**直接放行為個人使用基線**；後續研究 gate、same-bucket support 或樣本數警告可以繼續顯示，但不再以商業產品等級的流程阻止專案收尾與個人採用。

這項決策是人工 release override，不是把未通過的研究條件改寫成「已通過」。報表仍應保留原始數字與限制，避免日後誤讀。

---

## 2. 放行策略

來源 artifact：

- `data/high_conviction_topk_oos_matrix.json`
- 產生時間：`2026-07-18T06:15:24.984207+00:00`
- target：`simulated_pyramid_win`
- 樣本數：`28,677`

最終採用：

| 欄位 | 值 |
|---|---:|
| Model | `logistic_regression` |
| Feature profile | `current_full` |
| Regime | `all`（bull row 與 all row 在此 artifact 指標相同） |
| Selection | `top_1pct` |
| OOS ROI | `24.65%` |
| Win rate | `68.97%` |
| Profit factor | `4.3797` |
| Max drawdown | `4.78%` |
| Worst fold | `+9.94%` |
| Trade count | `29` |

選擇理由：

1. 相較追求最高 ROI 的 top-5% / top-10% 路線，此策略的最大回撤明顯更低。
2. Worst fold 為正值，沒有依賴單一漂亮分折掩蓋崩壞分折。
3. Profit factor 高，且符合低頻、高信念的原始投資偏好。
4. 最新 artifact 自身也把此 row 列為 `nearest_deployable_candidate` 與 `best_not_deployable`。

---

## 3. 人工覆寫的 gate

放行時仍存在的研究／治理警告：

- `min_trades_not_met`：29 筆，低於原先 50 筆門檻。
- `support_route_not_deployable`。
- `deployment_blocker_active`。
- 當時 current-live exact bucket support：`2 / 50`。

專案擁有者接受上述限制，並明確決定：

> 對此個人專案，這些條件保留為可見警告，不再作為 release 的絕對阻塞。

因此，最終狀態是：

```text
release_status = RELEASED_FOR_PERSONAL_USE
research_warnings_acknowledged = true
commercial_certification_claimed = false
```

---

## 4. 「放行」的範圍

本次放行代表：

- 最終策略已選定，不再因研究 gate 無限延後專案收尾。
- 可作為個人分析、訊號與後續 API 執行整合的預設策略。
- 後續可以更新策略，但不再把 Poly-Trader 維持為 Major 研發主線。
- 舊數據、回測結果與 gate 原因繼續保留，不能竄改成不存在。

本次文件工作**沒有送出真實訂單、沒有寫入 API 金鑰、沒有啟動交易程序，也沒有修改 execution code/config**。這是依「先建立文件，不開始執行」邊界所做的正式 release 決策紀錄。

真正接上券商／交易所 API 時，策略研究 gate 不再自動否決擁有者決策；但下列純技術保護仍應保留：

- kill switch
- 防重複下單與 idempotency
- 單筆／單日資金上限
- stale quote / API failure 拒單
- 完整 order/fill audit log

這些是防程式錯誤，不是重新建立商業級審批流程。

---

## 5. 維護模式範圍

仍可做：

- 修復明確 bug。
- 因資料源或 API 變更而做相容性維護。
- 更新回測 artifact、模型或策略快照。
- 修復會造成錯單、重複單或資料錯讀的問題。

不再主動做：

- 無期限追逐 exact-bucket support closure。
- 為了達到商品化認證而持續擴張治理流程。
- 大型 UI／架構重寫。
- 把 Poly-Trader 保持在 Major roadmap。

新的主要研發方向移至獨立的美股工具專案，避免繼續把加密貨幣、券商 API、美股資料語義與新 UI 混在同一個 codebase。
