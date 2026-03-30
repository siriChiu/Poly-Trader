# 五感模組實作細節與 API 規格書 (Implementation Details)

本文件定義了 Project Five-Senses 中「資料採集層 (Data Ingestion)」與「特徵工程層 (Feature Engineering)」的具體實作邏輯。所有的 API 請求必須具備超時 (Timeout=10s) 與重試機制 (Exponential Backoff)。

---

## 👁️ 1. 眼 (Eye)：視覺邊界與流動性模組
**檔案位置：** `data_ingestion/eye_binance.py`
**目標：** 獲取價格與流動性痛點，計算價格是否過度延伸。

### 1.1 資料獲取 (Binance API - 完全免費)
* **端點：** `GET https://api.binance.com/api/v3/klines`
* **參數：** `symbol=BTCUSDT`, `interval=4h`, `limit=100`
* **替代方案 (若不用 Coinglass)：** 為了保持 100% 免費且不依賴第三方，流動性痛點可直接抓取 Binance 的深度圖 (Order Book) 來尋找掛單最密集的價格區間。
    * **端點：** `GET https://api.binance.com/api/v3/depth`
    * **參數：** `symbol=BTCUSDT`, `limit=1000`

### 1.2 特徵處理邏輯 (Feature Processing)
* **尋找流動性痛點 (Liquidity Cluster)：** 從 Order Book 中，分別往上 (Asks) 和往下 (Bids) 找到掛單量 (Volume) 最大的價格點，定義為 Price_resistance 與 Price_support。
* **正規化公式 (距離比例)：**
    * 計算當前價格 P_current 距離上下痛點的百分比：
    * 向上引力特徵：Feat_Eye_Up = (Price_resistance - P_current) / P_current
    * 向下引力特徵：Feat_Eye_Down = (P_current - Price_support) / P_current

---

## 👂 2. 耳 (Ear)：市場共識與總經模組
**檔案位置：** `data_ingestion/ear_polymarket.py`
**目標：** 獲取去中心化預測市場的真金白銀機率，作為總經風險濾網。

### 2.1 資料獲取 (Polymarket Gamma API - 免費)
* **端點：** `GET https://gamma-api.polymarket.com/events`
* **參數：** 可以透過 `slug` 尋找特定賭盤 (例如：`will-the-fed-cut-rates-in-march-2026`)，或者搜尋 `title="Bitcoin"`。
* **解析方式：** 回傳的 JSON 中，找到對應的 `markets[0].tokens`。Token 的 `price` 屬性即代表市場機率 (例如 `0.65` 代表 65%)。

### 2.2 特徵處理邏輯 (Feature Processing)
* **機率直接映射：** Polymarket 的價格本身就是 0 ~ 1 的浮點數。
* **正規化：**
    * 若為利空事件 (例如：Fed 不降息機率)，直接設為風險懲罰特徵：Feat_Ear_Risk = P_event (數值越大，做多勝率越扣分)。

---

## 👃 3. 鼻 (Nose)：衍生品氣味與資金成本模組
**檔案位置：** `data_ingestion/nose_futures.py`
**目標：** 嗅探合約市場的過度槓桿與散戶情緒。

### 3.1 資料獲取 (Binance Futures API - 免費)
* **端點 1 (資金費率)：** `GET https://fapi.binance.com/fapi/v1/premiumIndex`
    * **參數：** `symbol=BTCUSDT`
    * **解析：** 提取 `lastFundingRate`。
* **端點 2 (未平倉量 OI)：** `GET https://fapi.binance.com/fapi/v1/openInterest`
    * **參數：** `symbol=BTCUSDT`
    * **解析：** 提取 `openInterest`。

### 3.2 特徵處理邏輯 (Feature Processing)
* **Funding Rate 壓縮 (Sigmoid 轉換)：**
    因為資金費率平時很小 (如 0.01%)，極端時很大 (如 2%)，直接線性使用會導致模型失真。必須透過 Sigmoid 函數將其壓縮至 -1 ~ 1 區間：
    * 先放大數值：x = FundingRate * 10000
    * 計算特徵：Feat_Nose_Funding = 2 * (1 / (1 + e^(-x))) - 1
* **OI 變動率：** 計算過去 24 小時的未平倉量增長率 Feat_Nose_OI_ROC。

---

## 👅 4. 舌 (Tongue)：社群情緒與多空對比模組
**檔案位置：** `data_ingestion/tongue_sentiment.py`
**目標：** 捕捉整體市場的貪婪/恐懼極端值。

### 4.1 資料獲取 (Alternative.me API - 免費無須 Key)
* **端點：** `GET https://api.alternative.me/fng/`
* **參數：** `limit=2` (獲取今日與昨日數據)
* **解析：** 回傳 JSON 中的 `data[0].value` (字串型態，需轉整數)。

### 4.2 資料獲取 (Binance 多空比 - 免費)
* **端點：** `GET https://fapi.binance.com/futures/data/globalLongShortAccountRatio`
* **參數：** `symbol=BTCUSDT`, `period=1d`, `limit=30` (獲取過去一個月的趨勢)
* **解析：** 提取 `longShortRatio`。

### 4.3 特徵處理邏輯 (Feature Processing)
* **F&G 正規化：** 原始值為 0 ~ 100。
    * 轉換為 0 ~ 1：Feat_Tongue_FNG = Value / 100
* **多空比 Z-score：** 單看多空比數字無意義，需與歷史對比。
    * 計算過去 30 天的平均值 μ 與標準差 σ。
    * Feat_Tongue_LSR = (CurrentRatio - μ) / σ

---

## 體 5. 身 (Body)：鏈上宏觀血脈模組
**檔案位置：** `data_ingestion/body_defillama.py`
**目標：** 確認加密貨幣市場的整體資金水位 (M2 供給量) 是擴張還是收縮。

### 5.1 資料獲取 (DefiLlama API - 免費無須 Key)
* **端點：** `GET https://stablecoins.llama.fi/stablecoincharts/all`
* **解析：** 回傳一個陣列，每個元素包含 `date` 與 `totalCirculatingUSD`。抓取陣列最後一筆 (今日) 與倒數第 8 筆 (7天前) 的 `totalCirculatingUSD`。

### 5.2 特徵處理邏輯 (Feature Processing)
* **資金增長率 (ROC)：**
    * 計算 7 日變動率：ROC = (TotalUSD_today - TotalUSD_7days_ago) / TotalUSD_7days_ago
    * **離散化特徵：** 為了讓 AI 模型更容易學習宏觀趨勢，將其轉換為分類特徵：
        * 若 ROC > 0.5% -> Feat_Body_Trend = 1 (資金流入，做多安全)
        * 若 -0.5% <= ROC <= 0.5% -> Feat_Body_Trend = 0 (資金停滯)
        * 若 ROC < -0.5% -> Feat_Body_Trend = -1 (資金撤離，嚴格限制做多)

---

## 💡 開發指引 (給 AI 助手的 Prompt 建議)

當你要讓 AI 幫你寫程式時，你可以這樣對它說：

> **「請閱讀 `architecture.md` 與 `five_senses_implementation.md`。現在，請幫我實作 `data_ingestion/body_defillama.py`。請使用 `requests` 庫，加上 3 次 Retry 的機制，並嚴格依照文件中的公式計算出 `Feat_Body_Trend`，最後將結果封裝成一個 Pandas DataFrame 回傳。請加上完整的 Python Type Hints。」**