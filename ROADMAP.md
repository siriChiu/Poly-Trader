# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 15:12 UTC_

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
  - **Metadata smoke 摘要**
  - **最近委託 normalization** 顯示
- Execution metadata smoke lane 已正式落地：
  - `execution/metadata_smoke.py`
  - `scripts/execution_metadata_smoke.py`
  - `data/execution_metadata_smoke.json`
  - `tests/test_execution_metadata_smoke.py`
- 既有 closure：
  - `/api/status` 會回傳 `execution_metadata_smoke.freshness={status,label,reason,age_minutes,stale_after_minutes}`
  - Dashboard 會顯示 `smoke freshness` badge 與 `artifact age ... · stale after ...`
  - `CandlestickChart` render loop 已修掉（stable empty prop defaults）
- **本輪新增 closure**：
  - `/api/status` 會在 `freshness in {stale, unavailable}` 時自動重跑 read-only `run_metadata_smoke()`
  - `execution_metadata_smoke.governance={status,operator_action,operator_message,refresh_command,escalation_message,auto_refresh}` 已成為 runtime contract
  - auto refresh 具有 **5 分鐘 cooldown**，避免 status 輪詢過度打擊 venue metadata lane
  - Dashboard 會顯示 **stale governance** 面板，直接揭露 auto refresh 狀態 / refresh command / escalation 訊息
  - `ARCHITECTURE.md` 已同步 execution metadata auto-refresh governance contract
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，Binance / OKX metadata contract 2/2 可讀**
  - `python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **14 passed**
  - `cd web && npm run build` → **成功**
  - browser runtime QA → **Dashboard 可見 smoke freshness FRESH、stale governance healthy、auto refresh state、refresh command，console 無 JS errors**

---

## 目前主目標

### 目標 A：把 execution runtime visibility 升級成 execution runtime governance
重點：
- stale / unavailable metadata smoke 不只要可見，還要有明確治理動作
- `/api/status` 與 Dashboard 必須共用同一套治理語義
- operator 需要一眼看懂：目前是健康、等待自動 refresh、還是該升級成 blocker

### 目標 B：把 stale governance 往 status polling 之外擴張
重點：
- 目前 auto-refresh 觸發仍依賴 `/api/status`
- 下一步要定義 scheduler / pager / background worker 的升級路徑
- 不讓治理能力只在 UI 被打開時才存在

### 目標 C：擴大 execution route coverage，但不誤擴 readiness 敘事
重點：
- 下一輪要先盤點有沒有第二個真正 operator-facing execution route
- 若沒有，要把 Dashboard execution lane 的 regression / browser evidence 固化得更完整
- runtime visibility / governance closure 仍 **不等於** live/canary order-level readiness

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只保留 freshness badge 與人工處置 | 改動最小 | stale artifact 仍要靠 operator 自己發現與手動補跑 | 治標（治本需做：把治理動作契約化） | 只想快速露出狀態 | ❌ 不建議 |
| 在 `/api/status` 內建 auto-refresh + governance payload，Dashboard 同步顯示 | 讓 stale artifact 從可見 warning 升級成真正治理閉環；API/UI 共用單一真相來源 | 需要補 cooldown、測試、文件同步；仍未涵蓋 scheduler/pager | **治本第一步** | 已有 read-only metadata smoke lane，可安全重跑 | ✅ 本輪採用 |
| 直接上 scheduler/pager/background worker | 治理更完整、不依賴 UI 輪詢 | 改動範圍較大，若先做會拉長本輪 closure，且尚未把 runtime contract 定好 | 治本第二步 | 先有 machine-readable governance contract | ⏳ 下一輪再做 |
| 先去驗第二個 execution route，不修 stale 治理 | 可以擴大 runtime coverage | stale 問題仍未閉環，會讓 execution surface 持續有已知缺口 | 治標 | 當前 stale contract 已完整 | ❌ 本輪不採用 |

### 效益前提驗證
- 前提 1：metadata smoke lane 是 read-only，可安全被 `/api/status` 自動重跑 → **成立**
- 前提 2：Dashboard 已有 execution metadata 區塊可承接治理訊息 → **成立**
- 前提 3：需要 cooldown 避免 polling 造成重複 refresh → **成立**
- 前提 4：本輪是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## Next focus
1. 把 stale metadata smoke 的治理從 `/api/status` 輪詢內建 refresh，升級到 scheduler / pager / background escalation
2. 盤點並驗證下一個 execution operator-facing surface；若實際上沒有第二 route，就把 Dashboard execution lane 的 regression path 再收斂成更強的固定驗證
3. 維持 readiness 文案只描述「runtime visibility / governance closure」，不升級成 live/canary safe

## Success gate
- stale metadata smoke 在 UI 之外也有明確升級路徑（scheduler/pager/background worker 至少一條落地）
- execution runtime 證據不再只集中在 Dashboard 單一路徑
- 文件仍明確區分 runtime governance closure 與 live/canary readiness

## Fallback if fail
- 若外部升級機制本輪做不出來，至少要把 scheduler / pager / cron 的責任邊界與手動 fallback contract 寫清楚，不可只留一句 future work
- 若盤點後根本沒有第二個 execution operator-facing route，必須把這件事正式寫進文件，並把 Dashboard lane 的 browser/runtime regression 固化成 canonical 驗證路徑
- 若有人開始把本輪結果誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 scheduler / pager / background governance contract）
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 必要時新增 execution runtime regression tests / browser QA 腳本

## Carry-forward input for next heartbeat
- 先檢查：`python scripts/execution_metadata_smoke.py --symbol BTCUSDT` 是否仍可重跑、`/api/status` 是否仍輸出 `freshness + governance`、Dashboard 是否仍可見 `stale governance` 面板
- 然後優先做：stale metadata smoke 的 **scheduler / pager / background escalation** 方案
- 接著處理：第二個 execution operator-facing route 的盤點與 browser/runtime 驗證；若實際上沒有第二 route，就把 Dashboard execution lane 升級成更完整的 canonical regression path
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
