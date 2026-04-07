# Poly-Trader PRD v3.0

> 產品需求規格。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)，問題見 [ISSUES.md](ISSUES.md)。

## 產品定位
Poly-Trader 是一套以「多感官訊號融合」為核心的加密貨幣預測系統。它將價格、衍生品、消息面、預期面與宏觀情緒轉成可量化感官，並對市場行為做可回測、可解釋、可持續擴充的預測。

## 核心目標
1. 模擬人類多感官，將加密貨幣市場拆成可辨識的訊號模組。
2. 支援價格 / 衍生品 / 消息面 / 預期面 / 宏觀情緒融合。
3. 支援歷史資料補齊與回測。
4. 以「賣出勝率」作為主要交易 KPI。
5. 感官可以替換、淘汰、重訓。

## 成功定義
### 主要 KPI
- **賣出勝率 ≥ 90%**：`sell_win_rate = profitable_sells / total_sells`
- **賣出勝率採樣一致**：所有回測與上線報表都使用相同定義。
- **可交易樣本覆蓋率**：系統能在足夠多的市場狀態下維持可用訊號。
- **期望值為正**：單筆交易平均期望報酬 > 0。
- **最大回撤受控**：回撤維持在策略容許範圍。
- **可解釋性**：每次決策可追溯至感官、來源與回測結果。

### 次要 KPI
- precision / recall
- profit factor
- sharpe / calmar
- sell precision / sell recall
- regime-wise performance
- coverage / abstain rate

## 產品範圍
### 本期要做
1. 新增消息面與宏觀感官。
2. 建立 raw / normalized / labels 三層資料結構。
3. 建立歷史補資料機制。
4. 建立以賣出勝率為核心的回測評估。
5. 建立感官淘汰與替換流程。

### 暫不做
- 不以「整體 accuracy」作為唯一目標。
- 不做無法回放歷史的黑箱特徵。
- 不把高勝率建立在低覆蓋率與過度 abstain 之上。

## 感官設計
### 第一組：價格 / 衍生品感官
- Eye：方向與趨勢
- Ear：波動與節奏
- Nose：均值回歸 / 自相關
- Tongue：噪音與波動味覺
- Body：結構位置與區間
- Pulse：資金壓力與多空擁擠
- Aura：複合結構與轉折區
- Mind：長周期風險狀態

### 第二組：消息面 / 社群感官
- Whisper：消息出現與討論聲量
- Tone：語氣正負向
- Chorus：共識與分歧
- Hype：炒作與爆量

### 第三組：預期面 / 事件面感官
- Oracle：市場預期變化
- Shock：事件驚訝程度

### 第四組：國際情緒 / 宏觀感官
- Tide：全球風險偏好
- Storm：宏觀波動壓力

## 資料需求
### 資料源
- 市場資料：Binance / OKX / Bybit K 線、funding、OI、liquidation、volume、basis
- 消息資料：Twitter / X、RSS news、Reddit、Telegram / Discord 公開訊號、GDELT
- 預期資料：Polymarket、prediction markets
- 宏觀資料：DXY、VIX、SPX / NQ futures、收益率、宏觀事件日曆

### 歷史補資料要求
- raw 資料需可回放、可追溯來源。
- normalized 特徵可依版本重算。
- labels 可依 horizon 重生。
- 任何新來源都要能補歷史或明確標註為 only-forward collection。

## 回測要求
### 必要指標
- sell_win_rate
- total return
- max drawdown
- profit factor
- expectancy
- coverage
- abstain rate
- regime-wise sell_win_rate

### 評估原則
- 90% 指的是賣出勝率，不是模型整體 accuracy。
- 高勝率必須同時檢查 coverage，不允許靠過度不交易達成。
- 所有回測必須可分市場狀態比較。

## 使用者界面
- 中文、暗色主題、3 秒內看懂。
- 回測首頁先顯示結果摘要，再顯示風險與會議整理。
- 感官頁需能看到 IC、分位數勝率、來源與版本。

  104|
  105|# 近期更新 v4
  106|
  107|## 2026-04-07: 4H 結構線 + 策略實驗室 (v4.0)
  108|
  109|### 新增
  110|- 4H 結構線距離特徵回填：bias50, bias200, swing_low_dist, ma_order 等 7 欄位 100% 填入
  111|- `/api/senses` 回傳 22 個特徵（8 Core + 2 Macro + 5 Technical + 7 4H）
  112|- Web Dashboard 加入「4H 結構線儀表板」：bias50 偏離、支撐線距離、牛熊判定、操作建議
  113|- 策略實驗室（Strategy Lab）：可互動參數調整 + 即時回測 + Leaderboard
  114|- `backtesting/strategy_lab.py`：規則引擎支援金字塔、止損/止盈、感官過濾
  115|- `/api/strategies/*` API：run / save / leaderboard / get / delete
  116|- 內建策略預設值：金字塔+SL/TP（歷史 +20.0% ROI）
  117|
  118|### 修正
  119|- `/api/features` ECDF 正規化取代 sigmoid（分數不再壓縮到 ~0.5）
  120|- `senses.py` 特徵映射修正：feat_eye → feat_eye（非 feat_eye_dist）
  121|- WebSocket `/ws/live` 支援全部 22 個特徵
  122|- 8 個核心感官 ECDF 錨點重新計算（全量資料，非 7 天視窗）
  123|
  124|### 產品策略轉向
  125|**從「優化 CV 準確率」轉向「策略回測比較」**——XGBoost CV ≤ 52%，但金字塔+SL/TP 策略達 +20.0% ROI。
  126|使用者不再是「看模型預測」而是「自己設計策略、比較結果、找到最有效的參數」。
  127|
  128|---
  129|
  130|## 近期補充需求

### 6. 價格 × 多感官走勢
- 儀表板需顯示價格與多感官同圖趨勢。
- 若資料窗不足，必須顯示 empty-state 說明，不可留白。
- 圖表資料需支援新舊 schema 對齊與 nearest-match。

### 7. 綜合推薦分數校準
- 綜合推薦分數需經過 confidence calibration。
- 需支援 regime-aware model selection 或權重切換。
- 不得把感官本身與模型校準問題混為一談。

### 8. 回測引擎可重現性
- 回測結果需可重跑、可比對、可追溯。
- 需明確輸出交易曲線、指標、sell_win_rate 與 abstain rate。
- schema 改版後不得因舊欄位殘留造成回測失效。
