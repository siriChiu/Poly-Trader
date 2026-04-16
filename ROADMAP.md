# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 14:49 UTC_

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
- 本輪新增 closure：
  - `/api/status` 會回傳 `execution_metadata_smoke.freshness={status,label,reason,age_minutes,stale_after_minutes}`
  - Dashboard 會顯示 `smoke freshness` badge 與 `artifact age ... · stale after ...`
  - browser QA 發現的 `CandlestickChart` render loop 已修掉（stable empty prop defaults）
  - `ARCHITECTURE.md` 已同步 freshness / chart-stability contract
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，Binance / OKX metadata contract 2/2 可讀**
  - `python -m pytest tests/test_execution_metadata_smoke.py tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → **26 passed**
  - `cd web && npm run build` → **成功**
  - browser runtime QA → **Dashboard 可見 smoke freshness FRESH、artifact age policy、venue contract 摘要，console 無 JS errors**

---

## 目前主目標

### 目標 A：把 execution runtime visibility 維持在可驗證、可判讀、不中斷的狀態
重點：
- Dashboard execution panel 必須持續可見 metadata smoke freshness、venue contract、最近委託 normalization
- stale / unavailable 不只存在資料結構裡，operator 也要在畫面上一眼看懂
- browser/runtime 驗證要能證明真實 route 與 console 都健康

### 目標 B：把 stale metadata smoke 從「可見」推進到「可治理」
重點：
- 定義 stale artifact 後的明確動作：refresh / warning / escalation
- `/api/status` 與 Dashboard 維持同一套 threshold 與語義
- 不讓 stale badge 變成只有看得到、但無後續動作的半閉環

### 目標 C：維持 execution readiness 敘事紀律
重點：
- public metadata smoke + success-path normalization + freshness badge = runtime visibility closure
- 這仍 **不等於** live/canary order-level readiness 完成
- 在沒有更高層級驗證前，不擴大 readiness 敘事

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只在 Dashboard 顯示 smoke 時間戳，不做 freshness 判讀 | 改動最小 | operator 仍要自己算時間差，stale artifact 容易被誤讀 | 治標（治本需做：API/UI 共用 freshness contract） | 只想快速露出 artifact 時間 | ❌ 不建議 |
| 在 `/api/status` 輸出 freshness 結構，Dashboard 同步 badge + age policy | API/UI 共用單一真相來源；operator 可立即判讀 fresh/stale/unavailable | 需補測試與文件，還要做 browser 驗證 | 治本 | 已有 metadata smoke artifact 與 status surface | ✅ 本輪採用 |
| browser QA 看到 chart console 爆錯先記錄不修 | 改動少、能快速出報告 | runtime surface 仍不乾淨，之後 QA 會一直被噪音污染 | 治標（治本需做：修 root cause） | 問題無法快速定位時 | ❌ 不建議 |
| 直接修掉 CandlestickChart render loop root cause | 清掉 browser QA 假訊號，讓 execution runtime 驗證可信 | 需找出真正的 rerender root cause | 治本 | browser QA 已穩定重現 `Maximum update depth exceeded` | ✅ 本輪採用 |
| 把本輪 closure 直接升級敘事成 live/canary ready | 對外看起來進度快 | 會把 runtime visibility 誤包裝成真實下單 readiness，形成假進度 | 治標 | 必須已有 order-ack / fill lifecycle 驗證 | ❌ 明確不做 |

### 效益前提驗證
- 前提 1：是否已有可重跑 metadata smoke artifact 可供 freshness policy 使用 → **成立**
- 前提 2：API 與 Dashboard 是否已共享同一 smoke summary → **成立**
- 前提 3：browser QA 暴露的 console 問題是否有明確 root cause 可修 → **成立（inline empty array defaults）**
- 前提 4：本輪 closure 是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## Next focus
1. 定義 stale metadata smoke 的自動治理動作（refresh / warning / escalation），不要停在可見 badge
2. 選定下一個 execution operator-facing surface，做同等級 browser/runtime 驗證
3. 維持 readiness 文案只描述「runtime visibility closure」，不升級成 live/canary safe

## Success gate
- stale metadata smoke 會觸發明確治理 contract，而不是只有 badge
- 新驗證的 execution surface 也能提供 browser-level evidence，且 console 無 JS errors
- 文件仍明確區分 runtime visibility closure 與 live/canary readiness

## Fallback if fail
- 若 stale artifact 治理動作做不出來，至少先把 warning / manual action path 寫成明確 contract，不可默默只留 badge
- 若下一個 execution surface 做 browser QA 時再出現 runtime/console 問題，升級為 blocker，先修 root cause 再宣稱 closure
- 若團隊開始把本輪結果誤寫成 live-ready，文件必須立即糾正，停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 stale governance / escalation contract）
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- `web/src/components/CandlestickChart.tsx`（若 chart runtime contract 再擴充）
- 必要時新增 browser/runtime regression tests

## Carry-forward input for next heartbeat
- 先檢查：`python scripts/execution_metadata_smoke.py --symbol BTCUSDT` 是否仍可重跑，Dashboard 是否仍可見 `smoke freshness` 與 `artifact age`
- 然後優先做：stale metadata smoke 的自動治理動作與契約化處置
- 接著補：下一個 execution operator-facing route 的 browser/runtime 驗證證據
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
