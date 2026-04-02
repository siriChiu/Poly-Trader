# Poly-Trader PRD v2.0

> 產品需求規格。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)，問題見 [ISSUES.md](ISSUES.md)。

## 產品定位
Poly-Trader 是一套以多感官為核心的加密貨幣量化交易系統。用戶是交易者，不是工程師——所以一切設計以「看一眼就知道該不該下單」為目標。

## 核心功能

### 1. 多邊形雷達圖（首頁核心）
- 多個感官各 0~1 分數，組成多邊形雷達圖
- 中心區域越大 = 多數感官偏多
- 綜合建議分數 0~100，大字體顯示
- 自然語言建議（中文），一眼看懂市場狀態

### 2. TradingView K 線圖
- lightweight-charts 專業級 K 線圖
- 疊加 MA20 / MA60 均線
- RSI / MACD 技術指標
- 支撐 / 阻力線標記

### 3. 回測系統
- 歷史回測勝率、盈虧比、最大回撤
- 資金曲線圖
- 每筆交易詳細記錄

### 4. 可插拔感官系統（最重要）
- 每個感官有多個數據源子模組
- Web UI 即時查看、啟用/停用、調整權重
- 權重改變即時預覽對建議分數的影響

## 目標用戶
加密貨幣交易者（非工程師），需要：
- 3 秒內判斷市場方向
- 可調參數，不需要改代碼
- 中文界面、暗色主題

## 技術棧
- 後端：FastAPI + SQLite + WebSocket
- 前端：React + TypeScript + Tailwind CSS + lightweight-charts

## 2026-04-01 Heartbeat 更新
- 90 天回填完成 (Jan 1 - Apr 1, 2026): 2166 raw, 2160 labels (0:1179, 1:981)
- XGBoost 重訓完成: train Acc=74.9%, recent200 Acc=69.0%, F1=0.68, WR=66%
- **關鍵發現**: 所有感官 IC < 0.03 (極弱), Nose/Tongue/Body IC 全部負值
- Tongue IC=-0.14 但模型給重要性 0.262 — 反向使用噪音
- 必須替換 Tongue (FNG 靜態) 和 Nose (funding sigmoid 無效)
