# ISSUES.md — Current State Only

_最後更新：2026-04-16 15:59 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，優先把 **execution metadata stale governance 從 API process 內 thread，推進成 process-external 可重跑治理路徑**。本輪沒有把時間分散到模型 / label / leaderboard side quest，也沒有把治理閉環誤包裝成 live/canary readiness。

本輪已完成的閉環：
1. `scripts/execution_metadata_external_monitor.py` 新增 **process-external governance lane**，可被 cron / scheduler / pager 直接呼叫，不依賴 FastAPI process 存活。
2. `server/routes/api.py` 新增 `external_monitor` 治理載入與 freshness 判讀，`/api/status` 的 `execution_metadata_smoke.governance` 現在同時包含 `auto_refresh + background_monitor + external_monitor`。
3. `web/src/pages/Dashboard.tsx` 的 stale governance 面板新增 **external monitor** 狀態、freshness、command 與 error 顯示，operator 可以直接看到 process 外治理是否最近真的跑過。
4. regression tests / build / smoke / external monitor script 已重跑，證明這不是只寫文件的 closure。

目前 execution lane 的主缺口已從：
- 「治理只有 API process 內 auto-refresh + background thread，API 掛掉就失聯」

收斂到：
- **P1：repo 已有 process-external monitor lane，但主機層級的常駐 scheduler / pager 安裝仍未在 repo 內自動佈署；目前留下的是可重跑 command + artifact contract，不是 host-level installer。**
- **P1：第二個 execution operator-facing route 仍未完成；目前完整 runtime governance surface 仍只有 Dashboard。**
- **P1：execution runtime closure 仍只能宣稱 governance / visibility 改善，不得誤寫成 live/canary order-level safe。**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`metadata smoke stale governance 已從 /api/status 輪詢升級為 API process 內 background monitor，但仍缺跨 process / pager / cron 的外部治理路徑；下一輪先補這條外部升級，避免 API 掛掉時治理一起消失。`
- 上輪指定本輪先做：
  1. 補上 stale governance 的 process-external scheduler / pager / cron 路徑
  2. 決定 `SignalBanner` 是否要升級成第二 execution route，或正式收斂 Dashboard 為唯一 canonical route
- 本輪明確不做：
  - 不擴 live/canary readiness 敘事
  - 不碰 execution 以外的模型 / label / leaderboard side quest
  - 不在治理閉環未完成前轉去做 UI 美化

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：metadata governance 仍缺 process-external 路徑，API process 掛掉就看不到治理狀態。
2. **上輪明確要求本輪處理的是什麼？**
   - 先補 process-external governance lane，再處理第二 execution route 的收斂。
3. **本輪要推進哪 1~3 件事？**
   - (a) 落地 external monitor script 與 artifact
   - (b) 把 external monitor state 掛回 `/api/status` contract 與 Dashboard
   - (c) 用 pytest / build / smoke / script 重跑驗證治理閉環
4. **哪些事本輪明確不做？**
   - live/canary readiness 升級、execution 以外主題、未驗證前就擴寫 `SignalBanner`

---

## 本輪事實摘要
### 已改善
- `scripts/execution_metadata_external_monitor.py`
  - 新增可由 **cron / scheduler / pager** 直接執行的 external monitor script。
  - 會寫出 `data/execution_metadata_external_monitor.json`，留下 process-external 治理證據。
- `server/routes/api.py`
  - 新增 `data/execution_metadata_external_monitor.json` 載入與 freshness policy。
  - `execution_metadata_smoke.governance` 現在包含 `external_monitor={status,reason,checked_at,freshness_status,governance_status,error,interval_seconds,command,freshness}`。
- `web/src/pages/Dashboard.tsx`
  - stale governance 面板新增 **external monitor** 狀態列與 command / error 顯示。
- `tests/test_server_startup.py`
  - 新增 external monitor artifact loading 與 governance contract regression tests。
- `tests/test_frontend_decision_contract.py`
  - 新增 Dashboard external monitor surface contract 檢查。
- `ARCHITECTURE.md`
  - 補上 process-external governance contract，避免文件仍停留在 API-only worldview。

### 驗證證據
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **18 passed**
- `cd web && npm run build`
  - **成功**
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 `2026-04-16T15:57:53Z`
  - `ok_count=2/2`、`all_ok=true`
- `source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_external_monitor.json` 更新為 `2026-04-16T15:58:27Z`
  - `status=healthy`、`freshness_status=fresh`、`governance_status=healthy`

### 卡住不動
- process-external lane 已可被 cron / scheduler 呼叫，但 repo 內還沒有 host-level installer / systemd / pager wiring；目前是 **可重跑 contract**，不是自動安裝器。
- 第二個 execution operator-facing route 仍未成立；`SignalBanner` 依然只有 `/api/trade` 送單，沒有 `/api/status` refresh / governance / guardrail context。
- readiness 邊界仍需持續守住：本輪只是把 governance lane 擴到 process 外，不是 live/canary order-level readiness。

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型主指標

本輪聚焦 execution governance，不對未重跑的模型數字做假更新。

---

## 策略決策紀錄（Step 2）
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續只靠 API process 內 background monitor | 改動最小 | API 掛掉就整條治理失聯 | 治標 | 只想改善 UI 輪詢依賴 | ❌ 不建議 |
| 新增 process-external monitor script + artifact contract | 真正留下 API process 之外可重跑的治理路徑；可被 cron/pager 直接接手 | 還需要後續 host-level scheduler wiring | **治本第一步** | 已有 read-only smoke 腳本與 machine-readable governance state | ✅ 本輪採用 |
| 直接去做 `SignalBanner` 第二 route | 可擴張 route coverage | 最大 blocker 仍是治理 lane 不可在 API 掛掉時存活 | 治標 | external governance 已完成且穩定 | ❌ 本輪不採用 |

### 效益前提驗證
- 前提 1：metadata smoke lane 是 read-only，可安全被 cron / scheduler 重跑 → **成立**
- 前提 2：Dashboard / API 已有 governance 面板可承接 external monitor state → **成立**
- 前提 3：先把 external artifact contract 落地，再談 host-level installer，比直接在本輪綁死具體部署方式更容易驗證 → **成立**
- 前提 4：本輪是否已足以宣稱 live/canary readiness 完成 → **不成立**

---

## 六帽會議摘要
- **白帽**：新增 external monitor script、API governance 載入、Dashboard 顯示；18 tests passed；web build 成功；smoke 2/2 成功；external monitor artifact healthy。
- **紅帽**：若只在文件裡說「未來可接 cron」，仍會是假進度；因此本輪強制留下可執行 script 與 JSON artifact。
- **黑帽**：若下一輪不處理第二 route 或 host-level wiring，團隊很容易再次把 Dashboard 唯一路徑誤認成完整 execution closure。
- **黃帽**：現在 governance contract 已具備 API 內 / API 外雙路徑語義，後續接 cron、pager 或健康檢查服務時有穩定 machine-readable surface 可沿用。
- **綠帽**：本輪可落地 patch 是 external monitor script + API/Dashboard contract，同時用測試與 artifact 驗證。
- **藍帽**：本輪範圍收斂到 external governance lane，不同時擴大到 live readiness 或第二 route 大改。

---

## ORID 決策
- **O（Objective）**
  - 先前已有 `auto_refresh` 與 `background_monitor`，但都依賴 API process。
  - 本輪新增 `scripts/execution_metadata_external_monitor.py`，並成功產出 healthy artifact。
  - `/api/status` 與 Dashboard 現在可讀 `external_monitor` 狀態。
- **R（Reflective）**
  - 最大風險不再是「完全沒有 process 外治理路徑」，而是「已有路徑但尚未做 host-level installer 與第二 route 收斂」。
- **I（Interpretive）**
  - 根因是治理 contract 之前只存在於 API runtime memory；只要 API 停掉，operator 就失去可見性。
  - 本輪修正把治理證據落到 file artifact，讓 process 外 scheduler 有落腳點。
- **D（Decisional）**
  - `Owner:` Hermes
  - `Action:` 落地 process-external governance script、把 external monitor 併入 `/api/status` / Dashboard contract、同步更新架構與追蹤文件。
  - `Artifact:` `scripts/execution_metadata_external_monitor.py`、`data/execution_metadata_external_monitor.json`、`server/routes/api.py`、`web/src/pages/Dashboard.tsx`
  - `Verify:` `pytest`、`npm run build`、`execution_metadata_smoke.py`、`execution_metadata_external_monitor.py`
  - `If fail:` 若 external artifact 無法穩定產生，升級為 blocker，明確標示 governance 仍依賴 API process 存活。

---

## Open Issues

### P1. process-external governance lane 已落地，但 host-level scheduler / pager 安裝仍未封裝
**現況**
- repo 內已有 `scripts/execution_metadata_external_monitor.py` 與 `data/execution_metadata_external_monitor.json` contract。
- `/api/status` 與 Dashboard 已能顯示 external monitor 的 freshness / command / error。

**缺口**
- 還沒有 repo 內建的 cron/systemd/pager installer；目前是可重跑 command，不是自動安裝。

**風險**
- 若團隊以為「external script 已存在」就等於「host-level 安裝已完成」，仍會形成治理假進度。

**下一步**
- 決定要交付哪種 host-level wiring（cron、systemd timer、pager webhook 其一），至少留下可驗證的 install / fallback contract。

### P1. 第二個 execution operator-facing route 仍未成立
**現況**
- Dashboard 是唯一完整顯示 execution status / guardrails / stale governance / order feedback 的 route。
- `SignalBanner.tsx` 仍只有 `/api/trade` / automation toggle，沒有 `/api/status` refresh、沒有 guardrail context、沒有 metadata governance contract。

**缺口**
- execution runtime 證據仍集中在 Dashboard 單一路徑。

**風險**
- 可能出現 API contract 已存在，但其他互動 surface 仍是半套 manual trade UI 的假完成。

**下一步**
- 二選一：
  1. 把 `SignalBanner` 升級成真正的 operator-facing execution surface（接 `/api/status` refresh + guardrail/governance context），或
  2. 正式文件化「目前只有 Dashboard 是 canonical execution route」。

### P1. execution readiness 邊界仍要持續守住
**現況**
- 本輪修的是 metadata governance 的 process-external closure。

**缺口**
- 尚未驗證真實 exchange credential、order ack、fill lifecycle、canary/live safety。

**風險**
- 若把本輪結果誤寫成 live/canary safe，會形成 readiness 假進度。

**下一步**
- 文件持續使用「runtime governance / visibility closure」語義；只有 order-level 驗證完成後才可升級 readiness 語言。

---

## 本輪已處理
- process-external metadata governance script 落地
- external monitor artifact contract 落地
- `/api/status` governance 新增 `external_monitor`
- Dashboard stale governance 面板顯示 external monitor
- regression tests 18 passed
- web build 成功
- metadata smoke 腳本成功（2/2）
- external monitor 腳本成功（healthy artifact）
- ARCHITECTURE 同步更新 process-external governance contract

---

## Current Priority
1. **P1：把 process-external governance 從「可重跑 script」升級成「明確的 host-level scheduler / pager install contract」**
2. **P1：決定 `SignalBanner` 要升級成第二 execution route，還是正式宣告 Dashboard 為唯一 canonical route**
3. **P1：維持 readiness 文案紀律，不把本輪 closure 誤寫成 live/canary safe**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`process-external execution metadata governance lane 已落地，但仍缺 host-level scheduler / pager installer；下一輪先把安裝/部署契約收斂清楚，避免 external lane 只停在可手動重跑。`
- 本輪已完成：`scripts/execution_metadata_external_monitor.py、data/execution_metadata_external_monitor.json、server/routes/api.py external_monitor governance、Dashboard external monitor 顯示、pytest 18 passed、web build 成功、execution_metadata_smoke.py 2/2 成功。`
- 下一輪必須先處理：`(1) external monitor 的 host-level wiring/install contract；(2) SignalBanner 是否升級成第二 execution operator-facing route，否則正式文件化 Dashboard 是唯一 canonical route。`
- 成功門檻：`process-external lane 不只可手動重跑，還有明確 scheduler / pager install or fallback contract；execution runtime route coverage 不再模糊。`
- 若失敗：`升級為 blocker，文件必須明確標示 external lane 仍停在手動/半自動階段、且 execution route coverage 仍不足，不可宣稱 execution readiness 已完成。`
