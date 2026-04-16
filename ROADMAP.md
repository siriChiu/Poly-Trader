# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 16:21 UTC_

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
  - `server/main.py` 啟動時會自動啟動 execution metadata background monitor
  - 背景監看器每 60 秒執行一次 stale governance 檢查
  - `execution_metadata_smoke.governance.background_monitor` 已成為 runtime contract
  - Dashboard 會顯示 `background monitor status / checked_at / freshness / interval_seconds`
- process-external governance closure：
  - `scripts/execution_metadata_external_monitor.py` 提供可由 cron / scheduler / pager 直接執行的 external monitor lane
  - `data/execution_metadata_external_monitor.json` 成為 process 外治理 artifact
  - `server/routes/api.py` 會把 `external_monitor` 併入 `execution_metadata_smoke.governance`
  - Dashboard stale governance 面板會顯示 `external monitor status / checked_at / freshness / command / error`
- **本輪新增 closure**：
  - `scripts/execution_metadata_external_monitor_install.py` 提供 **host-level install contract generator**
  - `data/execution_metadata_external_monitor_install_contract.json` 持久化 `user_crontab / systemd_user / fallback` 契約
  - `scripts/execution_metadata_external_monitor.py` 產出的 artifact 現在內嵌 `install_contract`
  - `/api/status` 與 Dashboard 會直接顯示 `preferred_host_lane / install command / install verify / fallback command / systemd timer`
  - `SignalBanner.tsx` 已正式標示：Dashboard 是 canonical execution route；SignalBanner 只是快捷下單 / automation lane
- 驗證已通過：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT` → **成功，2/2 venue metadata contract 可讀**
  - `python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT` → **成功，install contract artifact 生成**
  - `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT` → **成功，external governance artifact healthy**
  - `python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **19 passed**
  - `cd web && npm run build` → **成功**

---

## 目前主目標

### 目標 A：把 host-level install contract 從 install-ready 推進到 installed + verified
重點：
- install contract 與 Dashboard surface 已完成
- 下一步不是再證明 contract 存在，而是依 `preferred_host_lane=user_crontab`（或必要時 `systemd --user`）**真正安裝並驗證**
- 驗證標準必須是 install command 已採用、verify command 有證據，而不是單純 artifact 還能手動重跑

### 目標 B：維持清楚的 execution route 分工
重點：
- 目前只有 Dashboard 完整消費 `/api/status + guardrails + metadata governance + install/fallback contract`
- `SignalBanner.tsx` 已正式收斂為快捷下單 / automation lane，不再模糊扮演第二條完整 execution route
- 若未來要升級第二 route，必須沿用 Dashboard 的同一套 runtime contract，而不是只接 `/api/trade`

### 目標 C：維持 readiness 邊界紀律
重點：
- runtime governance / visibility closure **不等於** live/canary order-level readiness
- 在 order ack / fill lifecycle / live credential 驗證完成前，不得升級敘事

---

## 本輪決策收斂

| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續只保留 external monitor script | 改動最少 | host-level 安裝與 verify 仍模糊 | 治標 | 只想證明 script 還能跑 | ❌ 不建議 |
| 新增 host-level install contract generator + Dashboard surface | 讓安裝責任、verify、fallback 變成 machine-readable contract | 還沒真的安裝 | **治本第一步** | external monitor script 已穩定 | ✅ 本輪採用 |
| 直接在本輪硬裝 host scheduler | 最接近完成狀態 | 若沒有先收斂 contract，會留下黑盒部署 | 治本第二步 | install contract 已落地 | ⏳ 下一輪採用 |
| 直接把 `SignalBanner` 升級成第二 route | 可增加 route coverage | 會分散主題，且目前仍缺完整 runtime context | 治標 | host-level install 已完成後再評估 | ❌ 本輪不採用 |
| 正式把 Dashboard 定義為 canonical execution route | 立即消除 route 假完成 | 第二 route 仍待未來升級 | **語義治本** | `SignalBanner` 尚未具備完整 contract | ✅ 本輪採用 |

### 效益前提驗證
- 前提 1：external monitor script 已能穩定重跑並產生 healthy artifact → **成立**
- 前提 2：Dashboard 已有 stale governance 面板可承接 install/fallback contract → **成立**
- 前提 3：先明確標示 canonical route，比直接擴大第二 route 更能避免假完成 → **成立**
- 前提 4：本輪是否已可宣稱 host-level scheduler installed → **不成立**

---

## Next focus
1. 依 `preferred_host_lane` 真正安裝 external monitor scheduler，並用 `install verify` 證明 host-level lane 已存在
2. 維持 Dashboard 為 canonical execution route；未升級前不再把 SignalBanner 描述成完整 runtime governance surface
3. 繼續把 readiness 文案限制在 runtime governance / visibility，不升級成 live/canary safe

## Success gate
- host-level scheduler 已真正安裝，Dashboard 所顯示的 install/verify/fallback contract 與主機狀態一致
- execution route coverage 不再模糊：Dashboard 是 canonical route，SignalBanner 僅屬快捷 lane，除非未來另有完整升級 patch
- 文件仍明確區分 install-ready / installed / live-ready 三種狀態

## Fallback if fail
- 若本輪或下輪仍無法真正安裝 host-level scheduler，至少要把「未安裝原因 / 人工 fallback / verify 邊界」維持在 Dashboard 與文件中，不可再回退成一句 future work
- 若未來決定擴第二 route，必須先補 `/api/status` refresh、guardrail context、stale governance、install contract 消費，再宣稱 route coverage 擴張
- 若有人把 install-ready 誤寫成 live-ready，文件必須立即糾正並停止擴大 readiness 敘事

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若 host-level scheduler 已真正安裝，或第二 route 狀態有變）
- `scripts/execution_metadata_external_monitor_install.py`
- `scripts/execution_metadata_external_monitor.py`
- `server/routes/api.py`
- `web/src/pages/Dashboard.tsx`
- 若升級第二 route，則同步更新 `web/src/components/SignalBanner.tsx` 與 regression tests

## Carry-forward input for next heartbeat
- 先檢查：
  - `python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - `python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT`
  - `python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT`
  - `/api/status` governance 是否同時帶 `auto_refresh + background_monitor + external_monitor.install_contract`
- 然後優先做：依 `preferred_host_lane` 把 external monitor 真正安裝到 host-level scheduler，並執行 `install verify`
- 接著處理：在未升級完整 runtime contract 前，維持 `SignalBanner = 快捷 lane`、`Dashboard = canonical execution route`
- 若以上兩件事尚未完成，不要把 execution readiness 敘事升級成 live/canary safe
