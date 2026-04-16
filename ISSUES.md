# ISSUES.md — Current State Only

_最後更新：2026-04-16 14:49 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，先處理 **execution runtime surface 的真實瀏覽器驗證** 與 **metadata smoke freshness / stale policy**。

已完成的閉環：
1. `server/routes/api.py::_load_execution_metadata_smoke_summary()` 現在會輸出 `freshness={status,label,reason,age_minutes,stale_after_minutes}`，把 smoke artifact 正式分成 `fresh / stale / unavailable`。
2. `web/src/pages/Dashboard.tsx` 現在會顯示 `smoke freshness` badge 與 `artifact age ... · stale after ...`，不再只丟一個時間戳給 operator 自行判斷。
3. browser/runtime QA 過程中發現 `CandlestickChart` 用 inline `[]` 當 default props，導致 React `Maximum update depth exceeded`；已改成 module-level stable empty arrays，移除 render loop 根因。
4. 已補 regression tests，並同步 `ARCHITECTURE.md`，把 freshness contract 與 chart prop stability contract 升級為正式規約。

目前 execution lane 的主缺口已從：
- 「Dashboard 雖有 smoke 區塊，但沒有 freshness/stale policy」
- 「browser-level QA 暴露 chart render loop，runtime console 不乾淨」

收斂到：
- **P1：execution runtime 已完成 operator-facing freshness 顯示，但仍不是 live/canary order-level readiness**
- **P1：目前 browser QA 聚焦 Dashboard；其他 execution 相關 surface 尚未做同等級 route/runtime 驗證**
- **P1：smoke freshness 已有 API/UI contract，但 stale artifact 的實際運營處置（例如重新觸發 smoke / pager / badge escalation）尚未自動化**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`execution runtime surface 已可看到 metadata smoke 與 success-path normalized contract；下一輪先驗證這些資訊在真實 Dashboard route 上是否可見，並補 smoke freshness/stale policy`
- 上輪指定本輪先做：
  1. 用 browser/runtime 驗證 Dashboard execution panel 真實渲染
  2. 定義 metadata smoke fresh / stale / unavailable age gate
- 本輪明確不做：
  - 不擴 live 下單範圍
  - 不把 readiness 敘事升級成「已可安全放量」
  - 不做 execution P1 以外的模型 / label / leaderboard 調整

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大缺口是：smoke 只有 timestamp 沒有 freshness policy，且缺少真實瀏覽器驗證；browser QA 另外暴露 chart render loop。
2. **上輪明確要求本輪處理的是什麼？**
   - 先把 Dashboard execution panel 做成已驗證的 runtime surface，並補 metadata smoke stale / unavailable 判讀。
3. **本輪要推進哪 1~3 件事？**
   - (a) 定義 `/api/status` 的 metadata smoke freshness contract
   - (b) 讓 Dashboard 顯示 freshness badge 與 age policy
   - (c) 修掉 browser QA 暴露的 chart render loop
4. **哪些事本輪明確不做？**
   - live/canary readiness 擴張、execution 以外 side quest、未重跑的模型數字更新

---

## 本輪事實摘要
### 已改善
- `server/routes/api.py`
  - metadata smoke summary 新增 `freshness.status / age_minutes / stale_after_minutes / reason`
  - parse failure / invalid timestamp 會明確落成 `unavailable`
- `web/src/pages/Dashboard.tsx`
  - Metadata smoke 摘要新增 `smoke freshness` badge
  - 顯示 `artifact age ... · stale after ...`，讓 stale policy 可見
- `web/src/components/CandlestickChart.tsx`
  - 改用 stable empty arrays，修掉 browser QA 觀察到的 `Maximum update depth exceeded`
- `ARCHITECTURE.md`
  - 已同步 freshness contract 與 chart prop stability contract

### 驗證證據
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 2026-04-16 14:40 UTC
  - `ok_count=2/2`、`all_ok=true`
- `source venv/bin/activate && python -m pytest tests/test_execution_metadata_smoke.py tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
  - **26 passed**
- `cd web && npm run build`
  - **成功**
- Browser runtime QA（`http://127.0.0.1:5173/`）
  - Dashboard 可見：`smoke freshness FRESH`
  - Dashboard 可見：`artifact age 7.9m · stale after 30m`
  - Dashboard 可見 Binance / OKX venue contract 摘要
  - reload 後 console **無 JS errors**

### 卡住不動
- execution runtime closure 雖已更完整，但仍不等於 live/canary order-level readiness
- 目前只驗證到 Dashboard execution panel；其他 operator-facing execution surfaces 尚未做同級 browser/runtime 檢查
- stale artifact 的後續操作仍停留在人工判讀，尚未有自動 escalation / refresh 流程

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型面主指標

本輪聚焦 execution runtime closure，不對未重跑的模型數字做假更新。

---

## Open Issues

### P1. execution runtime closure 仍不可誤寫成 live/canary readiness 完成
**現況**
- Dashboard 已可見 metadata smoke freshness、venue contract、最近成功委託 normalization
- browser/runtime QA 已確認這些資訊在真實 route 上存在

**缺口**
- 尚未覆蓋真實 exchange credential / order-ack / fill lifecycle
- smoke 與 success contract 只證明 public metadata + UI closure，不代表 live order readiness

**風險**
- 若把本輪結果包裝成 execution 已可安全放量，會形成 readiness 假進度

**下一步**
- 文件維持「runtime visibility closure」敘事邊界
- 只有在 canary/live order-level 驗證完成後，才可升級 readiness 語義

### P1. execution browser QA 尚未擴展到其他 operator-facing routes
**現況**
- Dashboard execution panel 已完成 browser/runtime 驗證
- console 也已清乾淨，無 render loop / JS errors

**缺口**
- 其他與 execution 相關的 route / panel 尚未做相同層級驗證

**風險**
- 某些 route 可能仍有 source-level contract 已存在、但 runtime wiring 未實際可見的假完成

**下一步**
- 針對下一輪鎖定的 execution surface 做 route/runtime/browser 檢查
- 至少保留 console / DOM / 截圖等可驗證證據

### P1. metadata smoke stale policy 已可見，但沒有自動治理動作
**現況**
- `/api/status` 與 Dashboard 已能一致標示 `fresh / stale / unavailable`
- stale threshold 目前固定為 30 分鐘

**缺口**
- artifact stale 後沒有自動 refresh、提醒、或 escalate 流程
- 現階段仍依賴 operator 看到 badge 後手動處置

**風險**
- 若未來 smoke 長時間停留 stale，UI 雖不再假健康，但營運流程仍可能反應慢

**下一步**
- 定義 stale artifact 的運營處置：重新跑 smoke、提示 warning、或導入 scheduler/pager
- 保持 API 與 Dashboard 使用同一套 threshold

---

## 本輪已處理
- metadata smoke freshness contract 落地（API）
- Dashboard freshness badge / age policy 落地（UI）
- browser QA 暴露的 CandlestickChart render loop 已修復
- regression tests 26 passed
- `ARCHITECTURE.md` 同步完成

---

## Current Priority
1. **P1：維持 execution readiness 文案紀律，不把 runtime closure 誤寫成 live/canary safe**
2. **P1：把 browser/runtime QA 擴展到下一個 execution operator surface，避免只驗一條 route**
3. **P1：為 stale metadata smoke 定義自動治理動作（refresh / warning / escalation）**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`Dashboard 已可見 metadata smoke freshness badge、artifact age policy 與 venue contract；下一輪先決定 stale artifact 的自動治理動作，同時維持 readiness 邊界，不可誤升級成 live/canary safe`
- 本輪已完成：`/api/status metadata smoke freshness contract、Dashboard freshness badge + age policy、CandlestickChart stable-empty-defaults 修掉 render loop、browser runtime QA、pytest 26 passed、build 成功、ARCHITECTURE 同步完成`
- 下一輪必須先處理：`把 stale smoke 從可見 warning 推進到明確治理動作，並選定下一個 execution operator-facing route 做 browser/runtime 驗證`
- 成功門檻：`stale metadata smoke 不只可見，還有明確 refresh / escalation contract；新驗證的 execution surface 也要有 browser-level evidence 且 console 乾淨`
- 若失敗：`升級為 blocker，文件必須明確標示 execution runtime 雖已改善，但 stale artifact 治理與更高層 readiness 仍未閉環，不可宣稱 execution 已完成`
