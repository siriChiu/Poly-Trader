# 實作計畫 (給 AI 開發助手的提示詞與執行步驟)

**開發原則：** 請嚴格遵守 `architecture.md` 的目錄結構。每次只實作一個階段，確保該階段的單元測試通過後，再進入下一階段。撰寫程式碼時，請加上完整的型別提示 (Type Hints) 與 Docstrings。

## Phase 1: 基礎設施與資料庫建置
* **任務：** 1. 建立專案目錄結構。
  2. 撰寫 `config.yaml` 解析模組。
  3. 使用 SQLAlchemy 建立 `database/models.py` 的 SQLite 資料庫 Schema（包含 raw_market_data, features_normalized, trade_history）。
  4. 建立 `utils/logger.py` 實作 Rotating File Handler 與終端機輸出。

## Phase 2: 數據採集模組 (五感 API 串接)
* **任務：** 1. 實作 `data_ingestion/body_defillama.py`，抓取全網穩定幣市值 API。
  2. 實作 `data_ingestion/tongue_sentiment.py`，抓取 Alternative.me 恐懼貪婪指數。
  3. 實作 `data_ingestion/nose_futures.py`，透過 CCXT 或 Binance API 抓取 BTCUSDT 的 Funding Rate。
  4. **要求：** 所有 API 請求必須包含 `try-except` 區塊，並在發生 `Timeout` 或 `RateLimitExceeded` 時進行 Exponential Backoff 重試。

## Phase 3: 特徵工程與正規化
* **任務：** 1. 實作 `feature_engine/preprocessor.py`。
  2. 撰寫函數將 `raw_market_data` 的最新資料撈出，轉換為 DataFrame。
  3. 實作計算方法：ROC (變動率)、Z-score 標準化、以及針對 Funding Rate 的 Sigmoid 壓縮。將結果存入 `features_normalized`。

## Phase 4: 模型預測與大腦 (意)
* **任務：** 1. 撰寫一個 Dummy Model（暫時用隨機數或簡單邏輯代替，回傳 0~1 的浮點數），建立預測流程的接口 `model/predictor.py`。
  2. （後續需提供歷史數據供模型訓練 `train.py`，目前先確保預測推論管線暢通）。

## Phase 5: 交易執行與主程式排程
* **任務：** 1. 實作 `execution/risk_control.py`，確保單次下單金額不超過帳戶餘額的 5%。
  2. 實作 `execution/order_manager.py`，利用 CCXT 執行虛擬下單 (Dry Run 模式) 並寫入資料庫。
  3. 整合所有模組至 `main.py`，使用 APScheduler 設定每小時的 `01` 分執行一次完整迴圈 (採集 -> 特徵 -> 預測 -> 執行)。