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
- [x] 市場分類回測（依進場 regime 顯示 Bull / Bear / Chop ROI、勝率、PF）
- [ ] 策略匯入/匯出（JSON 分享）
- [ ] 自動最佳化（Optuna / 網格搜尋）
- [x] 心跳閉環標準化：`strategy-decision-guide.md` + 六帽 + ORID + issue/roadmap/architecture 同步更新，並由 `HEARTBEAT.md` 明確定義為強制流程
- [x] canonical target 統一：`simulated_pyramid_win` 為主；`label_spot_long_win` 僅作 path-aware 比較；`sell_win` 僅作 legacy 相容
- [x] P0/P1 修復驅動：每次心跳至少產出 1 個可驗證 patch，不允許只產出失敗報告
- [ ] 心跳 gate 自動化：把「patch / verify / doc sync / next gate」檢查做成腳本或模板驗證
- [ ] blocker 升級機制落地：同一 issue 連續 2~3 輪無進展時，自動升級 source-level investigation / alternative plan
- [x] source-level sparse feature hygiene：Fin / Fang / Web / Scales / Nest fetch failure 改為 `None`，不再把來源失敗寫成假中性 0
- [x] sparse source latest-row contract：Claw / Fang / Fin / Web / Scales / Nest 只允許使用 latest raw row；若最新來源缺值則保留 `None`，禁止把舊 sparse 值偷帶到新 features row
- [x] sparse-source historical decontamination：`cleanup_sparse_source_history.py` 已清除 Claw / Fin / Nest 假 0 與 Fang / Web / Scales stale carry-forward，coverage 現在反映真實 source history gap
- [x] canonical leaderboard target hygiene：`load_model_leaderboard_frame()` 以 `simulated_pyramid_win` 為主 target row gate，path-aware 僅保留比較用途，不再卡住 leaderboard 主資料流
- [x] regime label persistence：新 features row 在 preprocessor save 時即寫入 `regime_label`，`hb_collect.py` 在 `null_count=0` 時直接 early-exit
- [x] FeatureChart data-quality 標示：圖例與警示卡顯示 `coverage% / distinct / reasons`，低 coverage 特徵自動隱藏且原因可見
- [x] FeatureChart source-quality 標示：coverage API / report / UI 已可區分 `source_fallback_zero` vs `source_history_gap`
- [x] source-history blocker surfacing：coverage report / API / FeatureChart 已同步顯示 `history_class / backfill_status / backfill_blocker / recommended_action`，把 low-coverage sparse sources 明確升級成 source-level blocker，而不是前端顯示問題
- [x] shared source-history policy：`feature_engine/feature_history_policy.py` 成為 coverage/report/API 的單一 policy 實作，避免 blocker metadata 漂移造成 heartbeat 與 UI 對同一個 sparse source 給出不同結論
- [x] forward raw snapshot archive kickoff：`data_ingestion/collector.py` 現在每輪都會把 Claw / Fang / Fin / Web / Scales / Nest / Macro 寫入 `raw_events` (`*_snapshot`)，coverage/report/runtime 也同步顯示 `raw_snapshot_events`，正式開始累積 sparse sources 的 forward archive
- [x] fast heartbeat pre-collect：`hb_parallel_runner.py --fast` 現在會先跑 `hb_collect.py`，確保 cron fast heartbeat 先推進 raw/features/labels，再做 IC / blocker 診斷，避免心跳空轉
- [x] forward archive freshness gating：coverage report / API / FeatureChart / heartbeat summary 現在會顯示 sparse-source archive 的 `latest_age_min / span_hours / stale status`，archive 超過 60 分鐘未更新時直接升級為 collect blocker
- [x] archive-window coverage gating：coverage report / API / FeatureChart / heartbeat runner 現在額外顯示 `archive_window_coverage_pct`（自 snapshot archive 起點以來的 recent-window coverage），可區分「forward archive 已健康、只剩歷史缺口」與「forward archive 仍有 source/path 缺值」兩種 blocker
- [x] sparse-source latest snapshot status surfacing：CoinGlass / Nest 等 snapshot payload 現在會保留 `status/message`（如 `auth_missing` / `fetch_error`），heartbeat 與 coverage policy 會直接把「目前 live fetch 壞掉」和「只是歷史 coverage 缺口」分開，不再讓 blocker 判斷空轉
- [x] source auth/fetch blocker quality escalation：coverage policy / markdown report / FeatureChart 現在會把 `auth_missing` / 非 `ok` snapshot failure 升級為 `source_auth_blocked` / `source_fetch_error`，讓前端與報表直接顯示 credential / fetch blocker，而不是退化成 generic coverage 低
- [x] sparse-source pre-ready archive-window triage：在 forward archive 尚未滿 10 筆前，就先區分 **recent-window 已健康** vs **recent-window 僅部分有值**。Web / Fang / Scales 不再被誤導去重查 live fetch；Nest 這類 partial recent coverage 會被明確升級成 source/path quality gap。
- [x] Nest Gamma parser hardening：`nest_polymarket.py` 已支援 Gamma API 的 stringified `outcomes` / `outcomePrices` 欄位並擴大 market 搜尋範圍，forward archive 不再因 parser bug 長期維持 0% coverage
- [x] hb_parallel_runner fast-mode unblock：`python scripts/hb_parallel_runner.py --fast` 不再要求 `--hb`，並會把 source blockers 一起寫入 heartbeat summary，適合 cron 快速閉環檢查
- [x] hb_collect label horizon hygiene：修正 4h label job 誤寫成 14,400m 的單位 bug，並清除 accidental 14,400m labels
- [x] Canonical-window IC guardrails：full/regime/dynamic-window 腳本固定使用 `horizon_minutes=1440`，對 `constant_target` / `constant_feature` 顯式標註，避免 NaN 假 blocker
- [x] Strategy Lab canonical target emphasis：model leaderboard target comparison 現在把 `simulated_pyramid_win` 排在第一位並標成 `canonical`，`label_spot_long_win` 明確降級為 `legacy compare` 診斷卡，避免主 target 再被舊語義稀釋
- [x] warning-safe indicator math：`technical_indicators.py` / `ohlcv_4h.py` 已改用 warning-safe divide，fast heartbeat collect 在 flat price / zero-volume window 下不再噴 divide-by-zero RuntimeWarning，stderr 可重新代表真 blocker
- [ ] Sparse-source historical backfill：在 decontaminate 完成後，為 Web / Fang / Scales / Claw / Fin / Nest 補真正歷史 coverage，而不是再引入 fallback/carry-forward
- [ ] Dynamic Window recent-window 穩定化：N=100/200/400 已確認不是 merge bug，而是 canonical 24h labels 在最近窗口全部為 1；下一步需設計 distribution-aware window / alternate evaluation rule

### Phase 15 已落地（Web 對齊修補）

- [x] Dashboard 建議語義改為 **spot long / hold / reduce**，移除做空導向
- [x] 補上 `/api/trade` dry-run endpoint，確保 Web 操作不再 404
- [x] Backtest 初始資金輸入正式串接後端
- [x] Strategy Lab leaderboard `run_count` 首次執行顯示修正
- [x] `/api/models/leaderboard` 修復（asof 對齊 + walk-forward split 型別修正）
- [x] Strategy Lab 新增模型排行榜視覺表格
- [x] 訓練流程改為 sparse 4H snapshot asof 對齊，移除 training-time ffill 依賴
- [x] Strategy persistence schema sanitize（NaN/缺欄位修復 + internal strategy 過濾 + save 不再誤增 run_count）
