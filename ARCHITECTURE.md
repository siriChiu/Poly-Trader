# ARCHITECTURE.md — Poly-Trader 系統架構

> 完整技術架構文檔。問題追蹤見 [ISSUES.md](ISSUES.md)，產品需求見 [PRD.md](PRD.md)，發展路線見 [ROADMAP.md](ROADMAP.md)。

---

## 技術棧

| 層 | 技術 |
|----|------|
| 前端 | React + TypeScript + Tailwind CSS + Recharts + lightweight-charts |
| 後端 | FastAPI + SQLite + WebSocket |
| 模型 | XGBoost / LightGBM + confidence-based filtering |

---

## 系統分層

### 1. 資料層
統一所有來源進入 raw event store，保留原始事件與來源資訊，支援回放與補歷史。

### 2. 特徵層
將 raw 資料轉換為可量化特徵特徵，並提供 IC、穩定性與版本控制。

### 3. 標籤層
根據未來報酬建立多 horizon 標籤，並以 `label_spot_long_win` 作為主 KPI；`sell_win` 僅保留 legacy 相容欄位。

### 4. 模型層
使用特徵做交易決策與現貨 long 加碼判斷，允許 abstain 與 regime-aware weights。

### 5. 回測層
驗證不同特徵組合、不同市場狀態與不同入場／加碼／出場閾值下的表現。

### 6. 可視化層
顯示每個特徵的 IC、勝率、風險貢獻、spot-long 勝率、回測摘要與會議整理。

---

## 目錄結構

```
Poly-Trader/
├── data_ingestion/              ← 數據收集器 / backfill
│   ├── collector.py             ← 主收集器（整合所有來源）
│   ├── raw_events.py            ← raw event schema / 寫入介面（建議新增）
│   ├── market.py                ← K 線 / funding / OI / liquidation
│   ├── social.py                ← Twitter / RSS / 社群文本
│   ├── prediction.py            ← Polymarket / prediction markets
│   └── macro.py                 ← DXY / VIX / futures / event calendar
├── feature_engine/
│   └── preprocessor.py          ← 特徵工程 v4（IC-validated + versioned）
├── database/
│   └── models.py                ← ORM：raw_events / features / labels
├── model/
│   ├── predictor.py             ← 預測器（spot-long aware）
│   └── train.py                 ← 訓練腳本
├── backtesting/
│   ├── engine.py                ← 回測引擎（spot_long_win_rate / regime aware）
│   ├── metrics.py               ← 績效指標
│   └── optimizer.py             ← 參數優化
├── analysis/
│   ├── sense_effectiveness.py   ← IC / 分位數勝率 / regime analysis
│   └── regime.py                ← 市場狀態分類（建議新增）
├── dashboard/
│   └── app.py                   ← 儀表板（總覽 / 回測 / 特徵 / 會議）
├── server/
│   └── senses.py                ← 特徵引擎
└── tests/
```

---

## 特徵架構 v4（建議）

| # | 特徵 | 特徵主軸 | 資料源 | 用途 |
|---|------|----------|--------|------|
| 1 | Eye | 趨勢 / 方向 | K 線 / 報酬 | 判斷主方向 |
| 2 | Ear | 波動 / 節奏 | K 線 / ATR | 判斷躁動 |
| 3 | Nose | 均值回歸 / 自相關 | K 線衍生 | 判斷過熱 / 過冷 |
| 4 | Tongue | 噪音 / 波動味覺 | K 線 / wick-body | 判斷亂跳 |
| 5 | Body | 結構位置 | range / breakout | 判斷所處階段 |
| 6 | Pulse | 資金壓力 | funding / OI / liquidation | 判斷多空擁擠 |
| 7 | Aura | 複合結構 | vol×autocorr / funding×price | 判斷轉折區 |
| 8 | Mind | 長周期風險 | funding z / macro proxy | 判斷風險狀態 |
| 9 | Whisper | 討論量 / 爆量 | Twitter / RSS / 社群 | 判斷敘事熱度 |
|10 | Tone | 情緒極性 | Text sentiment | 判斷正負情緒 |
|11 | Chorus | 共識 / 分歧 | 文本聚類 / sentiment spread | 判斷市場一致性 |
|12 | Hype | 炒作 / 噪訊 | 重複帖 / influencer spread | 判斷熱炒 |
|13 | Oracle | 預期變化 | Polymarket | 判斷市場預期 |
|14 | Shock | 事件驚訝程度 | news / calendar | 判斷事件衝擊 |
|15 | Tide | 風險偏好 | DXY / VIX / futures | 判斷 risk-on / risk-off |
|16 | Storm | 宏觀壓力 | macro news / rates shock | 判斷宏觀波動 |

---

## 資料庫 Schema

### raw_events
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 事件時間 |
| source | STRING | twitter / polymarket / news / macro / exchange |
| entity | STRING | BTC / ETH / FED / ETF / event |
| subtype | STRING | sentiment / probability / funding / etc. |
| value | FLOAT | 原始值 |
| confidence | FLOAT | 來源可信度 |
| quality_score | FLOAT | 清洗後品質分數 |
| language | STRING | 語言 |
| region | STRING | 區域 |
| payload_json | JSON/TEXT | 原始 payload |
| ingested_at | DATETIME | 寫入時間 |

### features_normalized
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| feat_eye ~ feat_storm | FLOAT | 特徵特徵 |
| regime_label | STRING | trend / chop / panic / event |
| feature_version | STRING | 特徵版本 |

### labels
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| timestamp | DATETIME | 時間戳 |
| symbol | STRING | 交易對 |
| horizon_minutes | INTEGER | 預測窗口 |
| future_return_pct | FLOAT | 未來收益率 |
| future_max_drawdown | FLOAT | 未來最大回撤 |
| future_max_runup | FLOAT | 未來最大漲幅 |
|| label_spot_long_win | INTEGER | 現貨 long 是否獲利 |
| label_up | INTEGER | 漲跌分類 |
| regime_label | STRING | 市場狀態 |

---

## 歷史補資料方案

### 1. 可回補資料
- K 線 / volume / funding / OI / liquidation
- Polymarket 歷史事件
- 宏觀資料（DXY / VIX / futures / calendar）
- GDELT / RSS / 部分新聞歷史

### 2. 只能前向累積資料
- Twitter / X 即時流
- Telegram / Discord 即時訊號
- 私域社群事件

### 3. 補資料流程
1. 先寫 raw_events，不直接覆蓋。
2. 統一 timestamp、entity、source。
3. 依版本重算 features_normalized。
4. 依 horizon 重生 labels。
5. 重新回測與重訓。

### 4. 原則
- raw 永遠保留
- 特徵版本化
- labels 可重算
- 嚴禁未來函數洩漏
- 來源可信度需可追溯

---

## 回測評估指標

### 交易績效
- total return
- annualized return
- max drawdown
- sharpe
- calmar
- profit factor
- expectancy
- trade count

### 現貨 long 勝率
- spot_long_win_rate = profitable_longs / total_longs
- average long profit
- average long loss
- long precision
- long recall
- forward long win rate

### 模型品質
- coverage
- abstain rate
- confidence calibration
- regime-wise performance
- false sell rate
- delayed sell rate

### 特徵品質
- IC / rank IC
- stability
- regime-wise IC
- feature turnover
- mutual information

---

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/senses` | GET | 所有特徵分數 + 建議 |
| `/api/senses/config` | GET/PUT | 特徵配置 |
| `/api/recommendation` | GET | 交易建議 |
| `/api/predict/confidence` | GET | 信心分層預測 |
| `/api/backtest` | GET | 回測結果 |
| `/api/model/stats` | GET | 模型統計 |
| `/api/chart/klines` | GET | K 線數據 |
| `/ws/live` | WS | 即時推送 |
```

---

## 文檔關聯

| 文檔 | 用途 |
|------|------|
| [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md) | AI 角色、紀律、邊界 |
| [HEARTBEAT.md](HEARTBEAT.md) | 心跳詳細流程 |
| [ISSUES.md](ISSUES.md) | 問題追蹤 |
| [PRD.md](PRD.md) | 產品需求 |
| [ROADMAP.md](ROADMAP.md) | 發展路線 |


## 決策層補充

在特徵層與回測層之間，新增兩個關鍵控制點：

### 7. 時間對齊層
- 負責價格、特徵、標籤的 timestamp 對齊。
- 支援 nearest-match 與資料窗覆蓋檢查。
- 若樣本重疊不足，回傳明確 empty-state，而不是靜默空圖。

### 8. 模型校準層
- 負責 confidence calibration、regime-aware model selection、abstain 門檻。
- 用來區分「特徵有效」與「模型輸出不準」。
- 不可直接把特徵分數當成最終推薦分數，需保留校準與版本資訊。

### 9. 文件治理與心跳閉環
- 每次心跳後，必須同步更新 `HEARTBEAT.md`、`ISSUES.md`、`ROADMAP.md`，必要時修正 `ARCHITECTURE.md`。
- `HEARTBEAT.md` 現在是嚴格的 project-driver 憲章：流程固定為 `facts → strategy decision → 六帽/ORID → patch → verify → docs sync → next gate`。
- 使用六帽 + ORID 先把問題分層，再把 P0/P1 變成可執行 patch。
- 若本輪只得到「未達標」而沒有修復，視為流程不完整，不算閉環。
- 若一次心跳缺少 `patch + verify + 文件同步 + 下一輪 gate` 任一項，整輪視為失敗。

---

## API 端點補充

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/predict/confidence` | GET | 綜合信心預測與校準後信號 |
| `/api/backtest` | GET | 回測結果與 spot_long_win_rate（legacy sell_win_rate） |
| `/api/senses` | GET | 特徵分數 + 建議 |

