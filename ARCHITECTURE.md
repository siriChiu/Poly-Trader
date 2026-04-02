# ARCHITECTURE.md — Poly-Trader 系統架構

> 完整技術架構文檔。問題追蹤見 [ISSUES.md](ISSUES.md)，產品需求見 [PRD.md](PRD.md)，發展路線見 [ROADMAP.md](ROADMAP.md)。

---

## 技術棧

| 層 | 技術 |
|----|------|
| 前端 | React + TypeScript + Tailwind CSS + Recharts + lightweight-charts |
| 後端 | FastAPI + SQLite + WebSocket |
| 模型 | XGBoost (2-class) + confidence-based filtering |

---

## 目錄結構

```
Poly-Trader/
├── config.py / config.yaml     ← 配置
├── main.py                      ← FastAPI 入口
├── server/                      ← API + WebSocket + 感官引擎
│   ├── main.py                  ← FastAPI app
│   ├── senses.py                ← SensesEngine（8 感官計算）
│   ├── dependencies.py          ← 依賴注入
│   └── routes/
│       ├── api.py               ← REST API
│       └── ws.py                ← WebSocket
├── data_ingestion/              ← 數據收集器
│   ├── collector.py             ← 主收集器（整合所有模組）
│   ├── binance_derivatives.py   ← LSR / GSR / Taker / OI
│   ├── eye_binance.py           ← K 線數據
│   ├── nose_futures.py          ← Funding Rate
│   ├── ear_polymarket.py        ← Polymarket 概率
│   ├── tongue_sentiment.py      ← FNG + 情緒
│   ├── body_liquidation.py      ← OI + 清算
│   ├── pulse.py                 ← 波動率
│   ├── aura.py                  ← Funding×Price
│   └── mind.py                  ← 量比
├── feature_engine/
│   └── preprocessor.py          ← 特徵工程 v3（IC-validated）
├── model/
│   ├── predictor.py             ← 預測器（XGBoost + confidence）
│   ├── train.py                 ← 訓練腳本
│   └── xgb_model.pkl            ← 模型權重
├── backtesting/
│   ├── engine.py                ← 回測引擎 v2（金字塔加碼）
│   ├── metrics.py               ← 績效指標
│   └── optimizer.py             ← 參數優化
├── execution/
│   ├── risk_control.py          ← 風控
│   └── order_manager.py         ← 下單管理
├── database/
│   └── models.py                ← SQLAlchemy ORM 模型
├── web/                         ← React 前端
│   └── src/
│       ├── App.tsx              ← 路由
│       ├── pages/               ← 頁面（Dashboard, Senses, Backtest）
│       ├── components/          ← 元件（RadarChart, ConfidenceIndicator...）
│       └── hooks/               ← useApi, useWebSocket
├── scripts/                     ← 開發腳本
│   ├── dev_heartbeat.py         ← 心跳檢查
│   ├── recompute_features.py    ← 批量重算特徵
│   ├── retrain.py               ← 重訓模型
│   └── init_db.py               ← 初始化 DB
├── tests/                       ← 測試腳本
├── poly_trader.db               ← SQLite 資料庫（唯一）
└── 文檔
    ├── AI_AGENT_ROLE.md         ← AI 角色定義
    ├── HEARTBEAT.md             ← 心跳流程
    ├── ARCHITECTURE.md          ← 本文件
    ├── ISSUES.md                ← 問題追蹤
    ├── PRD.md                   ← 產品需求
    └── ROADMAP.md               ← 發展路線
```

---

## 8 感官架構 v3（IC-validated）

| # | 感官 | 特徵 | IC | 數據源 | 計算方式 |
|---|------|------|----|--------|----------|
| 1 | Eye 👁️ | `feat_eye_dist` | — | Binance Funding | 72h funding rate 均值 |
| 2 | Ear 👂 | `feat_ear_zscore` | — | Binance K線 | 48h 價格動量 |
| 3 | Nose 👃 | `feat_nose_sigmoid` | — | K線衍生 | 48h 收益率自相關 |
| 4 | Tongue 👅 | `feat_tongue_pct` | — | K線衍生 | 24h 波動率 |
| 5 | Body 💪 | `feat_body_roc` | — | K線衍生 | 24h 價格區間位置 |
| 6 | Pulse 💓 | `feat_pulse` | — | Binance Funding | Funding Rate 趨勢 |
| 7 | Aura 🌀 | `feat_aura` | — | 複合 | 波動率×自相關交互 |
| 8 | Mind 🧠 | `feat_mind` | — | Binance Funding | 24h Funding Z-score |

> IC 值每次心跳更新，見 [ISSUES.md](ISSUES.md) 的感官 IC 表。

---

## 數據庫 Schema

### raw_market_data
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| close_price | FLOAT | 收盤價 |
| volume | FLOAT | 成交量 |
| funding_rate | FLOAT | 資金費率 |
| fear_greed_index | FLOAT | FNG |
| polymarket_prob | FLOAT | Polymarket 概率 |
| eye_dist / ear_prob / tongue_sentiment / volatility / oi_roc / body_label | 各 FLOAT/STRING | 原始感官數據 |

### features_normalized
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| feat_eye_dist ~ feat_mind | 8 × FLOAT | IC-validated 特徵 |

### labels
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| horizon_hours | INTEGER | 預測時間窗口 |
| future_return_pct | FLOAT | 未來收益率 |
| label | INTEGER | 0=跌, 1=漲 |

---

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/senses` | GET | 所有感官分數 + 建議 |
| `/api/senses/config` | GET/PUT | 感官配置 |
| `/api/recommendation` | GET | 交易建議 |
| `/api/predict/confidence` | GET | 信心分層預測 |
| `/api/backtest` | GET | 回測結果 |
| `/api/model/stats` | GET | 模型統計 |
| `/api/chart/klines` | GET | K 線數據 |
| `/ws/live` | WS | 即時推送 |

---

## 文檔關聯

| 文檔 | 用途 |
|------|------|
| [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md) | AI 角色、紀律、邊界 |
| [HEARTBEAT.md](HEARTBEAT.md) | 心跳詳細流程 |
| [ISSUES.md](ISSUES.md) | 問題追蹤（含感官 IC 表） |
| [PRD.md](PRD.md) | 產品需求 |
| [ROADMAP.md](ROADMAP.md) | 發展路線 |

---

*架構變更時請更新本文件，並同步更新 [ISSUES.md](ISSUES.md) 和 [ROADMAP.md](ROADMAP.md)。*
