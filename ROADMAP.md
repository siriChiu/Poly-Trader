# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 15:34 UTC_

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
- `/api/trade` success path 已帶回 `guardrails + normalization`
- Dashboard 已具備：
  - manual trade 成功 / 失敗後主動 refresh `/api/status`
  - 手動交易即時回饋
  - Guardrail context 面板
  - Metadata smoke 摘要與 freshness badge
  - stale governance 面板
  - 最近委託 normalization 顯示
- Execution metadata smoke lane 已正式落地：
  - `execution/metadata_smoke.py`
  - `scripts/execution_metadata_smoke.py`
  - `data/execution_metadata_smoke.json`
  - `tests/test_execution_metadata_smoke.py`
- 既有 closure：
  - `/api/status` 會在 stale / unavailable 時自動嘗試 read-only refresh
  - governance payload 已帶 `auto_refresh` 與 5 分鐘 cooldown
  - Dashboard 會直接顯示 refresh command / escalation message / auto refresh state
- **本輪新增 closure**：
  - `server/main.py` 啟動時會自動啟動 **execution metadata background monitor**
  - 背景監看器每 60 秒執行一次 stale governance 檢查，不再只依賴 `/api/status` 輪詢
  - `execution_metadata_smoke.governance.background_monitor` 已成為 runtime contract
  - Dashboard 會顯示 `background monitor status / checked_at / freshness / interval_seconds`
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，2/2 venue metadata contract 可讀**
  - `python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **16 passed**
  - `cd web && npm run build` → **成功**

---

## 目前主目標

### 目標 A：把 execution runtime visibility 升級成真正的 process-independent governance
重點：
- stale / unavailable metadata smoke 不只要可見、也不只要 API 內自動 refresh
- 還要在 **API process 掛掉時** 仍保有外部治理路徑
- governance contract 必須能明確告訴 operator：現在是 API 裡的補救、背景 thread 的補救，還是需要 process 外升級

### 目標 B：定義第二個 execution operator-facing route 的真相
重點：
- 目前 code inventory 顯示，只有 Dashboard 完整消費 `/api/status + guardrails + metadata governance`
- `SignalBanner.tsx` 雖有 `/api/trade`，但沒有 runtime refresh / guardrail context / stale governance
- 下一輪必須在「升級 SignalBanner」與「正式文件化 Dashboard 是唯一 canonical route」之間做出明確決策

### 目標 C：維持 readiness 邊界紀律
重點：
- runtime governance / visibility closure **不等於** live/canary order-level readiness
- 在 order ack / fill lifecycle / live credential 驗證完成前，不得升級敘事

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續只靠 `/api/status` 輪詢 auto-refresh | 改動最小 | UI 沒被打開時就沒有治理；上輪 blocker 原樣存在 | 治標 | 只想保留現有 contract | ❌ 不建議 |
| 在 FastAPI 常駐 process 內加入 background monitor，並把 state 進 governance payload | 立即把 stale 治理從「被動輪詢」升級為「主動背景監看」，且可沿用既有 read-only smoke lane | 仍依賴 API process 存活，還不是跨 process 治理 | **治本第一步** | 已有安全可重跑的 metadata smoke 腳本 | ✅ 本輪採用 |
| 直接做外部 scheduler / pager / cron | 可真正擺脫 API process 依賴 | 範圍較大；若本輪直接做，會把 closure 拖散 | 治本第二步 | 先有 machine-readable background state | ⏳ 下一輪採用 |
| 先去做第二 route UI，不先補背景治理 | 可擴張 route coverage | stale governance 根因仍未處理完 | 治標 | stale 問題已完全解掉 | ❌ 本輪不採用 |

### 效益前提驗證
- 前提 1：metadata smoke lane 是 read-only，可安全被背景 thread 反覆檢查 → **成立**
- 前提 2：Dashboard 已有 stale governance 面板可承接新增 `background_monitor` contract → **成立**
- 前提 3：先把 API 內背景治理落地，再談 process 外升級，比直接跨 process 改動更容易形成可驗證閉環 → **成立**
- 前提 4：本輪是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## Next focus
1. 把 metadata smoke 背景監看從 **API process 內 thread** 升級成 **scheduler / pager / cron 外部治理路徑**
2. 收斂第二個 execution operator-facing route：升級 `SignalBanner`，或正式宣告 Dashboard 是唯一 canonical execution route
3. 維持 readiness 文案只描述 runtime governance / visibility，不升級成 live/canary safe

## Success gate
- stale metadata smoke 在 API process 掛掉時仍有外部治理路徑
- execution runtime 證據不再只集中在 Dashboard，或已正式文件化為單一路徑策略
- 文件仍明確區分 runtime governance closure 與 live/canary readiness

## Fallback if fail
- 若 process 外治理本輪做不出來，至少要把 scheduler / pager / cron 的責任邊界與人工 fallback contract 寫清楚，不可只留一句 future work
- 若盤點後決定不擴第二 route，必須正式把 Dashboard 定義為唯一 canonical execution route，避免後續假設已存在第二條驗證路徑
- 若有人把本輪結果誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 process 外 scheduler / pager / cron contract，或正式定義 canonical route）
- `server/main.py`
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 若升級第二 route，則同步更新對應前端元件與 regression tests

## Carry-forward input for next heartbeat
- 先檢查：`python scripts/execution_metadata_smoke.py --symbol BTCUSDT` 是否仍成功、`/api/status` governance 是否仍帶 `auto_refresh + background_monitor`、Dashboard stale governance 面板是否仍可見 background monitor 狀態
- 然後優先做：把背景治理升級到 **API process 外**（scheduler / pager / cron 至少一條）
- 接著處理：`SignalBanner` 是否升級成第二個 execution operator-facing route；若不升級，文件要正式說清楚 Dashboard 是唯一 canonical route
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
