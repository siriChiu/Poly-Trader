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

**Sparse-source contract（Heartbeat #614）**：對 Claw / Fang / Fin / Web / Scales / Nest 這類低頻/稀疏來源，特徵計算只允許讀取 **latest raw row**；若最新來源缺值，feature 必須保持 `NULL/None`。禁止用舊的非空值 forward-carry 到新 row，也禁止把 fetch failure 寫成 `0.0` 假中性值。

**Historical decontamination（Heartbeat #615）**：舊資料若出現「當前 raw row 已缺值，但 features row 仍殘留 sparse-source 值」或 sentinel fallback（如 Claw `ratio=1,total=0`、Nest `0.5`、Fin `0/0`），必須透過 `scripts/cleanup_sparse_source_history.py` 清回 `NULL`，避免 FeatureChart / coverage / 重算流程讀到假歷史訊號。

**Source-history blocker contract（Heartbeat #616）**：對 sparse sources，coverage/report/API/UI 不只回報 `coverage/distinct/quality_flag`，還必須同步回傳 `history_class / backfill_status / backfill_blocker / recommended_action`。若缺口根因是 `archive_required` / `snapshot_only` / `short_window_public_api`，前端應把它視為 source-level blocker，而不是可用前端美化或 carry-forward 修好的歷史線問題。

**Shared policy contract（Heartbeat #617）**：source-history policy 不可再在 report/API/heartbeat runner 各自複製一份。`feature_engine/feature_history_policy.py` 現在是單一真相來源（single source of truth），`scripts/feature_coverage_report.py`、`/api/features/coverage`、`hb_parallel_runner.py` 都必須共用它，避免 blocker metadata drift 導致 UI 與 heartbeat 對同一 sparse source 給出不同治理結論。

**Archive-window coverage contract（Heartbeat #620 / #632c）**：對 sparse sources，除了整體 `coverage_pct` 與 `raw_snapshot_events`，還必須同步輸出 `archive_window_rows / archive_window_non_null / archive_window_coverage_pct`（自第一筆 snapshot archive 起點以來的 recent-window coverage）。這個 recent-window denominator 不可再用「所有 feature rows since archive start」粗算；必須以 `raw_events` 的實際 snapshot timestamp buckets 對齊，只計算有對應 source snapshot 的 feature rows，排除 continuity bridge / non-snapshot rows。FeatureChart、coverage report、heartbeat runner 都必須顯示同一口徑，避免把歷史稀釋或 continuity workaround 誤判成 active source partial coverage。

**Source auth/fetch blocker contract（Heartbeat #622）**：若 sparse source 最新 snapshot `status != ok`（尤其 `auth_missing`），coverage policy 必須把 quality 從 generic `source_history_gap` 升級成 `source_auth_blocked` / `source_fetch_error`，並把 `raw_snapshot_latest_status/message` 同步給 API、markdown report、FeatureChart。這批欄位的用途不是附註，而是要讓 UI 與 heartbeat 明確知道「現在 live fetch 壞掉」優先於「歷史 coverage 還不夠」。

**Warning-safe indicator math contract（Heartbeat #626）**：feature layer 的技術指標 / 4H 指標計算不得在 flat price、zero-volume 或 zero-width band 視窗下產生 `divide by zero` / `invalid value` RuntimeWarning。所有分母可能為 0 的計算都必須使用 warning-safe divide（例如 `np.divide(..., where=...)`），確保 fast heartbeat stderr 只保留真實 blocker，而不是數值邊界噪音。

**Label horizon freshness contract（Heartbeat #627）**：heartbeat 維護的 active horizons 目前只有 **240m 與 1440m**。`scripts/hb_collect.py::summarize_label_horizons()` 與 `hb_parallel_runner.py` summary 必須把 label freshness 分成：
- `expected_horizon_lag`：符合 lookahead 預期
- `raw_gap_blocked`：label 落後主因是 target 之後的 raw timeline 出現超過 horizon 容許值的斷層
- `inactive_horizon`：DB 中保留的 legacy horizon（如 720m），不得再當 active heartbeat blocker

**Canonical label backfill contract（Heartbeat #627）**：`save_labels_to_db()` 不得只更新 `future_return_pct IS NULL` 的舊 rows。若既有 label row 已有 `future_return_pct`，但 `simulated_pyramid_*` / `label_spot_long_*` canonical 欄位仍為 `NULL`，heartbeat label generation 必須原地回填，避免 heartbeat 對 4h/24h freshness 做出假陰性判斷。

**Recent raw continuity repair contract（Heartbeat #628）**：當 heartbeat 偵測到 recent raw timeline 有多小時斷層時，`data_ingestion/collector.py::repair_recent_raw_continuity()` 必須先用 public Binance **closed 4h klines** 回補缺失 raw rows，再 append live snapshot。這條 lane 的目的不是重建完整 tick history，而是先把 4h canonical label 所需的 recent raw continuity 補回來，避免 `raw_gap_blocked` 永遠只能靠下一筆 live row 慢慢前進。

**Sub-4h continuity bridge contract（Heartbeat #629）**：若 4h repair 之後 240m label path 仍會因最近幾小時缺口被卡住，`repair_recent_raw_continuity()` 還必須再跑 **1h public-kline repair**；若 public kline 仍補不到 gap，則允許對 `max_gap_hours<=12h` 的 recent raw gap 生成 **hourly interpolated bridge rows** 作為 temporary continuity bridge。這個 bridge 只用來讓 canonical 240m label / freshness pipeline 繼續閉環，不是歷史價格真值替代；若它連續多輪被觸發，下一輪必須升級成 collector/service continuity root-cause investigation。

**Continuity telemetry contract（Heartbeat #631b）**：`repair_recent_raw_continuity()` 不可再只回傳單一 inserted count。Heartbeat collect / summary 必須同步落地 `coarse_inserted / fine_inserted / bridge_inserted / used_bridge / bridge_fallback_streak`，讓 runner、ISSUES、ROADMAP 能分辨「raw continuity 真健康」與「只是靠 interpolated bridge 暫時撐住」，避免 workaround 再次變成隱性假進度。

**SQLite writer resilience contract（Heartbeat #641）**：heartbeat collect / label pipeline 需要和常駐 API 共享同一個 SQLite DB，因此 `database.models.init_db()` 對 SQLite 連線必須統一使用 `timeout>=30s`、`check_same_thread=False`，並在 connect 時套用 `PRAGMA journal_mode=WAL`、`PRAGMA synchronous=NORMAL`、`PRAGMA busy_timeout=30000`、`PRAGMA foreign_keys=ON`。若缺少這層 writer-resilience，`hb_collect.py` 可能在 `save_labels_to_db()` commit 時被 API 讀流量卡成 `database is locked`，讓 heartbeat 假失敗並污染 raw/features/labels freshness 判讀。

**Missing feature-row backfill contract（Heartbeat #628）**：raw continuity repair 之後，`feature_engine/preprocessor.py::backfill_missing_feature_rows()` 必須把 repaired raw timestamps 補進 `features_normalized`。否則 raw rows 即使回來了，label generation 仍會因 feature timestamps 缺失而無法消化 repaired window，形成新的假進度。

**Fast heartbeat contract（Heartbeat #617）**：`python scripts/hb_parallel_runner.py --fast` 必須可直接在 cron 執行，不依賴額外 `--hb` 參數；fast summary 仍需包含 DB counts、canonical IC 腳本結果與 `source_blockers` 摘要，確保快檢查模式不是「只剩數字」的半閉環。

**Regime-aware IC fallback contract（Heartbeat #630）**：`scripts/regime_aware_ic.py` 必須以 `feat_mind` tertiles 作為首選 regime split，但當 canonical rows 的 `feat_mind` 缺值時，不可直接把 row 丟進 `neutral`。必須回退到 `features_normalized.regime_label`，並把 `regime_meta / regime_counts / fallback_rows` 寫入輸出 JSON，否則 heartbeat 會把 analysis artifact 誤判成市場 regime 崩壞，污染 P0/P1 優先級。

### 3. 標籤層
根據未來報酬建立多 horizon 標籤，並以 `simulated_pyramid_win` 作為 canonical 主 KPI；`label_spot_long_win` 僅保留 path-aware 比較診斷；`sell_win` 僅保留 legacy 相容欄位。

**Canonical consumer rule（Heartbeat #615）**：Leaderboard / target-comparison 類資料載入應優先以 `simulated_pyramid_win` 作為 row gate；`label_spot_long_win` 僅保留比較欄位，不得再作為 canonical dataset 的必要條件。

**Decision-quality label contract（Heartbeat #639）**：canonical labels 不得只剩 `simulated_pyramid_win + simulated_pyramid_pnl + simulated_pyramid_quality` 的半成品語義。`labels` 現在還必須持久化：
- `simulated_pyramid_drawdown_penalty`
- `simulated_pyramid_time_underwater`

這兩個欄位由 labeling pipeline 在生成金字塔路徑標籤時一併計算，heartbeat 也必須驗證它們在 active horizons（240m / 1440m）上有非空覆蓋，避免「說要低回撤 / 低深套，DB 卻沒有顯式欄位」的假對齊。

### 4. 模型層
使用特徵做交易決策與現貨 long 加碼判斷，允許 abstain 與 regime-aware weights。

**Decision-quality contract（2026-04-10 strategy review）**：模型層不可只回答「會不會贏」。canonical `simulated_pyramid_win` 已完成目標對齊，但下一階段必須把模型輸出升級成 **交易品質評分**，至少能區分：
- 勝率/是否獲利
- pnl quality（賺得是否夠乾淨）
- drawdown penalty（中間承受的回撤）
- time underwater（解套所需時間）

這樣模型學到的就不是單純 binary 結果，而是更貼近使用者真實偏好的「高勝率、低回撤、低深套」交易。

**Two-stage decision contract（2026-04-10 strategy review）**：正式決策流程應拆成兩層，而不是單段式 entry rule：
1. **4H regime gate**：先判斷目前市場背景是否允許 spot-long 金字塔（ALLOW / CAUTION / BLOCK）
2. **short-term entry-quality score**：只在 gate 允許時，才用短線 technical / microstructure 特徵決定進場品質與層數

這個 contract 的目的，是避免在錯的高時間框架背景裡，讓看似漂亮的短線訊號繼續造成深套或高回撤。

**Confidence-based sizing contract（2026-04-10 strategy review）**：模型輸出除了進/不進，還必須逐步演化成 `size / layer_count` 決策依據。低品質訊號只允許首層，強訊號才允許完整 20/30/50 金字塔；倉位本身就是回撤控制器，不可再完全與信號品質脫鉤。

**Live predictor decision-profile contract（Heartbeat #640）**：`model/predictor.py::predict()`、`scripts/hb_predict_probe.py`、`/predict/confidence` 必須共同輸出 `phase16_baseline_v2` contract，而不是只剩 signal/confidence：
- `regime_gate`（ALLOW / CAUTION / BLOCK）
- `entry_quality`
- `entry_quality_label`
- `allowed_layers`
- `decision_quality_calibration_scope`
- `decision_quality_sample_size`
- `expected_win_rate`
- `expected_pyramid_pnl`
- `expected_pyramid_quality`
- `expected_drawdown_penalty`
- `expected_time_underwater`
- `decision_quality_score`
- `decision_quality_label`
- `decision_profile_version`

其中 quality-related 欄位目前不是直接多目標模型輸出，而是用 canonical **1440m historical labels** 按 `regime_gate + entry_quality_label`（不足時 fallback 到 `regime_gate / entry_quality_label / global`）做 calibrated expectation layer。這層的目的，是讓 live path 直接說出「這筆 setup 在歷史上通常贏多少、回撤多深、會不會久套」，把 canonical quality semantics 從 DB / leaderboard 往前推到即時 API。下一階段若升級到完整 decision-quality target，必須沿用這個 contract 擴展，而不是另起一套平行語義。

**Leaderboard objective contract（Heartbeat #638 / #639 / #642）**：`backtesting/model_leaderboard.py` 與 `/api/models/leaderboard` 不可再只用 ROI / overfit gap / volatility 當主排序語義。當前 composite score 與 API payload 至少要同步輸出以下 decision-aware components：
- `avg_entry_quality`
- `avg_allowed_layers`
- `avg_trade_quality`
- `avg_decision_quality_score`
- `avg_expected_win_rate`
- `avg_expected_pyramid_quality`
- `avg_expected_drawdown_penalty`
- `avg_expected_time_underwater`
- `regime_stability_score`
- `max_drawdown_score`
- `profit_factor_score`
- `overfit_penalty`

Heartbeat #642 起，leaderboard 不只「能讀到」 canonical labels 中的 `simulated_pyramid_drawdown_penalty` / `simulated_pyramid_time_underwater`；它還必須在每個 fold 的**實際 trade entry timestamps** 上聚合這些欄位，計算與 predictor 對齊的 `avg_decision_quality_score`，並把這組欄位序列化到 API payload。Heartbeat #643 已把 Strategy Lab 模型排行榜前端摘要同步切到這組 canonical decision-quality semantics；Heartbeat #644 再把 `/api/strategies/leaderboard`、`/api/strategies/{name}` 與 Strategy Lab 的**策略排行榜主表**一起升級為同一組 `avg_decision_quality_score + avg_expected_*` contract。剩餘缺口不再是 leaderboard/detail path 漏接，而是 active strategy summary 與更深的 strategy comparison 文案仍需升級到同一語義。

**Core-vs-research signal contract（2026-04-10 strategy review）**：主模型與主 UI 必須區分兩類信號：
- **核心信號**：4H 結構 + 高 coverage technical（可直接參與主決策）
- **研究信號**：sparse-source / 低 coverage / forward-archive 中的特徵（只可作 overlay、bonus、veto 或研究用途）

若不分層，系統會把成熟度不足的 alpha source 誤混入主決策，造成假信心。

**Model feature parity contract（Heartbeat #633 / #642）**：`model/train.py`、`model/predictor.py`、`scripts/full_ic.py`、`load_model_leaderboard_frame()` 必須共用同一個 canonical base feature semantics。當 DB / preprocessor 新增可訓練特徵（例如 `feat_4h_bias200`、`feat_4h_dist_bb_lower`、`feat_4h_vol_ratio`）時，不允許只更新 schema 或 coverage/UI；訓練、推論、IC diagnostics、leaderboard frame 必須同輪一起升級，否則 heartbeat 會落入「資料已存在但模型、診斷、ranking 其中一條路仍忽略」的假進度。

**Sparse 4H inference alignment contract（Heartbeat #633）**：predictor 不可直接使用 latest dense row 上的 raw 4H 欄位，因為 4H features 在 dense rows 上可能是 sparse/NULL。`load_latest_features()` 必須套用與 training 相同的 asof alignment（目前沿用 `model.train._align_sparse_4h_features()`）來生成 base + lag 4H features；若 recent 4H rows 在 DB 已 stale，應先 backfill 4H history，而不是讓推論默默退回 0/NULL。

**Predictor probe contract（Heartbeat #634 / #635）**：repo 內必須保留可直接重跑的 live inference probe（目前為 `scripts/hb_predict_probe.py`），固定輸出 `target_col / used_model / canonical 4H feature non-null count / 4H lag non-null count`。這個 probe 必須能在 repo 根目錄直接用 `python scripts/hb_predict_probe.py` 執行，不得要求 heartbeat 額外手補 `PYTHONPATH=.`；否則文件會宣稱可重跑、實際上卻只在特定 shell 前提下可用。Heartbeat 不可再引用一次性臨時 probe 檔名作為唯一驗證證據。

**Training warning/logging hygiene contract（Heartbeat #634）**：`model/train.py` 的 cross-feature engineering 不可再用大量逐欄 `frame.insert` 方式製造 pandas fragmentation warnings；training stderr 應盡量只保留真實失敗訊號。同時 recent-vs-global IC log 必須分別輸出真實 `tw_ic_summary` 與 `core_ic_summary`，避免 heartbeat 被假觀測污染。

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

