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
