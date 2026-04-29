# ARCHITECTURE.md — Poly-Trader 系統架構

> 本文件只保留「目前有效」的架構與操作契約；歷史 heartbeat 更新流水帳不放在架構文檔內。當前問題追蹤見 [ISSUES.md](ISSUES.md)，近期計畫見 [ROADMAP.md](ROADMAP.md)，心跳流程見 [HEARTBEAT.md](HEARTBEAT.md)。

---

## 1. 系統定位

Poly-Trader 是 BTC/USDT 多特徵量化研究與策略實驗平台，核心目標是：

1. 以 **4H 結構背景 + 短線特徵** 建立可解釋 decision contract。
2. 在 **Strategy Lab** 中用回測、leaderboard、模型與參數比較驗證策略。
3. 以 **decision quality**（勝率、pnl quality、drawdown penalty、time underwater、allowed layers）取代只看 accuracy。
4. 在 execution surface 中維持 fail-closed：未 live-ready 時不能暗示可真實買入或加倉。

---

## 2. 技術棧

| 層 | 技術 |
|---|---|
| Frontend | React + TypeScript + Tailwind + Recharts + lightweight-charts |
| Backend | FastAPI + WebSocket |
| Storage | SQLite + SQLAlchemy |
| Modeling | XGBoost / LightGBM / CatBoost / sklearn baselines |
| Backtesting | Python strategy engine + async jobs |
| Governance | heartbeat runner + machine-readable artifacts + pytest contract tests |

---

## 3. Repo 結構

```text
Poly-Trader/
├── backtesting/           # Strategy Lab 回測、strategy runner、model leaderboard
├── data_ingestion/        # 市場資料與 sparse-source 收集
├── database/              # ORM schema、DB init、SQLite pragma/index 管理
├── execution/             # order manager、risk control、execution primitives
├── feature_engine/        # feature generation、coverage/maturity policy、4H projection
├── model/                 # predictor、train、runtime closure、calibration artifacts
├── server/                # FastAPI app、routes、API payload contracts
├── web/                   # React UI: Dashboard / Strategy Lab / Execution Console
├── scripts/               # heartbeat、probe、analysis、maintenance CLIs
│   └── legacy_checks/     # 舊一次性診斷腳本；不得作為正式 workflow 入口
├── tests/                 # pytest contract/regression tests
├── docs/
│   ├── analysis/          # 可重跑分析 artifact 的人類可讀摘要
│   └── plans/             # 實作計畫與設計藍圖
├── README.md              # 專案入口與使用說明
├── HEARTBEAT.md           # 心跳流程規範，不是每輪更新 log
├── ISSUES.md              # current-state issue view（由 runner overwrite）
├── ROADMAP.md             # current-state plan view（由 runner overwrite）
└── ORID_DECISIONS.md      # current ORID view（由 runner overwrite）
```

### Source vs generated

- **Source / contract**：Python/TypeScript 程式、pytest、README/ARCHITECTURE/HEARTBEAT、current-state docs。
- **Generated runtime artifacts**：`data/*.json`、`model/*.json`、`model/*.pkl`、`docs/analysis/*_audit.md` 類檔案由 heartbeat/probe 重建；若已被追蹤，只能在有驗證價值時提交。
- **Heartbeat run logs**：`data/heartbeat_*`、`HEARTBEAT_*_SUMMARY.md` 不再追蹤；需要追溯時看 git history 或本機 ignored artifacts。

---

## 4. 資料與特徵層

### 4.1 Raw data

`data_ingestion/` 負責把市場資料與 sparse-source snapshot 寫入 raw event store。raw 層必須保留來源、時間戳與 fetch 狀態，避免把缺值或 fetch failure 包裝成有效數值。

### 4.2 Feature engineering

`feature_engine/` 將 raw 資料轉為可訓練特徵。核心契約：

- sparse-source 最新 row 缺值時，feature 必須保持 `NULL/None`，不得 forward-carry 舊值或寫入假中性值。
- feature coverage 必須輸出 maturity：`core / research / blocked`，讓 UI 與模型區分正式決策特徵與研究觀察。
- 4H 欄位（`feat_4h_*`、`regime_label`）需與 training / predictor 使用同一套 as-of alignment。
- warning-safe math：指標分母可能為 0 時要使用安全除法，避免 RuntimeWarning 污染 heartbeat stderr。

---

## 5. 標籤、模型與 decision quality

### 5.1 Label semantics

canonical 目標以 spot-long pyramid 的路徑品質為主：

- `simulated_pyramid_win`
- `simulated_pyramid_pnl`
- `simulated_pyramid_quality`
- `simulated_pyramid_drawdown_penalty`
- `simulated_pyramid_time_underwater`

`label_spot_long_*` 與 legacy sell 欄位只作比較或相容，不應再成為主 gate。

### 5.2 Live decision profile

`model/predictor.py::predict()` 與 `/predict/confidence` 至少要能說明：

- `regime_gate`：ALLOW / CAUTION / BLOCK
- `structure_quality` 與 `structure_bucket`
- `entry_quality` / `entry_quality_label`
- `allowed_layers_raw` 與 `allowed_layers`
- `deployment_blocker` / `deployment_blocker_reason`
- expected win / pnl / drawdown / time-underwater
- decision-quality guardrail 是否啟動

### 5.3 Runtime closure

`model/runtime_closure.py` 是 runtime closure 文案與狀態的共同入口。Probe、API 與 UI 不應各自手寫 blocker 文案，避免 Dashboard、Strategy Lab、Execution Status 對同一 live state 顯示不同 truth。

---

## 6. 回測與 Strategy Lab

正式互動工作區是 `/lab`；舊 `/backtest` 只保留 compatibility/redirect。Strategy Lab 主要透過：

- `/api/strategies/run_async`
- `/api/strategies/jobs/{job_id}`
- `/api/strategies/leaderboard`
- `/api/models/leaderboard`

核心契約：

1. 預設排行榜/候選策略使用最近兩年視窗，UI 需直接揭露基準。
2. strategy detail 必須經過 decoration，保留 decision contract、trade log 與 canonical DQ 摘要。
3. system-generated auto leaderboard rows immutable；人工 rerun 應另存 editable copy。
4. stale leaderboard cache 必須明確顯示 stale 狀態，而不是偽裝成 fresh production truth。

---

## 7. Execution 與真實 API 前置安全

真實交易相關 surface 必須 fail-closed。當 `/api/status` 初次同步中、`deployment_blocker` 存在、`live_ready=false` 或 venue/runtime proof 缺失時：

- **買入 / 加倉 / 啟用自動模式**：暫停，UI disabled，後端直接 API 也要 409。
- **減碼 / 賣出風險降低 / 切手動 / diagnostics / refresh**：保持可用；這些是降風險或觀測路徑，不可被 buy blocker 一起鎖死。
- `/api/trade` blocked response 應提供前端可讀結構：`success=false`、`trade_blocked=true`、`blocked_side`、`reason`、`runtime_blocker`。
- venue readiness 要分清楚 metadata OK 與 live/canary proof；缺 credential、order ack、fill lifecycle 時不可宣稱 live-ready。

---

## 8. API surface

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | current live runtime truth、execution surface contract、metadata smoke |
| `GET /api/predict/confidence` | predictor decision profile |
| `GET /api/features/coverage` | feature coverage、maturity、source blockers |
| `GET /api/chart/klines` | K 線與增量補資料 |
| `POST /api/strategies/run_async` | 建立 Strategy Lab 背景回測 |
| `GET /api/strategies/jobs/{job_id}` | 查詢回測 job |
| `GET /api/strategies/leaderboard` | 策略排行榜 |
| `GET /api/models/leaderboard` | 模型排行榜 |
| `POST /api/trade` | manual trade/derisk entry；buy/add exposure 必須讀 current-live blocker |
| `GET /api/execution/overview` | Execution Console operator summary |
| `GET /api/execution/status` | execution diagnostics / readiness detail |
| `GET /ws/live` | 即時推送 |

---

## 9. Frontend surfaces

| Surface | Primary responsibility |
|---|---|
| Dashboard `/` | current live summary、4H context、advice card、venue summary |
| Strategy Lab `/lab` | 回測、leaderboard、strategy editor、model comparison |
| Execution Console `/execution` | manual buy/reduce shortcuts、automation toggle、operator workspace |
| Execution Status `/execution/status` | blocker-first diagnostics、venue/reconciliation detail |
| FeatureChart | feature coverage、maturity、price/feature overlays |

UI 原則：

- current-live blocker 優先於 venue summary。
- 初次 API sync 不得顯示假 `none/unavailable`；必須顯示同步中。
- operator-facing copy 需中文化，不直接暴露內部 routing token。

---

## 10. Heartbeat 與文件治理

- `scripts/hb_parallel_runner.py` 是 heartbeat runner 主入口。
- `HEARTBEAT.md` 是 evergreen 流程規範，不再承載單輪 summary。
- `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 只保留 current state，由 runner overwrite sync。
- 每輪 heartbeat 可以產出 `data/heartbeat_*`，但這些 run logs 預設 ignored，不應污染 git diff。
- 若 current-state docs 與 machine-readable artifacts 不一致，應修 runner/doc sync，而不是追加新的歷史段落。

---

## 11. 測試與驗證

常用驗證：

```bash
source venv/bin/activate
python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q
python -m pytest tests/test_hb_parallel_runner.py -q
cd web && npm run build
```

清理/重構後至少要跑：

```bash
source venv/bin/activate
python -m pytest tests/test_repo_hygiene.py -q
python -m pytest tests/test_frontend_decision_contract.py -q
cd web && npm run build
```

---

## 12. 維護規則

1. 新的一次性診斷腳本不得放 repo root；放到 `scripts/legacy_checks/` 或升級成正式 CLI。
2. 新 heartbeat run artifact 不得加入 git；若需要長期保留，先轉成穩定 schema 的 current-state artifact。
3. 架構文件不記錄歷史流水帳；只記目前有效契約。
4. 刪除文件或 artifact 前必須跑引用搜尋與 targeted tests。
5. 任何真實 API credential、token、secret 不可提交。