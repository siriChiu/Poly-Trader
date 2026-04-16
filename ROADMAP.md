# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 14:25 UTC_

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
- Dashboard 已具備：
  - manual trade 成功 / 失敗後主動 `refresh /api/status`
  - **手動交易即時回饋** 區塊
  - **Guardrail context 面板**（`raw_value / adjusted_value / delta / rules`）
- Execution metadata smoke lane 已正式落地：
  - `execution/metadata_smoke.py`
  - `scripts/execution_metadata_smoke.py`
  - `data/execution_metadata_smoke.json`
  - `tests/test_execution_metadata_smoke.py`
- **本輪新增：runtime closure 補齊**
  - `/api/status` 會回傳 `execution_metadata_smoke`
  - `/api/trade` / `ExecutionService.submit_order()` 成功路徑會回傳 `normalization={requested, normalized, contract}`
  - runtime `last_order` 會保留 normalized qty / price / contract 摘要
  - Dashboard 新增 **Metadata smoke 摘要** 與最近委託 normalization 顯示
  - `ARCHITECTURE.md` 已同步 runtime-surface contract
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，Binance / OKX metadata contract 2/2 可讀**
  - `python -m pytest tests/test_execution_metadata_smoke.py tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → **23 passed**

---

## 目前主目標

### 目標 A：把 execution runtime surface 做成真實可驗證的 operator 面板
重點：
- Dashboard 真實 route 必須可看到 metadata smoke 摘要
- 最近成功委託必須可看到 normalized qty / price / contract
- source contract 不只存在程式碼，要有 runtime / browser 驗證證據

### 目標 B：補 metadata smoke freshness / stale policy
重點：
- 將 smoke artifact 從「存在」升級為「可判讀新鮮度」
- `/api/status` 與 Dashboard 共用同一套 fresh / stale / unavailable 規則
- 避免舊 smoke artifact 被誤讀成 readiness 健康

### 目標 C：維持 execution readiness 敘事紀律
重點：
- public metadata smoke + success-path normalization = runtime closure 前進
- 這仍 **不等於** live/canary order-level readiness 完成
- 在沒有更高層級驗證前，不擴大 readiness 敘事

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只把 success path normalized 資訊留在 `/api/trade` 回應 | 改動最小、立刻改善單次操作可讀性 | refresh 後資訊消失，operator 仍無法在 `/api/status` 回放最近成功 contract | 治標（治本需做：runtime `last_order` 與 status surface 同步） | 只想暫時改善單次操作回饋 | ❌ 不建議 |
| 把 success normalization 同步寫入 runtime `last_order`，並讓 Dashboard 顯示 | 成功路徑與 status panel 使用同一份 contract；refresh 後仍可見 | 需改 execution service + Dashboard 型別與顯示 | 治本 | 已有 guardrails / last_order runtime surface | ✅ 本輪採用 |
| 只保留 `data/execution_metadata_smoke.json` 不進 `/api/status` | 保持簡單，不改 API | smoke 仍停留離線 artifact，operator 看不到最新結果 | 治標（治本需做：把 artifact 接進 runtime surface） | 只供 repo 開發者閱讀 | ❌ 不建議 |
| 將 metadata smoke 摘要注入 `/api/status` 並在 Dashboard 顯示 | operator 可直接看到 venue contract 摘要；與 execution panel 合併為單一真相來源 | 仍需下一輪補 freshness/stale policy 與 browser runtime QA | 治本 | smoke lane 已存在且可重跑 | ✅ 本輪採用 |
| 直接把本輪 closure 宣稱為 canary-safe readiness 完成 | 對外敘事看起來進度快 | 會把 public metadata + UI closure 誤包裝成真實下單 readiness，形成假進度 | 治標 | 必須已有 live/canary order-level 驗證 | ❌ 明確不做 |

### 效益前提驗證
- 前提 1：是否已有可重跑 metadata smoke artifact 可供 status surface 使用 → **成立**
- 前提 2：success path 是否能共享 market-rules contract 給 runtime `last_order` → **成立**
- 前提 3：本輪 closure 是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## Next focus
1. 以 browser/runtime 驗證 Dashboard execution panel 真實可見 metadata smoke 與 normalized contract
2. 定義 metadata smoke freshness / stale / unavailable policy，並同步到 `/api/status` + Dashboard
3. 保持 readiness 文案只描述「public metadata + success contract runtime 可見」，不升級成 live/canary safe

## Success gate
- 真實 Dashboard route 可見：
  - Metadata smoke venue-level contract 摘要
  - 最近成功委託的 normalized qty / price / contract
- `/api/status` 與 Dashboard 對同一 smoke artifact 會給出一致的 fresh / stale / unavailable 判讀
- 文件仍明確區分 runtime closure 與 live/canary readiness

## Fallback if fail
- 若 browser/runtime 看不到這些 surface，升級為 blocker：代表 code-level contract 不等於 runtime closure
- 若 smoke freshness policy 做不出來，至少先把 stale / unavailable 明確標成 warning，不可默默顯示舊綠燈
- 若團隊開始把本輪結果誤寫成 live-ready，文件必須立即糾正，停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 freshness/stale contract 或 browser/runtime QA contract）
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 必要時新增 browser/runtime regression tests

## Carry-forward input for next heartbeat
- 先檢查：`python scripts/execution_metadata_smoke.py --symbol BTCUSDT` 是否仍可重跑，`/api/status` 是否仍會帶 `execution_metadata_smoke`
- 然後優先做：browser/runtime 驗證 Dashboard execution panel 真實顯示 smoke 摘要與 normalized contract
- 接著補：metadata smoke freshness/stale/unavailable age gate，並讓 API 與 Dashboard 共用同一套規則
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
