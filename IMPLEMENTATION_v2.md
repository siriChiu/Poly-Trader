# 實作計畫 v2：完整開發路線圖

**原則：** 保持模組解耦，逐階段驗證，優先交付可視化與回測能力。

---

## Phase 6: 策略回測引擎（新增）

### Task 6.1: 建立回測引擎核心
- 檔案：`backtesting/engine.py`
- 功能：
  - 讀取歷史特徵 (`features_normalized`) 與交易記錄
  - 實現逐時點模擬：根據當時的特徵與模型輸出決定下單
  - 忽略未來信息（strict time-based split）
  - 計算累計資產曲線（假設初始資金 USDT）
- 輸出：`equity_curve`, `trade_log`, `metrics`

### Task 6.2: 績效指標計算
- 檔案：`backtesting/metrics.py`
- 函數：`calculate_metrics(equity_curve, trade_log) -> dict`
- 指標：Total Return, Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor

### Task 6.3: 參數優化框架
- 檔案：`backtesting/optimizer.py`
- 功能：
  - 網格搜索 `confidence_threshold` (0.5~0.9 step 0.05)
  - 網格搜索 `max_position_ratio` (0.01~0.1)
  - 對每組參數運行回測，收集指標
  - 返回最佳參數組合（例如Sharpe最大）

---

## Phase 7: 增強儀表板

### Task 7.1: 集成回測模塊
- 修改 `dashboard/app.py`：
  - 新增頁籤「策略回測」：讓使用者選擇日期區間、初始資金、參數
  - 呼叫 `backtesting.engine.run_backtest()` 並顯示曲線
  - 顯示 metrics 卡片

### Task 7.2: 參數優化界面
- 新增頁籤「參數優化」：
  - 選擇參數範圍（滑桿）
  - 執行優化並顯示熱圖（Plotly Heatmap）

### Task 7.3: 特徵重要性（可選）
- 使用 SHAP 庫對模型進行解釋
- 顯示五感特徵的平均 SHAP value 條形圖

---

## Phase 8: 數據完整性與標籤

### Task 8.1: 歷史標籤生成
- 由於缺乏歷史標籤，暫時使用 **未來 N 小時收益率** 作為標籤 surrogate
- 檔案：`data_ingestion/labeling.py`
- 邏輯：在 `run_collection_and_save()` 完成後，根據 `close_price` 計算未來 24h 收益率，二值化（>0 為 1）後存入 `labels` 表

### Task 8.2: 模型訓練更新
- 修改 `model/train.py` 讀取 `labels` 表進行真實訓練
- 保存模型並評估驗證集準確率

---

## Phase 9: 實測與部署

### Task 9.1: 端到端驗證
- 執行 `test_pipeline.py` 包括：DB 初始化 → 收集 → 特徵 → 預測 → 回測
- 確保無錯誤且結果合理

### Task 9.2: 部署腳本
- 創建 `deploy.bat` / `deploy.sh` 自動安裝依賴、初始化 DB、啟動儀表板
- 說明文件 `DEPLOYMENT.md`

---

## 里程碑檢查

- [ ] Phase 6 全部完成（engine, metrics, optimizer）
- [ ] Phase 7 儀表板回測頁籤可操作
- [ ] Phase 8 標籤生成與真實模型訓練
- [ ] Phase 9 端到端測試通過

---

## 後續（Phase 10+）

- 集成 LCM 作为长期记忆，存儲历史回測结果與策略版本
- 多策略框架（ allowing different feature sets）
- Telegram/Discord 警報與績效報告自動推送
