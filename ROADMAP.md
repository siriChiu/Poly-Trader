# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 13:19 UTC_

只保留目前計畫，不保留舊 roadmap。

---

## 已完成
- execution foundation 已落地：
  - `execution/exchanges/base.py`
  - `execution/exchanges/binance_adapter.py`
  - `execution/exchanges/okx_adapter.py`
  - `execution/execution_service.py`
  - `execution/account_sync.py`
- `/api/status` 已帶 DB-aware execution guardrails
- `/api/trade` reject path 已保留 structured `detail={code,message,context}`
- `/api/trade` success path 已帶回 `guardrails`
- market-rules pre-trade contract 已落地：
  - `qty_step_mismatch`
  - `qty_precision_mismatch`
  - `price_tick_mismatch`
  - `price_precision_mismatch`
- **本輪新增：operator-facing runtime closure 補上第一階段**
  - Dashboard manual trade callback 會在成功 / 失敗後主動 `refresh /api/status`
  - Dashboard 新增 **手動交易即時回饋** 區塊
  - Dashboard 新增 **Guardrail context 面板**，把 `raw_value / adjusted_value / delta / rules` 轉成可讀資訊
- 驗證已通過：
  - `python -m pytest tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → **21 passed**
  - `cd web && npm run build` → **成功**

---

## 目前主目標

### 目標 A：把 execution contract 從「UI 可讀」推進到「真實 venue metadata 可驗證」
重點：
- 建立 read-only / canary-safe metadata smoke verification
- 驗證 Binance / OKX 真實 market rules 能產出與單元測試一致的 contract
- 明確回答目前 readiness 是「UI/runtime closure 完成」還是「已經通過 venue metadata 驗證」

### 目標 B：把 success path 也升級為 operator-readable contract
重點：
- 成功路徑補上 normalized qty / price 摘要
- 讓操作者能直接看到最終合法值與 contract，不只看到 order accepted
- 讓 success/reject 兩條路都共享同一套 market-rules 語義

### 目標 C：驗證 Dashboard runtime closure 在真實 API 回應下穩定
重點：
- 確認 trade callback 的主動 refresh 不會被 cache / stale UI 掩蓋
- 確認 recent reject / recent order / guardrail context 在一次操作後能立即更新
- 若必要，補更細的 UI/runtime regression test

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 先補 post-trade refresh + Guardrail context 面板 | 直接解掉上輪最關鍵的 operator-facing runtime 缺口；讓 pre-trade guardrail 從 JSON 變成可操作資訊 | 仍未回答真實 venue metadata 是否完全一致 | 治本（runtime closure） | market-rules contract 已存在，缺的是 UI/runtime 最後一哩 | ✅ 本輪採用 |
| 先做 exchange metadata smoke verification | 能更快回答 readiness 問題 | 若 operator-facing closure 未先完成，驗證成功也無法被使用者操作面充分消化 | 治本，但前提未滿足時會留下 UX 缺口 | UI/runtime closure 已完成 | ✅ 下一輪主線 |
| 直接擴 live/canary 敘事 | 最接近產品化敘事 | 若未做 smoke verification，容易把 partial readiness 誤包裝成可安全嘗試 | 治標 | smoke verification 已完成 | ❌ 目前不做 |

### 效益前提驗證
- 前提 1：manual trade 後是否能立即看到最新 runtime 狀態 → **成立（已主動 refresh `/api/status`）**
- 前提 2：reject payload 是否已能被操作者直接讀懂 → **成立（Guardrail context 面板已顯示 raw → adjusted → delta → rules）**
- 前提 3：實際 venue metadata 是否已驗證與 contract 一致 → **不成立，因此下一輪先做 smoke verification，不擴 readiness 敘事**

---

## Next focus
1. 新增 canary-safe / read-only exchange metadata smoke verification（Binance / OKX）
2. 把 success path 的 normalized qty / price contract 摘要補到 Dashboard 或 API payload
3. 驗證 Dashboard 主動 refresh 後的 runtime status 與真實 API response 一致，不被 cache 掩蓋

## Success gate
- 至少一條 read-only smoke verification 證明真實 venue metadata 可產出與單元測試一致的 market-rules contract
- 成功下單路徑也能讓使用者看懂 normalized qty / price 與規則摘要
- manual trade 一次操作後，Dashboard 立即更新 recent reject / recent order / guardrail context

## Fallback if fail
- 若 smoke verification 做不出來，升級為 blocker
- 文件必須明確標示：`execution UI/runtime closure 已完成，但真實 venue metadata 尚未驗證，不能宣稱 canary-safe readiness`
- 暫停任何擴 live / 擴 venue 的產品敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 metadata smoke lane 或 success normalized contract）
- `web/src/pages/Dashboard.tsx`
- `server/routes/api.py` / `execution/exchanges/*.py`（若補 smoke lane）

## Carry-forward input for next heartbeat
- 先檢查：Dashboard 的 post-trade refresh 與 Guardrail context 面板是否仍在，沒有被後續改動移除
- 然後優先做：Binance / OKX 的 canary-safe metadata smoke verification（只讀、不送真單）
- 驗證：smoke lane 輸出的 `step_size / tick_size / precision` 必須與 ExecutionService / Dashboard 顯示契約一致
- 若 smoke verification 尚未完成，不要把 execution readiness 敘事升級成 canary-safe
