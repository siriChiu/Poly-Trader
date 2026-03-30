# 產品需求文件 (PRD)：Poly-Trader v2 - 五感量化與策略回測平台

## 1. 產品概述

Poly-Trader v2 是五感量化交易系統的完整platform，包含：
- **五感數據採集**（眼、耳、鼻、舌、身）
- **特徵工程與正規化**
- **機器學習決策引擎**
- **風險控制與執行**
- **📊 可視化儀表板**
- **📈 策略回測與模擬**（新）

核心價值：讓使用者不仅能live交易，還能**在歷史數據上驗證策略有效性**，並通過儀表板直觀理解模型表現。

---

## 2. 核心功能模組要求（續）

### 3.5 策略回測引擎 (Backtesting Engine)
**檔案位置：** `backtesting/engine.py`

**功能：**
- 載入歷史 `features_normalized` 與 `trade_history`
- 實現 **逐筆或逐時間段** 的回測模擬
- 計算關鍵績效指標 (KPI)：
  - 年化收益率、夏普比率、最大回撤
  - 勝率、盈虧比、總交易次數
  - 策略曲線 vs 標的 Buy & Hold
- 支援 **Walk-Forward Optimization**（滾動窗口訓練-驗證）

**輸入：**
- 歷史特徵序列（每小時或每日）
- 模型預測分數（或使用當時模型）
- 執行邏輯（風險參數：止損、部位大小）

**輸出：**
- 交易記錄 DataFrame
- 累計收益曲線
- 統計指標表

### 3.6 策略模擬與參數優化
**檔案位置：** `backtesting/optimizer.py`

**功能：**
- 网格搜索 (Grid Search) 或隨機搜索最佳超參數（如 `confidence_threshold`, `max_position_ratio`, `stop_loss_pct`）
- 避免前瞻偏差（look-ahead bias）的交叉驗證
- 生成 **敏感性分析圖**（參數熱圖）

### 3.7 增強可視化儀表板
**檔案位置：** `dashboard/app.py`

**頁面布局：**
1. **總覽頁**：關鍵指標（最新信心分數、持倉、P&L、策略曲線）
2. **特徵分析**：五感特徵時間序列 + 相關性熱圖
3. **模型預測**：輸入特徵 → 輸出信心分數（可手動輸入測試）
4. **交易歷史**：列表 + 累計 P&L 曲線
5. **策略回測**：
   - 選擇時間範圍、初始資金
   - 顯示回測收益率曲線（vs Buy & Hold）
   - 顯示 Sharpe、Max DD、Win Rate 等
6. **參數優化**：選擇參數範圍 → 執行優化 → 熱圖展示

**技術：** Streamlit + Plotly + SQLite

---

## 4. 資料庫結構 (新增)

### Table: backtest_results
- id (PK)
- timestamp
- params_json (JSON 字串，儲存本次回測參數)
- start_date, end_date
- total_return, sharpe_ratio, max_drawdown, win_rate
- equity_curve_path (或直接存序列 JSON)

### Table: strategy_parameters
- id (PK)
- name
- params_json
- created_at

---

## 5. 非功能性需求（續）

- **易用性**：使用者可透過儀表板一鍵啟動回測，無需命令行
- **可解釋性**：特徵重要性圖表（SHAP values）可選
- **可靠性**：回測引擎需處理缺失數據與前視偏差

---

## 6. 使用者故事

> 作為一名量化交易員，我希望查看我的策略在過去6個月的表現，包括收益曲線與最大回撤，以便評估策略是否值得實盤運行。

> 我希望調整 `confidence_threshold` 並立刻看到對勝率的影響，從而找到最佳參數組合。

> 我希望在儀表板上看到每次預測時所使用的五感特徵值，理解模型決策的依據。

---

## 7. 成功標準

- 使用者可在 < 5 分鐘內完成一次完整回測（6 個月數據）
- 儀表板載入時間 < 3 秒
- 回測結果包含至少 5 項統計指標
- 使用者手冊提供截圖與操作影片
