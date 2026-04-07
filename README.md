# Poly-Trader 🐰

> **多特徵量化交易系統** — 模擬人類特徵，用 AI 解讀加密貨幣市場

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 這是什麼？

Poly-Trader 是一套以**多特徵**為核心的加密貨幣量化交易系統。

傳統的交易機器人只看一個指標（例如 RSI 或 MACD），就像一個人只用眼睛看世界——能看到東西，但看不全。人類做交易決策時，會同時運用視覺（看 K 線）、聽覺（聽市場消息）、嗅覺（聞到不對勁）、味覺（感受情緒）、觸覺（感受壓力）等多種特徵，綜合判斷後才下決定。

**Poly-Trader 的核心理念：模擬人類多特徵，把加密貨幣市場行為映射到 8 個特徵維度，每個特徵獨立運作、獨立驗證，再由 AI 綜合判斷。**

### 為什麼是「多特徵」？

| 問題 | 單一指標的困境 | 多特徵的解法 |
|------|---------------|-------------|
| 指標失靈 | RSI 在趨勢市中一直超買，錯過大行情 | 8 個特徵同時運作，不會全部同時失靈 |
| 過擬合 | 單一模型容易記住歷史雜訊 | 多個獨立數據源降低過擬合風險 |
| 黑箱決策 | 不知道模型為什麼下單 | 每個特徵的貢獻可視化、可解釋 |
| 無法改進 | 不知道哪個環節有問題 | IC 驗證每個特徵，無效的直接汰換 |

---

## 🧠 8 特徵系統

每個特徵代表一種解讀市場的方式，經過 **IC（Information Coefficient）實證**，只有預測力達標的才會被採用。

| 特徵 | 圖示 | 解讀什麼 | 數據來源 | 特徵計算 |
|------|------|----------|----------|----------|
| **Eye（視覺）** | 👁️ | 資金費率的長期趨勢 | Binance Futures | 72 小時 funding rate 均值 |
| **Ear（聽覺）** | 👂 | 價格的動量方向 | Binance K 線 | 48 小時價格變化率 |
| **Nose（嗅覺）** | 👃 | 市場是否處於「反轉」狀態 | K 線衍生 | 48 小時收益率自相關 |
| **Tongue（味覺）** | 👅 | 市場波動的強度 | K 線衍生 | 24 小時收益率標準差 |
| **Body（觸覺）** | 💪 | 當前價格在近期區間中的位置 | K 線衍生 | 24 小時高低點之間的比例 |
| **Pulse（脈動）** | 💓 | 資金費率的變化方向 | Binance Futures | 24h MA − 72h MA |
| **Aura（磁場）** | 🌀 | 波動率和趨勢的交互關係 | 複合特徵 | 波動率 × 自相關 |
| **Mind（認知）** | 🧠 | 資金費率的標準化程度 | Binance Futures | 24h funding rate Z-score |

### 額外數據源（衍生品即時數據）

除了 8 個特徵之外，系統還收集 Binance 衍生品數據：

- **大戶持倉比（LSR）**：大戶的多空比例，反映聰明錢方向
- **多空人數比（GSR）**：散戶的多空比例，反向指標
- **主動買賣比（Taker）**：即時訂單流方向
- **持倉量（OI）**：市場槓桿程度

---

## 🎯 信心分層交易

系統不只是「買或賣」，而是會告訴你「我有多確定」。

```
信心等級        精確率          交易頻率
─────────────────────────────────────────
>0.75          ~92%            ~7% 的時間
>0.70          ~86%            ~14% 的時間
>0.65          ~81%            ~21% 的時間
全部            ~52%            100% 的時間
```

**核心策略：不是每次都交易，而是只在高信心時才出手。**

### 金字塔加碼

當信心持續上升時，系統會分批加碼：

| 層級 | 信心閾值 | 資金比例 | 累計 |
|------|----------|----------|------|
| Tier 1 | >0.65 | 5% | 5% |
| Tier 2 | >0.70 | 4% | 9% |
| Tier 3 | >0.75 | 3% | 12% |
| Tier 4 | >0.80 | 3% | 15% |

總暴露度上限 20%，確保風險可控。

---

## 🖥️ 前端操作指南

### 啟動

```bash
# 後端
uvicorn server.main:app --reload --port 8000

# 前端（新終端）
cd web
npm install
npm run dev
```

瀏覽器前往：**http://localhost:5173**

### 首頁儀表板（Dashboard）

打開首頁，你會看到：

```
┌────────────────────────────────────────────────────────────┐
│ 🔮 Poly-Trader v3.0           🟢 即時連線    更新: 14:30  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────┐    ┌─────────────────────────────┐  │
│  │                  │    │  🎯 信心分層                 │  │
│  │    多邊形雷達圖    │    │                             │  │
│  │                  │    │     87%         買入         │  │
│  │  👁️──────👂     │    │                             │  │
│  │  │╲      ╱│     │    │  高信心 | >0.65 或 <0.35     │  │
│  │  │  ╲  ╱  │     │    │  ████████████████░░░░░░     │  │
│  │  💪──────👅     │    │                             │  │
│  │                  │    │  💡 建議買入（信心 87%）     │  │
│  └──────────────────┘    └─────────────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  特徵走勢圖（點擊雷達圖上的特徵查看歷史）              │ │
│  │  ╱╲    ╱╲                                           │ │
│  │ ╱  ╲╱╲╱  ╲____╱╲                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  K 線圖 + 技術指標        [1H] [4H] [1D]             │ │
│  │  ┌────────────────────────────────────────────┐     │ │
│  │  │    ╱╲      ┌─┐                             │     │ │
│  │  │   ╱  ╲   ┌─┘ └─┐  ── MA20                 │     │ │
│  │  │  ╱    ╲─╱       └─ ── MA60                │     │ │
│  │  │ ╱                                       │     │ │
│  │  └────────────────────────────────────────────┘     │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

#### 操作說明

**雷達圖**：
- 8 個頂點代表 8 個特徵
- 中間區域越大 = 多數特徵偏多（看漲）
- 點擊任何一個特徵 → 下方顯示該特徵的歷史走勢
- Hover 可看到特徵的 IC 值和數據來源

**信心指示器**：
- 大字顯示模型的信心百分比
- 顏色：綠色 = 高信心（建議交易）、黃色 = 中信心、紅色 = 低信心（觀望）
- 只有顯示「建議交易」時才考慮下單

**K 線圖**：
- 支援 1H / 4H / 1D 時間框架切換
- 疊加 MA20（黃線）、MA60（粉線）
- RSI、MACD 技術指標

### 特徵管理頁（/senses）

在導航列點擊「🎛️ 特徵管理」進入。

此頁面可以：
- 查看每個特徵的即時分數和 IC 值
- 啟用 / 停用個別特徵
- 調整每個特徵的權重
- 即時預覽權重調整對綜合分數的影響

### 回測頁（/backtest）

在導航列點擊「🔬 回測」進入。

此頁面可以：
- 選擇回測時間範圍
- 設定初始資金、信心閾值、止損止盈
- 選擇金字塔模式（特徵信心 / 斐波那契支撐）
- 查看資金曲線圖和每筆交易明細

---

## 🚀 安裝與啟動

### 環境需求

- Python 3.10+
- Node.js 18+
- Git

### 步驟

```bash
# 1. 克隆專案
git clone <repo-url>
cd Poly-Trader

# 2. 安裝 Python 依賴
pip install -r requirements.txt

# 3. 初始化資料庫
python scripts/init_db.py

# 4. 啟動後端 API
uvicorn server.main:app --reload --port 8000

# 5. 啟動前端（新終端）
cd web
npm install
npm run dev
```

### 配置

編輯 `config.yaml`：

```yaml
database:
  url: sqlite:///poly_trader.db

trading:
  symbol: "BTCUSDT"
  confidence_threshold: 0.7    # 信心閾值
  max_position_ratio: 0.05     # 最大單筆倉位 5%
  dry_run: true                # true=模擬交易, false=實盤
```

---

## 📁 專案結構

詳細架構見 [ARCHITECTURE.md](ARCHITECTURE.md)。

```
Poly-Trader/
├── server/                    ← FastAPI 後端 + WebSocket
├── data_ingestion/            ← 數據收集器（8 特徵 + 衍生品）
├── feature_engine/            ← 特徵工程 v3
├── model/                     ← XGBoost 預測器
├── backtesting/               ← 回測引擎 v2（金字塔加碼）
├── execution/                 ← 風控 + 下單
├── database/                  ← SQLAlchemy ORM
├── web/                       ← React 前端
├── scripts/                   ← 開發腳本
├── tests/                     ← 測試
├── poly_trader.db             ← SQLite 資料庫
│
├── AI_AGENT_ROLE.md           ← AI 角色定義
├── HEARTBEAT.md               ← 心跳流程
├── ARCHITECTURE.md            ← 系統架構
├── ISSUES.md                  ← 問題追蹤
├── PRD.md                     ← 產品需求
└── ROADMAP.md                 ← 發展路線
```

---

## 🔧 開發指令

```bash
# 結構檢查
python scripts/dev_heartbeat.py

# 全面測試
python tests/comprehensive_test.py

# 批量重算特徵（特徵升級後）
python scripts/recompute_features.py

# 重訓模型
python scripts/retrain.py

# 手動收集一次數據
python -c "from data_ingestion.collector import run_collection_and_save; from database.models import init_db; from config import load_config; s=init_db(load_config()['database']['url']); run_collection_and_save(s)"
```

---

## 📊 API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/senses` | GET | 8 特徵分數 + 綜合建議 |
| `/api/predict/confidence` | GET | 信心分層預測（信號、信心值） |
| `/api/recommendation` | GET | 交易建議（自然語言） |
| `/api/senses/config` | GET/PUT | 查看 / 修改特徵配置 |
| `/api/backtest` | GET | 回測結果 |
| `/api/model/stats` | GET | 模型統計（IC、特徵重要性） |
| `/api/chart/klines` | GET | K 線數據 |
| `/ws/live` | WebSocket | 即時推送特徵更新 |

---

## 📄 相關文檔

| 文檔 | 說明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 完整系統架構（目錄、DB schema、API） |
| [PRD.md](PRD.md) | 產品需求規格 |
| [ROADMAP.md](ROADMAP.md) | 發展路線與進度 |
| [ISSUES.md](ISSUES.md) | 問題追蹤（含特徵 IC 表） |
| [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md) | AI 自主代理角色定義 |
| [HEARTBEAT.md](HEARTBEAT.md) | 自動化心跳流程 |

---

## License

MIT
