# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 16:42 UTC_

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
  - `SignalBanner.tsx` 已正式標示：Dashboard 是 canonical execution route；SignalBanner 只是快捷下單 / automation lane
- **本輪新增 closure**：
  - `preferred_host_lane=user_crontab` 已真正安裝到 host-level scheduler
  - install contract 現在會 machine-read `install_status={status, installed, active_lane, checked_at, lanes.*}`
  - Dashboard 會直接顯示 `install status / active lane / install checked at / crontab verify stdout`
  - `data/execution_metadata_external_monitor_install_contract.json` 與 `data/execution_metadata_external_monitor.json` 都已刷新為 `install_status.status=installed`
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，2/2 venue metadata contract 可讀**
  - `python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT` → **成功，artifact 顯示 installed + user_crontab**
  - `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT` → **成功，external governance artifact healthy**
  - `crontab -l | grep 'poly-trader-execution-metadata-external-monitor'` → **成功，host-level scheduler 已存在**
  - `python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **19 passed**
  - `cd web && npm run build` → **成功**

---

## 目前主目標

### 目標 A：確認 host-level scheduler 不是只「已安裝」，而是會自然週期地持續運作
重點：
- install-ready → installed 已完成
- 下一步不是再重做 install，而是驗證 **自然 cron 週期** 會刷新 external monitor artifact / log
- 驗證標準必須是 `generated_at/checked_at/log` 在無手動介入下前進

### 目標 B：維持清楚的 execution route 分工
重點：
- 目前只有 Dashboard 完整消費 `/api/status + guardrails + metadata governance + install_status`
- `SignalBanner.tsx` 仍維持快捷下單 / automation lane
- 若未來要升級第二 route，必須沿用 Dashboard 的同一套 runtime contract，而不是只接 `/api/trade`

### 目標 C：維持 readiness 邊界紀律
重點：
- runtime governance / visibility closure **不等於** live/canary order-level readiness
- 在 order ack / fill lifecycle / live credential 驗證完成前，不得升級敘事

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續停在 install-ready | 不用碰 host-level 環境 | blocker 原封不動，下一輪還是同一題 | 治標 | 只想保留契約文字 | ❌ 不建議 |
| 安裝 `user_crontab` 並用 `crontab -l` 驗證 | 直接完成 preferred host lane 落地 | 還需要把 installed 狀態同步到 artifact / UI | 治本第一步 | crontab 可用 | ✅ 本輪採用 |
| 只裝 cron，不補 installed-state surface | 主機上有 scheduler | UI/API 仍看不到是否真的 installed | 治標 | 只追求主機落地 | ❌ 不建議 |
| install status machine-readable + Dashboard surface | operator 能直接看到 installed / active lane / verify output | 需要 patch + regression | 治本收尾 | install contract 已存在 | ✅ 本輪採用 |
| 直接擴 `SignalBanner` 成第二 route | 可能增加操作入口 | 會分散主題，且仍缺完整 runtime contract | 治標 | scheduler 穩定後再評估 | ❌ 本輪不採用 |

### 效益前提驗證
- 前提 1：`crontab` 在本機可用 → **成立**
- 前提 2：external monitor 腳本已穩定 → **成立**
- 前提 3：Dashboard governance 面板可承接 install status → **成立**
- 前提 4：本輪是否已可宣稱 live/canary ready → **不成立**

---

## Next focus
1. 在**不手動重跑 external monitor** 的情況下，驗證 artifact / log 會由 cron 自然刷新
2. 維持 Dashboard 為 canonical execution route；未升級前不再把 SignalBanner 描述成完整 runtime governance surface
3. 繼續把 readiness 文案限制在 runtime governance / visibility，不升級成 live/canary safe

## Success gate
- external monitor artifact 與 log 在自然 cron 週期下前進，證明 host-level lane 不只是 installed，且會持續 ticking
- execution route coverage 不再模糊：Dashboard 是 canonical route，SignalBanner 僅屬快捷 lane
- 文件仍明確區分 install-ready / installed / observed-ticking / live-ready 幾種狀態

## Fallback if fail
- 若 scheduler 已安裝但下一輪觀察不到自然 tick，必須把狀態降級為 `installed-not-observed` 或 `installed-but-not-ticking`，並明確保留 fallback command / verify 邊界
- 若未來要擴第二 route，必須先補 `/api/status` refresh、guardrail context、stale governance、install status 消費，再宣稱 route coverage 擴張
- 若有人把 governance installed 誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若加入 observed-ticking / install-state 新 contract 或第二 route 狀態改變）
- `scripts/execution_metadata_external_monitor_install.py`
- `scripts/execution_metadata_external_monitor.py`
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 若升級第二 route，則同步更新 `web/src/components/SignalBanner.tsx` 與 regression tests

## Carry-forward input for next heartbeat
- 先檢查：
  - `crontab -l | grep 'poly-trader-execution-metadata-external-monitor'`
  - `tail -n 20 data/execution_metadata_external_monitor.log`
  - `python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT`
  - `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT`（只在需要人工 refresh 診斷時使用）
  - `/api/status` governance 是否同時帶 `background_monitor + external_monitor + external_monitor.install_contract.install_status`
- 然後優先做：確認 external monitor 的 `generated_at/checked_at` 是否在自然 cron 週期下前進，而不是只靠手動重跑
- 接著處理：在未升級完整 runtime contract 前，維持 `SignalBanner = 快捷 lane`、`Dashboard = canonical execution route`
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
