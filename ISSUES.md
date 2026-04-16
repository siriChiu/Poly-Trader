# ISSUES.md — Current State Only

_最後更新：2026-04-16 13:19 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，優先補上 **manual trade 的 operator-facing runtime closure**。已完成兩個直接補洞：
1. Dashboard 手動下單後會 **主動 refresh `/api/status`**，不再只靠 60 秒輪詢等狀態慢慢更新。
2. Dashboard 新增 **Guardrail context 面板**，把 reject payload 的 `raw_value → adjusted_value → delta → rules` 轉成可讀資訊，讓操作者知道被哪條 venue granularity 規則擋下，以及應該把 qty / price 調到多少。

目前 execution lane 的主要缺口已收斂到：**缺少 canary-safe exchange metadata smoke verification**，以及 **成功下單路徑尚未顯式回傳 normalized qty/price contract 摘要**。

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`manual trade runtime 閉環仍缺即時刷新與可讀 guardrail context 面板`
- 上輪指定本輪先做：
  1. manual trade success/failure 後主動 refresh `/api/status`
  2. 把 reject context 的 `raw -> adjusted -> delta -> rules` 變成 Dashboard 可讀資訊
- 本輪明確不做：
  - 不擴 live 下單範圍
  - 不做與 execution P0 無關的模型 / label / leaderboard 調整
  - 不把 readiness 敘事升級成「可安全放量」

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - P0：manual trade 後的 runtime 回饋若只剩輪詢與 JSON，execution guardrail 雖正確，操作者仍無法立即採取修正動作。
2. **上輪明確要求本輪處理的是什麼？**
   - 先補 post-trade refresh，再把 guardrail reject context 轉成可讀面板。
3. **本輪要推進哪 1~3 件事？**
   - (a) Dashboard trade callback 主動 refresh `/api/status`
   - (b) Dashboard 顯示手動交易即時回饋
   - (c) Dashboard 顯示 guardrail context 面板
4. **哪些事本輪明確不做？**
   - exchange live/canary readiness 擴張、模型面主指標重跑、UI 無關美化

---

## 本輪事實摘要
### 已改善
- `web/src/pages/Dashboard.tsx`
  - `useApi("/api/status")` 現在保留 `refreshRuntimeStatus`
  - `handleTrade()` 在成功與失敗路徑都會 `await refreshRuntimeStatus()`
  - 新增 **手動交易即時回饋** 區塊，清楚標示 pending / success / error
  - 新增 **Guardrail context 面板**，把最近 reject 的 `field / raw_value / adjusted_value / delta / step_size / precision / rules` 直接顯示在 Dashboard
- `tests/test_frontend_decision_contract.py`
  - 新增 regression 檢查，鎖住 post-trade refresh 與 context 面板不可再被移除

### 驗證證據
- `source venv/bin/activate && python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
  - **21 passed**
- `cd web && npm run build`
  - **成功**（Vite production build 完成）

### 卡住不動
- 尚未做 **Binance / OKX 真實 metadata smoke verification**；目前仍只有單元測試與前端 runtime surface，還不能宣稱 canary-safe readiness
- 成功下單路徑雖會回傳 `order + guardrails`，但 Dashboard 尚未把 **normalized qty/price contract** 明確顯示為成功摘要

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型面主指標

本輪聚焦 execution P0，不對未重跑的模型數字做假更新。

---

## Open Issues

### P0. Canary-safe exchange metadata smoke verification 仍缺失
**現況**
- pre-trade market-rules guardrail 已能在 UI 與 runtime surface 上完整顯示
- Binance / OKX contract 已有單元測試保護

**缺口**
- 尚未驗證真實 exchange metadata 是否在 live/canary config 下仍完全符合目前 contract
- 尚未有只讀 smoke lane 去回答「實際 market rules 是否與 UI 顯示一致」

**風險**
- 若實際 venue metadata 結構與測試假資料不同，仍可能在 canary 階段暴露 precision / tick-size 邊角錯誤

**下一步**
- 補一條 read-only metadata smoke verification（不送真單）
- 對 Binance / OKX 至少各保留一條 runtime-level 檢查腳本或測試

### P1. 成功下單路徑缺少 normalized contract 摘要
**現況**
- reject path 已可讀，操作者知道哪裡不合法
- success path 目前主要看到提交成功、venue、qty 與 guardrails snapshot

**缺口**
- 成功時尚未明確顯示 normalized qty / price 與對應 contract 摘要
- 使用者還無法直觀看到「本次送出的合法值是否與輸入不同」

**風險**
- 當 venue 需要 granularity 修剪時，操作者只知道成功，卻不知道最終合法值長什麼樣

**下一步**
- 決定 success payload 是否直接加入 normalized qty / price
- 若不放在 payload，至少在 Dashboard 顯示 success contract 摘要卡

---

## 本輪已處理
- 補上 Dashboard manual trade 後的主動 `/api/status` refresh 閉環
- 把 structured reject payload 轉成 operator-readable 的 Guardrail context 面板
- 補上前端 regression test，鎖住 refresh 與 context 顯示契約

---

## Current Priority
1. **P0：補 canary-safe exchange metadata smoke verification**
2. **P1：補 success path 的 normalized qty/price contract 摘要**
3. **P1：確認 Dashboard 的即時回饋與 runtime status 在真實 API 回應下保持一致**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`execution runtime surface 已補齊 post-trade refresh 與 reject context，可觀測性前進；下一輪先補 canary-safe exchange metadata smoke verification`
- 本輪已完成：`Dashboard handleTrade 成功/失敗後主動 refresh /api/status；新增手動交易即時回饋；新增 Guardrail context 面板；pytest 21 passed；web build 成功`
- 下一輪必須先處理：`用 read-only metadata smoke verification 驗證 Binance / OKX 真實 market rules 與 contract 一致，且不要送真單`
- 成功門檻：`至少一條 smoke verification 能證明實際 venue metadata 可產出與 UI/runtime guardrail 相同的 step_size / tick_size / precision contract`
- 若失敗：`升級為 blocker，文件必須明確標示 execution surface 可讀但 readiness 尚未被真實 venue metadata 驗證，不可宣稱 canary-safe`
