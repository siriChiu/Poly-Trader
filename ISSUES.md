# ISSUES.md — Current State Only

_最後更新：2026-04-16 12:42 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
Poly-Trader 的 execution foundation 已可走 `ExecutionService`，而本輪進一步補上 **runtime guardrail 可見性與 manual trade 拒單語義**：`/api/status` 現在會帶著 DB session 計算真實的 daily loss halt / recent reject 狀態，`/api/trade` 成功回應會帶回 guardrails，前端也不再把結構化拒單 payload 顯示成 `[object Object]`。目前最大的剩餘缺口已收斂到 **交易所 market-rules guardrail 仍未完整覆蓋 step-size / tick-size / venue-specific precision contract**，因此 live_canary 仍不可視為安全可放量。

---

## 本輪事實摘要
- Step 0.5 carry-forward 已對照上輪要求：
  - 上輪要求先處理 `ExecutionService 前置 market-rules / risk-halt guardrail`。
  - 本輪先修兩個會讓 guardrail 變成假可見性的 root cause：
    1. `/api/status` 建立 `ExecutionService` 時沒有傳入 DB session，導致 `daily_loss_ratio / daily_loss_halt` 在狀態面板上可能是盲的。
    2. `/api/trade` 拒單 payload 雖然後端已結構化，但前端 `fetchApi()` 會把 object detail 直接塞進 `Error()`，實際顯示成 `[object Object]`，使用者看不到真正 reject code/message。
- 本輪 patch：
  - `server/routes/api.py`
    - `/api/status` 改成 `ExecutionService(cfg, db_session=get_db())`
    - `/api/trade` 成功 payload 回傳 `guardrails`
  - `web/src/hooks/useApi.ts`
    - 新增 `formatApiErrorDetail()`，把結構化 reject payload 格式化成可讀訊息（如 `[min_notional] Order notional is below exchange minimum`）
- 驗證：
  - `source venv/bin/activate && python -m pytest tests/test_execution_service.py tests/test_server_startup.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q` → **53 passed**
  - `cd web && npm run build` → **PASS**
- 額外觀察：
  - repo 內 graphify rebuild 指令無法執行：`ModuleNotFoundError: No module named 'graphify'`，本輪未能刷新 graph artifact。

---

## Open Issues

### P0. Exchange market-rules guardrail 仍未完整覆蓋 step-size / tick-size / venue-specific precision
**現況**
- 已有 pre-trade guardrails：`kill_switch`、`daily_loss_halt`、`failure_halt`、`min_qty`、`min_notional`
- `/api/status` 現在能顯示真實 guardrail 狀態；`/api/trade` reject 也已能被前端正確讀出 code/message

**缺口**
- adapter `market_rules()` 目前仍以 `min_qty / min_cost / amount_precision / price_precision` 為主，尚未把 `step-size / tick-size` 明確拉成統一 contract
- venue-specific rounding / precision 規則還沒有獨立 regression tests 鎖住 Binance / OKX 差異
- 目前仍偏向「先 round、再送單」；尚未把「原始值 → 調整值 → 拒單/接受理由」完整結構化回傳給上層

**風險**
- live_canary 仍可能在某些交易對或 venue 上碰到 exchange-level precision rejection，而不是在 pre-trade lane 被穩定攔下
- readiness panel 現在看得到 halt / reject，但對「為何這個 qty/price 不合法」仍缺乏完整 contract

**下一步**
- 補齊 `step_size / tick_size / precision delta` 的統一 market-rules contract
- 針對 Binance / OKX 各加至少一條 pre-trade regression test，證明 exchange rejection 會在送單前被攔下

### P1. Dashboard execution panel 已可顯示最近 reject / failure / order，但 manual trade 後的即時 refresh 與 richer context 仍有限
**現況**
- Dashboard 已有 execution/account 狀態卡
- `fetchApi()` 現在能把結構化 reject 顯示成可讀文字，而不是 `[object Object]`

**缺口**
- manual trade 後尚未主動刷新 `/api/status`，最近 reject / recent order outcome 主要仍依賴輪詢更新
- reject `context` 尚未在 UI 展開顯示（例如 min_notional/min_qty 所對應的 rules）

**下一步**
- 在 manual trade 成功/失敗後觸發 runtime status refresh
- 若 guardrail context 有值，將其整理成可讀 UI 區塊而非只停在 alert 字串

### P1. OKX adapter 已存在，但 guardrail contract 仍未完成實場規則驗證
**現況**
- Binance / OKX adapter 都已存在
- 本輪修的是共用 execution surface，不是 venue-specific 細節

**缺口**
- 尚未確認 OKX spot-only `precision / lot size / reduceOnly` 行為是否完全符合目前 guardrail 假設
- 尚未有 OKX-specific guardrail regression 證據

**下一步**
- 先完成 Binance / OKX 共用 market-rules contract
- 再做 OKX-specific metadata / order param 驗證

---

## 本輪已處理
- 修復 `/api/status` 沒有把 DB session 傳進 `ExecutionService` 的 root cause，讓 daily halt / recent reject 狀態不再是盲的
- 修復 `/api/trade` structured reject 在前端被序列化成 `[object Object]` 的 root cause
- 補齊 `/api/trade` 成功 payload 的 `guardrails`，讓 manual trade 回應可直接攜帶當下 guardrail snapshot

---

## Current Priority
1. **P0：補齊 step-size / tick-size / venue-specific precision 的 pre-trade guardrail contract**
2. **P1：manual trade 後主動刷新 runtime status，讓 Dashboard 立即反映 recent outcome**
3. **P1：完成 Binance / OKX venue-specific guardrail regression tests**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`Exchange market-rules guardrail 仍未完整覆蓋 step-size / tick-size / venue-specific precision`
- 本輪已完成：`/api/status` 改為用 DB session 計算 execution guardrails；前端可正確顯示 structured reject code/message；/api/trade 成功回傳 guardrails`
- 下一輪必須先處理：`將 step_size / tick_size / precision delta 納入統一 pre-trade guardrail contract，並補 Binance/OKX regression tests`
- 成功門檻：`至少一條 precision/step-size 類錯誤能在送單前被結構化拒絕，且 pytest 證明不是 exchange runtime 才失敗`
- 若失敗：`升級為 blocker，文件明確標示 live_canary 僅具觀測能力，不具安全下單 readiness`
