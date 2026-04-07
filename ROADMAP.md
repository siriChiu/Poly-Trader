# Poly-Trader 發展路線圖 v3.0

> 發展路線與進度。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，需求見 [PRD.md](PRD.md)，問題見 [ISSUES.md](ISSUES.md)。

## 核心理念

**Validation-First**：先證明每個感官有預測力，再組合。多感官量化系統的價值不在於收集數據，而在於回答：哪些感官的設計是有效的？哪些需要改進？

---

## 路線圖

### Phase 8: Validation-First
**目標**：建立可回測、可比較、可淘汰的感官系統

- [ ] 擴充感官集合：加入 Whisper / Tone / Chorus / Hype / Oracle / Shock / Tide / Storm
- [ ] 建立 raw_events 統一資料層
- [ ] 建立 features_normalized 版本化重算流程
- [ ] 建立 sell_win_rate 標籤與回測指標
- [ ] 讓每個感官都能回測 IC、sell_win_rate、regime-wise performance

### Phase 9: 歷史補資料與回放
**目標**：讓系統具備可回放歷史的能力

- [ ] K 線 / funding / OI / liquidation 歷史補齊
- [ ] Polymarket 歷史事件補齊
- [ ] 宏觀資料（DXY / VIX / futures / calendar）補齊
- [ ] 新聞 / 社群資料的 forward collection pipeline
- [ ] raw → normalized → labels 可重算閉環

### Phase 10: 賣出勝率優化
**目標**：將主要 KPI 轉成賣出勝率

- [ ] `sell_win_rate = profitable_sells / total_sells`
- [ ] 建立 sell precision / sell recall / forward sell win rate
- [ ] abstain 機制：低信心不交易
- [ ] regime-aware 賣出閾值
- [ ] 回測比較：不同閾值與不同感官組合

### Phase 11: 市場環境分類器
**目標**：根據市場狀態切換感官權重

- [ ] 市場分類：trend / chop / panic / event
- [ ] 各 regime 的最佳感官權重
- [ ] 以 regime-wise IC 調整模型
- [ ] 回測 regime-wise sell_win_rate

### Phase 12: 模型升級與可解釋性
**目標**：從可用變成可控、可解釋

- [ ] IC-weighted ensemble
- [ ] confidence calibration
- [ ] SHAP / feature attribution
- [ ] 每次交易顯示「哪些感官促成賣出」

### Phase 13: 儀表板與報告
**目標**：讓策略狀態一眼可讀

- [ ] sell_win_rate 主視覺
- [ ] 感官 IC 條形圖
- [ ] 分位數勝率熱圖
- [ ] regime-wise 回測圖
- [ ] 歷史補資料覆蓋率面板

---

## 已完成

- Phase 1-5: 核心多感官框架
- Phase 6: 回測引擎
- Phase 7: 儀表板 + 多感官有效性分析

---


### Phase 14: 策略實驗室（Strategy Lab）
**目標**：讓使用者自己設計策略、比較參數、找到最有效的配置

- [x] 4H 結構線距離特徵回填（bias50, bias20, swing_low, ma_order）100% 覆蓋
- [x] 規則引擎：金字塔 + 止損/止盈 + 4H 過濾 + 感官條件
- [x] API `/api/strategies/*` — run / save / leaderboard / get / delete
- [x] Web 策略實驗室面板：參數調整 + 三鍵預設值 + Leaderboard 排行
- [ ] ML 模型模式：XGBoost / RandomForest / LightGBM 信心分數入場
- [ ] 混合模式：4H 過濾 + ML 入場
- [ ] 市場分類回測：牛市 vs 熊市 分開顯示結果
- [ ] 策略匯入/匯出：JSON 格式，可分享
- [ ] 自動最佳化：Optuna / 網格搜尋

---

## 已完成

- Phase 1-5: 核心多感官框架
- Phase 6: 回測引擎
- Phase 7: 儀表板 + 多感官有效性分析
- **Phase 14 (MVP): 策略實驗室 — 可互動參數調整 + 回測 + Leaderboard**

- [x] ECDF 錨點重新計算（全量資料）
- [x] WebSocket 支援全部 22 特徵

### Phase 13: 儀表板與報告
**目標**：讓策略狀態一眼可讀

- [ ] sell_win_rate 主視覺
- [ ] 感官 IC 條形圖
- [ ] 分位數勝率熱圖
- [ ] regime-wise 回測圖
- [ ] 歷史補資料覆蓋率面板
- [ ] 價格 × 多感官走勢圖與缺口提示
