# ISSUES.md — Current State Only

_最後更新：2026-04-16 13:00 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 直接承接上輪要求，先處理 **execution market-rules pre-trade guardrail contract**。本輪已把 `step_size / tick_size / precision delta` 正式拉進 `ExecutionService + Binance/OKX adapters`：下單前若 `qty` 不符合 step-size，或 `price` 不符合 tick-size，就會在送單前以結構化 reject 擋下，避免把 precision 類錯誤拖到 exchange runtime 才爆。剩餘主缺口已收斂到 **manual trade 後的即時刷新與 richer guardrail context 仍不足**，以及 **尚未做真實 venue/canary 層級的 exchange metadata smoke verification**。

---

## Step 0.5 承接結果
- 上輪最高優先：`Exchange market-rules guardrail 仍未完整覆蓋 step-size / tick-size / venue-specific precision`
- 上輪要求本輪先做：`把 step_size / tick_size / precision delta 納入統一 pre-trade guardrail contract，並補 Binance/OKX regression tests`
- 本輪實際處理：
  1. `ExecutionService` 在 pre-trade lane 直接拒絕 `qty_step_mismatch / qty_precision_mismatch / price_tick_mismatch / price_precision_mismatch`
  2. `BinanceAdapter.market_rules()` / `OKXAdapter.market_rules()` 補出 `step_size / tick_size / qty_contract / price_contract`
  3. 補齊 Binance / OKX 對應 regression tests
- 本輪明確不做：
  - 不擴 live 下單範圍
  - 不做 UI 美化
  - 不做與本輪 P0 無關的模型 / label / leaderboard 調整

---

## 本輪事實摘要
### 已改善
- `execution/execution_service.py`
  - pre-trade validation 現在不只檢查 `min_qty / min_notional`，也會檢查：
    - `qty_step_mismatch`
    - `qty_precision_mismatch`
    - `price_tick_mismatch`
    - `price_precision_mismatch`
  - reject context 會保留 `raw_value -> adjusted_value -> delta -> rules`
- `execution/exchanges/binance_adapter.py`
  - 會從 Binance market filters 萃取 `LOT_SIZE.stepSize` 與 `PRICE_FILTER.tickSize`
- `execution/exchanges/okx_adapter.py`
  - 會從 OKX market info 萃取 `lotSz/minSz` 與 `tickSz`
- 驗證已通過：
  - `source venv/bin/activate && python -m pytest tests/test_execution_service.py tests/test_server_startup.py tests/test_strategy_lab.py -q` → **53 passed**

### 卡住不動
- manual trade 完成後，Dashboard 仍主要依賴輪詢更新 `/api/status`；沒有明確的 post-trade 主動 refresh 閉環
- guardrail context 雖已存在於 reject payload，但 UI 尚未展成易讀的 rules/context 面板
- 尚未做真實 exchange metadata / live-canary smoke 驗證，因此不能把 readiness 敘事升級為「可安全放量」

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- coverage / IC / CV / ROI / canonical target drift
- predictor / leaderboard / Strategy Lab 的模型面主指標

本輪聚焦的是 Step 0.5 指定的 execution P0，不對未重跑的模型數字做假更新。

---

## Open Issues

### P0. Manual trade runtime 閉環仍缺「即時刷新 + 可讀 context 面板」
**現況**
- `/api/trade` 已可在送單前攔下 step-size / tick-size / precision 類錯誤
- reject payload 已保留 `raw_value / adjusted_value / delta / rules`

**缺口**
- manual trade 成功/失敗後尚未保證立即刷新 `/api/status`
- Dashboard 尚未把 reject `context.rules` 展成可讀區塊；操作者仍需自己拆 JSON

**風險**
- guardrail 雖已正確執行，但可觀測性仍偏工程向，不夠操作向
- 使用者可能知道「被拒單」，但仍看不出「該改成多少 qty/price」

**下一步**
- 在 manual trade 成功/失敗後主動 refresh runtime status
- 把 `raw_value -> adjusted_value -> delta -> rules` 顯示成 UI context 面板

### P1. Venue-specific regression 已有單元測試，但仍缺 exchange metadata / canary smoke verification
**現況**
- 已有 Binance / OKX 單元測試，證明 market-rules contract 會攜帶 `step_size / tick_size`
- 已有 pre-trade regression，證明 precision 類錯誤會在送單前被擋下

**缺口**
- 尚未驗證真實 exchange metadata 在 live config / canary mode 下是否完全符合目前 contract
- 尚未有「真實 market metadata → 預期 reject code」的 smoke lane

**風險**
- 若真實 venue metadata 結構有差異，仍可能留下 edge-case precision rejection

**下一步**
- 補一條 canary-safe metadata smoke 檢查（只讀 market rules，不實際下單）
- 對 Binance / OKX 各保留一條 runtime-level verification 腳本或測試

### P1. 成功下單路徑仍缺乏 operator-friendly 的 normalized order 回饋
**現況**
- 目前成功路徑會回傳 `guardrails` 與 order payload

**缺口**
- 成功路徑沒有明確回傳 normalized qty/price 與 market-rules contract 摘要
- 操作者無法直接確認「本次下單是否已符合 venue granularity」

**下一步**
- 評估是否在成功 payload 中加入 normalized qty/price 與 contract 摘要
- 若不加入，至少在 preview/readiness surface 提供對應資訊

---

## 本輪已處理
- 修復 `ExecutionService` 缺少 `step_size / tick_size / precision delta` pre-trade guardrail 的 root cause
- 修復 Binance / OKX adapter 的 market-rules contract，讓上層能拿到 venue-specific granularity 規則
- 新增 Binance / OKX regression tests，鎖住 pre-trade precision rejection 路徑

---

## Current Priority
1. **P0：manual trade 後建立即時 status refresh + guardrail context 展示閉環**
2. **P1：補 canary-safe exchange metadata smoke verification，確認 live metadata 與 contract 一致**
3. **P1：決定成功下單路徑是否也要回傳 normalized qty/price contract**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`manual trade runtime 閉環仍缺即時刷新與可讀 guardrail context 面板`
- 本輪已完成：`ExecutionService 已能在送單前拒絕 qty_step/price_tick/precision mismatch；Binance/OKX market-rules contract 已帶 step_size/tick_size；53 tests 通過`
- 下一輪必須先處理：`manual trade success/failure 後主動 refresh /api/status，並把 reject context 的 raw->adjusted->delta->rules 變成 UI 可讀資訊`
- 成功門檻：`manual trade 後無論成功或拒單，Dashboard 都能立即看到最新 guardrail / recent outcome，且使用者能讀懂要調整的 qty/price 規則`
- 若失敗：`升級為 blocker，文件明確標示 execution guardrail 已正確執行，但 operator-facing runtime closure 仍未完成，不可宣稱 canary-safe readiness`
