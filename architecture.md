# 系統架構文件 (Architecture)：Project Five-Senses

## 1. 技術棧 (Tech Stack)
* **核心語言：** Python 3.10+
* **資料處理與機器學習：** Pandas, NumPy, Scikit-Learn, XGBoost
* **交易所互動：** CCXT
* **排程與任務：** APScheduler 或 Celery
* **資料庫：** SQLite (輕量化首選) 或 PostgreSQL
* **部署與環境：** Docker, Docker Compose

## 2. 系統目錄結構
```text
five_senses_bot/
├── data_ingestion/       # 數據採集模組
│   ├── eye_binance.py
│   ├── ear_polymarket.py
│   ├── nose_futures.py
│   ├── tongue_sentiment.py
│   └── body_defillama.py
├── feature_engine/       # 特徵工程與正規化
│   └── preprocessor.py
├── model/                # 機器學習模型
│   ├── train.py
│   └── predictor.py
├── execution/            # 交易執行與風控
│   ├── order_manager.py
│   └── risk_control.py
├── database/             # 資料庫連線與 ORM
│   └── models.py
├── utils/                # 輔助工具 (Logging, 通知)
│   ├── logger.py
│   └── telegram_bot.py
├── main.py               # 主程式與排程器
├── config.yaml           # 系統設定檔 (API Keys, 參數)
└── requirements.txt
```

## 3. 資料庫結構 (Database Schema)
建議使用 SQLAlchemy 進行 ORM 管理。

* Table: raw_market_data (儲存五感原始數據)
    * id (PK), timestamp, symbol, close_price, volume, funding_rate, fear_greed_index, stablecoin_mcap, polymarket_prob
* Table: features_normalized (儲存轉換後的特徵，供模型訓練與預測用)
    * id (PK), timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid, feat_tongue_pct, feat_body_roc
* Table: trade_history (儲存交易紀錄)
    * id (PK), timestamp, action (BUY/SELL), price, amount, model_confidence, pnl (損益)

## 4. 資料流向 (Data Flow)

1. 排程觸發： main.py 透過 APScheduler 每小時觸發一次收集任務。
2. 並行抓取： data_ingestion 內的模組非同步獲取各方 API 數據，存入 raw_market_data。
3. 特徵轉換： feature_engine 讀取最新數據，進行數學轉換，存入 features_normalized。
4. 模型預測： model/predictor.py 載入 XGBoost 權重，讀取最新特徵，產出 0~1 信心分數。
5. 風控與執行： execution 評估分數。若符合設定閾值 (如 >0.7)，檢查風險限制後，透過 CCXT 發送訂單，寫入 trade_history 並透過 Telegram 發送通知。