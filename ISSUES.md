# ISSUES.md — Current State Only

_最後更新：2026-04-16 15:34 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，優先把 **metadata smoke stale governance 從 `/api/status` 輪詢內建 refresh，升級成 API 常駐 process 的背景監看機制**。本輪沒有把時間分散到新的模型 / label / leaderboard side quest，也沒有把 runtime closure 誤包裝成 live/canary readiness。

本輪已完成的閉環：
1. `server/main.py` 啟動 FastAPI 時，現在會自動啟動 **execution metadata background monitor**，每 60 秒在背景重跑治理檢查，不再只依賴有人呼叫 `/api/status`。
2. `server/routes/api.py` 新增 `run_execution_metadata_smoke_background_governance()` 與 `background_monitor` state，治理 payload 現在同時包含 `auto_refresh` 與 `background_monitor`，可區分「API 輪詢補救」與「常駐背景監看」。
3. `web/src/pages/Dashboard.tsx` 的 stale governance 面板新增 **background monitor** 狀態、最近檢查時間、freshness 狀態與間隔秒數，讓 operator 一眼看到背景治理是否真的在跑。
4. regression tests 與 build 已補上，證明 contract 不是只寫文件。

目前 execution lane 的主缺口已從：
- 「stale artifact 只有 badge；治理仍依賴 `/api/status` 被呼叫」

收斂到：
- **P1：背景監看已在 API process 內落地，但還沒有跨 process / pager / cron 的外部升級機制；若 API 本身停掉，治理仍會中斷。**
- **P1：第二個 execution operator-facing route 仍未完成；目前完整 runtime governance surface 仍只有 Dashboard。**
- **P1：execution runtime closure 仍只能宣稱 governance / visibility 改善，不得誤寫成 live/canary order-level safe。**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`metadata smoke stale governance 已在 /api/status + Dashboard 落地，但它仍主要依賴 status 輪詢；下一輪先決定是否要補 scheduler / pager / background escalation，並且確認是否存在第二個 execution operator-facing route 可做 browser/runtime 驗證。`
- 上輪指定本輪先做：
  1. 補上 stale governance 的外部升級機制
  2. 盤點第二個 execution operator-facing route
- 本輪明確不做：
  - 不擴 live/canary readiness 敘事
  - 不碰 execution 以外的模型 / label / leaderboard side quest
  - 不在 stale 治理未閉環前轉去做 UI 美化

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：stale metadata smoke 雖然已有 auto-refresh，但仍依賴 `/api/status` 輪詢觸發，沒有常駐背景治理。
2. **上輪明確要求本輪處理的是什麼？**
   - 先把 stale governance 往 scheduler / pager / background escalation 推進，再盤點第二個 execution route。
3. **本輪要推進哪 1~3 件事？**
   - (a) 在 FastAPI 啟動流程落地背景監看器
   - (b) 把 background monitor 狀態掛回 API governance contract 與 Dashboard
   - (c) 用 smoke / pytest / build 驗證治理閉環
4. **哪些事本輪明確不做？**
   - live/canary readiness 升級、execution 以外主題、未證實的第二 route UI 擴寫

---

## 本輪事實摘要
### 已改善
- `server/main.py`
  - 新增常駐 **execution metadata background monitor**，API 啟動後每 60 秒自動執行治理檢查。
- `server/routes/api.py`
  - `execution_metadata_smoke.governance` 新增 `background_monitor={status,reason,checked_at,freshness_status,governance_status,error,interval_seconds}`。
  - `run_execution_metadata_smoke_background_governance()` 會把背景監看狀態同步寫入 runtime status。
- `web/src/pages/Dashboard.tsx`
  - stale governance 面板新增 **background monitor** 狀態列。
- `tests/test_server_startup.py`
  - 新增背景治理狀態與背景監看 loop regression tests。
- `tests/test_frontend_decision_contract.py`
  - 新增 Dashboard background monitor surface contract 檢查。

### 驗證證據
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 `2026-04-16T15:32:59Z`
  - `ok_count=2/2`、`all_ok=true`
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **16 passed**
- `cd web && npm run build`
  - **成功**
- route inventory（以 code search 為證）
  - `web/src/pages/Dashboard.tsx`：唯一完整消費 `/api/status`、`execution_metadata_smoke`、guardrails、reject/order context 的 execution runtime surface
  - `web/src/components/SignalBanner.tsx`：雖會呼叫 `/api/trade`，但沒有接 `/api/status`、沒有 stale governance / guardrail context / refresh 閉環，因此**不算第二個完整 operator-facing runtime governance route**

### 卡住不動
- 背景治理目前是 **API process 內 thread**，還不是跨 process 的 scheduler / pager / cron；若 API 掛掉，治理仍會停。
- 第二個 execution operator-facing route 仍未完成；目前只有 Dashboard 達到完整 runtime governance contract。
- readiness 邊界仍需持續守住：本輪只是治理自動化更完整，不是 live/canary order-level readiness。

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型主指標

本輪聚焦 execution stale governance，不對未重跑的模型數字做假更新。

---

## Open Issues

### P1. stale governance 已進入背景監看，但仍缺跨 process / pager / cron 升級機制
**現況**
- FastAPI 啟動後已自動跑 background monitor，每 60 秒檢查一次 metadata smoke freshness。
- `/api/status` 與 Dashboard 已能同時看到 `auto_refresh` + `background_monitor` 狀態。

**缺口**
- 背景監看只存在於 API process 內。
- 若 API process 停止，stale governance 也會停止。

**風險**
- 真正的 process 級故障仍無法被 background monitor 自己發現並升級。

**下一步**
- 把治理升級到 scheduler / pager / cron lane，至少有一條不依賴 API process 的外部治理路徑。

### P1. 第二個 execution operator-facing route 仍未成立
**現況**
- Dashboard 是唯一完整顯示 execution status / guardrails / stale governance / order feedback 的 route。
- `SignalBanner.tsx` 雖有 `/api/trade` 按鈕，但沒有 `/api/status` refresh、沒有 guardrail context、沒有 metadata governance contract。

**缺口**
- execution runtime 證據仍集中在 Dashboard 單一路徑。

**風險**
- 可能出現 API contract 已存在，但其他互動 surface 仍是半套 manual trade UI 的假完成。

**下一步**
- 二選一：
  1. 把 `SignalBanner` 升級成真正的 operator-facing execution surface（接 `/api/status` refresh + guardrail/governance context），或
  2. 正式文件化「目前只有 Dashboard 是 canonical execution route」，避免假設存在第二條已驗證路徑。

### P1. execution readiness 邊界仍要持續守住
**現況**
- 本輪修的是 stale governance 自動化閉環。

**缺口**
- 尚未驗證真實 exchange credential、order ack、fill lifecycle、canary/live safety。

**風險**
- 若把本輪結果誤寫成 live/canary safe，會形成 readiness 假進度。

**下一步**
- 文件持續使用「runtime governance / visibility closure」語義；只有 order-level 驗證完成後才可升級 readiness 語言。

---

## 本輪已處理
- API process 內背景監看器落地（server startup）
- governance contract 新增 `background_monitor`
- Dashboard stale governance 面板顯示 background monitor
- regression tests 16 passed
- web build 成功
- metadata smoke 腳本成功（2/2）
- 第二 route inventory 已完成：目前只有 Dashboard 達完整 runtime governance contract

---

## Current Priority
1. **P1：把 background monitor 從 API process 內 thread，升級成 scheduler / pager / cron 外部治理路徑**
2. **P1：決定 `SignalBanner` 要升級成第二 execution route，還是正式宣告 Dashboard 為唯一 canonical execution route**
3. **P1：維持 readiness 文案紀律，不把本輪 closure 誤寫成 live/canary safe**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`metadata smoke stale governance 已從 /api/status 輪詢升級為 API process 內 background monitor，但仍缺跨 process / pager / cron 的外部治理路徑；下一輪先補這條外部升級，避免 API 掛掉時治理一起消失。`
- 本輪已完成：`server/main.py 背景監看器、server/routes/api.py background_monitor governance contract、Dashboard background monitor 顯示、pytest 16 passed、web build 成功、execution_metadata_smoke.py 2/2 成功、第二 route inventory（SignalBanner 目前不算完整 runtime governance route）。`
- 下一輪必須先處理：`(1) 外部 scheduler / pager / cron 治理路徑；(2) SignalBanner 是否升級成第二 execution operator-facing route，否則正式文件化 Dashboard 是唯一 canonical route。`
- 成功門檻：`stale governance 在 API process 掛掉時仍有外部治理路徑；execution runtime 證據不再只集中在 Dashboard，或已正式收斂為單一路徑策略。`
- 若失敗：`升級為 blocker，文件必須明確標示 stale governance 仍依賴 API process 存活、且 execution route coverage 仍不足，不可宣稱 execution readiness 已完成。`
