# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 12:42 UTC_

只保留目前計畫，不保留舊 roadmap。

---

## 已完成
- 已建立 execution foundation：
  - `execution/exchanges/base.py`
  - `execution/exchanges/binance_adapter.py`
  - `execution/exchanges/okx_adapter.py`
  - `execution/execution_service.py`
  - `execution/account_sync.py`
- 已將 `/api/trade` 接到 execution layer
- 已將 `/api/status` 補成 runtime 狀態聚合面，並在本輪修正為 **帶 DB session** 計算 execution guardrails：
  - `execution`
  - `account`
  - `raw_continuity`
  - `feature_continuity`
- 已在 Dashboard 補上 execution/account 狀態面板：
  - mode
  - venue
  - balance
  - positions / open orders
  - recent reject / recent failure / recent order
  - continuity 狀態
- 本輪已讓 manual trade reject 走到前端時保留可讀的 structured code/message，而不是 `[object Object]`
- 本輪已讓 `/api/trade` 成功回應帶回 `guardrails`
- 驗證已通過：
  - `python -m pytest tests/test_execution_service.py tests/test_server_startup.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`

---

## 目前主目標

### 目標 A：把 execution market-rules guardrail 補到可安全 canary
重點：
- `step-size / tick-size / venue-specific precision` contract
- pre-trade 層直接攔下 precision / lot-size / notional 類錯誤
- 回傳 `原始值 → 調整值 → 拒單原因` 的結構化結果

### 目標 B：把 execution 狀態卡升級成真正的 readiness panel
重點：
- manual trade 後主動刷新 status
- recent reject 顯示更完整 context
- 明確回答「目前是否具備 canary-safe 下單能力」

### 目標 C：分階段驗證交易所
重點：
- Binance 先完成完整 guardrail regression
- OKX 再做 metadata / precision / reduceOnly 驗證
- 維持 spot BTC/USDT，不擴 scope

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 先修 `/api/status` DB session 與 structured reject serialization | 直接修掉「guardrail 已存在但 UI/API 看起來像沒作用」的假可見性 root cause；立即提高排障品質 | 尚未補齊 venue-specific precision contract | 治本（execution surface 真實化） | 已有 execution layer，但 runtime status / reject 顯示失真 | ✅ 本輪採用 |
| 直接做完整 step-size / tick-size guardrail | 最接近 canary-safe 下單能力 | 範圍較大，若 execution surface 仍失真，除錯效率低 | 治本 | execution surface 已可正確回報 guardrails/reject | ✅ 下一輪主線 |
| 先做 OKX 實場驗證 | 可提早擴 venue | 在共用 market-rules contract 未鎖定前，容易放大 venue-specific 假象 | 治標 | Binance 路徑已完成 contract | ❌ 本輪不做 |

### 效益前提驗證
- 前提 1：execution guardrail 是否已能被狀態面板真實觀測 → **成立（/api/status 已帶 DB session）**
- 前提 2：manual reject 是否已能讓使用者看到真實 code/message → **成立（前端不再顯示 `[object Object]`）**
- 前提 3：在共用 precision/step-size contract 未完成前，是否應擴 venue 驗證 → **不成立，因此暫不擴 OKX readiness 敘事**

---

## Next focus
1. 在 `ExecutionService` / adapters 補齊 **step-size / tick-size / precision delta** contract
2. 讓 `manual trade -> /api/trade -> Dashboard status` 形成立即更新的 recent outcome 閉環
3. 為 Binance / OKX 各補至少一條 market-rules regression test

## Success gate
- 至少一條 `step-size / precision` 類錯誤可在送單前被結構化拒絕
- `/api/trade` reject 對前端顯示為可讀 code/message，不再出現 `[object Object]`
- `/api/status` 能穩定反映真實 `daily_loss_ratio / daily_loss_halt / recent reject`
- pytest 覆蓋至少一條成功委託與一條 precision/step-size guardrail 拒單路徑

## Fallback if fail
- 若下一輪無法補齊 venue-specific precision contract，升級為 blocker
- 文件必須明確標示：`execution surface 已可觀測，但 live_canary 仍非安全下單 readiness`
- 暫停 OKX readiness / live 擴張敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 step-size / tick-size / reject-context contract）
- `server/routes/api.py` / `execution/execution_service.py` / `web/src/hooks/useApi.ts` 若 execution surface 再擴充

## Carry-forward input for next heartbeat
- 先檢查 `ExecutionService` 與 adapters 是否已明確提供 `step_size / tick_size / precision delta` contract；若沒有，先做這件事
- 驗證 `/api/status` 是否仍以 DB session 計算 execution guardrails，而不是退回 blind summary
- 驗證 `/api/trade` structured reject 在前端仍顯示為 human-readable code/message
- 若 precision contract 已落地，下一輪必須追加 Binance/OKX regression tests；若沒落地，直接標 blocker
