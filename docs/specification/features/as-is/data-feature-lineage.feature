@as_is @data @lineage
Feature: 市場資料、特徵與標籤的 lineage
  為了讓研究與實盤使用同一個可追溯資料語義
  作為模型與執行系統
  我需要辨識 symbol、時間、feature definition、label definition 與 missingness

  # Sources: feature_engine/preprocessor.py, data_ingestion/labeling.py,
  # model/train.py, tests/test_labeling_p0_p1.py,
  # tests/test_train_alignment.py

  Background:
    Given canonical 研究 horizon 是 1440 分鐘
    And spot-long 金字塔權重是 20%、30%、50%

  Scenario: 有足夠 raw rows 時產生一筆 feature snapshot
    Given raw market data 至少有計算窗口所需的歷史 rows
    When preprocessor 對指定 symbol 執行
    Then 它計算 1m senses、技術指標、turning-point features
    And 它把結果儲存到 features_normalized
    And feature row 包含 timestamp 與 symbol

  Scenario: 同一市場的 slash 與 compact symbol 可在部分 pipeline 被視為等價
    Given symbol 是 "BTC/USDT" 或 "BTCUSDT"
    When labeling 查詢 features 與 raw prices
    Then 它同時查詢兩個 symbol variants
    And 相同 timestamp 優先使用非 NULL symbol row

  @known_inconsistency
  Scenario: raw feature loader 並未在所有路徑使用 symbol variants
    Given DB 中只有 compact symbol 的 raw rows
    And caller 以 slash symbol 請求 load_latest_raw_data
    When preprocessor 使用 exact-symbol query
    Then 目前可能得到空資料
    And 這個結果不得被解讀成市場真的沒有資料

  @known_gap @safety
  Scenario: 4H OHLCV fetch hard-code BTC USDT
    Given caller 請求一個非 BTC/USDT 的 symbol
    When preprocessor 需要 4H OHLCV
    Then 現行 fetcher 仍向 OKX 讀取 "BTC/USDT"
    And 產生的 4H features 可能與 caller symbol 不同
    And 在 to-be multi-symbol 支援前應明確拒絕而非靜默混用

  Scenario: 4H sparse snapshot 以 backward as-of 對齊 dense rows
    Given 4H features 不是每一筆 dense timestamp 都有值
    When training 對齊 sparse 4H rows
    Then 它只使用時間上較早或相同的 snapshot
    And tolerance 是 6 小時
    And 不應使用未來 4H snapshot

  @known_inconsistency
  Scenario: 4H fetch 的不同失敗型態使用不同 missingness 語義
    Given 4H API 回傳不足 200 candles
    When feature computation 完成
    Then 4H fields 可能維持缺值
    But Given 4H fetch 丟出 exception
    When fallback 執行
    Then 部分 4H fields 被寫成 0、0.5 或 1 的中性值
    And downstream 無法只靠數值辨識 outage 與真實 neutral market

  @known_inconsistency
  Scenario: 一般 missing features 會在 training 被 impute
    Given 某些 non-4H features 是 NULL
    When training frame 建立
    Then non-4H missing values 被填為 0
    And leading 4H missing values被填為 column median 或 0
    And model input目前沒有完整 missingness mask說明imputation來源

  Scenario: canonical spot-long label 使用 path-aware runup 與 drawdown
    Given current price 與未來 24 小時 price path 可用
    When label generator 計算 label_spot_long_win
    Then 只有 path 曾達到 take-profit
    And path 未突破最大 drawdown
    Then label_spot_long_win 是 1

  Scenario: canonical simulated pyramid target 使用固定策略語義
    Given entry price 與 horizon prices
    When simulated_pyramid outcome 被建立
    Then 第一層立即部署 20%
    And 價格跌 2% 時部署第二層 30%
    And 價格跌 5% 時部署第三層 50%
    And TP 預設是 2%
    And stop-loss 預設是 5%
    And quality 同時考慮 win、PnL、drawdown 與 time underwater

  @known_gap
  Scenario: saved strategy參數不會改變 canonical label definition
    Given Strategy Lab 的 strategy 使用不同 layer triggers 或 TP/DD
    When model仍以 simulated_pyramid_win 訓練
    Then target仍使用 labeling.py 的固定 20/30/50、-2%、-5%、2%、5%語義
    And strategy backtest target與model training target可能不一致

  @known_gap
  Scenario: label definition沒有versioned identity
    Given label公式或threshold發生改變
    When save_labels_to_db 以 force_update_all 更新
    Then 既有 timestamp+symbol+horizon row被原地改寫
    And DB schema沒有 label_definition_version 區分舊新語義

  @known_gap
  Scenario: training未鎖定 feature definition version
    Given features_normalized 同時存在多個 feature_version
    When load_training_data 執行
    Then 它讀取全部 feature rows
    And 不以 feature_version filter
    And model artifact metadata不足以證明每個row的同一definition lineage

  @known_gap @safety
  Scenario: training nearest join 未按 symbol partition
    Given 兩個symbol在相近timestamp都有feature與label
    When load_training_data 執行 merge_asof
    Then 現行 join key只有 timestamp 與 10 分鐘 tolerance
    And 可能把一個symbol的feature配到另一個symbol的label
    And multi-symbol promotion前必須由BDD與test修正

  Scenario: 沒有足夠 labeled samples 時training fail closed
    Given merge後canonical target rows少於 min_samples
    When load_training_data執行
    Then 它回傳 None
    And 不建立虛構deployable model
