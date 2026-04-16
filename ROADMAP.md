# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 13:00 UTC_

只保留目前計畫，不保留舊 roadmap。

---

## 已完成
- 已建立 execution foundation：
  - `execution/exchanges/base.py`
  - `execution/exchanges/binance_adapter.py`
  - `execution/exchanges/okx_adapter.py`
  - `execution/execution_service.py`
  - `execution/account_sync.py`
- `/api/status` 已用 DB session 計算 execution guardrails
- `/api/trade` structured reject 已能被前端以 human-readable code/message 顯示
- `/api/trade` 成功回應已帶回 `guardrails`
- **本輪新增：market-rules pre-trade contract 已落地**
  - `ExecutionService` 會在送單前拒絕：
    - `qty_step_mismatch`
    - `qty_precision_mismatch`
    - `price_tick_mismatch`
    - `price_precision_mismatch`
  - Binance market rules 會萃取 `LOT_SIZE.stepSize` / `PRICE_FILTER.tickSize`
  - OKX market rules 會萃取 `lotSz/minSz` / `tickSz`
  - reject context 會保留 `raw_value / adjusted_value / delta / rules`
- 驗證已通過：
  - `python -m pytest tests/test_execution_service.py tests/test_server_startup.py tests/test_strategy_lab.py -q` → **53 passed**

---

## 目前主目標

### 目標 A：把 operator-facing execution runtime 閉環補完整
重點：
- manual trade 成功/失敗後主動 refresh `/api/status`
- Dashboard 直接顯示 `raw -> adjusted -> delta -> rules` guardrail context
- recent reject / recent order / halt 狀態在一次操作後立即可見

### 目標 B：把 execution market-rules contract 從單元測試推進到 canary-safe verification
重點：
- Binance / OKX 真實 metadata smoke verification
- 驗證 live/canary config 讀到的 market rules 與 contract 欄位一致
- 明確回答目前 readiness 是「可觀測」還是「可安全嘗試」

### 目標 C：補齊成功下單路徑的 normalized contract 回饋
重點：
- 評估成功 payload 是否應同時回傳 normalized qty/price
- 若不走 success payload，至少要在 preview/readiness surface 暴露相同資訊
- 讓操作面能回答「如果被 venue granularity 修剪，結果會變成多少」

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 先補 `step_size / tick_size / precision delta` pre-trade contract | 直接堵住 precision 類錯誤在 exchange runtime 才失敗的缺口；讓 reject 有可讀根因 | 仍未解決 operator-facing refresh / UI context | 治本（execution lane 正確化） | 上輪已確認 execution surface 本身可觀測 | ✅ 本輪採用 |
| 直接做 manual trade UI refresh / context 面板 | 操作者體感最好 | 若底層 market-rules contract 未先正確化，UI 只會包裝假資訊 | 治標（治本需先有正確 contract） | pre-trade contract 已存在且可驗證 | ✅ 下一輪主線 |
| 直接擴 live venue/canary 敘事 | 可更快接近真實下單 | 若 smoke verification 未完成，容易把 partial contract 誤說成 readiness | 治標 | market-rules contract 與 operator closure 都已完成 | ❌ 本輪不做 |

### 效益前提驗證
- 前提 1：precision / step-size root cause 是否已能在 pre-trade 層被正確攔下 → **成立**
- 前提 2：Binance / OKX 是否都能提供 `step_size / tick_size` 給上層 contract → **成立（已有 regression tests）**
- 前提 3：operator 是否已能在一次 manual trade 後立刻理解最新 runtime 狀態與調整建議 → **不成立，因此下一輪先補 UI/runtime closure，不擴 readiness 敘事**

---

## Next focus
1. 在 manual trade 成功/失敗後主動 refresh `/api/status`，完成 recent outcome 閉環
2. 把 reject context 的 `raw_value / adjusted_value / delta / rules` 變成 Dashboard 可讀資訊
3. 補一條 canary-safe exchange metadata smoke verification，確認 Binance / OKX 真實 metadata 與 contract 一致

## Success gate
- manual trade 後不用等輪詢，也能立即看到最新 `guardrails / recent reject / recent order`
- reject context 能清楚顯示「原始值、合法值、差額、依據規則」
- 至少一條 smoke verification 證明實際 venue metadata 可產出與單元測試一致的 market-rules contract

## Fallback if fail
- 若下一輪無法補齊 post-trade refresh / context 展示，升級為 blocker
- 文件必須明確標示：`execution pre-trade guardrail 已正確，但 operator-facing runtime closure 仍未完成，尚不可宣稱 canary-safe readiness`
- 暫停任何擴 live / 擴 venue 的產品敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 post-trade refresh 或 normalized success contract）
- `server/routes/api.py` / `web/src/pages/Dashboard.tsx` / `web/src/hooks/useApi.ts`（若 runtime closure 擴充）

## Carry-forward input for next heartbeat
- 先檢查 manual trade 之後是否已主動 refresh `/api/status`；若沒有，先做這件事
- 驗證 Dashboard 是否已把 reject context 的 `raw -> adjusted -> delta -> rules` 顯示成可讀資訊，而不是只留在錯誤字串或 JSON
- 驗證本輪新增的 `qty_step_mismatch / price_tick_mismatch` guardrail 仍在，沒有被後續改動繞過
- 若 operator-facing runtime closure 已完成，再做 Binance / OKX canary-safe metadata smoke verification；若沒完成，不要擴 readiness 敘事
