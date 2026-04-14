# Poly-Trader 🐰

> **多特徵量化交易研究與策略實驗平台**
>
> 以多來源特徵、4H 結構背景、互動式回測與決策品質評估為核心，而不是用單一指標或黑箱模型直接下結論。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 這是什麼？

Poly-Trader 是一套面向 **BTC/USDT 多特徵研究、策略驗證、即時判讀** 的平台。

它目前的定位不是「神祕 AI 自動幫你交易」，而是：

- 把市場資料整理成可追蹤的 **多特徵框架**
- 用 **4H 結構 + 短線特徵** 建立可解釋的 decision contract
- 提供 **Strategy Lab** 讓你自己選模型、調參、回測、比較 leaderboard
- 用 **decision quality** 而不是只看 accuracy / 勝率 來評估策略

換句話說，這個專案現在的主軸是：

> **多特徵（multi-feature）描述市場 → 策略實驗 → 回測驗證 → 決策品質治理**

而不是早期那種偏人格化命名的產品敘事。

---

## Highlights

- **Strategy Lab**：互動式回測工作區，支援參數調整、leaderboard、策略回填
- **模型清單治理**：目前最適合主線的核心模型建議已整理於 `docs/analysis/model-shortlist-current.md`
- **Decision Quality**：不只看勝率，還看 drawdown penalty、time underwater、allowed layers
- **Feature-family shrinkage**：訓練流程會根據 `feature_group_ablation` 報告自動挑選目前最穩的特徵組合，不靠再加一堆使用者參數
- **Bull 4H pocket ablation**：可針對 bull live blocker 的 q35 collapse pocket 單獨分析 4H 結構特徵，而不是只做整體平均
- **Support-aware runtime blocker**：predictor 現在會把 `exact live structure bucket support=0` 視為顯式阻擋條件，neighbor buckets 只作保守參考，不再拿 broader same-bucket scope 直接放行；live probe 已驗證會實際輸出 `unsupported_exact_live_structure_bucket_blocks_trade`
- **4H 結構治理**：用高時間框架 regime gate 避免在錯的背景做低品質 spot-long
- **多特徵成熟度分級**：區分 `core / research / blocked`，避免稀疏來源污染主決策
- **快取與增量刷新**：圖表優先從本地還原，再只補缺的 K 線尾段
- **Heartbeat 閉環**：用固定治理流程推進 patch、驗證、文件同步與下一輪 gate

---

## 核心理念

### 1. 不迷信單一指標

RSI、MACD、布林帶、單一 funding 指標都可能在某些市場狀態下失效。

Poly-Trader 改用多特徵方式描述市場，包括：

- 價格 / 波動 / 動能 / 均值回歸
- 4H 結構位置與 regime
- microstructure / 衍生品 / macro 類特徵
- sparse-source 研究特徵與成熟度治理

### 2. 不把模型 accuracy 當成唯一目標

這個專案目前更重視：

- ROI
- 最大回撤
- Profit Factor
- time underwater
- drawdown penalty
- decision quality score

也就是說，**模型分類準確率只是中間訊號，不是最終目標**。

### 3. 不做黑箱

使用者可以：

- 看 leaderboard
- 選模型
- 調整 entry / stop loss / take profit / top-k / regime gate
- 點擊策略回填參數
- 直接檢視價格圖、權益圖、倉位水位、markers、decision fields

---

## 目前系統怎麼描述市場？

目前系統以 **多特徵（multi-feature）** 來描述市場，主要可分成幾類：

### A. 短線特徵

用來捕捉短時間框架中的節奏、強弱、過熱、回調與交易品質：

- RSI / MACD / ATR / VWAP deviation
- NW Envelope 位置與寬度
- ADX / Choppiness / Donchian position
- 量價與短期 momentum 類特徵

### B. 4H 結構特徵

用來判斷高時間框架的背景與 regime：

- `feat_4h_bias50`
- `feat_4h_bias200`
- `feat_4h_dist_swing_low`
- `feat_4h_dist_bb_lower`
- `feat_4h_bb_pct_b`
- `feat_4h_vol_ratio`
- `regime_label`

這些欄位主要負責：

- 判斷當前是 `ALLOW / CAUTION / BLOCK`
- 過濾不應該開倉的背景
- 避免在過度延伸或結構不支撐時硬做 spot-long pyramid

### C. 研究型 / sparse-source 特徵

部分資料源歷史較稀疏，或受授權 / 抓取狀態影響，因此系統會明確標示成熟度：

- `core`
- `research`
- `blocked`

這些研究型特徵可以作為 overlay / bonus / veto 參考，但不應和核心特徵同權看待。

---

## 核心工作區：Strategy Lab

目前正式回測與策略實驗工作區是：

- **`/lab`**

舊的 `/backtest` 已退役，會導向 `/lab`。

### Strategy Lab 目前支援

- 規則式 / Hybrid 模式切換
- 模型排行榜 + 策略排行榜
- leaderboard 會保留 deployment profile，讓評估更接近真實 OOS 高信念部署情境
- leaderboard 會把模型分成：**核心模型 / 對照模型 / 研究模型** 三層顯示
- 點擊 leaderboard row 回填策略設定
- 非同步回測背景任務
- 頁面上方統一 top progress 顯示真實進度
- 價格圖 / 權益圖上下同步顯示
- buy / sell markers、倉位水位、entry quality、model confidence
- 本地 K 線快取 + incremental append refresh
- 切頁後優先從 cache 還原，不必每次重抓完整資料

### 回測時會看到什麼

目前回測流程大致是：

1. 建立背景 job
2. 後端執行回測
3. 平行計算 benchmark / decision profile / quality summary
4. 前端輪詢 job 狀態
5. 工作區同步更新圖表、排行榜與策略詳情

這讓 Strategy Lab 不再只是「按下 Run 然後整頁卡住」。

---

## Dashboard 與 FeatureChart

### Dashboard

Dashboard 主要提供：

- 即時市場摘要
- predictor decision contract
- 4H 結構背景
- 多特徵視覺化
- 策略與風險相關提示

### FeatureChart

FeatureChart 現在聚焦在多特徵歷史結構，而不是舊命名包裝：

- 用多特徵歷史序列對照價格
- 顯示 feature coverage / maturity / usability
- 區分哪些特徵可進入主分數、哪些只是研究觀察
- 對 K 線使用本地 cache + incremental refresh，減少切頁等待

---

## 目前建議的模型清單

目前最適合 Poly-Trader 當前環境與概念的模型清單，已整理在：

- `docs/analysis/model-shortlist-current.md`

### 核心模型
- `rule_baseline`
- `random_forest`
- `xgboost`
- `logistic_regression`

### 對照模型
- `lightgbm`
- `catboost`
- `ensemble`

### 研究模型
- `mlp`
- `svm`

這個分層的目的不是裝飾排行榜，而是讓：
- 使用者知道目前哪些模型值得優先相信
- heartbeat / roadmap / issue 討論時不再把主線模型與研究模型混在一起
- leaderboard 更接近實際研發優先序，而不是單純把所有模型排成一條線

---

## 決策語義：不是只有 buy / sell

目前系統的決策語義重點包含：

- `regime_gate`
- `entry_quality`
- `entry_quality_label`
- `allowed_layers`
- `decision_quality_score`
- `expected_win_rate`
- `expected_pyramid_quality`
- `expected_drawdown_penalty`
- `expected_time_underwater`

也就是說，系統不只想回答：

> 這筆會不會贏？

而是更想回答：

> 這筆 setup 值不值得做？如果做，應該開幾層？它歷史上通常會賺得乾淨還是很容易深套？

---

## 快速開始

### 環境需求

- Python 3.10+
- Node.js 18+
- Git

### 啟動方式

```bash
# 1. clone
git clone <repo-url>
cd Poly-Trader

# 2. 安裝 Python 依賴
pip install -r requirements.txt

# 3. 初始化資料庫
python scripts/init_db.py

# 4. 啟動後端
uvicorn server.main:app --reload --port 8000

# 5. 啟動前端（新終端）
cd web
npm install
npm run dev
```

開啟：

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

---

## 常用開發指令

```bash
# Strategy Lab / leaderboard 核心測試
python -m pytest tests/test_strategy_lab.py -q
python -m pytest tests/test_model_leaderboard.py -q

# heartbeat / drift / live predictor probe
python scripts/hb_parallel_runner.py --fast
python scripts/hb_predict_probe.py

# 前端 build
cd web && npm run build

# 結構檢查 / heartbeat 類工作流
python scripts/dev_heartbeat.py
```

---

## 常用 API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/predict/confidence` | GET | 取得當前 predictor decision contract |
| `/api/features` | GET | 取得特徵歷史資料 |
| `/api/features/coverage` | GET | 取得特徵 coverage / maturity / blocker 資訊 |
| `/api/chart/klines` | GET | 取得 K 線；支援增量補資料 |
| `/api/strategies/run_async` | POST | 建立 Strategy Lab 背景回測任務 |
| `/api/strategies/jobs/{job_id}` | GET | 查詢回測 job 進度與結果 |
| `/api/strategies/leaderboard` | GET | 取得策略排行榜 |
| `/api/models/leaderboard` | GET | 取得模型排行榜 |
| `/ws/live` | WebSocket | 即時資料推送 |

---

## 專案結構

```text
Poly-Trader/
├── server/                    # FastAPI 後端 + API / WebSocket
├── data_ingestion/            # 市場 / sparse-source / heartbeat 收集器
├── feature_engine/            # 特徵工程與 maturity / coverage policy
├── model/                     # predictor / train / calibration artifacts
├── backtesting/               # Strategy Lab 與 leaderboard 核心
├── database/                  # SQLite / ORM schema
├── web/                       # React 前端（Dashboard / Strategy Lab）
├── scripts/                   # heartbeat / probe / analysis / maintenance
├── tests/                     # pytest
├── docs/
│   ├── plans/                 # 實作計畫
│   └── analysis/              # 分析報告與 sweep 結果
├── HEARTBEAT.md
├── ARCHITECTURE.md
├── ISSUES.md
├── PRD.md
└── ROADMAP.md
```

---

## 文件入口

| File | 說明 |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系統架構與核心 contract |
| [ROADMAP.md](ROADMAP.md) | 開發進度與已完成項目 |
| [ISSUES.md](ISSUES.md) | 目前問題與治理狀態 |
| [HEARTBEAT.md](HEARTBEAT.md) | heartbeat 閉環流程 |
| `docs/plans/` | 實作規劃 |
| `docs/analysis/` | 分析報告、sweep 與研究結果 |

---

## 現在這個專案不是什麼

為避免誤解，現在的 Poly-Trader **不是**：

- 單一指標交易機器人
- 只看 accuracy 的分類器 demo
- 只會吐出一個買賣建議的黑箱
- 以人格化命名為主體、卻缺少策略驗證與治理層的系統介紹

它現在更準確的描述是：

> **一個以多特徵、4H 結構、Strategy Lab、decision quality、heartbeat 治理為核心的量化策略研究平台。**

---

## License

MIT
