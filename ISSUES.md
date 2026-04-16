# ISSUES.md — Current State Only

_最後更新：2026-04-16 14:25 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，先處理 **execution runtime surface 要看到 metadata smoke 摘要，且成功路徑要顯式回傳 normalized qty / price / contract**。

已完成的閉環：
1. `ExecutionService.submit_order()` 成功路徑現在會回傳 `normalization={requested, normalized, contract}`，並把同一份摘要寫入 runtime `last_order`。
2. `/api/status` 現在會序列化 `execution_metadata_smoke` 摘要，直接暴露最近一次 `data/execution_metadata_smoke.json` 的 venue contract 結果。
3. Dashboard 已新增 **Metadata smoke 摘要** 區塊，並在 **最近委託 / 手動交易即時回饋** 顯示 normalized qty / price / contract。
4. 已補 regression tests，並同步 `ARCHITECTURE.md`，把 success-path normalization 與 metadata runtime-surface 升級為正式 contract。

目前 execution lane 的主缺口已從：
- 「smoke 只存在離線 artifact」
- 「success path 沒有 normalized contract 摘要」

收斂到：
- **P1：runtime surface 仍缺 browser-level / route-level 真實渲染驗證**
- **P1：metadata smoke 只有最近一次結果，尚未明確標示 stale / unavailable age policy**
- **P1：public metadata smoke 與 success contract 已補齊，但仍不可誤寫成 live/canary order-level readiness 完成**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`execution metadata smoke 已落地並實測通過；下一輪先補 success path 的 normalized qty/price contract 摘要，並把 smoke 結果接進 operator-facing runtime surface`
- 上輪指定本輪先做：
  1. 把 metadata smoke 摘要接到 `/api/status` 或 Dashboard
  2. 讓 success path 顯示 normalized qty / price / contract
- 本輪明確不做：
  - 不擴 live 下單範圍
  - 不把 readiness 敘事升級成「已可安全放量」
  - 不做 execution P1 以外的模型 / label / leaderboard 調整

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大缺口是：success path 沒有 normalized contract 摘要、metadata smoke 還沒進 runtime surface。
2. **上輪明確要求本輪處理的是什麼？**
   - 先把 metadata smoke 從離線 artifact 推進到 operator-facing runtime surface，並補 success path normalized qty / price / contract。
3. **本輪要推進哪 1~3 件事？**
   - (a) 補齊 success path normalization contract
   - (b) 讓 `/api/status` 帶出 metadata smoke 摘要
   - (c) 讓 Dashboard 直接顯示 smoke + normalized order contract
4. **哪些事本輪明確不做？**
   - browser 自動化 QA、live/canary readiness 擴張、execution 以外 side quest

---

## 本輪事實摘要
### 已改善
- `execution/execution_service.py`
  - success path 新增 `normalization={requested, normalized, contract}`
  - runtime `last_order` 現在會保留 normalized qty / price 與 step/tick/min 規則摘要
- `server/routes/api.py`
  - `/api/status` 新增 `execution_metadata_smoke` 摘要欄位
  - 直接讀取 `data/execution_metadata_smoke.json`，把最近一次 smoke 結果帶到 runtime surface
- `web/src/pages/Dashboard.tsx`
  - 新增 **Metadata smoke 摘要** 卡片
  - **手動交易即時回饋** 會顯示 normalized qty / price / contract
  - **最近委託** 會顯示最近一次成功路徑的 normalization 摘要
- `ARCHITECTURE.md`
  - 新增 success-path normalization contract 與 metadata runtime-surface contract

### 驗證證據
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 2026-04-16 14:19 UTC
  - `ok_count=2/2`、`all_ok=true`
  - Binance：`step=0.00001000`、`tick=0.01000000`、`min_cost=5.0`
  - OKX：`step=0.00000001`、`tick=0.1`
- `source venv/bin/activate && python -m pytest tests/test_execution_metadata_smoke.py tests/test_execution_service.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
  - **23 passed**

### 卡住不動
- Dashboard 雖已帶出 smoke / normalization 摘要，但本輪仍未做 browser runtime QA，尚未驗證真實畫面與 interaction 沒被其他條件擋住
- metadata smoke 現在只暴露「最近一次結果」，尚未有明確 stale / unavailable age badge policy
- execution readiness 仍缺 live/canary order-level 驗證，不可把本輪 patch 誤寫成 readiness 完整

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型面主指標

本輪聚焦 execution runtime closure，不對未重跑的模型數字做假更新。

---

## Open Issues

### P1. 缺少 browser-level execution runtime 驗證
**現況**
- API / Dashboard source contract 已補齊
- regression tests 已驗證 code surface 存在

**缺口**
- 尚未用真實瀏覽器確認 Dashboard 上的 smoke 卡、最近委託 normalization、手動交易回饋是否確實可見

**風險**
- 原始碼存在 ≠ route/runtime 真有正確顯示；仍可能出現條件渲染或 UI layout regression

**下一步**
- 以 browser QA 驗證 `/api/status` 與 Dashboard execution panel 真實渲染
- 至少截圖或 route/runtime 驗證 smoke 摘要與 normalized contract 可見

### P1. Metadata smoke 缺少 freshness / stale policy
**現況**
- `/api/status` 已能暴露最近一次 smoke artifact
- Dashboard 可直接看到 venue contract 摘要

**缺口**
- 目前只有時間戳顯示，沒有 stale / unavailable / parse-failed policy
- operator 還不知道什麼時間差算「過期的 smoke」

**風險**
- artifact 太舊時，runtime surface 仍可能被誤讀成 readiness 健康

**下一步**
- 定義 smoke freshness age gate（例如 warn / stale / unavailable）
- 讓 `/api/status` 與 Dashboard 用同一套 badge 規則

### P1. 不可把 runtime closure 誤寫成 live/canary readiness 完成
**現況**
- public metadata smoke 已進 runtime surface
- success path normalized contract 也已可讀

**缺口**
- 這仍不是 live/canary order-level readiness 驗證
- 尚未覆蓋真實 exchange credential / order-ack / fill lifecycle

**風險**
- 若把本輪結果過度包裝成 execution 已可安全放量，會形成 readiness 假進度

**下一步**
- 文件維持「public metadata + success contract visible」的敘事邊界
- 只有在更高層級 canary/live 驗證完成後，才可升級 readiness 語義

---

## 本輪已處理
- success path normalization contract 落地（API + runtime last_order）
- `/api/status` metadata smoke summary 落地
- Dashboard smoke / normalized contract surface 落地
- regression tests 23 passed
- `ARCHITECTURE.md` 同步完成

---

## Current Priority
1. **P1：做 browser-level Dashboard / `/api/status` execution runtime 驗證**
2. **P1：定義 metadata smoke freshness / stale policy，避免舊 artifact 被誤判成健康**
3. **P1：維持 readiness 文案紀律，不把本輪 closure 誤寫成 live/canary 已完成**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`execution runtime surface 已可看到 metadata smoke 與 success-path normalized contract；下一輪先驗證這些資訊在真實 Dashboard route 上是否可見，並補 smoke freshness/stale policy`
- 本輪已完成：`ExecutionService success path normalization、/api/status execution_metadata_smoke、Dashboard Metadata smoke 摘要 + 最近委託 normalization、pytest 23 passed、ARCHITECTURE 同步完成`
- 下一輪必須先處理：`用 browser/runtime 驗證 execution panel 真實可見，並定義 metadata smoke stale/unavailable age gate`
- 成功門檻：`Dashboard 上可明確看到 smoke venue contract 與最近成功委託 normalized qty/price；同時 runtime surface 能區分 fresh vs stale smoke artifact`
- 若失敗：`升級為 blocker，文件必須明確標示 execution contract 雖已進 API/source，但 operator-facing runtime verification 仍未閉環，不可宣稱 readiness 更進一步`
