# ISSUES.md — Current State Only

_最後更新：2026-04-16 15:12 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，優先把 **metadata smoke stale policy** 從「看得到 badge」推進成 **實際治理動作**。本輪選擇先修這條 P1，暫不擴寫其他 execution route，避免在 stale 治理未閉環前分散焦點。

已完成的閉環：
1. `server/routes/api.py::api_status()` 不再只回傳 freshness；現在會在 `freshness in {stale, unavailable}` 時自動嘗試重跑 read-only `run_metadata_smoke()`。
2. 新增 `governance={status, operator_action, operator_message, refresh_command, escalation_message, auto_refresh}` contract，並對自動 refresh 加上 **5 分鐘 cooldown**，避免 `/api/status` 輪詢放大 metadata lane 負載。
3. `web/src/pages/Dashboard.tsx` 新增 **stale governance** 面板，直接顯示目前治理狀態、auto refresh 結果、refresh command 與 escalation 訊息，不再只留下 FRESH/STALE badge。
4. 已補 regression tests 與 `ARCHITECTURE.md`，把 auto-refresh governance contract 升級為正式規約。

目前 execution lane 的主缺口已從：
- 「stale artifact 只有 badge，沒有後續治理」

收斂到：
- **P1：stale artifact 已有 API 內建 auto-refresh，但還沒有跨 process / scheduler / pager 的外部升級機制**
- **P1：本輪尚未驗證第二個 execution operator-facing route；目前 browser/runtime 證據仍集中在 Dashboard**
- **P1：execution runtime closure 仍不可誤寫成 live/canary order-level readiness**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`Dashboard 已可見 metadata smoke freshness badge、artifact age policy 與 venue contract；下一輪先決定 stale artifact 的自動治理動作，同時維持 readiness 邊界，不可誤升級成 live/canary safe`
- 上輪指定本輪先做：
  1. 把 stale metadata smoke 從可見 warning 推進到明確治理動作
  2. 選定下一個 execution operator-facing route 做 browser/runtime 驗證
- 本輪明確不做：
  - 不擴 live/canary readiness 敘事
  - 不碰 execution 以外的模型 / label / leaderboard side quest
  - 不在 stale 治理尚未落地前，把時間花在額外 UI 美化

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：stale metadata smoke 雖已可見，但沒有治理動作，造成 operator 只能看到 badge、不能閉環處置。
2. **上輪明確要求本輪處理的是什麼？**
   - 先把 stale metadata smoke 做成可治理 contract，再處理下一個 execution route 的 runtime/browser 驗證。
3. **本輪要推進哪 1~3 件事？**
   - (a) 在 `/api/status` 落地 auto-refresh governance contract
   - (b) 在 Dashboard 落地 operator-facing stale governance 面板
   - (c) 用 test/build/browser 證明新 contract 真正在 runtime surface 可見
4. **哪些事本輪明確不做？**
   - 第二 execution route 的擴張驗證、live order readiness 升級、execution 以外主題

---

## 本輪事實摘要
### 已改善
- `server/routes/api.py`
  - `execution_metadata_smoke` 除了 `freshness` 外，新增 `governance` payload
  - stale / unavailable 會自動重跑 `run_metadata_smoke()`
  - 自動 refresh 具備 5 分鐘 cooldown 與 machine-readable state
- `web/src/pages/Dashboard.tsx`
  - Metadata smoke 摘要新增 **stale governance** 面板
  - 顯示 auto refresh 狀態、refresh command、escalation 訊息
- `tests/test_server_startup.py`
  - 新增 stale artifact 自動 refresh 與 refresh failure 兩個 regression tests
- `tests/test_frontend_decision_contract.py`
  - 新增 governance surface 固定檢查
- `ARCHITECTURE.md`
  - 已同步 execution metadata auto-refresh governance contract

### 驗證證據
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 2026-04-16 15:05 UTC
  - `ok_count=2/2`、`all_ok=true`
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **14 passed**
- `cd web && npm run build`
  - **成功**
- Browser runtime QA（`http://127.0.0.1:5173/`）
  - Dashboard 可見：`smoke freshness FRESH`
  - Dashboard 可見：`stale governance healthy`
  - Dashboard 可見：`auto refresh idle`
  - Dashboard 可見：`refresh command: source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - reload 後 console **無 JS errors**
- Browser fetch `/api/status`
  - `execution_metadata_smoke.freshness.status = fresh`
  - `execution_metadata_smoke.governance.status = healthy`

### 卡住不動
- stale metadata smoke 已能在 API 內自動 refresh，但還沒有 scheduler / pager / 跨 process escalation
- 本輪尚未擴展到第二個 execution operator-facing route；browser/runtime 證據仍集中在 Dashboard
- execution runtime closure 仍只是 metadata / guardrail visibility，不是 live/canary order-level readiness

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型面主指標

本輪聚焦 execution stale governance，不對未重跑的模型數字做假更新。

---

## Open Issues

### P1. stale metadata smoke 已能 auto-refresh，但還沒有外部升級機制
**現況**
- `/api/status` 會在 stale / unavailable 時自動重跑 metadata smoke
- Dashboard 已可讀出治理狀態、auto refresh 結果、refresh command、escalation 訊息

**缺口**
- 目前治理觸發點仍綁在 `/api/status` 輪詢
- 沒有 scheduler / pager / background worker 形式的外部升級流程

**風險**
- 若 UI 沒被打開，stale artifact 可能不會立刻被治理
- 若 refresh 長期失敗，現在仍主要依賴 operator 看到 escalation 訊息後人工處理

**下一步**
- 把 governance contract 往 scheduler / pager / cron lane 擴展
- 讓 stale failure 能在 UI 之外也被主動升級

### P1. 尚未完成第二個 execution operator-facing route 的 browser/runtime 驗證
**現況**
- Dashboard execution panel 已完成 browser/runtime 驗證
- Dashboard 上的 stale governance contract 已可見，console 乾淨

**缺口**
- 其他 route 尚未做同等級 execution runtime 驗證
- 目前沒有正式文件化「下一個 execution surface 是哪一個」

**風險**
- 可能出現 source-level contract 已存在，但其他前端 surface 尚未正確接線的假完成

**下一步**
- 先盤點目前有沒有第二個真正 operator-facing execution route
- 若沒有，就把 Dashboard 內的最近拒單 / 最近委託 / stale governance 形成更強的 browser regression path；若有，就做 route/runtime/browser 驗證

### P1. execution readiness 邊界仍要持續守住
**現況**
- 本輪 closure 改善的是 metadata smoke stale governance
- browser/runtime 證據只證明 Dashboard execution surface 更完整

**缺口**
- 尚未觸及真實 exchange credential、order-ack、fill lifecycle、canary/live safety

**風險**
- 若把本輪結果誤包裝成 live/canary safe，會形成 readiness 假進度

**下一步**
- 文件持續維持「runtime visibility / governance closure」敘事
- 只有在 order-level 驗證完成後，才可升級 readiness 語義

---

## 本輪已處理
- metadata smoke stale governance contract 落地（API）
- stale / unavailable artifact auto-refresh + cooldown 落地（API）
- Dashboard stale governance 面板落地（UI）
- regression tests 14 passed
- build 成功
- browser runtime QA 完成
- `ARCHITECTURE.md` 同步完成

---

## Current Priority
1. **P1：把 stale governance 從 `/api/status` 輪詢內建 refresh，升級成 scheduler / pager / background escalation**
2. **P1：鎖定並驗證下一個 execution operator-facing surface，避免只驗 Dashboard**
3. **P1：維持 readiness 文案紀律，不把本輪 closure 誤寫成 live/canary safe**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`metadata smoke stale governance 已在 /api/status + Dashboard 落地，但它仍主要依賴 status 輪詢；下一輪先決定是否要補 scheduler / pager / background escalation，並且確認是否存在第二個 execution operator-facing route 可做 browser/runtime 驗證。`
- 本輪已完成：`/api/status auto-refresh governance contract、5 分鐘 cooldown、Dashboard stale governance 面板、pytest 14 passed、web build 成功、Dashboard browser runtime QA、ARCHITECTURE 同步完成。`
- 下一輪必須先處理：`(1) stale governance 的外部升級機制；(2) 第二個 execution operator-facing route 的盤點與 browser/runtime 驗證，若沒有第二 route，就把 Dashboard execution lane 的 regression path 再收斂成明確驗證腳本/契約。`
- 成功門檻：`stale metadata smoke 不只在 UI 打開時可治理，還有 scheduler/pager/background escalation 方案；execution runtime 證據不再只集中在 Dashboard 單一路徑。`
- 若失敗：`升級為 blocker，文件必須明確標示 execution runtime 雖已改善，但 stale governance 仍侷限在 status polling、且 execution route coverage 仍不足，不可宣稱 execution readiness 已完成。`
