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

### Phase 16（高勝率 / 低回撤 / 高可信度）

> Implementation plan：`docs/plans/2026-04-10-phase-16-implementation-plan.md`

>- 核心目標：從「模型能跑、UI 可用」升級到「只做高品質交易、降低無效加碼、把 drawdown 直接內建到決策裡」。
>
>- 主原則：**先提升訊號品質與決策分級，再追求更多模型與更多 feature。**

- [~] 兩階段決策架構：先做 **4H regime gate（ALLOW / CAUTION / BLOCK）**，再做短線 entry-quality score；避免在錯的背景裡用對的短線訊號進場  
↳ Heartbeat #640：live predictor / `hb_predict_probe.py` / `/predict/confidence` 已升級到 `phase16_baseline_v2`，除了 `regime_gate + entry_quality + allowed_layers`，還會輸出 calibrated decision-quality expectations； Heartbeat #650 再把 Dashboard `ConfidenceIndicator` 對齊到同一套 canonical contract； Heartbeat #651 讓 `/api/backtest` 也回傳 `avg_entry_quality / avg_allowed_layers / dominant_regime_gate` 與 canonical DQ 摘要；**Heartbeat #663 再修掉 live route 語義分裂：predictor routing 現在優先使用 `decision_profile.regime_label`，並額外輸出 `model_route_regime`，避免 `used_model` 與對外顯示的 regime_label 不一致； Heartbeat #666 再補上 calibration-scope guardrail，當最窄 `regime_gate+entry_quality_label` bucket 落入 label-imbalanced polluted slice 時，會自動回退到更廣的 `regime_gate / entry_quality_label / global` lane，避免 probe/API 繼續輸出虛高的 chop-only expectation； Heartbeat #692 再把 `decision_quality_scope_diagnostics` 併入 live probe contract，讓 heartbeat 可同時比較 `entry_quality_label=D` 與更窄 bull/ALLOW/D lane 的 pathology，而不必依賴 ad-hoc scope probe 腳本； Heartbeat #693 再把這組 scope drill-down 升級成 `pathology_consensus`，直接機器化輸出多個 pathological scopes 的 shared 4H collapse features與 worst scope，讓下一輪能直接沿 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 做 source/root-cause 修復； Heartbeat #694 再把這個 diagnosis 變成實際 parity patch：Strategy Lab / API / live predictor 現在都用真 `feat_4h_bias200` 當 regime gate，且 entry-quality 會直接吃 `feat_4h_bb_pct_b / feat_4h_dist_bb_lower / feat_4h_dist_swing_low`，不再讓 4H collapse pocket 只存在於 probe 報告中； Heartbeat #695 再把 **scope regime-mix** 變成 live contract 的一部分，新增 `recent500_regime_counts / recent500_dominant_regime`，讓 narrowed bull-only D pocket 與 broader D lane 的差異能直接 machine-check； Heartbeat #698 再把 **shared 4H collapse pocket 直接接進 regime gate downgrade**：當 `feat_4h_bb_pct_b / feat_4h_dist_bb_lower / feat_4h_dist_swing_low` 落入極弱結構，Strategy Lab 與 live predictor 會把原本僅靠正 `feat_4h_bias200` 支撐的 `ALLOW` 降成 `CAUTION/BLOCK`，並把 live calibration scope 從 broad `entry_quality_label` 收斂到更誠實的 `regime_gate+entry_quality_label` lane； **Heartbeat #712 再補 pocket-outcome evidence**：`spillover_gate_path` / `exact_gate_path` 現在會直接帶出 `targets / pnl_signs / quality_signs / true_negative_rows`，讓 heartbeat 能 machine-check blocker pocket 是「真 canonical 負樣本」還是「gate 過嚴誤傷」，避免僅憑 structure bands 猜測。 **He

- [~] canonical target 升級：從單一 `simulated_pyramid_win` 擴展到 **win + pnl_quality + drawdown_penalty + time_underwater** 的複合交易品質評分  
  ↳ Heartbeat #642：leaderboard scoring / API payload 已開始直接使用並輸出 `avg_decision_quality_score + avg_expected_*` canonical quality contract；Heartbeat #643 把 Strategy Lab 模型排行榜前端摘要切到這組欄位；Heartbeat #644 再把 Strategy Lab **策略排行榜主表 + `/api/strategies/{name}` 詳情** 切到同語義並改成依 DQ 排序；Heartbeat #645 再把 **active strategy summary + `/api/strategies/run` payload** 補上 `decision_contract`（target label / sort semantics / horizon）並直接顯示 DQ / 預期勝率 / DD-UW；Heartbeat #649 再把 Strategy Lab **side-by-side compare flow** 切到同一套 canonical DQ / expected win / DD-UW contract；Heartbeat #651 把 Dashboard `/api/backtest` + `BacktestSummary` 補到同一個 decision-quality contract；Heartbeat #652 再把 standalone `web/src/pages/Backtest.tsx` 與交易表一起切到相同 contract；Heartbeat #653 補上 `web/src/App.tsx` 的實際 `/backtest` route + nav，修掉「頁面存在但 router 仍導回 `/lab`」的假完成；Heartbeat #654 再新增 `tests/test_frontend_decision_contract.py`，把 `/backtest` route/nav 與 Dashboard / Backtest / StrategyLab 的 canonical DQ wiring 鎖進 regression guard；Heartbeat #655 再把 Strategy Lab active summary 中的 ROI / 勝率 / PF 區塊顯式降級為 **Legacy execution metrics（僅輔助 / tie-breaker）**，並把 canonical 欄位缺失時的 ROI fallback 改成醒目警告文案，避免使用者把 fallback 誤當正常主語義；Heartbeat #656 再把 Dashboard 4H 結構卡的手寫 bias→action copy 降級為 `結構背景`，主決策固定回到 live `regime_gate + entry_quality + allowed_layers` contract。下一步收斂到 Dashboard 其餘摘要卡與未來新增 compare surfaces，避免任何新比較入口又回退成 ROI / 勝率 / PF-only 或 route-level 假可用
- [~] confidence-based layer sizing：依 entry quality / confidence 決定只開第一層、允許兩層、或完整 20/30/50 金字塔，避免低品質訊號重倉進場  
  ↳ Heartbeat #637：live predictor 已回傳 `allowed_layers` 並讓 `should_trade` 受 layer allowance 約束；下一步是把 sizing 納入 leaderboard / live ranking 主排序
- [ ] 核心信號 vs 研究信號分級：把 4H 結構 + 高 coverage technical 納入主決策；把 sparse-source / 低 coverage 特徵降級為 research overlay，不再與核心信號同權  
  ↳ Heartbeat #688：`recent_drift_report.py` 已先把 sparse-source frozen / shift diagnostics 降級成 `overlay_only=research_sparse_source`，讓 recent drift sibling-window 主證據優先聚焦 core features。下一步是把同一條 core-vs-research contract 推到 calibration / ranking / UI 全鏈路，而不只停在 drift 報表。 
- [~] leaderboard 改版：主排序改成 **ROI / 最大回撤 / PF / decision quality**，勝率只保留為參考指標，避免高命中率卻低資金效率的假優勢  
  ↳ Heartbeat #638：`backtesting/model_leaderboard.py` 與 API payload 已輸出 trade-quality / drawdown-aware component fields；本輪再把 `backtesting/model_leaderboard.py` composite 與 `server/routes/api.py::_strategy_leaderboard_sort_key()` 明確改成 `ROI -> lower max_drawdown -> decision_quality -> profit_factor`，並同步更新 Strategy Lab 的 sort semantics / fallback 文案。**Leaderboard 2.0 第一版現已上線：`backtesting/model_leaderboard.py` 新增 `Reliability / Return Power / Risk Control / Capital Efficiency / Overall Score` 五個能力分數，`/api/models/leaderboard` 會回傳 `quadrant_points + score_dimensions + storage`，`StrategyLab.tsx` 也新增可排序總表與象限圖。正式資料不再只靠 JSON cache，而是同時寫入 SQLite 的 `leaderboard_model_snapshots` / `leaderboard_model_scorecards`，JSON 只保留作 stale-while-revalidate 快取。** **接著 strategy leaderboard 也已升級到同一套五維能力分數、可排序表格、策略象限圖、快照歷史與 rank delta；後端新增 `/api/strategies/leaderboard/history` 與 SQLite `leaderboard_strategy_snapshots` / `leaderboard_strategy_scorecards`。** 下一步是比較 **classic pyramid vs reserve_90** 的 OOS ROI / DD / underwater time，再把 capital-mode filter / trend chart 補齊，最後才決定是否升級到 storm-unwind inventory engine
- [~] Dynamic Window distribution-aware 版：窗口評估必須顯示 label distribution / regime distribution / constant-target guardrail，不再只看固定 N 導致近期窗口誤判  
  ↳ Heartbeat #661–#676 已把 recent drift artifact、dynamic-window guardrail、training-side TW damping、live calibration / scope fallback、execution-time layer caps、以及 frozen-vs-compressed feature diagnostics 串成同一條 distribution-aware policy。**Heartbeat #679 再補 persistent-pathology selection**：`scripts/recent_drift_report.py` 與 `model/predictor.py` 不再在 severity / delta 同級時偏向較短的 100-row slice，而是優先揭露更持久的 recent pathology window。**Heartbeat #680 再補 target-path adverse-streak evidence**：drift artifact / auto-propose / live predictor 不再只看恢復中的 tail streak，而會同步暴露 chosen pathology window 內最長 adverse target streak。**Heartbeat #682 再補 sibling-window contrast**：`scripts/recent_drift_report.py` / `scripts/auto_propose_fixes.py` 現在會把 primary pathology slice 與前一個等長 sibling window 直接對比，輸出 `prev_win_rate / quality / pnl` 與 `top_mean_shift_features`。**Heartbeat #683 再把這份 sibling-window contract 推進 live predictor**：`model/predictor.py::_recent_scope_pathology_summary()` 與 `scripts/hb_predict_probe.py` 現在也會直接輸出 same-scope `reference_window_comparison`（`prev_win_rate / Δquality / Δpnl / top shifts`），讓 runtime guardrail 與 heartbeat drift artifact 對齊到同一個 collapse evidence，而不是只有報表層知道 sibling collapse。**Heartbeat #686 再修正 canonical drift interpretation**：高品質 `simulated_pyramid_win` recent pockets 若同時滿足正向 pnl / quality / 低 DD，不再因較弱的 legacy `spot_long_win_rate` 被誤標為 `distribution_pathology`；治理層現在會把這類視窗回歸為 `supported_extreme_trend`，避免用非 canonical compare target 重新污染 drift triage。**Heartbeat #687 再修補 TUW-threshold regression**：當 `avg_time_underwater` 只是略高於舊 0.45 cutoff，但 canonical `win/pnl/quality/drawdown` 仍明顯健康時，`recent_drift_report.py::_classify_window()` 會保留 `supported_extreme_trend`，避免 drift triage 因近閾值 TUW 假陰性再次抖動。下一步是針對 500-row pathology block 裡被反覆指向的 `feat_4h_dist_bb_lower / feat_4h_dist_swing_low / feat_4h_bb_pct_b` 做 source / feature / label root-cause fix，而不是再被 generic streak 敘事稀釋。

- [ ] strategy archetype layer：把策略從 `rule_baseline` / `xgboost` 升級成「抄底型 / 趨勢型 / 均值回歸型 / 4H濾網型」等決策語義層
- [~] maturity-aware UI：FeatureChart / Strategy Lab 明確顯示 **核心可用 / 研究中 / blocked** 三層成熟度，讓使用者知道哪些訊號能當主判斷、哪些只能輔助觀察  
  ↳ Heartbeat #647：`/api/features/coverage` 與 `FeatureChart` 已新增 `maturity_tier + score_usable` contract，legend / summary / composite score 已區分 core vs research vs blocked；Heartbeat #648 再把同一套 maturity summary 推進到 Dashboard 雷達與 AdviceCard。下一步收斂到 Dashboard 其他摘要卡與 Strategy Lab compare flow，避免首頁/實驗室又回退成只看數值不看成熟度

- [x] Web Model Leaderboard 視覺化（表格版已上線；後續可再補柱狀圖 + Fold 比較）
- [x] 市場分類回測（依進場 regime 顯示 Bull / Bear / Chop ROI、勝率、PF）
- [ ] 策略匯入/匯出（JSON 分享）
- [ ] 自動最佳化（Optuna / 網格搜尋）
- [x] 心跳閉環標準化：`strategy-decision-guide.md` + 六帽 + ORID + issue/roadmap/architecture 同步更新，並由 `HEARTBEAT.md` 明確定義為強制流程
- [x] canonical target 統一：`simulated_pyramid_win` 為主；`label_spot_long_win` 僅作 path-aware 比較；`sell_win` 僅作 legacy 相容
- [x] P0/P1 修復驅動：每次心跳至少產出 1 個可驗證 patch，不允許只產出失敗報告
- [~] 心跳 gate 自動化：`hb_parallel_runner.py` 已會把 `ic_diagnostics + drift_diagnostics + auto_propose` 寫入 `heartbeat_N_summary.json`，並在 fast heartbeat 自動執行 canonical auto-propose；Heartbeat #665 再補上治理細節：`auto_propose_fixes.py` 會優先比較**正式編號心跳**而非匿名 `fast` alias，避免 blocker 歷史被 ad-hoc summary 汙染；**Heartbeat #670 再補 issue-lifecycle recovery：當 current run 的 TW-IC / streak 已恢復時，auto-propose 必須 resolve 舊 blocker，而不是把上一輪告警殘留成新的假 P0；Heartbeat #672 再補 negative-pathology escalation：即使 TW-IC 已恢復，只要 recent canonical window 仍是 `distribution_pathology` + 負 quality，治理層也必須升級 `#H_AUTO_RECENT_PATHOLOGY`，不能只剩 regime-drift 這種較弱訊號；Heartbeat #673 再把 drift summary / runner stdout / auto-propose wording 同步升級成 `variance + frozen + compressed + null_heavy`，避免 heartbeat 再用過度粗糙的 feature-collapse 描述收斂錯方向；Heartbeat #689 再補 stale-regime-drift recovery：當 `TW-IC` 已回落到 `Global IC + 2` 以內時，`#H_AUTO_REGIME_DRIFT` 也必須自動 resolve，避免治理層殘留假開啟 blocker；Heartbeat #691 再把 `hb_predict_probe.py` 接進 fast heartbeat，讓 summary 持久化 `live_predictor_diagnostics`，並讓 auto-propose 可直接升級 `#H_AUTO_LIVE_DQ_PATHOLOGY`；Heartbeat #692 再讓 live probe 內建 `decision_quality_scope_diagnostics`，把 `entry_quality_label` / `regime_gate+entry_quality_label` / `regime_label+entry_quality_label` 的 lane comparison 一起 machine-check 化；Heartbeat #696 再補 **narrowed-lane escalation**：即使 broad calibration scope 本身健康，只要 `pathology_consensus.worst_pathology_scope` 已證明存在嚴重的 bull-only / narrow pathology lane，auto-propose 也必須直接升級 `#H_AUTO_LIVE_DQ_PATHOLOGY`，避免 heartbeat 自動治理還停留在 generic regime drift；Heartbeat #713 再補 **exact-live-lane toxicity surfacing**：auto-propose summary 現在必須直接寫出 `exact_live_lane=(rows/wr/q/dd/tuw/targets/true_negative_rows/final_gate)`，並在 exact lane 仍是 `ALLOW` 但 `canonical_true_negative_share` 偏高時標記 `exact_lane_status=toxic_allow_lane`，避免治理層只盯 spillover `bull|BLOCK` pocket，卻漏掉 current exact `bull+ALLOW+D` lane 本身也持續虧損。** 下一步是把 patch / verify / doc sync / next gate 的缺欄也 machine-check 化
- [~] blocker 升級機制落地：Heartbeat #659 已讓 TW-IC 連續低於 14/30 時自動觸發 `#H_AUTO_TW_DRIFT`；Heartbeat #661 再把 distribution-aware recent-window / calibration drift 報表直接接進該 issue，已能指出 `constant_target + chop concentration` 的污染視窗；Heartbeat #664 進一步讓 **training-side TW weighting** 也實際消費同一份 guardrail；Heartbeat #665 則修正 `#H_AUTO_TW_DRIFT` 的歷史對照口徑，讓 escalation 以 `#665 -> #664 -> #663` 這種可追蹤鏈條呈現；**Heartbeat #670 再修掉 recovery path 缺失，讓 `#H_AUTO_TW_DRIFT` / `#H_AUTO_STREAK` 在 current run recovered 時自動解除；Heartbeat #672 再把真正的 recent negative pathology 獨立升級成 `#H_AUTO_RECENT_PATHOLOGY`；Heartbeat #673 再補上 frozen-vs-compressed drift contract，讓 blocker 能區分「真 freeze」與「只是振幅壓縮」。** 下一步是把 blocker 收斂到 recent distribution pathology 的真根因，而不是繼續被 stale 或過弱的治理訊號綁架
- [x] regime-aware IC null-bucket hygiene：`regime_aware_ic.py` 對 `feat_mind` 缺值 row 改用 `features_normalized.regime_label` fallback，並把 `regime_meta/regime_counts` 寫入輸出，避免 75%+ canonical rows 被誤判成 neutral 造成錯誤決策
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
- [x] 4h canonical label backfill hygiene：`save_labels_to_db()` 現在會補齊既有 row 中缺失的 `simulated_pyramid_*` / `label_spot_long_*` 欄位，不再把已有 `future_return_pct` 的 legacy rows 留成半遷移狀態；heartbeat 240m target_rows 因此回到真實量級
- [x] label horizon freshness root-cause gating：`hb_collect.py` / `hb_parallel_runner.py` 現在會把 horizon 分成 `expected_horizon_lag` / `raw_gap_blocked` / `inactive_horizon`，避免把 720m legacy rows 或 upstream raw gap 誤報成 label pipeline 本身故障
- [x] Recent raw continuity repair lane：`data_ingestion/collector.py` 現在會在 live collect 前以 Binance 4h closed klines 回補 recent raw gaps，`hb_collect.py` 也會把 repaired raw timestamps 補進 `features_normalized`，避免 raw 修回來卻卡在 feature/label 斷層
- [x] Sub-4h raw continuity bridge lane：Heartbeat #629 已補上 **1h public-kline repair + hourly interpolated bridge fallback**，把 240m freshness 從 `raw_gap_blocked`（latest raw gap 6.42h）拉回 `expected_horizon_lag`（latest raw gap 1.42h），不再只靠下一根 4h candle 才能恢復 labels
- [x] Raw continuity recovery telemetry gate：`repair_recent_raw_continuity()` / `hb_collect.py` / `hb_parallel_runner.py` 現在會把 `coarse/fine/bridge_inserted` 與 `bridge_fallback_streak` 寫進 heartbeat summary，後續已可明確監控 **bridge fallback 是否連續多輪被迫介入**。若 streak 再升高，直接升級成 collector/service continuity 根因修復，而不是持續依賴 bridge workaround
- [x] SQLite heartbeat writer resilience：Heartbeat #641 已把 `database.models.init_db()` 升級為 SQLite-safe runtime（`timeout=30s`、`check_same_thread=False`、`journal_mode=WAL`、`busy_timeout=30000`），修掉 `hb_collect.py` 與常駐 API 共享 DB 時的 `database is locked` 假失敗，讓 fast heartbeat pre-collect 重新穩定通過
- [x] Sparse-source archive-window denominator hygiene：`feature_history_policy.py` 現在以 `raw_events` 的實際 snapshot minute buckets 對齊 recent-window coverage，排除 continuity bridge / non-snapshot feature rows，避免 Web/Fang/Scales/Nest 因 1h continuity bridge 被誤判成 partial source coverage
- [x] Canonical 4H feature parity + freshness：`model/train.py` / `model/predictor.py` / `scripts/full_ic.py` 已統一納入 `feat_4h_bias200` / `feat_4h_dist_bb_lower` / `feat_4h_vol_ratio`，predictor 也改成使用 training-style 4H asof alignment；Heartbeat #633 已用 `backfill_4h_distance.py` 將 recent 4H rows 補回最新 timestamp，避免 train / infer / diagnostics 再使用不同 4H 語義。**Heartbeat #684 再補齊 `feature_engine/preprocessor.py::recompute_all_features()` 的 4H/regime projection 寫回，並回填 recent NULL `feat_4h_*` rows，避免 recompute/backfill 流程把 canonical recent window 留成半同步狀態。**
- [x] Predictor probe reproducibility：`scripts/hb_predict_probe.py` 成為 canonical inference verification 腳本，固定輸出 `target_col / used_model / 4H feature non-null count / 4H lag non-null count`，避免 heartbeat 驗證再依賴漂移的臨時 probe 檔名
- [x] Predictor probe self-contained execution：Heartbeat #635 已讓 `scripts/hb_predict_probe.py` 自動注入 project root `sys.path`，`python scripts/hb_predict_probe.py` 在 repo 根目錄即可直接執行，不再要求人工補 `PYTHONPATH=.`
- [x] Live predictor baseline decision contract：Heartbeat #637 已讓 `model/predictor.py`、`scripts/hb_predict_probe.py`、`/predict/confidence` 同步輸出 `regime_gate / entry_quality / entry_quality_label / allowed_layers`，live path 不再只剩 signal/confidence；Heartbeat #650 再把 Dashboard `ConfidenceIndicator` 升級成直接消費這套 canonical decision-quality contract。
- [x] Leaderboard canonical decision-quality contract：Heartbeat #642 已讓 `backtesting/model_leaderboard.py` 在實際 trade entry timestamps 上聚合 `simulated_pyramid_win / quality / drawdown_penalty / time_underwater`，並經由 `/api/models/leaderboard` 輸出 `avg_decision_quality_score + avg_expected_*` 欄位；Heartbeat #643 再把 Strategy Lab 模型排行榜前端直接顯示這批 canonical quality fields，ranking contract 不再只存在 backend / payload。
- [x] Leaderboard 4H feature parity：Heartbeat #642 已讓 `load_model_leaderboard_frame()` 補齊 `feat_4h_bias200 / feat_4h_dist_bb_lower / feat_4h_vol_ratio`，讓 leaderboard feature frame 與 canonical train/predict path 對齊。
- [x] Train warning / logging hygiene：`model/train.py` cross-feature 建構改為單次 concat，移除 pandas fragmentation warning；`TW-IC (core)` log 也已修正為真實 `tw_ic_summary`，heartbeat runtime 不再被假 warning / 假 log 汙染
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
