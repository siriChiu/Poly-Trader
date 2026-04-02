# Poly-Trader 🐰

> **多感官量化交易系統** — 8 個 IC-validated 感官 + 信心分層交易 + 金字塔加碼

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 核心特色

**8 感官架構**（每個經過 IC 實證）：

| 感官 | 特徵 | 數據源 |
|------|------|--------|
| 👁️ Eye | 72h Funding 均值 | Binance Futures |
| 👂 Ear | 48h 價格動量 | Binance K線 |
| 👃 Nose | 48h 收益率自相關 | K線衍生 |
| 👅 Tongue | 24h 波動率 | K線衍生 |
| 💪 Body | 24h 區間位置 | K線衍生 |
| 💓 Pulse | Funding 趨勢 | Binance Futures |
| 🌀 Aura | 波動率×自相關 | 複合特徵 |
| 🧠 Mind | 24h Funding Z-score | Binance Futures |

**衍生品即時數據**：大戶持倉比 (LSR)、多空人數比 (GSR)、主動買賣比、OI

**信心分層交易**：只在高信心時交易（>0.7 → 80%+ 準確率）

**金字塔加碼**：感官信心模式 + 斐波那契支撐位模式

---

## 🚀 快速開始

```bash
# 安裝
pip install -r requirements.txt

# 初始化資料庫
python scripts/init_db.py

# 啟動 API
uvicorn server.main:app --reload --port 8000

# 啟動前端（新終端）
cd web && npm install && npm run dev
```

瀏覽器前往：**http://localhost:5173**

---

## 📁 專案結構

```
Poly-Trader/
├── server/                    ← FastAPI 後端 + WebSocket
├── data_ingestion/            ← 數據收集器（含衍生品）
├── feature_engine/            ← 特徵工程 v3（IC-validated）
├── model/                     ← XGBoost 預測器
├── backtesting/               ← 回測引擎 v2（金字塔加碼）
├── execution/                 ← 風控 + 下單
├── database/                  ← SQLAlchemy ORM
├── web/                       ← React 前端
├── scripts/                   ← 開發腳本
├── tests/                     ← 測試
├── poly_trader.db             ← SQLite 資料庫
│
├── 文檔
│   ├── AI_AGENT_ROLE.md       ← AI 角色定義
│   ├── HEARTBEAT.md           ← 心跳流程
│   ├── ARCHITECTURE.md        ← 系統架構
│   ├── ISSUES.md              ← 問題追蹤
│   ├── PRD.md                 ← 產品需求
│   └── ROADMAP.md             ← 發展路線
```

---

## 📊 API 端點

| 端點 | 說明 |
|------|------|
| `/api/senses` | 8 感官分數 + 建議 |
| `/api/predict/confidence` | 信心分層預測 |
| `/api/backtest` | 回測結果 |
| `/api/chart/klines` | K 線數據 |
| `/ws/live` | WebSocket 即時推送 |

---

## 🔧 開發

```bash
python scripts/dev_heartbeat.py      # 結構檢查
python tests/comprehensive_test.py   # 全面測試
python scripts/recompute_features.py # 批量重算特徵
python scripts/retrain.py            # 重訓模型
```

---

## 📄 License

MIT
