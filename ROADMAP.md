# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 18:06 UTC_

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
- API process 內治理 closure 已落地：
  - `server/main.py` 啟動時會自動啟動 execution metadata background monitor
  - 背景監看器每 60 秒執行一次 stale governance 檢查
  - `execution_metadata_smoke.governance.background_monitor` 已成為 runtime contract
- process-external governance closure 已落地：
  - `scripts/execution_metadata_external_monitor.py`
  - `data/execution_metadata_external_monitor.json`
  - `/api/status` 會把 `external_monitor` 併入 governance payload
  - Dashboard 會顯示 `external monitor status / checked_at / freshness / command / error`
- install contract closure 已落地：
  - `scripts/execution_metadata_external_monitor_install.py`
  - `data/execution_metadata_external_monitor_install_contract.json`
  - `/api/status` 與 Dashboard 會顯示 `preferred_host_lane / install command / install verify / fallback command / systemd timer`
- explicit ticking-state contract 已落地：
  - `/api/status` 導出 `execution_metadata_smoke.governance.external_monitor.ticking_state`
  - `ticking_state.status` 正式收斂為四態：
    - `install-ready`
    - `installed`
    - `observed-ticking`
    - `installed-but-not-ticking`
  - API 在 external artifact 缺失時，會 fallback 讀取 install contract
  - Dashboard 已新增 `external monitor state` 區塊
- execution surface contract 已落地：
  - `/api/status` 新增 `execution_surface_contract`
  - `execution_surface_contract` 正式收斂 route split + readiness boundary：
    - `canonical_execution_route=dashboard`
    - `canonical_surface_label=Dashboard / Execution 狀態面板`
    - `shortcut_surface.name=signal_banner`
    - `shortcut_surface.role=shortcut-only`
    - `shortcut_surface.status=not-upgraded`
    - `readiness_scope=runtime_governance_visibility_only`
    - `live_ready=false`
    - `live_ready_blockers=[credential, order ack, fill lifecycle]`
  - Dashboard 已新增 `execution route contract` 區塊，不再只靠文件或靜態文案維持 route 邊界
  - SignalBanner 已新增回 Dashboard 的明示導引，避免 shortcut lane 被誤當成完整 execution surface
- **本輪新增 closure**：
  - 直接驗證 `http://127.0.0.1:8000/api/status` 仍回傳完整 `execution_surface_contract`
  - 直接驗證 `external_monitor.ticking_state.status = observed-ticking`
  - regression tests 現在補鎖 execution route contract 細節：
    - `canonical_surface_label`
    - `shortcut_surface.status / message / upgrade_prerequisite`
    - `operator_message`
    - `live_ready_blockers`
  - 對應檔案：
    - `tests/test_server_startup.py`
    - `tests/test_frontend_decision_contract.py`

---

## 目前主目標

### 目標 A：守住 execution route contract
重點：
- `/api/status` 與 Dashboard 已能直接回答：
  - canonical execution route 是哪一條
  - canonical surface label 是什麼
  - SignalBanner 目前是什麼角色
  - readiness scope / live blockers 是什麼
- 下一步不是擴第二 route，而是守住這份 contract 不被 UI / API / 文件 / 文案回退
- regression tests 與 runtime smoke 必須持續一起維護，避免 contract 細節靜默流失

### 目標 B：維持清楚的 execution route 分工
重點：
- Dashboard 仍是唯一 canonical execution route
- `SignalBanner.tsx` 仍維持快捷下單 / automation lane
- 如果未來要升級第二 route，必須完整消費 `/api/status` 的：
  - `ticking_state`
  - `stale governance`
  - `guardrail context`
  - `install_contract`
  - `execution_surface_contract`

### 目標 C：維持 readiness / ticking 邊界紀律
重點：
- 本輪完成的是 execution governance / visibility / ticking contract 驗證
- 這不等於 live/canary order-level readiness
- 在 order ack / fill lifecycle / live credential 驗證完成前，不得升級敘事
- 在 `ticking_state` 與 `live_ready=false` 仍存在時，任何 surface 都不得把 host scheduler 健康誤寫成實盤可用

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只做一次 runtime smoke，不補測試 | 快速知道現在有沒有壞 | 之後仍可能靜默回退 | 治標 | 只想臨時確認 | ❌ 不建議 |
| 直接把 SignalBanner 升成第二 execution route | 表面 coverage 增加 | 會跳過既有 contract 邊界，重新引入假完成 | 治標（治本需先補同一份 runtime contract） | 已完整消費同一份 `/api/status` contract 時 | ❌ 不建議 |
| 先驗證 runtime contract，再補 regression lock 守住細節 | 同時處理「現在還在嗎」與「之後會不會靜默消失」 | 不會直接提升 live readiness | 治本 | Dashboard 仍是 canonical route | ✅ 本輪採用 |

### 效益前提驗證
- 前提 1：Dashboard 仍是 canonical execution route → **成立**
- 前提 2：SignalBanner 現階段不應升級為第二 route → **成立**
- 前提 3：`/api/status` 仍是各 surface 的共同入口 → **成立**
- 前提 4：本輪是否可升級成 live/canary ready → **不成立**

---

## Next focus
1. 再次確認 `/api/status`、Dashboard、SignalBanner 仍同時維持 `canonical route / canonical surface / shortcut-only / live_ready=false / observed-ticking`
2. 維持 Dashboard 為 canonical execution route；未升級前不再把 SignalBanner 描述成完整 runtime governance surface
3. 繼續把 readiness 文案限制在 runtime governance / visibility / ticking，不升級成 live/canary safe

## Success gate
- `/api/status` 與 Dashboard 持續直接區分 canonical route / canonical surface / shortcut lane / readiness scope / live blockers
- `external_monitor.ticking_state` 持續可 machine-read，且健康時明確顯示 `observed-ticking`
- execution route coverage 不再模糊：Dashboard 是 canonical route，SignalBanner 僅屬 shortcut lane
- 文件、UI、API 都持續明確顯示 `live_ready=false`，沒有把 governance/ticking closure 誤寫成 live-ready

## Fallback if fail
- 若 `execution_surface_contract` 或 `ticking_state` 無法維持，立即退回 blocker 敘事，明示目前又回到文件/人工判讀維持 route 邊界
- 若未來要擴第二 route，必須先補 `/api/status` refresh、guardrail context、stale governance、install/ticking-state 顯示，再宣稱 route coverage 擴張
- 若任何 surface 把 governance / ticking closure 誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `tests/test_server_startup.py`
- `tests/test_frontend_decision_contract.py`
- `server/routes/api.py`（若 contract 欄位變動）
- `web/src/pages/Dashboard.tsx`（若 contract 顯示變動）
- `web/src/components/SignalBanner.tsx`（若 shortcut lane 邊界變動）
- `ARCHITECTURE.md`（若 execution surface contract 或 ticking contract 再擴充）

## Carry-forward input for next heartbeat
- 先檢查：
  - `http://127.0.0.1:8000/api/status` 的 `execution_surface_contract`
  - `http://127.0.0.1:8000/api/status` 的 `execution_metadata_smoke.governance.external_monitor.ticking_state`
  - Dashboard 是否仍顯示 `execution route contract` 與 `external monitor state`
  - SignalBanner 是否仍明確導回 Dashboard
- 然後優先做：確認 route split / readiness / ticking boundary 是否仍穩定存在，沒有退回人工拼裝判讀
- 接著處理：在未升級完整 runtime contract 前，維持 `SignalBanner = shortcut lane`、`Dashboard = canonical execution route`
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
