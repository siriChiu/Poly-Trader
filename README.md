# Poly-Trader 🐰

> **多感官量化交易系統** — 用免費 API 打造的 AI 自動化交易引擎

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 多感官系統

| 感官 | 數據源 | 特徵 | 狀態 |
|------|--------|------|------|
| 👁️ **Eye**（眼） | Binance Order Book | 阻力/支撐距離比例 | ✅ |
| 👂 **Ear**（耳） | Polymarket + 價格動量 | 市場共識 Z-score | ✅ |
| 👃 **Nose**（鼻） | Binance Futures | 資金費率 Sigmoid + OI ROC | ✅ |
| 👅 **Tongue**（舌） | Alternative.me | 恐懼貪婪指數 0~1 | ✅ |
| 💪 **Body**（身） | Binance Futures OI/LS | **清算壓力綜合指標**（v3） | ✅ 🆕 |

**🧠 決策引擎**：XGBoost 分類器 → 信心分數 0~1 → BUY/HOLD 信號

**特徵重要性排名**（667 筆訓練樣本）：
```
🥇 Nose (資金費率)    ████████████████  33.7%
🥈 Tongue (情緒)     ███████████████   32.5%
🥉 Eye (技術面)      █████████         18.5%
4️⃣  Ear (市場共識)   ████████          15.3%
5️⃣  Body (清算壓力)   待重新訓練驗證     🔄
```

---

## 🚀 快速開始

### 環境需求

- Python 3.10+
- Node.js 18+（前端）
- Git

### 安裝

```bash
# 1. 克隆
git clone https://github.com/siriChiu/Poly-Trader.git
cd poly-trader

# 2. Python 後端
pip install -r requirements.txt
pip install fastapi uvicorn websockets

# 3. 初始化資料庫
python init_db.py

# 4. 回填歷史數據（一次性，約 30 秒）
python data_ingestion/backfill_historical.py

# 5. 啟動後端 API
uvicorn server.main:app --reload --port 8000

# 6. 啟動前端（新終端）
cd web
npm install
npm run dev
```

### 🌐 打開儀表板

瀏覽器前往：**http://localhost:5173**

---

## 📊 Dashboard 功能

### TradingView 風格 K 線圖
- 即時 BTC/USDT K 線（來自 Binance）
- 成交量柱狀圖
- 時間框架切換：1H / 4H / 1D / 1W
- 暗色主題，專業級圖表

### 多感官即時狀態
- 5 個感官卡片，即時顯示數值與狀態
- WebSocket 推送，無需手動刷新

### 手動交易
- 🟢 **買進按鈕** — 點擊 → 確認 → 下單
- 🔴 **賣出按鈕** — 同上
- 🤖 **自動模式開關** — 一鍵切換自動/手動

### 回測 & 參數優化
- 選擇時間範圍、初始資金
- 一鍵執行回測，查看 Sharpe / Max DD / 勝率
- 網格搜索最佳參數組合

### 感官有效性分析
- IC（Information Coefficient）條形圖
- 分位數勝率熱圖
- 自動標記無效感官

---

## 📁 專案結構

```
poly-trader/
├── data_ingestion/           # 多感官數據採集
│   ├── eye_binance.py        # Eye: 訂單簿流動性
│   ├── ear_polymarket.py     # Ear: 預測市場概率
│   ├── nose_futures.py       # Nose: 資金費率 + OI
│   ├── tongue_sentiment.py   # Tongue: 恐懼貪婪指數
│   ├── body_liquidation.py   # Body: 清算壓力（v3）🆕
│   ├── collector.py          # 整合多感官 → DB
│   ├── labeling.py           # 生成訓練標籤
│   └── backfill_historical.py # 歷史數據回填 🆕
├── feature_engine/
│   └── preprocessor.py       # 特徵標準化
├── model/
│   ├── predictor.py          # 模型預測
│   └── train.py              # XGBoost 訓練
├── execution/
│   ├── order_manager.py      # 下單管理（CCXT）
│   └── risk_control.py       # 風控 & 止損
├── backtesting/
│   ├── engine.py             # 回測引擎
│   ├── metrics.py            # 績效指標
│   └── optimizer.py          # 參數優化
├── analysis/
│   ├── sense_effectiveness.py # 多感官有效性分析
│   └── sense_validator.py    # 感官驗證 + 六帽觸發
├── server/                   # FastAPI 後端 🆕
│   ├── main.py               # API + WebSocket
│   ├── routes/api.py         # 9 個 REST 端點
│   └── routes/ws.py          # WebSocket 即時推送
├── web/                      # React 前端 🆕
│   └── src/
│       ├── components/       # K線圖、感官卡片、信號面板
│       └── pages/            # 首頁、交易歷史、回測、驗證
├── dashboard/                # 舊版 Streamlit（備用）
├── database/
│   └── models.py             # SQLAlchemy ORM
├── config.yaml               # 設定檔
├── main.py                   # 主程式排程器
├── comprehensive_test.py     # 全面規格驗證
├── dev_heartbeat.py          # 開發心跳
├── ISSUES.md                 # 問題追蹤
├── ROADMAP.md                # 發展路線圖
└── ai_dev_role.md            # 閉迴路開發角色
```

---

## ⚙️ 配置

`config.yaml`：

```yaml
database:
  url: sqlite:///poly_trader.db

binance:
  api_key: ""         # 填入 Binance API Key（選填，Dry Run 不需要）
  api_secret: ""

trading:
  symbol: "BTCUSDT"
  confidence_threshold: 0.7   # 預測信心閾值
  max_position_ratio: 0.05    # 最大倉位比例 5%
  dry_run: true              # true=模擬, false=實盤
```

---

## 🔄 自動化

### Heartbeat（每 5 分鐘）
自動執行：
1. 多感官數據收集
2. 特徵計算
3. 感官有效性驗證（IC）
4. 結構健康檢查
5. 六帽會議（感官有問題時自動觸發）

### 歷史回填
```bash
python data_ingestion/backfill_historical.py
```
一次拉取 30 天歷史數據（720 筆），立即可用於訓練。

### 模型訓練
```bash
python -c "from model.train import run_training; from database.models import init_db; from config import load_config; cfg=load_config(); s=init_db(cfg['database']['url']); run_training(s)"
```

---

## 📈 API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/status` | GET | 系統狀態 |
| `/api/senses/latest` | GET | 最新多感官數據 |
| `/api/features` | GET | 特徵歷史 |
| `/api/trades` | GET | 交易歷史 |
| `/api/predict` | POST | 觸發預測 |
| `/api/trade` | POST | 手動下單 |
| `/api/automation/toggle` | POST | 切換自動/手動 |
| `/api/backtest` | GET | 觸發回測 |
| `/api/validation` | GET | 感官有效性 |
| `/ws/live` | WebSocket | 即時推送 |

---

## 🛠️ 開發

### 閉迴路開發流程
每個任務經過三個角色：
1. **架構師** — 設計符合 PRD 的架構
2. **工程師** — 撰寫完整程式碼
3. **QA** — 實際測試驗證

### 六帽會議
當感官驗證發現 Critical 問題時自動觸發，六個角度分析後產出決議。

### 驗證
```bash
python comprehensive_test.py   # 7 項全面測試
python dev_heartbeat.py        # 快速心跳
```

---

## 📄 License

MIT
