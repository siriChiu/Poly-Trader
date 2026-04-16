# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 15:59 UTC_

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
- API process 內治理 closure：
  - `server/main.py` 啟動時會自動啟動 **execution metadata background monitor**
  - 背景監看器每 60 秒執行一次 stale governance 檢查，不再只依賴 `/api/status` 輪詢
  - `execution_metadata_smoke.governance.background_monitor` 已成為 runtime contract
  - Dashboard 會顯示 `background monitor status / checked_at / freshness / interval_seconds`
- **本輪新增 closure**：
  - `scripts/execution_metadata_external_monitor.py` 提供 **process-external governance lane**，可由 cron / scheduler / pager 直接執行
  - `data/execution_metadata_external_monitor.json` 成為 process 外治理 artifact
  - `server/routes/api.py` 會把 `external_monitor` 併入 `execution_metadata_smoke.governance`
  - Dashboard stale governance 面板會顯示 `external monitor status / checked_at / freshness / command / error`
- 驗證已通過：
  - `python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **18 passed**
  - `cd web && npm run build` → **成功**
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，2/2 venue metadata contract 可讀**
  - `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT` → **成功，external governance artifact healthy**

---

## 目前主目標

### 目標 A：把 process-external governance 從「可重跑 script」升級成「可安裝的 host-level contract」
重點：
- external monitor lane 已存在，但目前仍是 repo 內 command + artifact contract
- 下一步不是再證明 script 能跑，而是定義 **如何在 host 上穩定安裝與監控**
- 至少要在 cron / systemd timer / pager webhook 三者中收斂一條主路徑，並附 install / verify / fallback 說明

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
| 繼續只靠 API process 內 background monitor | 改動最小 | API 掛掉就整條治理失聯 | 治標 | 只想讓 UI 輪詢更舒服 | ❌ 不建議 |
| 新增 process-external monitor script + artifact contract | 立刻留下 API process 外可重跑治理路徑；可被 cron/pager 接手 | 還需要後續 host-level installer | **治本第一步** | 已有 read-only metadata smoke 腳本與 machine-readable governance state | ✅ 本輪採用 |
| 直接先做 host-level installer | 能直接碰部署 | 若沒有 machine-readable external artifact，installer 驗證邊界會模糊 | 治本第二步 | external monitor contract 已先存在 | ⏳ 下一輪採用 |
| 先去做第二 route UI，不先補 process-external lane | 可擴張 route coverage | 最大 blocker 仍是治理 lane 無法脫離 API process | 治標 | external governance 已完成且穩定 | ❌ 本輪不採用 |

### 效益前提驗證
- 前提 1：metadata smoke lane 是 read-only，可安全被 cron / scheduler 重跑 → **成立**
- 前提 2：Dashboard 已有 stale governance 面板可承接 external monitor contract → **成立**
- 前提 3：先落地 external artifact contract，再談 host-level installer，比直接跳部署更容易驗證 → **成立**
- 前提 4：本輪是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## Next focus
1. 把 `scripts/execution_metadata_external_monitor.py` 升級成 **明確的 host-level scheduler / pager install contract**（至少收斂一條主路徑）
2. 收斂第二個 execution operator-facing route：升級 `SignalBanner`，或正式宣告 Dashboard 是唯一 canonical execution route
3. 維持 readiness 文案只描述 runtime governance / visibility，不升級成 live/canary safe

## Success gate
- process-external governance 不只可手動重跑，還有清楚的 install / verify / fallback contract
- execution runtime 證據不再只集中在 Dashboard，或已正式文件化為單一路徑策略
- 文件仍明確區分 runtime governance closure 與 live/canary readiness

## Fallback if fail
- 若 host-level installer 本輪做不出來，至少要把 cron/systemd/pager 的責任邊界與人工 fallback contract 寫清楚，不可只留一句 future work
- 若盤點後決定不擴第二 route，必須正式把 Dashboard 定義為唯一 canonical execution route，避免後續假設已存在第二條驗證路徑
- 若有人把本輪結果誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若新增 host-level installer contract，或正式定義 canonical route）
- `scripts/execution_metadata_external_monitor.py`
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 若升級第二 route，則同步更新對應前端元件與 regression tests

## Carry-forward input for next heartbeat
- 先檢查：`python scripts/execution_metadata_smoke.py --symbol BTCUSDT` 與 `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT` 是否都仍成功，`/api/status` governance 是否同時帶 `auto_refresh + background_monitor + external_monitor`
- 然後優先做：把 external monitor 從 **可重跑 script** 升級成 **host-level scheduler / pager install contract**
- 接著處理：`SignalBanner` 是否升級成第二個 execution operator-facing route；若不升級，文件要正式說清楚 Dashboard 是唯一 canonical route
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
