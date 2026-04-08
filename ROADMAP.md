# Poly-Trader 發展路線圖 v4.1

## 核心理念

**Strategy-First, Anti-Overfitting**：不再追求 CV 準確率（天花板 ~52%），而是提供可互動的策略實驗室，讓使用者在**防過擬合**的前提下比較 8 個模型。

**投資方式一律金字塔**（20% → 30% → 50% + SL -5% + TP），模型只提供入場信號的置信度。

---

## 已完成 ✅

- Phase 1-5: 核心多特徵框架
- Phase 6: 回測引擎
- Phase 7: 儀表板 + 多特徵有效性分析
- Phase 12: 模型校準與圖表對齊
- Phase 13: 4H 結構線儀表板 + ECDF 正規化
- **Phase 14: 策略實驗室 + 模型排行榜**

### Phase 14 完整清單

#### Backend
- [x] `backtesting/strategy_lab.py` — 規則引擎（金字塔 + SL/TP + 4H 過濾）
- [x] `backtesting/model_leaderboard.py` — Walk-Forward 驗證引擎（8 個模型）
- [x] `/api/strategies/*` — run / save / leaderboard / get / delete
- [x] `/api/models/leaderboard` — 8 模型 WL 排名
- [x] `/api/senses` — 22 特徵 + `raw` 欄位

#### Frontend
- [x] Web Dashboard: 4H 結構線儀表板（牛熊、位置、操作建議）
- [x] Web Strategy Lab: 參數表單 + 3 預設值 + 即時回測 + Leaderboard 表格
- [x] Web `/lab` 路由

#### Data
- [x] 4H 距離特徵 100% 回填（9757/9757 rows）
- [x] `data/ecdf_anchors.json` — 全量 ECDF 錨點
- [x] ECDF 正規化取代 sigmoid

---

## 下一步（Phase 15）

- [x] Web Model Leaderboard 視覺化（表格版已上線；後續可再補柱狀圖 + Fold 比較）
- [ ] 市場分類回測（牛市 vs 熊市分開顯示）
- [ ] 策略匯入/匯出（JSON 分享）
- [ ] 自動最佳化（Optuna / 網格搜尋）
- [ ] 心跳閉環標準化：`strategy-decision-guide.md` + 六帽 + ORID + issue/roadmap/architecture 同步更新
- [ ] canonical target 統一：`label_spot_long_win` 為主，`sell_win` 僅作 legacy 相容
- [ ] P0/P1 修復驅動：每次心跳至少產出 1 個可驗證 patch，而不是只產出失敗報告

### Phase 15 已落地（Web 對齊修補）

- [x] Dashboard 建議語義改為 **spot long / hold / reduce**，移除做空導向
- [x] 補上 `/api/trade` dry-run endpoint，確保 Web 操作不再 404
- [x] Backtest 初始資金輸入正式串接後端
- [x] Strategy Lab leaderboard `run_count` 首次執行顯示修正
- [x] `/api/models/leaderboard` 修復（asof 對齊 + walk-forward split 型別修正）
- [x] Strategy Lab 新增模型排行榜視覺表格
- [x] 訓練流程改為 sparse 4H snapshot asof 對齊，移除 training-time ffill 依賴
