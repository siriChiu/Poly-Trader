# PRD — v4.0 產品需求規格

## 產品定位
Poly-Trader 是一套以「**多感官訊號融合**」為核心的加密貨幣**投資決策實驗室**。

它將價格、技術指標、4H 結構、宏觀情緒轉成可量化的特徵，並透過**可互動策略實驗室**讓使用者：
- 自己設計策略參數（金字塔比例、止損/止盈、進場條件）
- 即時看回測結果
- 比較不同 ML 模型的真實 OOS 表現（防過擬合）
- 找到最適合當下市場的配置

**投資方式一律使用金字塔**（20% → 30% → 50% 分批加碼 + 止損/止盈），**不需要其他模式。**

---

## 成功定義

### 主要 KPI
- **策略 ROI > 買入持有** — 任何策略如果輸給 buy-and-hold 就沒有意義
- **防過擬合排名** — 模型排行榜必須基於 Walk-Forward 驗證（訓練集和測試集時間不重疊）
- **Train-Test Gap < 10pp** — 訓練準度 - 測試準度 < 10%（超過標示紅字）
- **最大回撤受控** — 單筆不超過 5%，整體策略不超過 20%

### 次要 KPI
- 策略勝率 > 50%
- Profit Factor > 1.0
- Sharpe Ratio > 0.5
- 最少 10 筆交易/策略（避免偶然性）

---

## 核心架構

### 1. 4H 結構線（低雜訊定位）
用 4H K 線畫出：MA50、MA200、布林通道、Swing 支撐/壓力線。
每分鐘計算 1m 價格到這些線的**距離 %**，作為交易定位特徵。

| 特徵 | 意義 |
|------|------|
| `feat_4h_bias50` | 距離 MA50 (%) |
| `feat_4h_bias200` | 距離 MA200 (%) — 牛熊判定 |
| `feat_4h_rsi14` | 4H RSI |
| `feat_4h_macd_hist` | 4H MACD Histogram |
| `feat_4h_dist_swing_low` | 距離最近 Swing Low (%) |
| `feat_4h_ma_order` | MA 排列方向 (+1 多 / -1 空) |

### 2. 金字塔交易框架（固定）
- **Layer 1 (20%)**: 正常區間進場
- **Layer 2 (30%)**: 回調加碼
- **Layer 3 (50%)**: 大幅回調重倉
- **止損**: -5% 全砍
- **止盈**: bias50 > +4% 或 ROI > +8%

### 3. 策略實驗室（Strategy Lab）
Web 面板讓使用者：
- 調進場條件（bias50 上限、nose 上限、層級觸發點）
- 調金字塔比例
- 調止損/止盈
- 一鍵跑回測
- 看 Leaderboard

### 4. 模型排行榜（Model Leaderboard）
比較不同 ML 模型在**同一金字塔框架、同一 Walk-Forward 驗證**下的表現：

- **Rule Baseline**: 純 4H 偏離（不用 ML）
- **Logistic Regression**: 線性基準
- **XGBoost**: 樹模型
- **Random Forest**: 抗過擬合
- **MLP**: 神經網絡

**反過擬合機制：**
- Expanding Window Walk-Forward 驗證
- Train/Val/Test 時間嚴格分離
- 報告每個 Fold 的 ROI、勝率、交易次數
- 顯示 Train-Test Gap（過擬合指標）

---

## 使用者故事

1. **作為投資者**，我想一進 Web 就看到「現在離 MA50 多遠、是不是靠近支撐線、牛市還是熊市」，這樣我 3 秒就知道該不該買。
2. **作為工程師**，我想改策略參數（bias50 從 -3% 改成 -5%，止損從 5% 改成 3%），按一個按鈕就看到新 ROI、新勝率。
3. **作為研究者**，我想看 XGBoost vs Random Forest vs 純規則，在「完全沒看過的未來資料」上誰表現最好。我不要在訓練集上比較。
4. **作為風險管理者**，我想看到每筆策略的最大回撤和 Profit Factor，不只 ROI。

---

## 已完成的 v4.0 功能

- [x] 4H 距離特徵 100% 回填（9757/9757 行）
- [x] 22 特徵 API (`/api/senses`) + raw 值
- [x] Web 4H 結構線儀表板
- [x] ECDF 正規化（分數有差異，不再壓縮到 0.5）
- [x] 策略實驗室 Web 面板（參數調整 + 回測 + Leaderboard）
- [x] `/api/strategies/*` 完整 API
- [x] `backtesting/strategy_lab.py` 規則引擎
- [x] `backtesting/model_leaderboard.py` WL 驗證引擎
- [x] Walk-Forward 5-7 個 ML 模型比較

## 下一步（Phase 14 後續）

- [ ] Web Leaderboard 視覺化（柱狀圖 + Fold 比較）
- [ ] ML 模型模式接入（XGBoost/LightGBM/RF 信心分數入場）
- [ ] 市場分類回測（牛市 vs 熊市分開）
- [ ] 策略匯入/匯出（JSON 分享）
