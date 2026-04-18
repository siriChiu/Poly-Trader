# Execution Console 實戰交易頁產品化計畫

> **For Hermes:** 後續實作時請用 subagent-driven-development，逐 task 落地、先測試後實作、每步都驗證。

**Goal:** 新增一個與原本 Dashboard 分離的「Execution Console / 實戰交易頁」，讓使用者能選擇既有策略、設定資金、同時啟動多組策略實盤/模擬運行，並即時查看每組策略的盈虧、狀態、風控與停止控制。

**Architecture:** 前端新增獨立頁面 `/execution`，不再把交易營運 UI 塞在 Dashboard。後端新增「策略執行設定檔 + 執行實例 + 生命週期事件 + PnL 快照」資料模型與 API，ExecutionService 只負責下單/風控，不再承擔 UI session state。以 Pionex 風格的多組 bot 卡片做營運面板，但先做 MVP：單頁總覽 + 詳情抽屜 + 開始/停止/資金配置。

**Tech Stack:** React + TypeScript + FastAPI + SQLAlchemy/SQLite + 既有 ExecutionService/AccountSyncService。

---

## 現況盤點
- `web/src/App.tsx` 目前只有 `/`、`/senses`、`/lab` 三頁，尚無獨立 execution route。
- `web/src/pages/Dashboard.tsx` 目前內嵌大段 Execution 狀態面板，偏 operator/診斷，不是實戰營運頁。
- `web/src/pages/StrategyLab.tsx` 已有 strategy leaderboard/workspace，可作為「策略來源」與「選擇策略名稱」的上游。
- `server/routes/api.py` 目前已有 `/api/status` 與 `/api/trade`，但尚無「多策略執行個體管理」API。
- `execution/execution_service.py` 已有多 venue foundation，但還沒有「bot/session/profile」概念。

---

# 六色帽會議：需求補齊

## 白帽（事實）
1. 使用者明確要一個**獨立新頁面**，不是 Dashboard 裡的一塊卡片。
2. 頁面目的是**交易實戰/營運**，不是研究或 debug。
3. 使用者希望：
   - 選擇前面已設定好的策略名稱
   - 設定使用資金，例如 100 美元
   - 可同時開多組策略
   - 隨時看到各組賺多少、虧多少
   - 可開始、停止
4. 現有系統已有 strategy source 與 execution foundation，但缺少：
   - execution profile/runs
   - 多 bot 狀態管理
   - PnL 彙總模型
   - 獨立營運頁

## 紅帽（感受）
1. Dashboard 現在太像工程總控台，對實戰使用者不夠直觀。
2. 使用者想要的是「我開了哪些 bot、現在賺多少、能不能停」，不是一堆 contract/governance 字樣。
3. 如果 execution UI 不獨立，會讓研究、診斷、營運三種心智混在一起，產品感很差。

## 黑帽（風險）
1. 若直接用目前 `/api/trade` 拼 UI，會變成一次性按鈕，不具備 bot/session 管理能力。
2. 多組同時交易若沒有資金保留/分配治理，可能超配資金、重複下單或互相污染。
3. 若只顯示未實現盈虧，不顯示已實現盈虧、資金占用、停止原因，使用者會誤判 bot 績效。
4. 若沒有「策略版本快照」，之後 strategy name 同名改參數，會無法知道正在跑的是哪個版本。
5. 若沒有 canary / paper / live 明確分層，產品頁會讓人誤以為已 fully live-ready。
6. 若為了做出「活躍感」而刻意降低 confidence / entry-quality / gate threshold，會把系統推向假高頻，放大噪音交易與回撤，違背產品方向。

## 黃帽（機會）
1. 新頁面可把 Poly-Trader 從「研究工具」推向「可營運產品」。
2. Strategy Lab 已有 leaderboard，可直接成為 bot 建立入口，形成完整漏斗：研究 → 選策略 → 上線運行。
3. 多組 bot 面板會自然帶出後續高價值功能：
   - 資金配置器
   - 風控組合管理
   - venue 切換
   - PnL / 勝率 / 回撤營運追蹤

## 綠帽（創意）
1. 採 **Pionex 式 bot 卡片**：每張卡即一個 strategy run，顯示狀態、投入資金、當前淨值、PnL、今日變化、停止按鈕。
2. 新增 **Bot Draft / Bot Run** 雙層：
   - Draft：使用者設定但未開始
   - Run：已啟動且有生命週期、資金與績效
3. 加入 **資金池視角**：總可用資金 / 已分配 / 未分配，避免多 bot 超配。
4. 每個 bot 都要有**策略快照摘要**：策略名稱、來源（leaderboard/workspace）、建立時參數 hash、venue、mode、symbol universe。
5. 狀態採產品語言：
   - 草稿
   - 運行中
   - 暫停中
   - 已停止
   - 風控停止
   - 交易所異常
   而不是 raw internal wording。

## 藍帽（決策）
### 決策結論
先做一個獨立的 **Execution Console MVP**，範圍明確切成 3 層：
1. **MVP 營運層**：建立/啟動/停止多組 bot，顯示資金與 PnL。
2. **治理層**：資金分配限制、mode/venue、風控停止原因。
3. **診斷層**：詳情抽屜顯示 recent orders / rejects / lifecycle，必要時再跳回 Dashboard。

另外強制產品原則：
- **取消「靠降低閾值做短期高頻」這條路線**。
- 實戰頁與策略 preset 不應為了增加 trade count 而降低 `confidence_min`、`entry_quality_min` 或放寬 gate。
- 若要提高資金使用率，應優先靠更好的策略品質、更多經驗證的策略組合、或更清楚的資金編排，而不是用低閾值換高頻。

不在 MVP 先做：
- 全自動再平衡
- 跨 bot 資金最佳化
- 複雜網格/加碼編排器
- 高級報表頁

---

# MVP 需求定義

## 核心頁面
### 新頁面：`/execution`
主用途：實戰交易營運，不放研究圖與心跳治理主內容。

### 頁面區塊
1. **總覽列**
   - 總資金
   - 已分配資金
   - 未分配資金
   - 運行中 bot 數
   - 今日總 PnL
   - 累積總 PnL

2. **建立 bot 區**
   - 策略名稱下拉選單（來源：已儲存策略 / leaderboard 選中策略）
   - mode：paper / live_canary / live
   - venue：binance / okx
   - symbol 或 market scope
   - 投入金額（例如 100 USD）
   - 可選：每 bot 最大層數 / 啟用與否
   - 按鈕：建立草稿、立即開始

3. **Bot 卡片區**
   每張卡顯示：
   - bot 名稱
   - 策略名稱
   - 策略版本快照
   - venue / mode
   - 分配資金
   - 現值 / 可用 / 已用
   - 未實現 PnL
   - 已實現 PnL
   - 累積 ROI
   - 狀態 badge
   - 最後動作時間
   - 開始 / 暫停 / 停止 / 查看詳情

4. **詳情抽屜 / Modal**
   - 最近 orders / fills
   - 最近 reject / failure
   - 持倉
   - 掛單
   - 停止原因
   - guardrail 命中紀錄
   - 跳轉 Dashboard 診斷

---

# 後端需求定義

## 新資料模型
### 1. Execution Profile
用來保存使用者配置的 bot 範本。
- id
- profile_name
- strategy_name
- strategy_source (`leaderboard` / `workspace` / `manual`)
- strategy_snapshot_json
- strategy_hash
- venue
- mode
- quote_budget
- enabled
- created_at / updated_at

### 2. Execution Run
用來保存每次啟動後的營運實例。
- id
- profile_id
- run_status (`draft` / `running` / `paused` / `stopped` / `halted` / `error`)
- allocated_capital
- capital_currency
- start_time
- stop_time
- stop_reason
- realized_pnl
- unrealized_pnl
- total_pnl
- total_roi
- last_heartbeat_at

### 3. Execution Event
保存 bot 生命周期事件。
- id
- run_id
- event_type (`started`, `order_submitted`, `filled`, `rejected`, `halted`, `stopped`...)
- level
- message
- payload_json
- created_at

## 新 API
1. `GET /api/execution/profiles`
2. `POST /api/execution/profiles`
3. `PATCH /api/execution/profiles/{id}`
4. `GET /api/execution/runs`
5. `POST /api/execution/runs/{profile_id}/start`
6. `POST /api/execution/runs/{run_id}/pause`
7. `POST /api/execution/runs/{run_id}/stop`
8. `GET /api/execution/runs/{run_id}`
9. `GET /api/execution/summary`
10. `GET /api/execution/strategies/source`
   - 回傳可選策略清單與必要快照摘要

## 資金治理規則
1. 不得讓 bot 配置總額超過 account free balance。
2. 每個 bot 都要記錄自己的 quote_budget。
3. 啟動前顯示剩餘可分配資金。
4. paper 與 live 資金池要分開看，避免混淆。
5. 不得把「降低入場閾值以增加成交頻率」當成資金利用率優化手段；這屬於策略劣化，不屬於產品化。

---

# 前端需求定義

## 路由與導航
### Task A
- 修改 `web/src/App.tsx`
- 新增 `ExecutionConsole` 頁面 route：`/execution`
- 導航列新增：`⚡ 實戰交易`

## 頁面檔案
### Task B
建立：`web/src/pages/ExecutionConsole.tsx`

## 共用元件
### Task C
建立：
- `web/src/components/execution/BotComposer.tsx`
- `web/src/components/execution/BotRunCard.tsx`
- `web/src/components/execution/BotRunDrawer.tsx`
- `web/src/components/execution/CapitalSummaryBar.tsx`

---

# 產品語義規則
1. **Dashboard** 保留 canonical diagnostics/operator surface。
2. **Execution Console** 是 canonical trading operations surface。
3. 同一份 runtime truth 要分兩種語言：
   - Dashboard：debug / governance / proof chain
   - Execution Console：bot / 資金 / PnL / 可操作狀態
4. 若 live blocker 未解除，Execution Console 仍可顯示 bot，但開始按鈕需明確受限或降級為 paper。

---

# 驗收標準

## MVP 必達
1. 使用者可從獨立頁面 `/execution` 選擇已存在策略名稱。
2. 可設定投入資金，例如 100 USD。
3. 可建立 2 組以上 bot 並同時顯示在同頁。
4. 每組 bot 可看到：
   - 當前狀態
   - 分配資金
   - realized / unrealized / total PnL
   - 開始 / 停止
5. 可以即時或準即時刷新 bot 狀態。
6. Execution Console 與 Dashboard 不再混為同一主頁。

## 明確不算完成
1. 只有單筆 `/api/trade` 按鈕，不算 bot 營運頁完成。
2. 只有 account-level PnL，沒有 per-bot PnL，不算完成。
3. 只有策略名稱顯示，沒有策略快照/version，不算完成。
4. 只有前端假資料，不算完成。

---

# 實作順序

### Phase 1：資料模型與 API 骨架
1. 新增 execution profile / run / event model
2. 寫 migration
3. 新增 profiles / runs / summary API
4. 測試 API CRUD 與 start/stop state transition

### Phase 2：前端獨立頁 MVP
1. 新增 `/execution` route
2. 做資金總覽與 bot composer
3. 做 bot 卡片列表
4. 串接 start / stop / refresh
5. 顯示 per-bot PnL 與狀態

### Phase 3：runtime 整合
1. 將 run 綁到 ExecutionService
2. 產生 event log
3. 接 account snapshot / orders / positions
4. 補詳情抽屜

### Phase 4：風控與產品 polish
1. 資金超配防呆
2. live blocker gating
3. mode/venue 標示一致化
4. 文案全繁中、降低工程味

---

# 驗證命令
```bash
source venv/bin/activate
python -m pytest tests/test_execution_service.py tests/test_server_startup.py -q
cd web && npm run build
```

後續新增測試建議：
```bash
source venv/bin/activate
python -m pytest tests/test_execution_console_api.py -q
python -m pytest tests/test_frontend_execution_console_contract.py -q
```

---

# 本計畫對應的當前產品決策
- 先把 Execution 從 Dashboard 分離，避免研究/診斷/營運三種心智混在一起。
- 先做多 bot 資金與 PnL 營運面板，再回頭加進階自動化。
- 先用策略名稱 + 策略快照驅動 execution profile，不直接讓使用者從零亂填所有參數。
- 以產品化為主，不再把 Dashboard 上的 operator 面板誤當成實戰交易頁。
- 維持低頻高信念原則；不採用透過降低 gate/threshold 製造短期高頻交易的方向。